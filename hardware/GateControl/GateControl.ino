#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>
#include "../secrets.h"

// Configuration
unsigned int locPort     = 8112;
unsigned int logPort     = 8111;
IPAddress    logAddress (172,16,20,1);

// Timers
const unsigned long MsgTxPeriod   = 1000;  // 1 seconds
const unsigned long AnalogPeriod  = 60000; // 1 minute
const unsigned long DigitalPeriod = 60000; // 1 minute

// Outputs
unsigned int OutputCount       = 4;
const char * OutputCmndTopic[] = {"cmnd/gate_control/front_lawn_1", 
                                  "cmnd/gate_control/front_lawn_2", 
                                  "cmnd/gate_control/front_lawn_3", 
                                  "cmnd/gate_control/west_trees"};
const char * OutputStatTopic[] = {"stat/gate_control/front_lawn_1", 
                                  "stat/gate_control/front_lawn_2", 
                                  "stat/gate_control/front_lawn_3", 
                                  "stat/gate_control/west_trees"};
unsigned int OutputChannel[]   = {0, 1, 2, 3};
unsigned int OutputMaxTime[]   = {3600000, 3600000, 3600000, 3600000}; // 1 Hour

// Analog Inputs
unsigned int InAnalogCount     = 0;
const char * InAnalogTopic[]   = {};
unsigned int InAnalogChannel[] = {};

// Gate IO
const char * GateCmndTopic  = "cmnd/gate_control/car_gate";
const char * GateStatTopic  = "stat/gate_control/car_gate";

unsigned int GateOutChannel = 5;
unsigned int GateInChannel  = 0;
unsigned int GateInvert     = 1;

unsigned int ResetPin = 2;

// Temperature
const char * TempTopic  = "stat/gate_control/temp";
const char * WifiTopic  = "stat/gate_control/wifi";
const char * ResetTopic = "cmnd/gate_control/reset";

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Variables
unsigned long lastMsgRx   = 0;
unsigned long lastMsgTx   = millis();
unsigned long lastAnalog  = millis();
unsigned long lastDigital = millis();
unsigned long lastReset   = millis();
unsigned long currTime;
unsigned int x;

float value;
char  valueStr[50];

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP logUdp;

unsigned int rxCount;

char txBuffer[50];
char rxBuffer[50];
char mark[10];
int  tmp;
char c;

unsigned int outputRelays[6];
unsigned int outputTime[6];
unsigned int inputValues[6];
unsigned int tempValue;
unsigned int currGate;

// Macro for logging
#define logPrintf(...) logUdp.beginPacket(logAddress,logPort); logUdp.printf(__VA_ARGS__); logUdp.endPacket();

int wifiPct() {
   long rssi = WiFi.RSSI();

   if ( rssi >= -50 ) return 100;
   else if ( rssi <= -100 ) return 0;
   else return (int(2 * (rssi + 100)));
}

// Reset io board
void resetIoBoard() {
   logPrintf("Sending reset to arduino")
   digitalWrite(ResetPin,LOW);
   delay(500);
   digitalWrite(ResetPin,HIGH);
   lastReset = millis();
}

// Send message to arduino
void sendMsg() {

   sprintf(txBuffer,"STATE %i %i %i %i %i %i\n",
                    outputRelays[0], outputRelays[1], outputRelays[2],
                    outputRelays[3], outputRelays[4], outputRelays[5]);

   Serial.write(txBuffer);
   logPrintf("Sending message to arduino: %s",txBuffer)
   lastMsgTx = millis();
}

void recvMsg() {

   // Get serial data
   while (Serial.available()) {
      if ( rxCount == 50 ) rxCount = 0;

      c = Serial.read();
      rxBuffer[rxCount++] = c;
      rxBuffer[rxCount] = '\0';
   }

   // Check for incoming message
   if ( rxCount > 7 && rxBuffer[rxCount-1] == '\n' ) {

      // Parse string
      tmp = sscanf(rxBuffer,"%s %i %i %i %i %i", 
                   mark, &(inputValues[0]), &(inputValues[1]), &(inputValues[2]),
                   &(inputValues[3]), &(tempValue));

      // Check marker
      if ( tmp == 6 && strcmp(mark,"STATUS") == 0 ) {
         logPrintf("Got arduino message: %s",rxBuffer)
         lastMsgRx = millis();
         lastReset = millis();
      }

      rxCount = 0;
   }
}


