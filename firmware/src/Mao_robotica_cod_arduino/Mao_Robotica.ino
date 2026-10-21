#include <ESP32Servo.h>

Servo servo1;
Servo servo2;
Servo servo3;
Servo servo4;
Servo servo5;

#define SERVO1_PIN 3
#define SERVO2_PIN 4
#define SERVO3_PIN 5
#define SERVO4_PIN 6
#define SERVO5_PIN 7

void setup() {
  Serial.begin(115200);

  // Frequência típica de servo
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo3.setPeriodHertz(50);
  servo4.setPeriodHertz(50);
  servo5.setPeriodHertz(50);

  servo1.attach(SERVO1_PIN, 500, 2500);
  servo2.attach(SERVO2_PIN, 500, 2500);
  servo3.attach(SERVO3_PIN, 500, 2500);
  servo4.attach(SERVO4_PIN, 500, 2500);
  servo5.attach(SERVO5_PIN, 500, 2500);

  // Posição inicial
  servo1.write(0);
  servo2.write(0);
  servo3.write(0);
  servo4.write(0);
  servo5.write(0);
}

void loop() {

  if (Serial.available()) {

    String comando = Serial.readStringUntil('\n');

    int separador = comando.indexOf(',');

    if (separador > 0) {

      int servo = comando.substring(0, separador).toInt();
      int angulo = comando.substring(separador + 1).toInt();

      angulo = constrain(angulo, 0, 180);

      switch (servo) {

        case 1:
          servo1.write(angulo);
          break;

        case 2:
          servo2.write(angulo);
          break;

        case 3:
          servo3.write(angulo);
          break;

        case 4:
          servo4.write(angulo);
          break;

        case 5:
          servo5.write(angulo);
          break;
      }
    }
  }
}