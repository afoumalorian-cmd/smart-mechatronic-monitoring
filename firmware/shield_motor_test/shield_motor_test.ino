// KEYES L298P V1 shield: one motor on socket A1.
// Channel A: D6 = PWM, D2 = direction.
// Channel B remains disabled.

const byte MOTOR_A_PWM = 6;
const byte MOTOR_A_DIRECTION = 2;
const byte MOTOR_B_PWM = 5;
const byte MOTOR_B_DIRECTION = 4;

const unsigned long TEST_DURATION_MS = 5000;
const unsigned long RESTART_DELAY_MS = 1000;

byte selectedPwm = 150;
bool testRunning = false;
unsigned long testStartedAt = 0;
unsigned long stoppedAt = 0;

void stopMotor() {
  analogWrite(MOTOR_A_PWM, 0);
  testRunning = false;
  stoppedAt = millis();
}

void setup() {
  pinMode(MOTOR_A_PWM, OUTPUT);
  pinMode(MOTOR_A_DIRECTION, OUTPUT);
  pinMode(MOTOR_B_PWM, OUTPUT);
  pinMode(MOTOR_B_DIRECTION, OUTPUT);

  analogWrite(MOTOR_B_PWM, 0);
  digitalWrite(MOTOR_A_DIRECTION, LOW);
  digitalWrite(MOTOR_B_DIRECTION, LOW);
  stopMotor();

  Serial.begin(9600);
  Serial.println("Ready: F/T = forward, R = reverse, S = stop.");
  Serial.println("PWM presets: 1 = 100, 2 = 125, 3 = 150.");
  Serial.println("Initial PWM: 150. Automatic stop: 5 seconds.");
}

void loop() {
  // Check the timeout before processing new commands.
  if (testRunning &&
      millis() - testStartedAt >= TEST_DURATION_MS) {
    stopMotor();
    Serial.println("STOP: timeout");
  }

  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 'S' || command == 's') {
      stopMotor();
      Serial.println("STOP");
    } else if (command >= '1' && command <= '3') {
      selectedPwm = 100 + (command - '1') * 25;

      if (testRunning) {
        analogWrite(MOTOR_A_PWM, selectedPwm);
      }

      Serial.print("Selected PWM: ");
      Serial.println(selectedPwm);
    } else if (command == 'F' || command == 'f' ||
               command == 'T' || command == 't' ||
               command == 'R' || command == 'r') {
      if (testRunning) {
        Serial.println("Stop before starting another test.");
      } else if (millis() - stoppedAt < RESTART_DELAY_MS) {
        Serial.println("Wait before restarting.");
      } else {
        bool reverse = (command == 'R' || command == 'r');
        digitalWrite(MOTOR_A_DIRECTION, reverse ? LOW : HIGH);

        testStartedAt = millis();
        testRunning = true;
        analogWrite(MOTOR_A_PWM, selectedPwm);

        Serial.println(reverse ? "REVERSE" : "FORWARD");
        Serial.print("PWM: ");
        Serial.println(selectedPwm);
      }
    } else if (command != '\n' && command != '\r') {
      Serial.println("Unknown command. Use F, R, S, 1, 2 or 3.");
    }
  }
}