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
#define shadowChannel 2
#define vacuumChanel 3

int relayPin[relayCount] = {2,3,4,5};
bool relayState[relayCount];

int digitalReadTool() {
  return digitalRead(toolPin[0]);
}
int analogReadTool() {
  return analogRead(toolPin[0]);
}
void relay(int channel, bool status, int timeout = 0) {
  relayState[channel] = status;
  digitalWrite(relayPin[channel], status ? LOW : HIGH);
  toolState = status ? 2 : getTool();
}


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
  int timeout = 0;
  while (Serial.available()) {
    int incoming;
    int error = 0;
    bool analogRequest = false;
    bool digitalRequest = false;
    incoming = Serial.read();
    switch (incoming) {
      case 10:
      case 13:
        if (error) {
          Serial.print ("error:");
          Serial.println (error);
        }
        else {
          Serial.println("ok");
          analogRequest && analogReadTool();
          digitalRequest && digitalReadTool();
          error = 0;
          analogRequest = false;
          digitalRequest = false;
        }
        break;
      case '?': reportStatus(); break;
      case 'M':
      case 'm':
        int command;
        command = Serial.parseInt();
        
        switch (command) {
          case 0: relay(shadowChannel, true, timeout); break;
          case 1: relay(shadowChannel, false, timeout); break;

          case 3: relay(motorChannel, true, timeout); break;
          case 4: relay(laserChannel, true, timeout); break;
          case 5: relay(motorChannel, false, timeout); break;
          case 6: relay(laserChannel, false, timeout); break;
          case 10: relay(vacuumChanel, true, timeout); break;
          case 11: relay(vacuumChanel, false, timeout); break;
          case 12: analogRequest = true; break;
          case 13: digitalRequest = true; break;
          default: error = 20;
        }
        break;
      case 'S':
      case 's':
        timeout = Serial.parseInt();
      default:
        error = 21;
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
  //TODO: LOOKAHEAD BUFFER |Bf:lookahead_buffer
  //Fecha mensagem
  Serial.println(">");
}
void reportError(int error) {
  Serial.println("error: 20");
  Serial.println(error);
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
  }
  return tool;
}
void alarm() {
  for (int i=0; i<relayCount; i++) {
    digitalWrite(relayPin[i], LOW);
  }
  toolState = 1;
}