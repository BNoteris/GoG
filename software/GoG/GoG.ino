#include <Wire.h>

void setup() {
  Serial.begin(115200);
  Wire.begin();

}

void loop() {
  // put your main code here, to run repeatedly:
  Serial.println("loop");
  delay(1000);
}
