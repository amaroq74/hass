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
const unsigned long DigitalPeriod  = 60000; // 1 minute
const unsigned long DebouncePeriod = 250;   // 0.25 second

// Analog Inputs
const unsigned int InputCount = 1;
const char * InputStatTopic[] = {"stat/door_bell/door_bell"};
unsigned int InputPin[]       = {5};

const char * WifiTopic = "stat/door_bell/wifi";

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

// Variables
unsigned int lastDigital = millis();
unsigned int x;
unsigned int currTime;

char  valueStr[50];

unsigned int inputLevel[InputCount];
unsigned int inputRaw[InputCount];
unsigned int inputTime[InputCount];

WiFiClient espClient;
PubSubClient client(espClient);
WiFiUDP logUdp;

unsigned int  tmp;

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

   // Init inputs
   for (x=0; x < InputCount; x++) {
      pinMode(InputPin[x],INPUT_PULLUP);
      inputLevel[x] = 0;
      inputRaw[x]   = 0;
      inputTime[x]  = millis();
   }

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

            delay(10);
         }
      }

      inputRaw[x] = tmp;
   }

   // Refresh digital values
   if ( (currTime - lastDigital) > DigitalPeriod) {
      logPrintf("Updating digital values.");

      for (x=0; x < InputCount; x++) {
         if (inputLevel[x] == 1 )
            client.publish(InputStatTopic[x],"ON");
         else
            client.publish(InputStatTopic[x],"OFF");
         delay(10);
      }

      lastDigital = currTime;
      sprintf(valueStr,"%i",wifiPct());
      logPrintf("Wifi strenth = %s",valueStr);
      client.publish(WifiTopic,valueStr);
   }
}

