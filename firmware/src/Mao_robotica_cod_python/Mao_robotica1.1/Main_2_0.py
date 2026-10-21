import cv2
import mediapipe as mp
import math
import mao3d as mao


# ============================================================
# CÂMERA
# ============================================================

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


# ============================================================
# MEDIAPIPE
# ============================================================

hands = mp.solutions.hands

Hands = hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

mpDraw = mp.solutions.drawing_utils


# ============================================================
# MAPA DOS SERVOS
# ============================================================

# Mantive exatamente a organização que você estava usando
SERVO_POLEGAR = 1
SERVO_INDICADOR = 2

# Médio e anelar estão trocados propositalmente
SERVO_MEDIO = 4
SERVO_ANELAR = 3

SERVO_MINIMO = 5


# ============================================================
# JANELA DE CONFIGURAÇÃO
# ============================================================

cv2.namedWindow("Configuracao", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Configuracao", 500, 350)


# Valores iniciais
cv2.createTrackbar(
    "Polegar MAX",
    "Configuracao",
    150,
    180,
    lambda x: None
)

cv2.createTrackbar(
    "Indicador MAX",
    "Configuracao",
    180,
    180,
    lambda x: None
)

cv2.createTrackbar(
    "Medio MAX",
    "Configuracao",
    140,
    180,
    lambda x: None
)

cv2.createTrackbar(
    "Anelar MAX",
    "Configuracao",
    140,
    180,
    lambda x: None
)

cv2.createTrackbar(
    "Minimo MAX",
    "Configuracao",
    140,
    180,
    lambda x: None
)


# Suavização do movimento
cv2.createTrackbar(
    "Suavizacao",
    "Configuracao",
    70,
    95,
    lambda x: None
)


# ============================================================
# ÂNGULOS ATUAIS DOS SERVOS
# ============================================================

angulosAtuais = {
    SERVO_POLEGAR: 0,
    SERVO_INDICADOR: 0,
    SERVO_MEDIO: 0,
    SERVO_ANELAR: 0,
    SERVO_MINIMO: 0
}


# Último ângulo enviado para ESP32
ultimoEnviado = {
    SERVO_POLEGAR: -100,
    SERVO_INDICADOR: -100,
    SERVO_MEDIO: -100,
    SERVO_ANELAR: -100,
    SERVO_MINIMO: -100
}


# ============================================================
# FUNÇÃO PARA CALCULAR ÂNGULO ENTRE 3 PONTOS
# ============================================================

def calcular_angulo(p1, p2, p3):

    """
    Calcula o ângulo:

            p1
             \
              p2
             /
            p3

    p2 é o ponto central.
    """

    vetor1 = (
        p1[0] - p2[0],
        p1[1] - p2[1]
    )

    vetor2 = (
        p3[0] - p2[0],
        p3[1] - p2[1]
    )

    produto = (
        vetor1[0] * vetor2[0]
        +
        vetor1[1] * vetor2[1]
    )

    modulo1 = math.sqrt(
        vetor1[0] ** 2 +
        vetor1[1] ** 2
    )

    modulo2 = math.sqrt(
        vetor2[0] ** 2 +
        vetor2[1] ** 2
    )

    if modulo1 == 0 or modulo2 == 0:
        return 180

    cosAngulo = produto / (modulo1 * modulo2)

    # Evita erro numérico
    cosAngulo = max(-1, min(1, cosAngulo))

    angulo = math.degrees(
        math.acos(cosAngulo)
    )

    return angulo


# ============================================================
# CONVERTE CURVATURA DO DEDO PARA 0-100%
# ============================================================

def calcular_fechamento(angulo):

    """
    Dedo esticado:
        aproximadamente 170 - 180 graus

    Dedo fechado:
        aproximadamente 50 - 80 graus

    Resultado:

        0.0 = totalmente aberto
        1.0 = totalmente fechado
    """

    ANGULO_ABERTO = 175
    ANGULO_FECHADO = 65

    fechamento = (
        ANGULO_ABERTO - angulo
    ) / (
        ANGULO_ABERTO - ANGULO_FECHADO
    )

    fechamento = max(
        0.0,
        min(1.0, fechamento)
    )

    return fechamento


# ============================================================
# CONTROLAR SERVO PROPORCIONALMENTE
# ============================================================

def controlar_servo(
    servo,
    fechamento,
    anguloMaximo,
    suavizacao
):

    global angulosAtuais
    global ultimoEnviado

    # ==========================================
    # TRANSFORMA 0-100% EM ÂNGULO DO SERVO
    # ==========================================

    anguloDesejado = (
        fechamento * anguloMaximo
    )


    # ==========================================
    # SUAVIZAÇÃO
    # ==========================================

    # Slider:
    #
    # 0 = quase sem suavização
    # 95 = movimento bem suave

    alpha = 1 - (suavizacao / 100)

    # Evita ficar completamente travado
    alpha = max(0.05, alpha)


    novoAngulo = (
        angulosAtuais[servo]
        +
        alpha
        *
        (
            anguloDesejado
            -
            angulosAtuais[servo]
        )
    )


    angulosAtuais[servo] = novoAngulo


    anguloInteiro = int(novoAngulo)


    # ==========================================
    # EVITA MANDAR COMANDOS DESNECESSÁRIOS
    # ==========================================

    # Só envia se mudar pelo menos 2 graus

    if abs(
        anguloInteiro
        -
        ultimoEnviado[servo]
    ) >= 2:

        mao.rotateServo(
            servo,
            anguloInteiro
        )

        ultimoEnviado[servo] = anguloInteiro


# ============================================================
# LOOP PRINCIPAL
# ============================================================

while True:

    success, img = cap.read()

    if not success:
        print("Erro ao receber imagem da camera")
        continue


    frameRGB = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2RGB
    )


    results = Hands.process(
        frameRGB
    )


    handPoints = (
        results.multi_hand_landmarks
    )


    h, w, _ = img.shape


    # ========================================================
    # LÊ CONFIGURAÇÕES DOS SLIDERS
    # ========================================================

    maxPolegar = cv2.getTrackbarPos(
        "Polegar MAX",
        "Configuracao"
    )

    maxIndicador = cv2.getTrackbarPos(
        "Indicador MAX",
        "Configuracao"
    )

    maxMedio = cv2.getTrackbarPos(
        "Medio MAX",
        "Configuracao"
    )

    maxAnelar = cv2.getTrackbarPos(
        "Anelar MAX",
        "Configuracao"
    )

    maxMinimo = cv2.getTrackbarPos(
        "Minimo MAX",
        "Configuracao"
    )

    suavizacao = cv2.getTrackbarPos(
        "Suavizacao",
        "Configuracao"
    )


    # ========================================================
    # MÃO DETECTADA
    # ========================================================

    if handPoints:

        for points in handPoints:

            mpDraw.draw_landmarks(
                img,
                points,
                hands.HAND_CONNECTIONS
            )


            pontos = []


            # =================================================
            # CONVERTE LANDMARKS EM PIXELS
            # =================================================

            for id, cord in enumerate(
                points.landmark
            ):

                cx = int(cord.x * w)
                cy = int(cord.y * h)

                pontos.append(
                    (cx, cy)
                )


            if len(pontos) == 21:


                # =================================================
                # POLEGAR
                #
                # pontos:
                #
                # 2 = MCP
                # 3 = IP
                # 4 = ponta
                # =================================================

                angPolegar = calcular_angulo(
                    pontos[2],
                    pontos[3],
                    pontos[4]
                )


                # =================================================
                # INDICADOR
                #
                # 5 = MCP
                # 6 = PIP
                # 8 = ponta
                # =================================================

                angIndicador = calcular_angulo(
                    pontos[5],
                    pontos[6],
                    pontos[8]
                )


                # =================================================
                # MÉDIO
                # =================================================

                angMedio = calcular_angulo(
                    pontos[9],
                    pontos[10],
                    pontos[12]
                )


                # =================================================
                # ANELAR
                # =================================================

                angAnelar = calcular_angulo(
                    pontos[13],
                    pontos[14],
                    pontos[16]
                )


                # =================================================
                # MÍNIMO
                # =================================================

                angMinimo = calcular_angulo(
                    pontos[17],
                    pontos[18],
                    pontos[20]
                )


                # =================================================
                # CONVERTE PARA % DE FECHAMENTO
                # =================================================

                fecharPolegar = calcular_fechamento(
                    angPolegar
                )

                fecharIndicador = calcular_fechamento(
                    angIndicador
                )

                fecharMedio = calcular_fechamento(
                    angMedio
                )

                fecharAnelar = calcular_fechamento(
                    angAnelar
                )

                fecharMinimo = calcular_fechamento(
                    angMinimo
                )


                # =================================================
                # MOVE SERVOS
                # =================================================

                controlar_servo(
                    SERVO_POLEGAR,
                    fecharPolegar,
                    maxPolegar,
                    suavizacao
                )


                controlar_servo(
                    SERVO_INDICADOR,
                    fecharIndicador,
                    maxIndicador,
                    suavizacao
                )


                controlar_servo(
                    SERVO_MEDIO,
                    fecharMedio,
                    maxMedio,
                    suavizacao
                )


                controlar_servo(
                    SERVO_ANELAR,
                    fecharAnelar,
                    maxAnelar,
                    suavizacao
                )


                controlar_servo(
                    SERVO_MINIMO,
                    fecharMinimo,
                    maxMinimo,
                    suavizacao
                )


                # =================================================
                # MOSTRA INFORMAÇÕES NA TELA
                # =================================================

                cv2.putText(
                    img,
                    f"Polegar: {int(fecharPolegar * 100)}% | {int(angulosAtuais[SERVO_POLEGAR])} graus",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    img,
                    f"Indicador: {int(fecharIndicador * 100)}% | {int(angulosAtuais[SERVO_INDICADOR])} graus",
                    (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    img,
                    f"Medio: {int(fecharMedio * 100)}% | {int(angulosAtuais[SERVO_MEDIO])} graus",
                    (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    img,
                    f"Anelar: {int(fecharAnelar * 100)}% | {int(angulosAtuais[SERVO_ANELAR])} graus",
                    (10, 105),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )


                cv2.putText(
                    img,
                    f"Minimo: {int(fecharMinimo * 100)}% | {int(angulosAtuais[SERVO_MINIMO])} graus",
                    (10, 130),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2
                )


    # ========================================================
    # EXIBIÇÃO
    # ========================================================

    cv2.imshow(
        "Controle Mao Robotica",
        img
    )


    tecla = cv2.waitKey(1) & 0xFF


    # ESC fecha programa
    if tecla == 27:
        break


# ============================================================
# FINALIZAÇÃO
# ============================================================

Hands.close()

cap.release()

mao.fechar_porta()

cv2.destroyAllWindows()