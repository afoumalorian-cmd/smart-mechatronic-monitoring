// Send a startup message and a periodic counter over serial.

unsigned long messageCount = 0;

void setup() {
  Serial.begin(9600);
  Serial.println("Arduino serial test started");
}

void loop() {
  Serial.print("Message count: ");
  Serial.println(messageCount);

  messageCount++;
  delay(1000);
}