// Prepare L298N channel A control without motor power.
// Serial commands: F = forward, R = reverse, S = stop.

const byte MOTOR_IN1 = 8;
const byte MOTOR_IN2 = 9;

void stopMotor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
}

void setup() {
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  stopMotor();

  Serial.begin(9600);
  Serial.println("Ready: F = forward, R = reverse, S = stop.");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 'F' || command == 'R') {
      stopMotor();
      delay(500);

      if (command == 'F') {
        digitalWrite(MOTOR_IN1, HIGH);
        Serial.println("Control state: FORWARD");
      } else {
        digitalWrite(MOTOR_IN2, HIGH);
        Serial.println("Control state: REVERSE");
      }
    } else if (command == 'S') {
      stopMotor();
      Serial.println("Control state: STOP");
    } else if (command != '\n' && command != '\r') {
      Serial.println("Unknown command: use F, R or S.");
    }
  }
}