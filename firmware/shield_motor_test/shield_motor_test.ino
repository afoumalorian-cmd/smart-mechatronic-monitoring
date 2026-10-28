// KEYES L298P V1 quick-connector shield.
// Motor connected to motor socket A1.
// Channel A: D6 = PWM, D2 = direction.
// Channel B remains disabled.

const byte MOTOR_A_PWM = 6;
const byte MOTOR_A_DIRECTION = 2;
const byte MOTOR_B_PWM = 5;
const byte MOTOR_B_DIRECTION = 4;

const byte TEST_PWM = 150;
const unsigned long TEST_DURATION_MS = 5000;

bool testRunning = false;
unsigned long testStartedAt = 0;

void stopMotor() {
  analogWrite(MOTOR_A_PWM, 0);
  testRunning = false;
}

void setup() {
  pinMode(MOTOR_A_PWM, OUTPUT);
  pinMode(MOTOR_A_DIRECTION, OUTPUT);
  pinMode(MOTOR_B_PWM, OUTPUT);
  pinMode(MOTOR_B_DIRECTION, OUTPUT);

  stopMotor();
  analogWrite(MOTOR_B_PWM, 0);
  digitalWrite(MOTOR_A_DIRECTION, LOW);
  digitalWrite(MOTOR_B_DIRECTION, LOW);

  Serial.begin(9600);
  Serial.println("Ready: T = 5000 ms test, S = stop.");
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if ((command == 'T' || command == 't') && !testRunning) {
      digitalWrite(MOTOR_A_DIRECTION, HIGH);

      testStartedAt = millis();
      testRunning = true;
      analogWrite(MOTOR_A_PWM, TEST_PWM);

      Serial.println("Test command started.");
    } else if (command == 'S' || command == 's') {
      stopMotor();
      Serial.println("STOP");
    }
  }

  if (testRunning &&
      millis() - testStartedAt >= TEST_DURATION_MS) {
    stopMotor();
    Serial.println("Test command finished.");
  }
}