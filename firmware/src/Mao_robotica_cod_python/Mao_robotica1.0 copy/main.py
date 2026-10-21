import cv2
import mediapipe as mp
import servo_braco3d as mao

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

mpHands = mp.solutions.hands
hands = mpHands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

draw = mp.solutions.drawing_utils

estadoAnterior = {i: None for i in range(1, 6)}


def dedo(servo, estado):

    if estadoAnterior[servo] != estado:

        mao.abrir_fechar(servo, estado)

        estadoAnterior[servo] = estado


while True:

    ok, img = cap.read()

    if not ok:
        continue

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    resultado = hands.process(rgb)

    if resultado.multi_hand_landmarks:

        pontosMao = resultado.multi_hand_landmarks[0]

        draw.draw_landmarks(
            img,
            pontosMao,
            mpHands.HAND_CONNECTIONS
        )

        h, w, _ = img.shape

        pontos = [
            (
                int(p.x * w),
                int(p.y * h)
            )
            for p in pontosMao.landmark
        ]

        # Distâncias dos dedos
        distPolegar = abs(pontos[17][0] - pontos[4][0])

        distancias = [
            pontos[5][1] - pontos[8][1],    # Indicador
            pontos[9][1] - pontos[12][1],  # Médio
            pontos[13][1] - pontos[16][1], # Anelar
            pontos[17][1] - pontos[20][1]  # Mínimo
        ]

        # Polegar
        dedo(1, distPolegar >= 80)

        # Outros dedos
        dedo(2, distancias[0] >= 1)  # Indicador

        dedo(4, distancias[1] >= 1)  # Médio

        dedo(3, distancias[2] >= 1)  # Anelar

        dedo(5, distancias[3] >= 1)  # Mínimo

    cv2.imshow("Mao Robotica", img)

    if cv2.waitKey(1) & 0xFF == 27:
        break


hands.close()
cap.release()
cv2.destroyAllWindows()