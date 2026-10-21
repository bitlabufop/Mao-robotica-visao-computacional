import serial
import time

esp = serial.Serial("COM3", 115200)
time.sleep(2)

# ==========================================
# CONFIGURAÇÃO DOS ÂNGULOS DE CADA DEDO
# Altere somente estes valores
# ==========================================

ANGULOS_MAX = {
    1: 80,   # Polegar
    2: 130,   # Indicador
    3: 140,   # Anelar
    4: 160,   # Médio
    5: 120    # Mínimo
}

ANGULO_ABERTO = 0


def rotateServo(servo, angulo):
    angulo = max(0, min(ANGULOS_MAX[servo], angulo))
    esp.write(f"{servo},{angulo}\n".encode())


def abrir_fechar(servo, estado):
    # estado = 1 -> aberto
    # estado = 0 -> fechado

    angulo = ANGULO_ABERTO if estado else ANGULOS_MAX[servo]

    rotateServo(servo, angulo)


def testeTodos():

    # Abre todos
    for servo in range(1, 6):
        rotateServo(servo, ANGULO_ABERTO)

    time.sleep(1)

    # Testa cada dedo
    for servo in range(1, 6):

        rotateServo(servo, ANGULOS_MAX[servo])
        time.sleep(1)

        rotateServo(servo, ANGULO_ABERTO)
        time.sleep(1)