#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <PubSubClient.h>

// Configuration
const char * ssid        = "amaroq";
const char * password    = "1er4idnfu345os3o283";
const char * mqtt_server = "aliska.amaroq.net";
unsigned int locPort     = 8112;
unsigned int logPort     = 8111;
IPAddress    logAddress (172,16,20,1);

// Timers
const unsigned long DigitalPeriod  = 60000; // 1 minute
const unsigned long DebouncePeriod = 250;   // 0.25 second

// LED Pins
const unsigned int LedPin    = 13;
const unsigned int LedPeriod = 100;

// Outputs
const unsigned int OutputCount = 2;
const char * OutputCmndTopic[] = {"cmnd/pantry_control/house_heat", 
                                  "cmnd/pantry_control/house_fan" };
const char * OutputStatTopic[] = {"stat/pantry_control/house_heat", 
                                  "stat/pantry_control/house_fan" };
unsigned int OutputPin[]       = {12, 5};
unsigned int OutputMaxTime[]   = {2100000, 36000000}; // 35 Min, 10 Hours

// Analog Inputs
const unsigned int InputCount = 3;
const char * InputStatTopic[] = {"stat/pantry_control/gate_bell", 
                                 "stat/pantry_control/door_bell", 
                                 "stat/pantry_control/gate_toggle"};
unsigned int InputPin[]       = {9, 10, 14};

const char * WifiTopic = "stat/pantry_control/wifi";

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Variables
unsigned int lastDigital = millis();
unsigned int x;
unsigned int currTime;

unsigned int outputLevel[OutputCount];
unsigned int outputTime[OutputCount];

char  valueStr[50];

unsigned int inputLevel[InputCount];
unsigned int inputRaw[InputCount];
unsigned int inputTime[InputCount];

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP logUdp;

unsigned long ledTime;
unsigned int  tmp;

// Macro for logging
#define logPrintf(...) logUdp.beginPacket(logAddress,logPort); logUdp.printf(__VA_ARGS__); logUdp.endPacket();

// MQTT Message Received
void callback(char* topic, byte* payload, unsigned int length) {
   digitalWrite(LedPin,LOW);
   ledTime = millis();

   for (x=0; x < OutputCount; x++) {

      // Topic match
      if ( strcmp(OutputCmndTopic[x],topic) == 0 ) {

         // Turn On      
         if ( length == 2 && strncmp((char *)payload,"ON",2) == 0 ) {
            digitalWrite(OutputPin[x],HIGH);
            client.publish(OutputStatTopic[x],"ON");
            outputLevel[x] = 1;
            outputTime[x] = millis();
            logPrintf("Turning on relay %i",OutputPin[x])
         }

         // Turn Off
         else if ( length == 3 && strncmp((char *)payload,"OFF",3) == 0 ) {
            digitalWrite(OutputPin[x],LOW);
            client.publish(OutputStatTopic[x],"OFF");
            outputLevel[x] = 0;
            logPrintf("Turning off relay %i",OutputPin[x])
         }
      }
   }
}


// Initialize
void setup() {

   lastDigital = millis();

   // Start and connect to WIFI
   WiFi.mode(WIFI_STA);
   WiFi.setSleepMode(WIFI_NONE_SLEEP);
   WiFi.begin(ssid, password);

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
      digitalWrite(LedPin,LOW);
      ledTime = millis();
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

   // Init relays
   for (x=0; x < OutputCount; x++) {
      pinMode(OutputPin[x],OUTPUT);
      digitalWrite(OutputPin[x],LOW);
      outputTime[x] = millis();
   }

   // Init inputs
   for (x=0; x < InputCount; x++) {
      pinMode(InputPin[x],INPUT);
      inputLevel[x] = 0;
      inputRaw[x]   = 0;
      inputTime[x]  = millis();
   }

   pinMode(LedPin,OUTPUT);
   digitalWrite(LedPin,HIGH);
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

   // LED Off
   if ( (currTime - ledTime) > LedPeriod ) digitalWrite(LedPin,HIGH);

   // Read digital input states
   for (x=0; x < InputCount; x++) {
      if ( digitalRead(InputPin[x]) == 0 ) tmp = 1;
      else tmp = 0;

      // Digital Input Debounce
      if ( tmp != inputRaw[x]) inputTime[x] = currTime;

      // Input is stable
      if ( (currTime - inputTime[x]) > DebouncePeriod ) {

         // State changed
         if ( inputRaw[x] != inputLevel[x] ) {

            // Update state
            inputLevel[x] = inputRaw[x];

            if (inputLevel[x] == 1 )  {
               client.publish(InputStatTopic[x],"ON");
               logPrintf("Input %i is on",InputPin[x])
            }
            else {
               client.publish(InputStatTopic[x],"OFF");
               logPrintf("Input %i is off",InputPin[x])
            }
            digitalWrite(LedPin,LOW);
            ledTime = millis();

            delay(10);
         }
      }
   
      inputRaw[x] = tmp;
   }

   // Refresh digital values
   if ( (currTime - lastDigital) > DigitalPeriod) {
      logPrintf("Updating digital values.");

      for (x=0; x < OutputCount; x++) {
         if (outputLevel[x] == 1 ) 
            client.publish(OutputStatTopic[x],"ON");
         else
            client.publish(OutputStatTopic[x],"OFF");
         delay(10);
      }

      for (x=0; x < InputCount; x++) {
         if (inputLevel[x] == 1 ) 
            client.publish(InputStatTopic[x],"ON");
         else
            client.publish(InputStatTopic[x],"OFF");
         delay(10);
      }

      digitalWrite(LedPin,LOW);
      ledTime = millis();
      lastDigital = currTime;
      sprintf(valueStr,"%i",WiFi.RSSI());
      logPrintf("Wifi strenth = %s",valueStr);
      client.publish(WifiTopic,valueStr);
   }

   // Max On state timeout
   for (x=0; x < OutputCount; x++) {
      if (outputLevel[x] == 1) {
         if ((currTime - outputTime[x]) > OutputMaxTime[x] ) {
            digitalWrite(OutputPin[x],LOW);
            client.publish(OutputStatTopic[x],"OFF");
            outputLevel[x] = 0;
            logPrintf("Turning off relay %i due to timeout",OutputPin[x])
            digitalWrite(LedPin,LOW);
            ledTime = millis();
         }
      }
   }
}

