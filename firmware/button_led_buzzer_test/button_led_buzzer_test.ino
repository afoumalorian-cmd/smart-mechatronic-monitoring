// Experimental button, LED and buzzer test.
const byte LED_PIN = A1;
const byte BUTTON_PIN = A2;
const byte BUZZER_PIN = A3;
// false: generate a tone for a passive buzzer
// true: use a steady signal for an active buzzer
const bool ACTIVE_BUZZER = false;
bool previousButtonState = false;
void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(LED_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
}
void loop() {
  bool buttonPressed = (digitalRead(BUTTON_PIN) == LOW);
  // Recheck the button after a 20 ms debounce delay.
  if (buttonPressed != previousButtonState) {
    delay(20);
    buttonPressed = (digitalRead(BUTTON_PIN) == LOW);
    if (buttonPressed != previousButtonState) {
      previousButtonState = buttonPressed;
      digitalWrite(LED_PIN, buttonPressed ? HIGH : LOW);
      if (buttonPressed) {
        if (ACTIVE_BUZZER) {
          digitalWrite(BUZZER_PIN, HIGH);
        } else {
          tone(BUZZER_PIN, 2000);
        }
      } else {
        noTone(BUZZER_PIN);
        digitalWrite(BUZZER_PIN, LOW);
      }
    }
  }
}
