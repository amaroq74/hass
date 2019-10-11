#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>
#include "SolarTemps.h"

// Configuration
const char * ssid        = "amaroq";
const char * password    = "1er4idnfu345os3o283";
const char * mqtt_server = "aliska.amaroq.net";
unsigned int locPort     = 8112;
unsigned int logPort     = 8111;
IPAddress    logAddress (172,16,20,2);

// Timers
const unsigned long msgTxPeriod  = 1000;  // 1 seconds
const unsigned long analogPeriod = 60000; // 1 minute

// Outputs
unsigned int OutputCount = 3;
const char * OutputCmndTopic[] = {"/cmnd/pool_control/main", "/cmnd/pool_control/sweep", "/cmnd/pool_control/heat"};
const char * OutputStatTopic[] = {"/stat/pool_control/main", "/stat/pool_control/sweep", "/stat/pool_control/heat"};
unsigned int OutputChannel[]   = {0, 1, 2};
unsigned int OutputMaxTime[]   = {36000000, 36000000, 36000000}; // 10 Hours

// Analog Inputs
unsigned int InAnalogCount     = 2;
const char * InAnalogTopic[]   = {"/stat/pool_control/solar/in", "/stat/pool_control/solar/out"};
unsigned int InAnalogChannel[] = {2,3};

// Temperature
const char * TempTopic = "/state/pool_control/temp";

/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Variables
unsigned int lastMsgRx  = 0xFFFF;
unsigned int lastMsgTx  = millis();
unsigned int lastAnalog = millis();
unsigned int x;
unsigned int currTime;

float value;
char  valueStr[50];

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP logUdp;

String txBuffer;
String rxBuffer;
char   mark[10];
int    ret;

unsigned int outputRelays[6];
unsigned int outputTime[6];
unsigned int inputValues[6];
unsigned int tempValue;


// Macro for logging
#define logPrintf(...) logUdp.beginPacket(logAddress,logPort); logUdp.printf(__VA_ARGS__); logUdp.endPacket();


// Send message to arduino
void sendMsg() {
   txBuffer  = "STATE";
   for (x=0; x < 6; x++) txBuffer += " " + String(outputRelays[x]);

   //Serial.println(txBuffer);
   logPrintf("Sending message to arduino: %s",txBuffer.c_str())
   lastMsgTx = millis();
}

void recvMsg() {

   // Get serial data
   while (Serial.available()) rxBuffer += Serial.read();

   // Check for incoming message
   if ( rxBuffer.length() > 7 && rxBuffer.endsWith("\n") ) {

      // Parse string
      ret = sscanf(rxBuffer.c_str(),"%s %i %i %i %i %i", 
                   mark, &(inputValues[0]), &(inputValues[1]), &(inputValues[2]),
                   &(inputValues[3]), &(tempValue));

      // Check marker
      if ( ret == 6 && strcmp(mark,"STATUS") == 0 ) {
         logPrintf("Got arduino message: %s",rxBuffer.c_str())
         lastMsgRx = millis();
      }

      rxBuffer = "";
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

   sendMsg();
}


// Initialize
void setup() {

   // Start and connect to WIFI
   WiFi.mode(WIFI_STA);
   WiFi.setSleepMode(WIFI_NONE_SLEEP);
   WiFi.begin(ssid, password);

   // Connection to arduino
   //Serial.begin(115200);

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

   rxBuffer = "";

   // Init relays
   for (x=0; x < 6; x++) {
      outputRelays[x] = 0;
      outputTime[x] = millis();
   }
   sendMsg();
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

         // Subscribe and publish current states
         for (x=0; x < OutputCount; x++) {
            client.subscribe(OutputCmndTopic[x]);
            if ( outputRelays[x] == 100 )
               client.publish(OutputStatTopic[x],"ON");
            else
               client.publish(OutputStatTopic[x],"OFF");
         }
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

   currTime = millis();

   if (( currTime - lastMsgTx ) > msgTxPeriod) sendMsg();

   // Attempt to receive input message
   recvMsg();

   // Process analog and Temperature values
   if ( (( currTime - lastMsgRx) < analogPeriod) && (( currTime - lastAnalog ) > analogPeriod) ) {
      logPrintf("Updating analog values.");

      for (x=0; x < InAnalogCount; x++) {
         value = SolarTempTable[inputValues[InAnalogChannel[x]]];
         sprintf(valueStr,"%0.2f",value);
         client.publish(InAnalogTopic[x],valueStr);
      }   

      value = (float(tempValue) / 1023.0) * 500.0;
      sprintf(valueStr,"%0.2f",value);
      client.publish(TempTopic,valueStr);

      lastAnalog = currTime;
   }

   // Max output time
   ret = 0;
   for (x=0; x < OutputCount; x++) {
      if (outputRelays[OutputChannel[x]] == 100 ) {
         if ((currTime - outputTime[OutputChannel[x]]) > OutputMaxTime[x] ) {
            outputRelays[OutputChannel[x]] = 0;
            client.publish(OutputStatTopic[x],"OFF");
            logPrintf("Turning off relay %i due to timeout",OutputChannel[x])
            ret = 1;
         }
      }
   }

   if ( ret == 1 ) sendMsg();
}


