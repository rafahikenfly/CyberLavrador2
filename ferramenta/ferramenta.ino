#include "Wire.h" 
#include "Ultrasonic.h"

// *** FERRAMENTA
#define toolIDBits 3
int toolPin[2] = {A0, A1};
int toolID[toolIDBits] = {6,7,8};
int toolState = 0;
char* state[4]= {"Idle", "Alarm", "Run", "Engaged"};
char* tool[8] = {"Disengaged", "Umidade", "pH", "res1", "res2", "res3", "res4", "res5"};
// 0 = Idle (parado, sem ferramenta e longe de obstáculo)
// 1 = Alarm (próximo de obstáculo)
// 2 = Run (não deve se mexer)
// 3 = Engaged (com alguma ferramenta acoplada, mas parado)

// *** ULTRASSONICOS
int trigger[4]   = {12,12,12,12};
int echo[4]      = {13,13,13,13};
int clearance[4] = {0,  0, 0, 0};
Ultrasonic clearanceA(trigger[0],echo[0]);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic clearanceB(trigger[1],echo[1]);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic clearanceC(trigger[2],echo[2]);             //Configura os pinos sensor ultrassonico (Trigger,Echo)
Ultrasonic clearanceD(trigger[3],echo[3]);             //Configura os pinos sensor ultrassonico (Trigger,Echo)

// *** RELAY
#define relayCount 4
#define laserChannel 0
#define motorChannel 1
int relayPin[relayCount] = {2,3,4,5};
bool relayState[relayCount];

void setup() {
  Serial.begin(9600);
  for (int i=0; i<relayCount;i++) {
    relayState[i] = false;
    pinMode(relayPin[i], OUTPUT);
    digitalWrite(relayPin[i], HIGH);
  }
  for (int i=0; i<toolIDBits;i++) {
    pinMode(toolID[i], INPUT);
  }
  getTool();
}

void loop() {
  getClearance();
  while (Serial.available()) {
    int incoming;
    int error = 0;
    incoming = Serial.read();
    //Serial.print("Received: ");
    //Serial.println(incoming);
    switch (incoming) {
      case 10:
      case 13:
        if (error) {
          Serial.print ("error:");
          Serial.println (error);
        }
        else Serial.println("ok");
        break;
      case '?': reportStatus(); break;
      case 'G':
      case 'g':
        int command;
        command = Serial.read();
        if (command == '1') relay(laserChannel, true);
        if (command == '2') relay(laserChannel, false);
        if (command == '3') relay(motorChannel, true);
        if (command == '4') relay(motorChannel, false);
        if (command == '5') relay(2, true);
        if (command == '6') relay(2, false);
        if (command == '7') relay(3, true);
        if (command == '8') relay(3, false);
        break;
      default:
        Serial.print("Received: ");
        Serial.println(incoming);
    }
  }
  delay(1000);
}

void reportStatus() {
  // State
  Serial.print ("<");
  Serial.print(state[toolState]);
  // Clearance
  getClearance();
  Serial.print("|Clearance:");
  for (int i=0;i<3;i++) {
    Serial.print(clearance[i]);
    Serial.print(",");
  }
  Serial.print(clearance[3]);
  // Relays
  Serial.print ("|Relay:");
  for (int i=0;i<relayCount-1;i++) {
    Serial.print(relayState[i]);
    Serial.print(",");
  }
  Serial.print(relayState[relayCount-1]);
  // Ferramenta
  int ID = getTool();
  Serial.print("|Tool:");
  Serial.print(tool[ID]);
  if (ID) {
    Serial.print("|Data:");
    Serial.print(analogRead(toolPin[0]));  //Mostra o valor da porta analogica no serial monitor
    Serial.print(",");
    Serial.print(analogRead(toolPin[1]));  //Mostra o valor da porta analogica no serial monitor
  }
  //Fecha mensagem
  Serial.println(">");
}

void getClearance() {
  clearance[0] = clearanceA.read();
  if (clearance[0] < 5) alarm();
  clearance[1] = clearanceB.read();
  if (clearance[1] < 5) alarm();
  clearance[2] = clearanceC.read();
  if (clearance[2] < 5) alarm();
  clearance[3] = clearanceD.read();
  if (clearance[3] < 5) alarm();
}

int getTool() {
  int tool = 0;
  // Le o ID da ferramenta
  for (int i=0; i<toolIDBits; i++) {
   if(digitalRead(toolID[i])) tool += pow(2,i);
//    Serial.println();
//    Serial.print(i);
//    Serial.print("/");
//    Serial.print(digitalRead(toolID[i]));
//    Serial.print("/");
//    Serial.println(tool);
  }
  return tool;
}
void relay(int channel, bool status) {
  relayState[channel] = status;
  digitalWrite(relayPin[channel], status ? LOW : HIGH);toolState = status ? 2 : getTool();
}
void alarm() {
  for (int i=0; i<relayCount; i++) {
    digitalWrite(relayPin[i], LOW);
  }
  toolState = 1;
}