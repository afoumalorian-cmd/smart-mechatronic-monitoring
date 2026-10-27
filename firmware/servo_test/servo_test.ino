#include <Servo.h>
// Experimental servo test; movement has not been validated.
Servo testServo;
void setup() {
  testServo.attach(9);  // Servo signal connected to shield D9
  testServo.write(90);
  delay(1000);
}
void loop() {
  testServo.write(45);
  delay(1500);
  testServo.write(90);
  delay(1500);
  testServo.write(135);
  delay(1500);
}
