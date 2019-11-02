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
const char *  OutputCmndTopic = "cmnd/sonoff2/switch";
const char *  OutputStatTopic = "stat/sonoff2/switch";
unsigned int  OutputPin       = 12;
unsigned int  LedPin          = 13;
unsigned long DigitalPeriod   = 30000;
unsigned long LedPeriod       = 500;

const char * WifiTopic = "stat/sonoff2/wifi";

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Variables
unsigned long currTime;
unsigned long lastDigital = millis();

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP logUdp;

char  valueStr[50];

unsigned int outputLevel;
unsigned int outputTime;
unsigned int ledTime;

// Macro for logging
#define logPrintf(...) logUdp.beginPacket(logAddress,logPort); logUdp.printf(__VA_ARGS__); logUdp.endPacket();

int wifiPct() {
   long rssi = WiFi.RSSI();

   if ( rssi >= -50 ) return 100;
   else if ( rssi <= -100 ) return 0;
   else return (int(2 * (rssi + 100)));
}

// MQTT Message Received
void callback(char* topic, byte* payload, unsigned int length) {
   ledTime = millis();
   digitalWrite(LedPin,LOW);

   // Topic match
   if ( strcmp(OutputCmndTopic,topic) == 0 ) {

      // Turn On      
      if ( length == 2 && strncmp((char *)payload,"ON",2) == 0 ) {
         digitalWrite(OutputPin,HIGH);
         client.publish(OutputStatTopic,"ON");
         outputLevel = 1;
         outputTime  = millis();
         logPrintf("Turning on relay %i",OutputPin)
      }

      // Turn Off
      else if ( length == 3 && strncmp((char *)payload,"OFF",3) == 0 ) {
         digitalWrite(OutputPin,LOW);
         client.publish(OutputStatTopic,"OFF");
         outputLevel = 0;
         logPrintf("Turning off relay %i",OutputPin)
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

   pinMode(OutputPin,OUTPUT);
   pinMode(LedPin,OUTPUT);

   digitalWrite(LedPin,HIGH);
   digitalWrite(OutputPin,LOW);

   outputLevel = 0;
   outputTime = millis();
   ledTime = millis();
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
         client.subscribe(OutputCmndTopic);
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

   // Refresh digital values
   if ( (currTime - lastDigital) > DigitalPeriod) {
      logPrintf("Updating digital values.");

      if (outputLevel) client.publish(OutputStatTopic,"ON");
      else client.publish(OutputStatTopic,"OFF");

      lastDigital = currTime;
      sprintf(valueStr,"%i",wifiPct());
      logPrintf("Wifi strenth = %s",valueStr);
      client.publish(WifiTopic,valueStr);
   }

   if ( (currTime - ledTime) > LedPeriod ) {
      ledTime = millis();
      digitalWrite(LedPin,HIGH);
   }
}

