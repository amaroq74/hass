// include the library code:
#include <string.h>
#include <avr/wdt.h>

// Define for revsion 1 board
// Comment out for revision 2 board
#define REV1

// Setup pins
const unsigned int relayCount           = 6;
const unsigned int relayPin[relayCount] = {3,2,5,4,7,6};
const unsigned int inputCount           = 4;

#ifdef REV1
const unsigned int digitalCount         = 4;
const unsigned int inputPin[inputCount] = {8,9,10,11};
#else
const unsigned int digitalCount         = 2;
const unsigned int inputPin[inputCount] = {8,9,2,1};
#endif

const unsigned int tempPin  = 0;  // Analog 0
const unsigned int txLedPin = 12;
const unsigned int rxLedPin = 13;

// Setup constants
const unsigned int  relayPulse     = 50;
const unsigned int  relayOff       = 0;
const unsigned int  relayOn        = 100;
const unsigned long ledBlinkTime   = 100;    // 0.1  second
const unsigned long relayPulseTime = 500;    // 0.5  seconds
const unsigned long msgRxTimeout   = 300000; // 5    minutes
const unsigned long minMsgPeriod   = 1000;   // 1    second
const unsigned long debounceTime   = 250;    // 0.25 second
const unsigned long analogPeriod   = 10;     // 10   msec
const unsigned long averagePeriod  = 10000;  // 10   seconds

///////////////////////////////////////////////////////////////////////////

// TX/RX Buffer
String txBuffer;
String rxBuffer;

// Variables
unsigned int  reqRelState[relayCount];
unsigned int  curRelState[relayCount];
unsigned long curRelTime[relayCount];

unsigned int  curInState[inputCount];
unsigned long rawInState[inputCount];
unsigned long rawInTime[inputCount];

unsigned long minMsgTime;
unsigned long msgRxTime;

unsigned long txLedTime;
unsigned long rxLedTime;

unsigned long analogTime;
unsigned long averageTime;
unsigned long averageCount;
unsigned long rawTemp;
unsigned int  curTemp;

unsigned long currTime;

unsigned int  x;
unsigned int  txReq;
unsigned int  tmp;
char          mark[20];
int           ret;

// Initialize
void setup() {

   // Setup and init outputs
   for (x=0; x < relayCount; x++) {
      pinMode(relayPin[x],OUTPUT);
      digitalWrite(relayPin[x],LOW);
      reqRelState[x] = 0;
      curRelState[x] = 0;
      curRelTime[x]  = millis();
   }

   // Setup digital inputs
   for (x=0; x < digitalCount; x++) {
      pinMode(inputPin[x],INPUT);
      digitalWrite(inputPin[x],HIGH); // Enable pullup
      curInState[x] = 0;
      rawInState[x] = 0;
      rawInTime[x]  = millis();
   }

   // Setup analog inputs
   for (x=digitalCount; x < inputCount; x++) {
      curInState[x] = 0;
      rawInState[x] = 0;
      rawInTime[x]  = millis();
   }

   // Setup LEDs, turn on
   pinMode(txLedPin,OUTPUT);
   digitalWrite(txLedPin,LOW);
   pinMode(rxLedPin,OUTPUT);
   digitalWrite(rxLedPin,LOW);
   rxLedTime = millis();
   txLedTime = millis();

   // Init variables
   txBuffer     = "";
   rxBuffer     = "";
   minMsgTime   = 0;
   msgRxTime    = 0;
   averageCount = 0;
   analogTime   = millis();
   averageTime  = millis();

   rawTemp = 0;
   curTemp = 0;

   // start serial
   Serial.begin(115200);

   // Enable watchdog timer
   wdt_enable(WDTO_8S);
}

