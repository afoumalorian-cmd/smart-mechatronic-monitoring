// L298N channel A:
// Arduino D8 -> IN1
// Arduino D9 -> IN2
// ENA jumper installed: no PWM speed control.
//
// Logic supply:
// Arduino 5V -> driver +5V, Arduino GND -> driver GND.
// Driver 5V regulator jumper removed.
//
// Motor -> OUT1 / OUT2.
// An appropriate external motor supply is required.
// Do not connect the available 12V batteries directly.

const byte MOTOR_IN1 = 8;
const byte MOTOR_IN2 = 9;

const unsigned long RUN_DURATION_MS = 3000;
const unsigned long DIRECTION_PAUSE_MS = 500;

bool motorCommandActive = false;
unsigned long motorStartedAt = 0;

void stopMotor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  motorCommandActive = false;
}

void startMotor(bool forward) {
  stopMotor();
  delay(DIRECTION_PAUSE_MS);

  digitalWrite(forward ? MOTOR_IN1 : MOTOR_IN2, HIGH);

  motorStartedAt = millis();
  motorCommandActive = true;

  Serial.println(forward
                     ? "Control state: FORWARD"
                     : "Control state: REVERSE");
}

void setup() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);

  Serial.begin(9600);
  Serial.println("Ready: F = forward, R = reverse, S = stop.");
  Serial.println("Automatic stop after 3 seconds.");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    switch (command) {
      case 'F':
      case 'f':
        startMotor(true);
        break;

      case 'R':
      case 'r':
        startMotor(false);
        break;

      case 'S':
      case 's':
        stopMotor();
        Serial.println("Control state: STOP");
        break;

      case '\n':
      case '\r':
        break;

      default:
        Serial.println("Unknown command: use F, R or S.");
        break;
    }
  }

  if (motorCommandActive &&
      millis() - motorStartedAt >= RUN_DURATION_MS) {
    stopMotor();
    Serial.println("Control state: STOP (timeout)");
  }
}