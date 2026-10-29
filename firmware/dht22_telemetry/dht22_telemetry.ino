#include <DHT.h>

const byte DHT_PIN = 7;
const unsigned long SAMPLE_INTERVAL_MS = 3000;

DHT dht(DHT_PIN, DHT22);

unsigned long lastSampleAt = 0;
unsigned long sequenceNumber = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();
}

void loop() {
  unsigned long now = millis();

  // Wait between measurements and allow sensor startup.
  if (now - lastSampleAt < SAMPLE_INTERVAL_MS) {
    return;
  }

  lastSampleAt = now;

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // Emit one JSON object per line, including failed readings.
  Serial.print("{\"device_id\":\"machine_001\",\"sequence\":");
  Serial.print(sequenceNumber++);
  Serial.print(",\"uptime_ms\":");
  Serial.print(now);
  Serial.print(",\"sensor\":\"dht22\",\"status\":");

  if (isnan(humidity) || isnan(temperature)) {
    Serial.println(
        "\"error\",\"temperature_c\":null,\"humidity_pct\":null}");
    return;
  }

  Serial.print("\"ok\",\"temperature_c\":");
  Serial.print(temperature, 1);
  Serial.print(",\"humidity_pct\":");
  Serial.print(humidity, 1);
  Serial.println("}");
}