// Main loop
void loop() {
   txReq = 0;

   // Get current time
   currTime = millis();

   // LED to be turned off
   if ( (currTime - rxLedTime) > ledBlinkTime ) digitalWrite(rxLedPin,HIGH);
   if ( (currTime - txLedTime) > ledBlinkTime ) digitalWrite(txLedPin,HIGH);

   // Poll timer
   if ( (currTime - minMsgTime) > minMsgPeriod ) txReq = 1;

   // Get serial data
   while (Serial.available()) rxBuffer += Serial.read();

   // Check for incoming message
   if ( rxBuffer.length() > 6 && rxBuffer.endsWith("\n") ) {

      // Parse string
      ret = sscanf(rxBuffer.c_str(),"%s %i %i %i %i %i %i", 
                   mark, &(reqRelState[0]), &(reqRelState[1]), &(reqRelState[2]),
                   &(reqRelState[3]), &(reqRelState[4]), &(reqRelState[5]));
      rxBuffer = "";

      // Check marker
      if ( ret == 7 && strcmp(mark,"STATE") == 0 ) {

         // Update state
         for (x=0; x < relayCount; x++) {
            if (curRelState[x] != relayPulse ) {
               curRelState[x] = reqRelState[x];
               curRelTime[x]  = currTime;
            }

            // Turn on RX LED
            digitalWrite(rxLedPin,LOW);
            msgRxTime = currTime;
            rxLedTime = currTime;
         }

         // Immediate reply
         txReq = 1;
      }
   }

   // Bad message
   else if ( rxBuffer.length() > 40 ) rxBuffer = "";

   // Update relay states
   for (x=0; x < relayCount; x++) {

      // Receiver timeout, turn off all outputs
      if ( (currTime - msgRxTime ) > msgRxTimeout ) 
         curRelState[x] = relayOff;

      // Turn off pulsed outputs
      if ( (curRelState[x] == relayPulse) && ((currTime - curRelTime[x]) > relayPulseTime) ) 
         curRelState[x] = relayOff;

      if ( curRelState[x] == relayOn || curRelState[x] == relayPulse ) digitalWrite(relayPin[x],HIGH);
      else digitalWrite(relayPin[x],LOW);
   }

   // Read digital input states
   for (x=0; x < digitalCount; x++) {
      if ( digitalRead(inputPin[x]) == 0 ) tmp = 1;
      else tmp = 0;

      // Digital Input Debounce
      if ( tmp != rawInState[x]) rawInTime[x] = currTime;

      // Input is stable
      if ( (currTime - rawInTime[x]) > debounceTime ) {

         // State changed
         if ( rawInState[x] != curInState[x] ) txReq = 1;

         // Update state
         curInState[x] = rawInState[x];
      }
   
      rawInState[x] = tmp;
      txReq = 1;
   }

   // Analog sample period
   if ((currTime - analogTime) > analogPeriod ) {
      analogTime = currTime;
      averageCount += 1;

      // Read raw analog input states
      for (x=digitalCount; x < inputCount; x++) {
         analogRead(inputPin[x]);
         delay(10);
         rawInState[x] += analogRead(inputPin[x]);
      }

      // Read Temperature value
      analogRead(tempPin);
      delay(10);
      rawTemp += analogRead(tempPin);
   }

   // Analog input average
   if ( (currTime - averageTime) > averagePeriod ) {
      for (x=digitalCount; x < inputCount; x++) {
         curInState[x] = rawInState[x] / averageCount; 
         rawInState[x] = 0;
      }

      curTemp = rawTemp / averageCount;
      rawTemp = 0;

      averageCount = 0;
      averageTime = currTime;
   }

   // Transmit if requested
   if ( txReq == 1 ) {

      // Setup message
      txBuffer  = "STATUS";
      for (x=0; x < 4; x++) txBuffer += " " + String(curInState[x]);
      txBuffer += " " + String(curTemp) + "\n";

      // Send message
      Serial.write(txBuffer.c_str());

      // Turn on TX LED
      digitalWrite(txLedPin,LOW);
      txLedTime  = currTime;
      minMsgTime = currTime;
   }

   // Pet the dog
   wdt_reset();
}