// MQTT Message Received
void callback(char* topic, byte* payload, unsigned int length) {

   for (x=0; x < OutputCount; x++) {

      // Topic match
      if ( strcmp(OutputCmndTopic[x],topic) == 0 ) {

         // Turn On      
         if ( length == 2 && strncmp((char *)payload,"ON",2) == 0 ) {
            outputRelays[OutputChannel[x]] = 100;
            client.publish(OutputStatTopic[x],"ON");
            outputTime[x] = millis();
            logPrintf("Turning on relay %i",OutputChannel[x])
         }

         // Turn Off
         else if ( length == 3 && strncmp((char *)payload,"OFF",3) == 0 ) {
            outputRelays[OutputChannel[x]] = 0;
            client.publish(OutputStatTopic[x],"OFF");
            logPrintf("Turning off relay %i",OutputChannel[x])
         }
      }
   }

   // Gate topic match
   if ( strcmp(GateCmndTopic,topic) == 0 ) {

      // Turn On, with gate off (closed)
      if ( currGate == 0 && length == 2 && strncmp((char *)payload,"ON",2) == 0 ) {
         outputRelays[GateOutChannel] = 50;
         logPrintf("Pulsing relay %i to open gate",GateOutChannel)
      }

      // Turn Off, with gate on (open)
      else if ( currGate == 1 && length == 3 && strncmp((char *)payload,"OFF",3) == 0 ) {
         outputRelays[GateOutChannel] = 50;
         logPrintf("Pulsing relay %i to close gate",GateOutChannel)
      }
   }

   // Clear Gate relay
   sendMsg();
   outputRelays[GateOutChannel] = 0;
   sendMsg();

   if ( strcmp(ResetTopic,topic) == 0 && strncmp((char *)payload,"ON",2) == 0 ) resetIoBoard();
}


// Initialize
void setup() {

   lastMsgRx   = 0;
   lastMsgTx   = millis();
   lastAnalog  = millis();
   lastDigital = millis();

   // Start and connect to WIFI
   WiFi.mode(WIFI_STA);
   WiFi.setSleepMode(WIFI_NONE_SLEEP);
   WiFi.begin(ssid, password);

   // Connection to arduino
   Serial.begin(9600);

   while (WiFi.waitForConnectResult() != WL_CONNECTED) {
      delay(5000);
      ESP.restart();
   }
   delay(1000);

   // Start logging
   logUdp.begin(locPort);
   delay(1000);
   logPrintf("System booted!")

   // Firmware download start callback
   ArduinoOTA.onStart([]() {
      if (ArduinoOTA.getCommand() == U_FLASH) {
         logPrintf("Starting sketch firmware upload")
      }
      else { // U_SPIFFS
         logPrintf("Starting filesystem firmware upload")
      }
   });

   // Firmware download done callback
   ArduinoOTA.onEnd([]() {
      logPrintf("Finished firmware upload. Rebooting....")
   });

   // Firmware download progress
   ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
      logPrintf("Download Progress: %u%%",(progress / (total / 100)))
   });

   ArduinoOTA.onError([](ota_error_t error) {
      if      (error == OTA_AUTH_ERROR)    {logPrintf("Download Failed: Auth Failed")}
      else if (error == OTA_BEGIN_ERROR)   {logPrintf("Download Failed: Begin Failed")}
      else if (error == OTA_CONNECT_ERROR) {logPrintf("Download Failed: Connect Failed")}
      else if (error == OTA_RECEIVE_ERROR) {logPrintf("Download Failed: Receive Failed")}
      else if (error == OTA_END_ERROR)     {logPrintf("Download Failed: End Failed")}
   });

   ArduinoOTA.begin();

   client.setServer(mqtt_server, 1883);
   client.setCallback(callback);

   rxCount = 0;

   // Init relays
   for (x=0; x < 6; x++) {
      outputRelays[x] = 0;
      outputTime[x] = millis();
   }
   currGate = 0;

   sendMsg();

   pinMode(ResetPin,OUTPUT);
   digitalWrite(ResetPin,HIGH);
}


