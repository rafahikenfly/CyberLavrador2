#include "Wire.h" 
#include "Ultrasonic.h"

#define laserPin 2
#define motorPin 3
#define button0Pin 4
#define button1Pin 5
#define button2Pin A2

#define toolA0Pin A0
#define toolA1Pin A1

Ultrasonic plusX(12,13);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic plusY(10,11);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic lessX( 8, 9);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic lessY( 6, 7);             //Configura os pinos sensor ultrassonico (Trigger,Echo)

bool laserState = false;
bool motorState = false;
int clearance[4] = {0, 0, 0, 0};
int toolState = 0;
// 0 = Idle (parado e longe de obstáculo)
// 1 = Alarm (próximo de obstáculo)
// 2 = Run (não deve se mexer)
// 3 = Engaged (com alguma ferramenta acoplada)

void setup() {
  Serial.begin(9600);
  pinMode(laserPin, OUTPUT);
  pinMode(motorPin, OUTPUT);
  pinMode(button0Pin, INPUT);
  pinMode(button1Pin, INPUT);
  pinMode(button2Pin, INPUT);
  pinMode(A0, INPUT);
}

void loop() {
  while (Serial.available()) {
    int incoming;
    incoming = Serial.read();
    switch (incoming) {
      case '?':
        status();
        break;
      case 'G':
      case 'g':
        int command;
        command = Serial.read();
        if (command == '0') unalarm();
        if (command == '1') laser(true);
        if (command == '2') laser(false);
        if (command == '3') motor(true);
        if (command == '4') motor(false);
        break;
      case 10:
      case 13:
      break;
      default:
        Serial.print("Received: ");
        Serial.println(incoming);
    }
  }
  delay(1000);
}

void status() {
  Serial.print("X: ");
  Serial.print(clearance[0]);
  Serial.print(" / ");
  Serial.println(lessX.read());       //Mostra o valor do sensor ultrassonico X+
  Serial.print("Y: " );
  Serial.print(plusY.read());
  Serial.print(" / ");
  Serial.println(lessY.read());       //Mostra o valor do sensor ultrassonico X+
  Serial.print("Laser: ");
  Serial.print(laserState);                  //Mostra o valor do laser no serial monitor
  Serial.print(" / Motor: ");
  Serial.print(motorState);                  //Mostra o valor do motor no serial monitor
  Serial.print(" / Ferramenta: ");
  Serial.println(getTool());//Mostra o valor da porta analogica no serial monitor
  Serial.print("Dados Ferramenta: ");
  Serial.print(analogRead(toolA0Pin));  //Mostra o valor da porta analogica no serial monitor
  Serial.print(" / ");
  Serial.println(analogRead(toolA1Pin));  //Mostra o valor da porta analogica no serial monitor
}

void getClearance() {
  clearance[0] = plusX.read();
  if (clearance[0] < 5) alarm();
  clearance[1] = lessX.read();
  if (clearance[1] < 5) alarm();
  clearance[2] = plusY.read();
  if (clearance[2] < 5) alarm();
  clearance[3] = lessY.read();
  if (clearance[3] < 5) alarm();
}

int getTool() {
  int tool;
  tool = digitalRead(button0Pin) + 2 * digitalRead(button1Pin) + 4 * digitalRead(button2Pin);
  if (tool != 0) toolState = 3;
  else if (toolState == 3) toolState = 0;
  return tool;
}
void laser(bool status) {
  laserState = status;
  digitalWrite(laserPin, status ? HIGH : LOW);
  toolState = 2;
}

void motor(bool status) {
  motorState = status;
  digitalWrite(motorPin, status ? HIGH : LOW);
  toolState = 2;
}

void alarm() {
  digitalWrite(laserPin, LOW);
  digitalWrite(motorPin, LOW);
  toolState = 1;
}

void unalarm() {
  digitalWrite(laserPin, laserState ? HIGH : LOW);
  digitalWrite(motorPin, motorState ? HIGH : LOW);
}