// include the library code:
#include <string.h>
#include <avr/wdt.h>

// Define for revsion 1 board
// Comment out for revision 2 board
#define REV1

// Setup pins
const unsigned int relCnt         = 6;
const unsigned int relPin[relCnt] = {3,2,5,4,7,6};
const unsigned int inCnt          = 4;

#ifdef REV1
const unsigned int digCnt         = 4;
const unsigned int inPin[inCnt]   = {8,9,10,11};
#else
const unsigned int digCnt         = 2;
const unsigned int inPin[inCnt]   = {8,9,2,1};
#endif

const unsigned int tempPin        = 0;  // Analog 0
const unsigned int txLedPin       = 12;
const unsigned int rxLedPin       = 13;

// Setup constants
const unsigned int  relPulse     = 50;
const unsigned int  relOff       = 0;
const unsigned int  relOn        = 100;
const unsigned long ledBlinkTime = 1000;    // 1 second
const unsigned long relPulseTime = 500;     // 0.5 seconds
const unsigned long rxTimeout    = 300000;  // 5 minutes
const unsigned long pollPeriod   = 30000;   // 30 seconds

// TX/RX Buffer
String txBuffer;
String rxBuffer;

// Variables
unsigned int  relState[relCnt];
unsigned int  newState[relCnt];
unsigned long relTime[relCnt];
unsigned int  inState[inCnt];
unsigned long pollTime;
unsigned long txLedTime;
unsigned long rxLedTime;
unsigned int  tempValue;
unsigned long currTime;
unsigned long rxTime;
unsigned int  x;
unsigned int  txReq;
unsigned int  tmp;
char          mark[20];
int           ret;

// Initialize
void setup() {

   // Setup and init outputs
   for (x=0; x < relCnt; x++) {
      pinMode(relPin[x],OUTPUT);
      digitalWrite(relPin[x],LOW);
      relState[x] = 0;
      relTime[x]  = 0;
   }

   // Setup digital inputs
   for (x=0; x < digCnt; x++) {
      pinMode(inPin[x],INPUT);
      digitalWrite(inPin[x],HIGH); // Enable pullup
      inState[x] = 0;
   }

   // Setup analog inputs
   for (x=digCnt; x < inCnt; x++) inState[x] = 0;

   // Setup LEDs, turn on
   pinMode(txLedPin,OUTPUT);
   digitalWrite(txLedPin,LOW);
   pinMode(rxLedPin,OUTPUT);
   digitalWrite(rxLedPin,LOW);
   rxLedTime = 0;
   txLedTime = 0;

   // Init variables
   txBuffer  = "";
   rxBuffer  = "";
   pollTime  = 0;
   tempValue = 0;
   rxTime    = 0;

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

   // Detect timer rollover
   if ( currTime < rxLedTime ) rxLedTime = currTime;
   if ( currTime < txLedTime ) txLedTime = currTime;
   if ( currTime < rxTime    ) rxTime    = currTime;
   if ( currTime < pollTime  ) pollTime  = currTime;
   for (x=0; x < relCnt; x++) {
      if (currTime < relTime[x] ) relTime[x] = currTime;
   }

   // LED to be turned off
   if ( (currTime - rxLedTime) > ledBlinkTime ) digitalWrite(rxLedPin,HIGH);
   if ( (currTime - txLedTime) > ledBlinkTime ) digitalWrite(txLedPin,HIGH);

   // Pulsed relay output to off state
   for (x=0; x < relCnt; x++) {
      if ( relState[x] == relPulse && ((currTime - relTime[x]) > relPulseTime) ) relState[x] = relOff;
   }

   // Receiver timeout, turn off all outputs
   if ( (currTime - rxTime ) > rxTimeout ) {
      for (x=0; x < relCnt; x++) relState[x] = relOff;
      rxTime = currTime;
   }

   // Poll timer
   if ( (currTime - pollTime) > pollPeriod ) txReq = 1;

   // Get serial data
   while (Serial.available()) rxBuffer += Serial.read();

   // Check for incoming message
   if ( rxBuffer.length() > 5 && rxBuffer.endsWith("\n") ) {

      // Parse string
      ret = sscanf(rxBuffer.c_str(),"%s %i %i %i %i %i %i", mark, &(newState[0]), &(newState[1]), &(newState[2]),
                                                            &(newState[3]), &(newState[4]), &(newState[5]));
      rxBuffer = "";

      // Check marker
      if ( ret == 7 && strcmp(mark,"STATE") == 0 ) {

         // Update state
         for (x=0; x < relCnt; x++) {
            if (relState[x] != relPulse ) {
               relState[x] = newState[x];
               relTime[x] = currTime;
            }

            // Turn on RX LED
            digitalWrite(rxLedPin,LOW);
            rxTime    = currTime;
            rxLedTime = currTime;
         }
      }
   }

   // Bad message
   else if ( rxBuffer.length() > 40 ) rxBuffer = "";

   // Update relay states
   for (x=0; x < relCnt; x++) {
      if ( relState[x] == relOn || relState[x] == relPulse ) digitalWrite(relPin[x],HIGH);
      else digitalWrite(relPin[x],LOW);
   }

   // Read digital input states
   for (x=0; x < digCnt; x++) {

      // Read current value
      if ( digitalRead(inPin[x]) == 0 ) tmp = 1;
      else tmp = 0;

      // State change
      if ( inState[x] != tmp ) txReq = 1;
      inState[x] = tmp;
   }

   // Read Temperature value
   analogRead(tempPin);
   delay(10);
   tempValue = analogRead(tempPin);

   // Read analog input states
   for (x=digCnt; x < inCnt; x++) {
      analogRead(inPin[x]);
      delay(10);
      inState[x] = analogRead(inPin[x]);
   }

   // Transmit if requested
   if ( txReq == 1 ) {

      // Setup message
      txBuffer  = "STATUS";
      for (x=0; x < 4; x++) txBuffer += " " + String(inState[x]);
      txBuffer += " " + String(tempValue);
      for (x=0; x < 6; x++) txBuffer += " " + String(relState[x]);
      txBuffer += "\n";

      // Send message
      Serial.write(txBuffer.c_str());

      // Turn on TX LED
      digitalWrite(txLedPin,LOW);
      txLedTime = currTime;
      pollTime = currTime;
   }

   // Pet the dog
   wdt_reset();
}