// MQTT Connect
void reconnect() {

   // Loop until we're reconnected
   while (!client.connected()) {
      logPrintf("Attempting MQTT connection...")

      // Create a random client ID
      String clientId = "ESP8266Client-";
      clientId += String(random(0xffff), HEX);

      // Attempt to connect
      if (client.connect(clientId.c_str())) {
         logPrintf("Connected to MQTT Server");

         // Subscribe
         for (x=0; x < OutputCount; x++) {
            client.subscribe(OutputCmndTopic[x]);
         }

         client.subscribe(GateCmndTopic);
         client.subscribe(ResetTopic);

      } else {
         logPrintf("Failed to connect to MQTT, waiting 5 seconds.")
         delay(5000);
      }
   }
}


// Service Loop
void loop() {
   ArduinoOTA.handle();

   if (!client.connected()) reconnect();
   client.loop();

   // Attempt to receive input message
   recvMsg();

   currTime = millis();

   // tmp hold current gate state, depends on input and inverted flag
   tmp = (inputValues[GateInChannel] == 0)?GateInvert:!GateInvert;

   // Test for gate change
   if ( tmp != currGate ) {
      currGate = tmp;

      if ( currGate ) client.publish(GateStatTopic,"ON");
      else client.publish(GateStatTopic,"OFF");
   }

   // Process analog and Temperature values
   if ( (lastMsgRx != 0) && 
        ((currTime - lastMsgRx)  < AnalogPeriod) && 
        ((currTime - lastAnalog) > AnalogPeriod) ) {

      logPrintf("Updating analog values.");

      for (x=0; x < InAnalogCount; x++) {
         value = float(inputValues[InAnalogChannel[x]]);
         sprintf(valueStr,"%0.2f",value);
         client.publish(InAnalogTopic[x],valueStr);
         logPrintf("Topic %s = %s",InAnalogTopic[x],valueStr);
         delay(10);
      }   

      value = (float(tempValue) / 1023.0) * 500.0;
      sprintf(valueStr,"%0.2f",value);
      client.publish(TempTopic,valueStr);
      logPrintf("Topic %s = %s",TempTopic,valueStr);
      delay(10);

      lastAnalog = currTime;
   }

   // 1 Minute has passed without receiving a message
   if ( ((currTime - lastReset) > AnalogPeriod) ) resetIoBoard();

   // Refresh digital values
   if ( (currTime - lastDigital) > DigitalPeriod) {
      logPrintf("Updating digital values.");

      for (x=0; x < OutputCount; x++) {
         if (outputRelays[OutputChannel[x]] == 100 ) 
            client.publish(OutputStatTopic[x],"ON");
         else
            client.publish(OutputStatTopic[x],"OFF");
         delay(10);
      }

      if ( currGate ) client.publish(GateStatTopic,"ON");
      else client.publish(GateStatTopic,"OFF");

      lastDigital = currTime;
      sprintf(valueStr,"%i",wifiPct());
      logPrintf("Wifi strenth = %s",valueStr);
      client.publish(WifiTopic,valueStr);
   }

   if (( currTime - lastMsgTx ) > MsgTxPeriod) tmp = 1;
   else tmp = 0;

   // Max On state timeout
   for (x=0; x < OutputCount; x++) {
      if (outputRelays[OutputChannel[x]] == 100 ) {
         if ((currTime - outputTime[OutputChannel[x]]) > OutputMaxTime[x] ) {
            outputRelays[OutputChannel[x]] = 0;
            client.publish(OutputStatTopic[x],"OFF");
            logPrintf("Turning off relay %i due to timeout",OutputChannel[x])
            tmp = 1;
         }
      }
   }

   if ( tmp == 1 ) sendMsg();
}

