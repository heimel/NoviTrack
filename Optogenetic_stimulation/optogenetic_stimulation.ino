/*
  Optogenetics trigger program for Arduino Uno R3

  Behavior after button press:
    - Pin 8: HIGH for duration_ms
    - Pin 9: 20 Hz square wave, 50% duty cycle
    - Built-in LED mirrors pin 9

  Connections:
    - External pushbutton between pin 2 and GND
    - Use INPUT_PULLUP mode

  Author: ChatGPT
*/

const int buttonPin = 2;
const int triggerPin = 8;
const int pulsePin = 9;
const int ledPin = LED_BUILTIN;

// Parameters
const unsigned long duration_ms = 1000;   // 1 second
const float pulse_frequency = 20.0;       // Hz

// Derived timing
const unsigned long half_period_ms =
    (1000.0 / pulse_frequency) / 2.0;

bool lastButtonState = HIGH;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);

  pinMode(triggerPin, OUTPUT);
  pinMode(pulsePin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  digitalWrite(triggerPin, LOW);
  digitalWrite(pulsePin, LOW);
  digitalWrite(ledPin, LOW);
}

void loop() {

  bool buttonState = digitalRead(buttonPin);

  // Detect button press (HIGH -> LOW)
  if (lastButtonState == HIGH && buttonState == LOW) {

    runStimulus();

    // Simple debounce
    delay(50);
  }

  lastButtonState = buttonState;
}

void runStimulus() {

  unsigned long startTime = millis();

  // Channel 1 immediately HIGH
  digitalWrite(triggerPin, HIGH);

  bool pulseState = false;
  unsigned long lastToggle = millis();

  while (millis() - startTime < duration_ms) {

    unsigned long currentTime = millis();

    // Toggle pulse channel at correct interval
    if (currentTime - lastToggle >= half_period_ms) {

      pulseState = !pulseState;

      digitalWrite(pulsePin, pulseState);
      digitalWrite(ledPin, pulseState);

      lastToggle = currentTime;
    }
  }

  // Turn everything off
  digitalWrite(triggerPin, LOW);
  digitalWrite(pulsePin, LOW);
  digitalWrite(ledPin, LOW);
}
