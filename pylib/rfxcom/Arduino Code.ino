// Weather Station & Power Monitor
// Chris Wicks 2011/12
// Oregon decoder by Dominique Pierre at JeeLabs (thanks for all his support and help).

#include <SdFat.h>
#include <Ethernet.h>
#include <SPI.h>
#include <Wire.h>
#include <RTClib.h>
#include <EEPROM.h>
#include <EEPROMAnything.h>
#include <TimeLord.h>

//Set up the RTC
RTC_DS1307 RTC;

//Set up general variables
#define BUFSIZ 100
#define MAX_STRING_LEN  20
#define BMP085_ADDRESS 0x77  // I2C address of BMP085
int OutTempNow=-999;
int OutHumNow=-999;
int UVNow=-999;
int GustNow=-999;
int AverageNow=-999;
int DirectionNow=-999;
int BarrometerNow=-999;
String Forecast="";
int InTempNow=-999;
int InHumNow=-999;
String Comfort="";
int CH1TempNow=-999;
int CH1HumNow=-999;
int CH2TempNow=-999;
int CH2HumNow=-999;
int CH3TempNow=-999;
int CH3HumNow=-999;
int RainRateNow=-999;
int TotalRainFrom0000=0;
int TotalRainHour=0;
int PowerNow=0;
int RainDaysMonth=-999;
int RainTotalMonth=-999;
int OutTempBat=100;
int UVBat=100;
int WindBat=100;
int RainBat=100;
int InTempBat=100;
int CH1Bat=100;
int CH2Bat=100;
int CH3Bat=100;
String CH1Name = "Room 1";
String CH2Name = "Room 2";
String CH3Name = "Room 3";
String IndoorName = "Room 4";
float PF=0.71;
float TotalPower24 = 0;
float TotalPowerHr = 0;
int MaxTemp24=-999;
int MinTemp24=999;
int MaxGust24=-999;
int Direction24=-999;
int MaxPower24=-999;
int MaxUV24=-999;
long PreviousTime;
long UVTime = 0;
long WindTime = 0;
long OutTime = 0;
long RainTime = 0;
long InTime = 0;
long CH1Time = 0;
long CH2Time = 0;
long CH3Time = 0;
long PowerTime = 0;
long WindTriggerTime = 0;
long TempTriggerTime = 0;
int TempTriggerMax=150; //temp * 10
int TempTriggerMin=0;
int WindTrigger=15; //mph
boolean WindTriggerFlag = false;
boolean TempTriggerMaxFlag = false;
boolean TempTriggerMinFlag = false;
extern volatile unsigned long timer0_overflow_count;
int Trends [14] [24] [2] = {-999}; //Item, Hour, 24/48
int OldRainTotal=0;
char LogMonth[3], LogDay[3], LogHour[3], LogMinute[3], LogSecond[3], PrintDay[3], PrintMonth[3];
char ExtremeMonth[3], ExtremeDay[3], ExtremeTime[3];
int monat, yeaat;
char charbuffermonat[4],charbufferyeaat[4];
boolean WriteFlag = false;
boolean PowerFlag = false;
boolean Extreme24Flag = false;
boolean ExtremeYearFlag = false;
boolean RainNewFlag = true;
String MyTag="";
DateTime now;

//Log compile time for reference
char compiledate[] = __DATE__;
char compiletime[] = __TIME__;

//Set up BMP085 if instaled
//const unsigned char OSS = 0;  // Oversampling Setting
// Calibration values
//int ac1;
//int ac2;
//int ac3;
//unsigned int ac4;
//unsigned int ac5;
//unsigned int ac6;
//int b1;
//int b2;
//int mb;
//int mc;
//int md;
//long b5; 

//Set up variable list for the max and min yearly data
struct config_t
{
  int MaxTempY;
  long MaxTempYD;
  int MinTempY;
  long MinTempYD;
  int MaxGustY;
  int DirectionY;
  long WindYD;
  float TotalPowerY;
  int TotalRainY;
} YearData;


String Myversion = "1.2<br>&#169;Chris Wicks 2011/12<br>Compiled on Arduino 1.0";

//Set Up Ethernet
byte mac[] = {Your MAC Address }; //change to your MAC address on the Ethernet Shield
char serverName[] = "www.host.com"; //host web site for the php files to enable emails
EthernetServer server(9876); //select the port you wish to use
EthernetClient client; 

//Setp Up Moon Phase data
TimeLord SuriseLocation;
double Ln = 50.0;
double Lw = 0.0;
byte IsToDay[]  = {0, 0, 12, 1,1 , 2000};

//Set up SD card
int cardSize;
Sd2Card card;
SdVolume volume;
SdFile root;
SdFile logfile;
SdFile html;
SdFile file;
SdFat sd;

//OOK Deoder from http://jeelabs.net/projects/11/wiki/Decoding_the_Oregon_Scientific_V2_protocol
class DecodeOOK {
protected:
  byte total_bits, bits, flip, state, pos, Min_bits, data[25];
  virtual char decode (word width) =0;

public:
  enum {
    UNKNOWN, T0, T1, T2, T3, OK, DONE     };

  DecodeOOK () {
    resetDecoder(); 
  }

  bool nextPulse (word width) {
    if (state != DONE)

      switch (decode(width)) {
      case -1: 
        resetDecoder(); 
        break;
      case 1:  
        done(); 
        break;
      }
    return isDone();
  }

  bool isDone () const { 
    return state == DONE; 
  }

  const byte* getData (byte& count) const {
    count = pos;
    return data; 
  }

  void resetDecoder () {
    total_bits = bits = pos = flip = 0;
    state = UNKNOWN;
  }

  // add one bit to the packet data buffer

  virtual void gotBit (char value) {
    total_bits++;
    byte *ptr = data + pos;
    *ptr = (*ptr >> 1) | (value << 7);

    if (++bits >= 8) {
      bits = 0;
      if (++pos >= sizeof data) {
        resetDecoder();
        return;
      }
    }
    state = OK;
  }

  // store a bit using Manchester encoding
  void manchester (char value) {
    flip ^= value; // manchester code, long pulse flips the bit
    gotBit(flip);
  }

  // move bits to the front so that all the bits are aligned to the end
  void alignTail (byte Min =0) {
    // align bits
    if (bits != 0) {
      data[pos] >>= 8 - bits;
      for (byte i = 0; i < pos; ++i)
        data[i] = (data[i] >> bits) | (data[i+1] << (8 - bits));
      bits = 0;
    }
    // optionally shift bytes down if there are too many of 'em
    if (Min > 0 && pos > Min) {
      byte n = pos - Min;
      pos = Min;
      for (byte i = 0; i < pos; ++i)
        data[i] = data[i+n];
    }
  }

  void reverseBits () {
    for (byte i = 0; i < pos; ++i) {
      byte b = data[i];
      for (byte j = 0; j < 8; ++j) {
        data[i] = (data[i] << 1) | (b & 1);
        b >>= 1;
      }
    }
  }

  void reverseNibbles () {
    for (byte i = 0; i < pos; ++i)
      data[i] = (data[i] << 4) | (data[i] >> 4);
  }

  void done () {
    while (bits)
      gotBit(0); // padding
    state = DONE;
  }
};

class OregonDecoderV2 : 
public DecodeOOK {
public:
  OregonDecoderV2() {
    Min_bits = 160;
  }

  // add one bit to the packet data buffer
  virtual void gotBit (char value) {
    if(!(total_bits & 0x01))
    {
      data[pos] = (data[pos] >> 1) | (value ? 0x80 : 00);
    }
    total_bits++;
    pos = total_bits >> 4;
    if(2 == pos)
    {
      // 80 * 2
      Min_bits = 160;
      if(0xEA == data[0])  Min_bits = 240;
      if(0x5A == data[0])  Min_bits = 176;
    }
    if (pos >= sizeof data) {
      resetDecoder();
      return;
    }
    state = OK;
  }

  virtual char decode (word width) {
    if (200 <= width && width < 1200) {
      byte w = width >= 700;
      switch (state) {
      case UNKNOWN:
        if (w != 0) {
          // Long pulse
          ++flip;
        } 
        else if (16 <= flip) {
          // Short pulse, start bit
          flip = 0;
          state = T0;
        } 
        else {
          // Reset decoder
          return -1;
        }
        break;
      case OK:
        if (w == 0) {
          // Short pulse
          state = T0;
        } 
        else {
          // Long pulse
          manchester(1);
        }
        break;
      case T0:
        if (w == 0) {
          // Second short pulse
          manchester(0);
        } 
        else {
          // Reset decoder
          return -1;
        }
        break;
      }
    } 
    else {
      return -1;
    }
    return total_bits == Min_bits ? 1: 0;
  }
};

class OregonDecoderV3 : 
public DecodeOOK {
public:
  OregonDecoderV3() {
  }

  // add one bit to the packet data buffer
  virtual void gotBit (char value) {
    data[pos] = (data[pos] >> 1) | (value ? 0x80 : 00);
    total_bits++;
    pos = total_bits >> 3;
    if (pos >= sizeof data) {
      resetDecoder();
      return;
    }
    state = OK;
  }

  virtual char decode (word width) {
    if (200 <= width && width < 1200) {
      byte w = width >= 700;
      switch (state) {
      case UNKNOWN:
        if (w == 0)
          ++flip;
        else if (32 <= flip) {
          flip = 1;
          manchester(1);
        } 
        else
          return -1;
        break;
      case OK:
        if (w == 0)
          state = T0;
        else
          manchester(1);
        break;
      case T0:
        if (w == 0)
          manchester(0);
        else
          return -1;
        break;
      }
    } 
    else {
      return -1;
    }
    return  total_bits == 80 ? 1: 0;
  }
};

/*class CrestaDecoder : public DecodeOOK {
  public: CrestaDecoder () {}
      
  virtual char decode (word width) {
    if (pos > 0 && data[0] != 0x75) {
      //packets start with 0x75!
      return -1;
    }

    if (200 <= width && width < 1300) {
      byte w = width >= 750;
      switch (state) {
      case UNKNOWN:
      case OK:
        if (w == 0)
          state = T0;
        else
          manchester(1);
        break;
      case T0:
        if (w == 0)
          manchester(0);
        else
          return -1;
        break;
      }

      if (pos > 6) {
        byte len = 3 + ((data[2] >> 1) & 0x1f); //total packet len
        byte csum = 0;
        for (byte x = 1; x < len-1; x++) {
          csum ^= data[x];
        }

        if (len == pos) {
          if (csum == 0) {
            return 1;
          } 
          else {
            return -1;
          }
        }
      } 
    } 
    else return -1;
    return 0;
  }
};*/

volatile word pulse;

//CrestaDecoder cres;
OregonDecoderV2 orscV2;
OregonDecoderV3 orscV3;

void ext_int_1(void) {
  static word last;
  // determine the pulse length in microseconds, for either polarity
  pulse = micros() - last;
  last += pulse;
}

void reportSerial (const char* s, class DecodeOOK& decoder) {

  //Get Time from RTC
  now = RTC.now();  
  formatTimeDigits(LogMonth, now.month());
  formatTimeDigits(LogDay, now.day());
  formatTimeDigits(LogHour, now.hour());
  formatTimeDigits(LogMinute, now.minute());
  formatTimeDigits(LogSecond, now.second());

  //get pressure and indoor temp from BMP085
  //InTempNow = (bmp085GetTemperature(bmp085ReadUT())*10); //MUST be called first
  //PressureNow = (bmp085GetPressure(bmp085ReadUP())+50)/100; //round up and convert pascals to mbar
  
  byte pos;    
  const byte* data = decoder.getData(pos);
    
  //Serial.print(LogHour);
  //Serial.print(":");
  //Serial.print(LogMinute);
  //Serial.print(":");
  //Serial.print(LogSecond);
  //Serial.print("  ");

  for (byte i = 0; i < pos; ++i) {
      //Serial.print(data[i] >> 4, HEX);
      //Serial.print(data[i] & 0x0F, HEX);
  }
  
  //General note where possible, values multiplied by 10 to give integers to 1 dcimal point when divided by 10 later.  Less memory hungry.
  
  // OWL Electricty Meter
  if (data[0] == 0x06 && data[1] == 0xC8) {
    //Serial.print("Current ");
    PowerNow = (data[3] + ((data[4] & 0x03)*256));
    //Serial.print(float(PowerNow)/10,1);
    //Serial.println("amps"); 
    int Duration = now.unixtime()-PreviousTime;
    float ActualPower = Duration * ((PowerNow * 240 * PF)/36000.0);
    if (ActualPower < 0) ActualPower = -ActualPower;
    if (ActualPower > 0) {  
      TotalPowerHr += ActualPower; //W/s
      TotalPower24 += ActualPower; //W/s
      YearData.TotalPowerY += ActualPower;
      PreviousTime = now.unixtime();
      PowerTime = now.unixtime();
      //Serial.print("Added... ");
      //Serial.print(ActualPower);
      //Serial.print("W (over ");
    }
    //Serial.print(Duration);
    //Serial.print(" seconds). Total Today ");
    //Serial.print(TotalPower24,0);
    //Serial.println("W/hs ");
    //Check Extremes
    if (PowerNow > MaxPower24 && PowerNow != -999) {
      MaxPower24 = PowerNow;
    }
  }

  // WGR918 Annometer
  if (data[0] == 0x3A && data[1] == 0x0D) {
    //Checksum - add all nibbles from 0 to 8, subtract A and compare to byte 9, should = 0
    int cs = 0;
    for (byte i = 0; i < pos-1; ++i) { //all but last byte
        cs += data[i] >> 4;
        cs += data[i] & 0x0F;
    }
    int csc = ((data[9] >> 4)*16) + (data[9] & 0x0F);
    cs -= 10;
    //Serial.print(csc); 
    //Serial.print(" vs ");   
    //Serial.println(cs); 
    if (cs == csc){ //if checksum is OK
      //Serial.print("Direction ");
      DirectionNow = ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + (data[4] >> 4);    
      //Serial.print(DirectionNow);
      //Serial.print(" degrees  Current Speed (Gust) ");
      GustNow = ((data[7] & 0x0F) * 100)  + ((data[6]>>4) * 10)  + ((data[6] & 0x0F)) ;
      //Serial.print(float(GustNow)/10,1);   
      //Serial.print("m/s  Average Speed ");
      AverageNow = ((data[8]>>4) * 100)  + ((data[8] & 0x0F) * 10)+((data[7] >>4)) ;      
      //Serial.print(float(AverageNow)/10,1); 
      //Serial.print("m/s  Battery ");      
      WindBat=(10-(data[4] & 0x0F))*10;
      //Serial.print(WindBat);
      //Serial.println("%");
      // Check Extremes
      WindTime = now.unixtime();
      if (GustNow > MaxGust24 && GustNow != -999) {
        MaxGust24 = GustNow; 
        Direction24 = DirectionNow;
        //Serial.print("MaxGust today ");
        //Serial.println(MaxGust24);
      }
      if (MaxGust24 > YearData.MaxGustY && GustNow != -999) {
        YearData.MaxGustY = MaxGust24; 
        YearData.DirectionY = Direction24; 
        YearData.WindYD = now.unixtime();
        //Serial.print("MaxGust this Year ");
        //Serial.println(YearData.MaxGustY);
      }
      // Check Triggers
      if ((float(AverageNow)/10)*2.2369362920544025 > WindTrigger && WindTriggerFlag == false){
        WindTriggerFlag = true; //stops multiple emails for same excursion
        WindTriggerTime=now.unixtime() + 7200; //2 hours
        SendEmail(1);
      }
      if (((float(AverageNow)/10)*2.2369362920544025 < WindTrigger) && (now.unixtime() > WindTriggerTime )){ 
        WindTriggerFlag = false;
      } 	
    }  
  }

  //RGR918 Rain Guage 
  if (data[0] == 0x2A && data[1] == 0x1D) {
    //Checksum - add all nibbles from 0 to 8, subtract 9 and compare, should = 0
    //Serial.print(" - ");
    int cs = 0;
    for (byte i = 0; i < pos-2; ++i) { //all but last byte
        cs += data[i] >> 4;
        cs += data[i] & 0x0F;
    }
    int csc = (data[8] >> 4) + ((data[9] & 0x0F)*16);    
    cs -= 9;  //my version as A fails?
    //Serial.print(csc); 
    //Serial.print(" vs ");   
    //Serial.println(cs);
    if (cs == csc){ //if checksum is OK      
      //Serial.print("Rain ");
      RainRateNow = ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + (data[4] >> 4);
      //Serial.print(RainRateNow);
      //Serial.print("mm/hr  Total ");
      int RainTotal = ((data[7]  >> 4) * 10)  + (data[6]>>4);
      RainTime = now.unixtime();
      if (RainTotal != OldRainTotal){
        if (RainNewFlag == false){  //Stops 1st reading going through and giving additonal values
          TotalRainFrom0000 += 1;
          TotalRainHour += 1;
          YearData.TotalRainY += 1;
          SendEmail(2);
        }
        OldRainTotal=RainTotal;
        RainNewFlag=false;
      }
      //Serial.print(TotalRainFrom0000);   
      //Serial.print(" ");
      //Serial.print(RainTotal); 
      //Serial.print(" ");
      //Serial.print(OldRainTotal); 
      //Serial.print("mm  Battery ");
      if ((data[4] & 0x0F) >= 4){
        RainBat=0;
        //Serial.println("Low"); 
      }
      else
      {
        RainBat=100;
        //Serial.println("OK"); 
      }          
    }
  }  

  //UV138
  if (data[0] == 0xEA && data[1] == 0x7C) {
    //Serial.print("UV ");
    UVNow = ((data[5] & 0x0F) * 10)  + (data[4] >> 4);
    UVTime = now.unixtime();
    //Serial.print(UVNow);
    //Serial.print("  Battery ");
    if ((data[4] & 0x0F) >= 4){
      UVBat=0;
      //Serial.println("Low"); 
    }
    else
    {
      UVBat=100;
      //Serial.println("OK"); 
    }  
    //Check Extremes
    if (UVNow > MaxUV24 && UVNow != -999) {
      MaxUV24 = UVNow;
    }    
  }  

  //THGR228N Inside Temp-Hygro
  if (data[0] == 0x1A && data[1] == 0x2D) {
    int battery=0;
    int celsius= ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + ((data[4] >> 4));
    if ((data[6] & 0x0F) >= 8) celsius=-celsius;
    int hum = ((data[7] & 0x0F)*10)+ (data[6] >> 4);
    if ((data[4] & 0x0F) >= 4){
      battery=0;
    }
    else
    {
      battery=100;
    }   
    //Serial.print("Additional Channel ");
    switch (data[2]) {
    case 0x10:
      CH1TempNow=celsius;
      CH1HumNow=hum;
      CH1Bat=battery;
      CH1Time = now.unixtime();
      //Serial.print("1  ");
      break;
    case 0x20:
      CH2TempNow=celsius;
      CH2HumNow=hum;
      CH2Bat=battery;
      CH2Time = now.unixtime();
      //Serial.print("2  ");
      break;
    case 0x40:
      CH3TempNow=celsius;
      CH3HumNow=hum;
      CH3Bat=battery;
      CH3Time = now.unixtime();
      //Serial.print("3  ");
      break;
    }    
    //Serial.print(float(celsius)/10,1);
    //Serial.print("C  Humidity ");
    //Serial.print(hum);
    //Serial.print("%  Battery ");  
    //Serial.print(battery);
    //Serial.println("%");      
  }   

  //THGR918  Outside Temp-Hygro
  if (data[0] == 0x1A && data[1] == 0x3D) {
    //Checksum - add all nibbles from 0 to 8, subtract 9 and compare, should = 0
    //Serial.print(" - ");
    int cs = 0;
    for (byte i = 0; i < pos-2; ++i) { //all but last byte
      cs += data[i] >> 4;
      cs += data[i] & 0x0F;
    }
    int csc = ((data[8] >> 4)*16) + (data[8] & 0x0F);    
    cs -= 10; 
    //Serial.print(csc); 
    //Serial.print(" vs ");   
    //Serial.println(cs);
    if (cs == csc){ //if checksum is OK 
      //Serial.print("Outdoor temperature ");
      OutTempNow= ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + ((data[4] >> 4));
      if ((data[6] & 0x0F) >= 8) OutTempNow=-OutTempNow;
      //Serial.print(float(OutTempNow)/10,1);
      //Serial.print("C  Humidity ");
      OutHumNow = ((data[7] & 0x0F)*10)+ (data[4] >> 4);
      //Serial.print(OutHumNow);
      //Serial.print("%  Battery ");
      OutTempBat=(10-(data[4] & 0x0F))*10;
      //Serial.print(OutTempBat);
      //Serial.println("%");
      OutTime = now.unixtime();
      //Check Extremes
      if (OutTempNow > MaxTemp24 && OutTempNow != -999) {
        MaxTemp24 = OutTempNow;
      }
      if (OutTempNow < MinTemp24 && OutTempNow != -999) {
        MinTemp24 = OutTempNow;
      }
      if (MaxTemp24 > YearData.MaxTempY && OutTempNow != -999) {
        YearData.MaxTempY = MaxTemp24; 
        YearData.MaxTempYD = now.unixtime();
      }
      if (MinTemp24 < YearData.MinTempY && OutTempNow != -999) {
        YearData.MinTempY = MinTemp24; 
        YearData.MinTempYD = now.unixtime();
      }
      // Check Triggers
      if (OutTempNow > TempTriggerMax && TempTriggerMaxFlag == false){
        TempTriggerMaxFlag = true; //stops multiple emails for same excursion
        TempTriggerTime=now.unixtime() + 7200; //2 hours
        SendEmail(3);
      }
      if ((OutTempNow < TempTriggerMax) && (now.unixtime() > TempTriggerTime)){ 
        TempTriggerMaxFlag = false;
      }  
      if (OutTempNow < TempTriggerMin && TempTriggerMinFlag == false){
        TempTriggerMinFlag = true; //stops multiple emails for same excursion
        TempTriggerTime=now.unixtime() + 7200;  //2 hours
        SendEmail(4);
      }
      if ((OutTempNow > TempTriggerMin)&& (now.unixtime() > TempTriggerTime)){ 
        TempTriggerMinFlag = false;
      } 
    }
  }
  

  //BTHR918 Temp-Hygro-Baro
  if (data[0] == 0x5A && data[1] == 0x6D) {
    //Serial.print("Indoor temperature ");
    InTempNow= ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + ((data[4] >> 4));
    if ((data[6] & 0x0F) >= 8) InTempNow=-InTempNow;
    //Serial.print(float(InTempNow)/10,1);
    //Serial.print("C  Humidity ");
    InHumNow = ((data[7] & 0x0F)*10)+ (data[6] >> 4);
    //Serial.print(InHumNow);
    //Serial.print("%  Pressure ");
    BarrometerNow = (data[8])+856;
    //Serial.print(BarrometerNow);
    //Serial.print("hPa  ");
    switch (data[7] & 0xC0) {
    case 0x00:
      Comfort="Normal";
      break;
    case 0x40:
      Comfort="Comfortable";
      break;
    case 0x80:
      Comfort="Dry";
      break;
    case 0xC0:
      Comfort="Wet";
      break;
    }
    //Serial.print(Comfort);
    //Serial.print("  ");
    switch (data[9] >> 4) {
    case 0x0C:
      Forecast="Sunny";
      break;
    case 0x06:
      Forecast="Partly Cloudy";
      break;
    case 0x02:
      Forecast="Cloudy";
      break;
    case 0x03:
      Forecast="Wet";
      break;
    }     
    InTime = now.unixtime();
    //Serial.print(Forecast);
    //Serial.print("  Battery ");               
    InTempBat=(10-(data[4] & 0x0F))*10;
    //Serial.print(InTempBat);
    //Serial.println("%");      
  } 
  
  /*
  //Outside Temp - Cresta
  if (data[1] >= 0x20 && data[1] <= 0x3F) {
    //Serial.print(" Outdoor temperature ");
    OutTempNow= ((data[5]& 0x0F) * 100)  + ((data[4] & 0x0F)) + ((data[4] >> 4)*10);
    if ((data[5] >> 4) != 12) OutTempNow=-OutTempNow;
    //Serial.print(float(OutTempNow)/10,1);
    //Serial.println("C");
    OutTime = now.unixtime();
    //Check Extremes
    if (OutTempNow > MaxTemp24 && OutTempNow != -999) {
      MaxTemp24 = OutTempNow;
    }
    if (OutTempNow < MinTemp24 && OutTempNow != -999) {
      MinTemp24 = OutTempNow;
    }
    if (OutTempNow > YearData.MaxTempY && OutTempNow != -999) {
      YearData.MaxTempY = OutTempNow; 
      YearData.MaxTempYD = now.unixtime();
    }
    if (OutTempNow < YearData.MinTempY && OutTempNow != -999) {
      YearData.MinTempY = OutTempNow; 
      YearData.MinTempYD = now.unixtime();
    }
  }
  else
  {
    //Rain Guage - Cresta
    //Serial.print(" Rain ");
    //RainRateNow = ((data[5]>>4) * 100)  + ((data[5] & 0x0F) * 10) + (data[4] >> 4);
    ////Serial.print("mm/hr  Total ");
    int RainTotal = (data[5]*256)+data[4];
    RainTime = now.unixtime();
    if (RainTotal != OldRainTotal){
      if (RainNewFlag == false){  //Stops 1st reading going through and giving additonal values
        TotalRainFrom0000 += 7; //0.7mm for this guage
        TotalRainHour += 7;
        YearData.TotalRainY += 7;
      }
      OldRainTotal=RainTotal;
      RainNewFlag=false;
    }
    //Serial.print(TotalRainFrom0000);   
    //Serial.print(" ");
    //Serial.print(RainTotal); 
    //Serial.print(" ");
    //Serial.print(OldRainTotal); 
    //Serial.println("mm");         
  }*/
  
  decoder.resetDecoder();
  //given that we have just processed a rf signal, check to see if there is any web requests
  WebServer();
}

void setup () {
  
  attachInterrupt(5, ext_int_1, CHANGE); //from the RF receiver
  Wire.begin();
  RTC.begin();
  now = RTC.now();  
  PreviousTime = now.unixtime();

  //Start SD card
  pinMode(53, OUTPUT);         //53 for Mega
  digitalWrite(53, HIGH);  
  root.close();
  file.close();  
  if (!card.init(SPI_HALF_SPEED, 4)) sd.initErrorHalt();
  if (!volume.init(&card))  sd.initErrorHalt(); 
  if (!root.openRoot(&volume))  sd.initErrorHalt();

  //Serial.begin(115200);
  //Serial.println("\n[ookDecoder]");
  
  cardSize = card.cardSize() / 512 / 4; //calcualte sd card size for display later
  //Serial.println(float(cardSize)/1000,1);

  //Setup Arrays for 24/28 hour trends
  for(int z = 0; z<2 ; z++){
    for(int x = 0; x<24; x++){
      for(int y = 0 ; y<14; y++){
        Trends [y] [x] [z] = -999;
      }
    }
  }

  //Get Yearly Extremes
  EEPROM_readAnything(0, YearData);

  Ethernet.begin(mac);
  server.begin();

  //bmp085Calibration();
  SuriseLocation.Position(Ln, Lw); // set position to SuriseLocation
  SuriseLocation.TimeZone(0);
  
  delay(1000);
  SendEmail(-1);  //forces IP email to update user on IP address (note only required if router has dynamic IP address from IP host and resets on loss of power)
}

void loop () {
    
  static int i = 0;
  cli();
  word p = pulse;

  pulse = 0;
  sei();

  if (p != 0) {
    if (orscV2.nextPulse(p))reportSerial("OSV2", orscV2);  
    if (orscV3.nextPulse(p)) reportSerial("OSV3", orscV3);
    //if (cres.nextPulse(p)) reportSerial("CRES", cres); 
  } 
  //Only check for web request every 5 seconds or so so that RF signals are not 'lost'
  if (timer0_overflow_count > 5000){ //check every 5 seconds or so
    WebServer();
    timer0_overflow_count = 0;
  }
  //Rem Update SD card every hour    
  if (now.minute() <= 5  && now.year() != 2000) {
    if (WriteFlag == true) {
      //Serial.println("Writing Log..............");
      WriteFlag=false;
      char filename[]="L";  //file prefix
      monat = now.month();  // convert byte to int 
      yeaat = now.year();
      itoa(monat,charbuffermonat,10);
      itoa(yeaat,charbufferyeaat,10);
      strcat(filename, charbufferyeaat); //append the month to the prefix
      strcat(filename, charbuffermonat); //append the month to the prefix
      strcat(filename, ".csv");   //append the file ending
      logfile.open(&root, filename, O_CREAT | O_APPEND | O_WRITE);
      logfile.print(LogDay);
      logfile.print("/");    
      logfile.print(LogMonth);
      logfile.print("/");    
      logfile.print(now.year());
      logfile.print(" ");    
      logfile.print(LogHour);
      logfile.print(":");    
      logfile.print(LogMinute);
      logfile.print(", ");   
      logfile.print(float(OutTempNow)/10.0,1);
      logfile.print(", ");   
      logfile.print(OutHumNow);
      logfile.print(", ");   
      logfile.print(UVNow);
      logfile.print(", ");   
      logfile.print((float(GustNow)/10.0),1);  //m/s
      logfile.print(", ");   
      logfile.print((float(AverageNow)/10.0),1);  //m/s
      logfile.print(", ");   
      logfile.print(DirectionNow);
      logfile.print(", ");   
      logfile.print(BarrometerNow);
      logfile.print(", ");   
      logfile.print(float(InTempNow)/10.0,1);
      logfile.print(", ");   
      logfile.print(InHumNow);
      logfile.print(", ");   
      logfile.print(float(CH1TempNow)/10.0,1);
      logfile.print(", ");   
      logfile.print(CH1HumNow);
      logfile.print(", ");   
      logfile.print(float(CH2TempNow)/10.0,1);
      logfile.print(", ");   
      logfile.print(CH2HumNow);
      logfile.print(", ");   
      logfile.print(float(CH3TempNow)/10.0,1);
      logfile.print(", ");   
      logfile.print(CH3HumNow);
      logfile.print(", ");   
      logfile.print(RainRateNow);
      logfile.print(", "); 
      logfile.print(TotalRainFrom0000);
      logfile.print(", ");    
      logfile.print(TotalRainHour);
      logfile.print(", ");   
      logfile.print(float(PowerNow)/10.0,1);
      logfile.print(", ");   
      logfile.println(float(TotalPowerHr)/1000.0,1);        
      logfile.close(); 

      //update trends on the hour
      if (now.hour() != 0) { 
        Trends [0] [now.hour()] [0] = OutTempNow;
        Trends [1] [now.hour()] [0] = OutHumNow;
        Trends [2] [now.hour()] [0] = UVNow;
        Trends [3] [now.hour()] [0] = GustNow;
        Trends [4] [now.hour()] [0] = AverageNow;
        Trends [5] [now.hour()] [0] = DirectionNow;
        Trends [6] [now.hour()] [0] = BarrometerNow;
        Trends [7] [now.hour()] [0] = InTempNow;
        Trends [8] [now.hour()] [0] = CH1TempNow;
        Trends [9] [now.hour()] [0] = CH2TempNow;
        Trends [10] [now.hour()] [0] = CH3TempNow;
        Trends [11] [now.hour()] [0] = TotalRainHour;        
        Trends [12] [now.hour()] [0] = PowerNow; 
        Trends [13] [now.hour()] [0] = TotalPowerHr;                            
      }
      
      if (now.hour() == 0) { 
        //If midnight, copy data from this 24hrs to previous and clear data
        for(int x = 0; x<24; x++){
          for(int y = 0 ; y<14; y++){
            //move all data from this 24hrs to 'yesterday'
            Trends [y] [x] [1] = Trends [y] [x] [0];
            Trends [y] [x] [0] = -999;
          }
        }          

        //add in midnight
        Trends [0] [0] [0] = OutTempNow;
        Trends [1] [0] [0] = OutHumNow;
        Trends [2] [0] [0] = UVNow;
        Trends [3] [0] [0] = GustNow;
        Trends [4] [0] [0] = AverageNow;
        Trends [5] [0] [0] = DirectionNow;
        Trends [6] [0] [0] = BarrometerNow;
        Trends [7] [0] [0] = InTempNow;
        Trends [8] [0] [0] = CH1TempNow;
        Trends [9] [0] [0] = CH2TempNow;
        Trends [10] [0] [0] = CH3TempNow;
        Trends [11] [0] [0] = TotalRainHour;   
        Trends [12] [0] [0] = PowerNow; 
        Trends [13] [0] [0] = TotalPowerHr; 
        
        //UpdateYearlyExtremes                 
        EEPROM_writeAnything(0, YearData);

        //Reset 24hr Extrememes     
        MaxTemp24=OutTempNow;
        MinTemp24=OutTempNow;
        MaxGust24=GustNow;
        Direction24=DirectionNow;
        MaxPower24=PowerNow;
        MaxUV24=UVNow;
        TotalRainFrom0000=0;
        TotalPower24=0.0;
        PreviousTime = now.unixtime();
      
        if (now.day()==1 && now.month()==1){ //1st January reset years data
          YearData.MaxTempY = OutTempNow;
          YearData.MaxTempYD = now.unixtime();
          YearData.MinTempY = OutTempNow;
          YearData.MinTempYD = now.unixtime();
          YearData.MaxGustY = GustNow;
          YearData.DirectionY = DirectionNow;
          YearData.WindYD = now.unixtime();
          YearData.TotalPowerY = 0.0;
          YearData.TotalRainY = 0;
          EEPROM_writeAnything(0, YearData);         
        }          
      }
      //reset hours totals
      TotalPowerHr = 0.0;
      TotalRainHour = 0;   
    }
  }
  else
  { 
    //reset flag to allow write to SD at next sync interval
    WriteFlag=true;
  }
}

void WebServer(){
  // Server Stuff
  EthernetClient client = server.available();
  if (client) {
    // an http request ends with a blank line
    boolean current_line_is_blank = true;
    char clientline[BUFSIZ];
    int index = 0;
    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        // //Serial.print(c);
        // If it isn't a new line, add the character to the buffer
        if (c != '\n' && c != '\r') {
          clientline[index] = c;
          index++;
          // are we too big for the buffer? start tossing out data
          if (index >= BUFSIZ) 
            index = BUFSIZ -1;

          // continue to read more data!
          continue;
        }
        // //Serial.println(" ");
        //Serial.println(clientline);

        // Look for substring such as a request to get the root file
        if (strstr(clientline, "GET / ") != 0) {
          // send a standard http response header
          client.println("HTTP/1.1 200 OK");
          client.println("Content-Type: text/html");
          client.println();
          client.println("<html><body><h2>Weather Station Summary</h2><br>Software Version ");
          client.print(Myversion);         
          client.println("<br><br>Software Compiled on<br>");
          //Printing date one char at the time
          for(int i=0;i<strlen(compiledate);++i){
          client.print(compiledate[i]);
          }
          client.print(" at ");
          //Printing time one char at the time
          for(int i=0;i<strlen(compiletime);++i){
          client.print(compiletime[i]);
          }
          client.println("<br><br>");
          client.println("<h2>Files Available:</h2>");
          client.println("Links to raw data files only - Please use address bar to access 'live' content.");

          ListFiles(client, LS_SIZE);
          client.println("<br><h2>Card Details:</h2><ul>");
          client.print("<li>Card Type: ");
          switch (card.type()) {
          case SD_CARD_TYPE_SD1:
            client.println("SD1</li>");
            break;                  
          case SD_CARD_TYPE_SD2:
            client.println("SD2</li>");
            break;                  
          case SD_CARD_TYPE_SDHC:
            client.println("SDHC</li>");
            break;                  
          default:
            client.println("Unknown</li>");
          }                       
          client.print("<li>Volume Size: ");
          client.print(float(cardSize)/1000,1);  
          client.println(" Gbytes</li>");                    
          client.print("<li>Volume Type: FAT");
          client.println(volume.fatType(),DEC);    

          client.println("</li></ul><h2>Data:</h2><ul>Data last received at");
          client.print(LogHour);          
          client.print(':');
          client.print(LogMinute);
          client.print(':');                  
          client.print(LogSecond);
          client.print(" on ");
          client.print(LogDay);
          client.print('/');
          client.print(LogMonth);
          client.print('/');
          client.print(now.year(), DEC);
          client.println("<br><br>");
          client.print("<li>"); 
          client.print("Outdoor Temperature "); 
          client.print(float(OutTempNow)/10,1);
          client.println("&#176;C");          
          client.print("</li><li>");  
          client.print("Wind Chill "); 
          float wc = 13.12 + (0.6215*(float(OutTempNow)/10)) - (11.37 * pow((float(GustNow) / 10) *3.6,0.16)) + (0.3965 * (float(OutTempNow)/10) * pow((float(GustNow) / 10) *3.6,0.16));
          if (wc > float(OutTempNow)/10) wc = float(OutTempNow)/10;  
          client.print(wc,1);
          client.println("&#176;C");          
          client.print("</li><li><i>");
          client.print("Max "); 
          client.print(float(MaxTemp24)/10,1); 
          client.print("&#176;C today");  
          client.print("</li><li>"); 
          client.print("Max "); 
          client.print(float(YearData.MaxTempY)/10,1); 
          client.print("&#176;C this year on ");
          DateTime ExtremeDate (YearData.MaxTempYD);
          formatTimeDigits(ExtremeDay, ExtremeDate.day());
          client.print(ExtremeDay); 
          client.print("/");
          formatTimeDigits(ExtremeMonth, ExtremeDate.month());
          client.print(ExtremeMonth);                                         
          client.print("</li><li>"); 
          client.print("Min "); 
          client.print(float(MinTemp24)/10,1); 
          client.print("&#176;C today");  
          client.print("</li><li>"); 
          client.print("Min "); 
          client.print(float(YearData.MinTempY)/10,1); 
          client.print("&#176;C this year on ");
          ExtremeDate = YearData.MinTempYD;
          formatTimeDigits(ExtremeDay, ExtremeDate.day());
          client.print(ExtremeDay); 
          client.print("/");
          formatTimeDigits(ExtremeMonth, ExtremeDate.month());
          client.print(ExtremeMonth);    
          client.print("</i></li><li>"); 
          client.print("Outdoor Humidty "); 
          client.print(OutHumNow);
          client.println("%");
          client.print("</li><br><li>"); 
          client.print("Cloud Height "); 
          float dp = (((float(OutTempNow) / 10) - ((100 - float(OutHumNow))/5))*9/5)+32;
          float tf = ((float(OutTempNow) / 10)*9/5)+32;
          float cb = (tf - dp)/4.5;                                           
          client.print(cb * 0.3048,2); //km
          client.println("km");
          client.print("</li><br><li>");
          client.print("UV "); 
          client.print(UVNow);
          client.print("</li><li><i>"); 
          client.print("Max UV "); 
          client.print(MaxUV24);
          client.print(" today");
          client.print("</i></li><br><li>"); 
          client.print("Wind Gust "); 
          client.print((float(GustNow)/10)*2.2369362920544025,1);
          client.println("mph");
          client.print("</li><li>"); 
          client.print("Wind Average Speed "); 
          client.print((float(AverageNow)/10)*2.2369362920544025,1);
          client.println("mph");
          client.print("</li><li>"); 
          client.print("Wind Direction "); 
          client.print(DirectionNow);
          client.println("&#176;");          
          client.print("</li><li><i>"); 
          client.print("Max Gust "); 
          client.print((float(MaxGust24)/10)*2.2369362920544025,1);
          client.print("mph from ");
          client.print(Direction24);
          client.print("&#176; today");
          client.print("</li><li>"); 
          client.print("Max Gust "); 
          client.print((float(YearData.MaxGustY)/10)*2.2369362920544025,1);
          client.print("mph from ");
          client.print(YearData.DirectionY);
          client.print("&#176; this year on ");
          ExtremeDate = YearData.WindYD;
          formatTimeDigits(ExtremeDay, ExtremeDate.day());
          client.print(ExtremeDay); 
          client.print("/");
          formatTimeDigits(ExtremeMonth, ExtremeDate.month());
          client.print(ExtremeMonth);   
          client.print("</i></li><br><li>"); 
          client.print("Pressure "); 
          client.print(BarrometerNow);
          client.println("mbar");
          client.print("</li><li>"); 
          client.print("Forecast is "); 
          client.print(Forecast);
          client.print("</li><li>"); 
          client.print(IndoorName);          
          client.print(" Temperature "); 
          client.print(float(InTempNow)/10,1);
          client.println("&#176;C");
          client.print("</li><li>"); 
          client.print(IndoorName);
          client.print(" Humidity "); 
          client.print(InHumNow);
          client.println("%");
          client.print("</li><li>"); 
          client.print("Feels "); 
          client.print(Comfort);
          client.print("</li><br><li>");
          client.print(CH1Name); 
          client.print(" Temperature "); 
          client.print(float(CH1TempNow)/10,1);
          client.println("&#176;C");
          client.print("</li><li>"); 
          client.print(CH1Name); 
          client.print(" Humidity "); 
          client.print(CH1HumNow);
          client.println("%");
          client.print("</li><li>"); 
          client.print(CH2Name); 
          client.print(" Temperature "); 
          client.print(float(CH2TempNow)/10,1);
          client.println("&#176;C");
          client.print("</li><li>"); 
          client.print(CH2Name);           
          client.print(" Humidity "); 
          client.print(CH2HumNow);
          client.println("%");
          client.print("</li><li>"); 
          client.print(CH3Name); 
          client.print(" Temperature "); 
          client.print(float(CH3TempNow)/10,1);
          client.println("&#176;C");
          client.print("</li><li>"); 
          client.print(CH3Name); 
          client.print(" Humidity "); 
          client.print(CH3HumNow);
          client.println("%");
          client.print("</li><br><li>"); 
          client.print("Rain Rate "); 
          client.print(RainRateNow);
          client.println("mm/hr");
          client.print("</li><li>"); 
          client.print("Total Rain "); 
          client.print(TotalRainFrom0000);
          client.println("mm today");
          client.print("</li><li><i>"); 
          client.print("Total Rain "); 
          client.print(YearData.TotalRainY);
          client.println("mm this year");
          client.print("</i></li><br><li>"); 
          client.print("Current "); 
          client.print(float(PowerNow)/10,1);
          client.println("Amps");
          client.print("</li><li><i>"); 
          client.print("Max Current "); 
          client.print(float(MaxPower24)/10,1);
          client.print("Amps today");
          client.print("</li><li>"); 
          client.print("Total Power this hour "); 
          client.print(TotalPowerHr/1000.0,1);
          client.print("kWhrs");
          client.print("</li><li>"); 
          client.print("Total Power so far "); 
          client.print(TotalPower24/1000.0,1);
          client.print("kWhrs today");
          client.print("</li><li>"); 
          client.print("Total Power so far "); 
          client.print(YearData.TotalPowerY/1000000.0,1);
          client.print("MWhrs this year");
          client.print("</i></li><br><li>"); 
          client.print("Outdoor Battery "); 
          client.print(OutTempBat);
          client.println("%");
          client.print("</li><li>"); 
          client.print("UV Battery "); 
          client.print(UVBat);
          client.println("%");
          client.print("</li><li>"); 
          client.print("Anemometer Battery "); 
          client.print(WindBat);
          client.println("%");
          client.print("</li><li>"); 
          client.print("Rain Guage Battery "); 
          client.print(RainBat);
          client.println("%");
          client.print("</li><li>"); 
          client.print("Indoor Temperature Battery "); 
          client.print(InTempBat);
          client.println("%");
          client.print("</li><li>"); 
          client.print(CH1Name);  
          client.print(" Battery "); 
          client.print(CH1Bat);
          client.println("%");
          client.print("</li><li>"); 
          client.print(CH2Name);  
          client.print(" Battery "); 
          client.print(CH2Bat);
          client.println("%");
          client.print("</li><li>"); 
          client.print(CH3Name);  
          client.print(" Battery "); 
          client.print(CH3Bat);
          client.println("%");
          client.print("</i></li>");
          client.println("</ul><h2>Sensors Last Updated:</h2><ul><li>"); 
          client.print("Outdoor "); 
          DateTime UpdateDate (OutTime);
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>"); 
          client.print("UV "); 
          UpdateDate =UVTime;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>"); 
          client.print("Anemometer "); 
          UpdateDate =WindTime;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>");  
          client.print("Rain "); 
          UpdateDate =RainTime;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>"); 
          client.print("Indoor "); 
          UpdateDate =InTime;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>");  
          client.print(CH1Name);
          client.print(" "); 
          UpdateDate =CH1Time;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>");  
          client.print(CH2Name);
          client.print(" "); 
          UpdateDate =CH2Time;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>");  
          client.print(CH3Name);
          client.print(" "); 
          UpdateDate =CH3Time;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.print("</li><li>");  
          client.print("Power "); 
          UpdateDate =PowerTime;
          formatTimeDigits(ExtremeTime, UpdateDate.hour());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.minute());
          client.print(ExtremeTime); 
          client.print(":");
          formatTimeDigits(ExtremeTime, UpdateDate.second());
          client.print(ExtremeTime); 
          client.println("</li></ul></body></html>");          
        } 
        else if (strstr(clientline, "GET /") != 0) {
          // this time no space after the /, so a sub-file!
          char *filename;

          filename = clientline + 5; // look after the "GET /" (5 chars)
          // a little trick, look for the " HTTP/1.1" string and 
          // turn the first character of the substring into a 0 to clear it out.
          (strstr(clientline, " HTTP"))[0] = 0;

          //Serial.println(filename);
          if (strstr(clientline,"EEPROM")) 
          {
            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: text/html");
            client.println();
            //Force UpdateYearlyExtremes                 
            EEPROM_writeAnything(0, YearData);
            client.println("<html><body><h2>EEPROM Forced Write</h2></body></html>");
          } 
          else if (strstr(clientline,"TIME")) 
          {
            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: text/html");
            client.println();
            UpdateRTC(clientline);
            //Reset RTC to TIME provided
            client.println("<html><body><h2>RTC Reset</h2>");
            now = RTC.now();  
            formatTimeDigits(LogMonth, now.month());
            formatTimeDigits(LogDay, now.day());
            formatTimeDigits(LogHour, now.hour());
            formatTimeDigits(LogMinute, now.minute());
            formatTimeDigits(LogSecond, now.second());
            client.print(LogDay);
            client.print("/");
            client.print(LogMonth);
            client.print("/");
            client.print(now.year());
            client.print(" ");
            client.print(LogHour);
            client.print(":");
            client.print(LogMinute);
            client.print(":");
            client.print(LogSecond);
            client.println("</body></html>");
          }            
          else if (strstr(clientline,"htm"))
          {            
            //Serial.print("My file ");
            //Serial.println(filename);

            if (!html.open(&root, filename, O_READ)) {
              //Serial.println("html template file not Found!");
              NotFoundError(client);
              break;
            }

            client.println("HTTP/1.1 200 OK");
            client.println("Content-Type: text/html");
            client.println();
            int16_t t;
            while ((t = html.read()) > 0) {
              // uncomment the //Serial to debug (slow!)
              //Serial.print(t);
              //If the file being 'streamed' from the sd card contains a ~~, replace variable with data
              if (t != 126) {
                client.print(char(t));
              }
              else
              {
                t = html.read();
                if (t == 126) {
                  do {
                    t = html.read();                       
                    if (t != 126) MyTag += char(t);                          
                  } 
                  while (t != 126);  
                  t = html.read();  //Get 2nd ~
                  //Serial.println(MyTag);  
                  //Do print here 
                  if (MyTag == "SIMPLETIME" || MyTag == "FULLTIME") {
                    client.print(LogHour);
                    ;
                    client.print(':');
                    client.print(LogMinute);
                  }
                  if (MyTag == "FULLTIME") {
                    client.print(':');                  
                    client.print(LogSecond);
                  }
                  if (MyTag == "SHORTDATE") {
                    client.print(LogDay);
                    client.print('/');
                    client.print(LogMonth);
                    client.print('/');
                    client.print(now.year(), DEC);
                  }
                  if (MyTag == "OUTTEMPGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [0] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "OUTTEMPGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [0] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "OUTWINDCHILLGC") {
                    for(int x = 0; x<24; x++){
                      float wc = 13.12 + (0.6215*(float(Trends [0] [x] [0])/10)) - (11.37 * pow((float(Trends [3] [x] [0]) / 10) *3.6,0.16)) + (0.3965 * (float(Trends [0] [x] [0])/10) * pow((float(Trends [3] [x] [0]) / 10) *3.6,0.16));
                      if (wc > float(Trends [0] [x] [0])/10) wc = float(Trends [0] [x] [0])/10;  // wind chill cannot be greater than actual temp                                        
                      if (Trends [0] [x] [0] == -999 || Trends [3] [x] [0] == -999) wc=-999;
                      client.print(wc*10,1);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "OUTWINDCHILLGP") {
                    for(int x = 0; x<24; x++){
                      float wc = 13.12 + (0.6215*(float(Trends [0] [x] [1])/10)) - (11.37 * pow((float(Trends [3] [x] [1]) / 10) *3.6,0.16)) + (0.3965 * (float(Trends [0] [x] [1])/10) * pow((float(Trends [3] [x] [1]) / 10) *3.6,0.16));
                      if (wc > float(Trends [0] [x] [1])/10) wc = float(Trends [0] [x] [1])/10;   // wind chill cannot be greater than actual temp               
                      if (Trends [0] [x] [1] == -999 || Trends [3] [x] [1] == -999) wc=-999;
                      client.print(wc*10,1);
                      if (x<23) client.print(",");
                    }
                  }
                  if (MyTag == "WINDCHILLNOW") {
                    float wc = 13.12 + (0.6215*(float(OutTempNow)/10)) - (11.37 * pow((float(GustNow) / 10) *3.6,0.16)) + (0.3965 * (float(OutTempNow)/10) * pow((float(GustNow) / 10) *3.6,0.16));
                    if (wc > float(OutTempNow)/10) wc = float(OutTempNow)/10;                       
                    client.print(wc,1);
                  } 
                  if (MyTag == "CLOUDGC") {
                    for(int x = 0; x<24; x++){
                      float dp = (((float(Trends [0] [x] [0]) / 10) - ((100 - float(Trends [1] [x] [0]))/5))*9/5)+32;
                      float tf = ((float(Trends [0] [x] [0]) / 10)*9/5)+32;
                      float cb = (tf - dp)/4.5;                                        
                      if (Trends [0] [x] [0] == -999 || Trends [1] [x] [0] == -999) cb=-999;
                      client.print(cb * 0.3048,1); //km
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CLOUDGP") {
                    for(int x = 0; x<24; x++){
                      float dp = (((float(Trends [0] [x] [1]) / 10) - ((100 - float(Trends [1] [x] [1]))/5))*9/5)+32;
                      float tf = ((float(Trends [0] [x] [1]) / 10)*9/5)+32;
                      float cb = (tf - dp)/4.5;                                                                                    
                      if (Trends [0] [x] [1] == -999 || Trends [1] [x] [1] == -999) cb=-999;
                      client.print(cb * 0.3048,1); //km
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CLOUDNOW") {
                    float dp = (((float(OutTempNow) / 10) - ((100 - float(OutHumNow))/5))*9/5)+32;
                    float tf = ((float(OutTempNow) / 10)*9/5)+32;
                    float cb = (tf - dp)/4.5;                                       
                    client.print(cb * 0.3048,1); //km
                  } 
                  if (MyTag == "OUTHUMGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [1] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "OUTHUMGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [1] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  }
                  if (MyTag == "UVGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [2] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "UVGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [2] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "GUSTGC") {
                    for(int x = 0; x<24; x++){
                      client.print(float(Trends [3] [x] [0])/10 * 2.2369362920544025,2); //mph
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "GUSTGP") {
                    for(int x = 0; x<24; x++){
                      client.print(float(Trends [3] [x] [1])/10 * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "AVERAGEGC") {
                    for(int x = 0; x<24; x++){
                      client.print(float(Trends [4] [x] [0])/10 * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "AVERAGEGP") {
                    for(int x = 0; x<24; x++){
                      client.print(float(Trends [4] [x] [1]) / 10 * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "DIRECTIONGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [5] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "DIRECTIONGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [5] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "ROSEX") {
                    for(int x = 0; x<24; x++){
                      client.print((sin(Trends [5] [x] [1]*0.0174532925))*Trends [4] [x] [1] * 2.2369362920544025,2); //10's mph
                      if (x<23) client.print(",");
                    }
                    client.print(",");
                    for(int x = 0; x<24; x++){
                      client.print(sin((Trends [5] [x] [0]*0.0174532925))*Trends [4] [x] [0] * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "ROSEY") {
                    for(int x = 0; x<24; x++){
                      client.print((cos(Trends [5] [x] [1]*0.0174532925))*Trends [4] [x] [1] * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                    client.print(",");
                    for(int x = 0; x<24; x++){
                      client.print(cos((Trends [5] [x] [0]*0.0174532925))*Trends [4] [x] [0] * 2.2369362920544025,2);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "PRESSUREGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [6] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "PRESSUREGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [6] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "INTEMPGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [7] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "INTEMPGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [7] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH1TEMPGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [8] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH1TEMPGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [8] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH2TEMPGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [9] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH2TEMPGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [9] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH3TEMPGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [10] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "CH3TEMPGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [10] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  }                   
                  if (MyTag == "RAINGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [11] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "RAINGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [11] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  }                   
                  if (MyTag == "POWERGC") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [13] [x] [0]);
                      if (x<23) client.print(",");
                    }
                  } 
                  if (MyTag == "POWERGP") {
                    for(int x = 0; x<24; x++){
                      client.print(Trends [13] [x] [1]);
                      if (x<23) client.print(",");
                    }
                  }                   
                  if (MyTag == "OutTempNow") {
                    client.print(float(OutTempNow)/10,1);
                  }
                  if (MyTag == "OutHumNow") {
                    client.print(OutHumNow);
                  }
                  if (MyTag == "UVNow") {
                    client.print(UVNow);
                  }
                  if (MyTag == "GustNow") {
                    client.print((float(GustNow)/10)*2.2369362920544025,1);
                  }
                  if (MyTag == "AverageNow") {
                    client.print((float(AverageNow)/10)*2.2369362920544025,1);
                  }
                  if (MyTag == "DirectionNow") {
                    client.print(DirectionNow);
                  }
                  if (MyTag == "BarrometerNow") {
                    client.print(BarrometerNow);
                  }
                  if (MyTag == "Forecast") {
                    client.print(Forecast);
                  }
                  if (MyTag == "InTempNow") {
                    client.print(float(InTempNow)/10,1);
                  }
                  if (MyTag == "InHumNow") {
                    client.print(InHumNow);
                  }
                  if (MyTag == "Comfort") {
                    client.print(Comfort);
                  }
                  if (MyTag == "CH1TempNow") {
                    client.print(float(CH1TempNow)/10,1);
                  }
                  if (MyTag == "CH1HumNow") {
                    client.print(CH1HumNow);
                  }
                  if (MyTag == "CH2TempNow") {
                    client.print(float(CH2TempNow)/10,1);
                  }
                  if (MyTag == "CH2HumNow") {
                    client.print(CH2HumNow);
                  }
                  if (MyTag == "CH3TempNow") {
                    client.print(float(CH3TempNow)/10,1);
                  }
                  if (MyTag == "CH3HumNow") {
                    client.print(CH3HumNow);
                  }
                  if (MyTag == "RainRateNow") {
                    client.print(RainRateNow);
                  }
                  if (MyTag == "TotalRainFrom0000") {
                    client.print(TotalRainFrom0000);
                  }
                  if (MyTag == "PowerNow") {
                    client.print(float(PowerNow)/10,1);
                  } //Amps
                  if (MyTag == "WPowerNow") {
                    client.print((240*PF*float(PowerNow)/10)/1000,2);
                  }  //kW
                  if (MyTag == "OutTempBat") {
                    client.print(OutTempBat);
                  }
                  if (MyTag == "UVBat") {
                    client.print(UVBat);
                  }
                  if (MyTag == "WindBat") {
                    client.print(WindBat);
                  }
                  if (MyTag == "RainBat") {
                    client.print(RainBat);
                  }
                  if (MyTag == "InTempBat") {
                    client.print(InTempBat);
                  }
                  if (MyTag == "CH1Bat") {
                    client.print(CH1Bat);
                  }
                  if (MyTag == "CH2Bat") {
                    client.print(CH2Bat);
                  }
                  if (MyTag == "CH3Bat") {
                    client.print(CH3Bat);
                  }
                  if (MyTag == "CH1Name") {
                    client.print(CH1Name);
                  }
                  if (MyTag == "CH2Name") {
                    client.print(CH2Name);
                  }
                  if (MyTag == "CH3Name") {
                    client.print(CH3Name);
                  }
                  if (MyTag == "IndoorName") {
                    client.print(IndoorName);
                  }
                  if (MyTag == "MaxTemp24") {
                    client.print(float(MaxTemp24)/10,1);
                  } 
                  if (MyTag == "MinTemp24") {
                    client.print(float(MinTemp24)/10,1);
                  } 
                  if (MyTag == "MaxGust24") {
                    client.print(float(MaxGust24)/10*2.2369362920544025,1);
                  } 
                  if (MyTag == "Direction24") {
                    client.print(Direction24);
                  }
                  if (MyTag == "MaxPower24") {
                    client.print(float(MaxPower24)/10,1);
                  } 
                  if (MyTag == "MaxUV24") {
                    client.print(MaxUV24);
                  } 
                  if (MyTag == "MaxTempY") {
                    client.print(float(YearData.MaxTempY)/10,1);
                  } 
                  if (MyTag == "MinTempY") {
                    client.print(float(YearData.MinTempY)/10,1);
                  } 
                  if (MyTag == "MaxGustY") {
                    client.print(float(YearData.MaxGustY)/10*2.2369362920544025,1);
                  } 
                  if (MyTag == "DirectionY") {
                    client.print(YearData.DirectionY);
                  }
                  if (MyTag == "PowerH") {
                    client.print(TotalPowerHr/1000.0,1);
                  }
                  if (MyTag == "Power24") {
                    client.print(TotalPower24/1000.0,1);
                  }
                  if (MyTag == "MaxTempYD") {
                    DateTime ExtremeDate (YearData.MaxTempYD);
                    formatTimeDigits(ExtremeDay, ExtremeDate.day());
                    client.print(ExtremeDay); 
                    client.print("/");
                    formatTimeDigits(ExtremeMonth, ExtremeDate.month());
                    client.print(ExtremeMonth);               
                  }
                  if (MyTag == "MinTempYD") {
                    DateTime ExtremeDate (YearData.MinTempYD);
                    formatTimeDigits(ExtremeDay, ExtremeDate.day());
                    client.print(ExtremeDay); 
                    client.print("/");
                    formatTimeDigits(ExtremeMonth, ExtremeDate.month());
                    client.print(ExtremeMonth);               
                  } 
                  if (MyTag == "WindYD") {
                    DateTime ExtremeDate (YearData.WindYD);
                    formatTimeDigits(ExtremeDay, ExtremeDate.day());
                    client.print(ExtremeDay); 
                    client.print("/");
                    formatTimeDigits(ExtremeMonth, ExtremeDate.month());
                    client.print(ExtremeMonth);               
                  } 
                  if (MyTag == "TotalRainY") {
                    client.print(YearData.TotalRainY);
                  } 
                  if (MyTag == "TotalPowerY") {
                    client.print(YearData.TotalPowerY/1000000.0);
                  }
                  if (MyTag == "SEASON") {
                    byte season;
                    season=SuriseLocation.Season(IsToDay);
                    if (season==0) client.print("Winter");          
                    if (season==1) client.print("Sprintg");          
                    if (season==2) client.print("Summer");          
                    if (season==3) client.print("Autumn");
                  }                             
                  if (MyTag == "MOONPHASE") {
                    float phase;
                    phase=SuriseLocation.MoonPhase(IsToDay); 
                    if (phase <= 0.05) client.print("New Moon");
                    if ((phase < 0.15) && (phase > 0.05)) client.print("Waxing Crescent");
                    if ((phase < 0.25) && (phase >= 0.15)) client.print("First Quarter");
                    if ((phase < 0.45) && (phase >= 0.25)) client.print("Waxing Gibbous");
                    if ((phase < 0.55) && (phase >= 0.45)) client.print("Full Moon");
                    if ((phase < 0.75) && (phase >= 0.55)) client.print("Waning Gibbous");
                    if ((phase < 0.85) && (phase >= 0.75)) client.print("Last Quarter");
                    if ((phase < 0.95) && (phase >= 0.85)) client.print("Waning Crescent");
                    if (phase >= 0.95) client.print("New Moon"); 
                  } 
                  if (MyTag == "MOONILL") {  
                     float phase;
                     phase=SuriseLocation.MoonPhase(IsToDay);       
                     if (phase*2 <1){
                       client.print(phase*200,1);
                     }
                     else
                     {
                        client.print((2-(phase*2))*100,1);
                     }   
                  }                    
                  if (MyTag == "SUNRISE") {        
                    DateTime SunDate = SuriseLocation.SunRise(IsToDay);
                    formatTimeDigits(PrintMonth, IsToDay[2]);
                    client.print(PrintMonth);    
                    client.print(":");
                    formatTimeDigits(PrintDay, IsToDay[1]);
                    client.print(PrintDay);   
                  }
                  if (MyTag == "SUNSET") {        
                    DateTime SunDate = SuriseLocation.SunSet(IsToDay);
                    formatTimeDigits(PrintMonth, IsToDay[2]);
                    client.print(PrintMonth);    
                    client.print(":");
                    formatTimeDigits(PrintDay, IsToDay[1]);
                    client.print(PrintDay);   
                  }
                  if (MyTag == "SDCARD") {
                    switch (card.type()) {
                    case SD_CARD_TYPE_SD1:
                      client.print("SD1");
                      break;                  
                    case SD_CARD_TYPE_SD2:
                      client.print("SD2");
                      break;                  
                    case SD_CARD_TYPE_SDHC:
                      client.print("SDHC");
                      break;                  
                    default:
                      client.print("Unknown");
                    }                     
                  }       
                  if (MyTag == "SDSIZE") {
                    client.print(cardSize,DEC);  
                    client.print(" Mbytes");                   
                  } 
                  if (MyTag == "VOLTYPE") {
                    client.print("FAT");
                    client.print(volume.fatType(),DEC);                     
                  }                 
                  MyTag="";              
                }
                else
                {
                  client.print("~");
                  client.print(char(t));
                }               
              }
            }
            html.close();           
          }
          else
          {            
            //Serial.println("Opened!");
            if (filename != "favicon.ico")
            {             
              if (!file.open(&root, filename, O_READ)) {
                //Serial.println("html template file not Found!");
                NotFoundError(client);
                break;
              }

              client.println("HTTP/1.1 200 OK");
              client.println("Content-Type: text/plain");
              client.println();

              int16_t c;
              while ((c = file.read()) > 0) {
                // uncomment the //Serial to debug (slow!)
                // //Serial.print((char)c);
                client.print((char)c);
              }
              file.close();
            }
          }
        } 
        else {
          // everything else is a 404
          NotFoundError(client);
        }
        break;
      }
    }
    // give the web browser time to receive the data
    delay(3000);           
  }
  client.stop();
}

void formatTimeDigits(char strOut[3], int num)
{
  strOut[0] = '0' + (num / 10);
  strOut[1] = '0' + (num % 10);
  strOut[2] = '\0';
}

void NotFoundError(EthernetClient client) 
{
  client.println("HTTP/1.1 404 Not Found");
  client.println("Content-Type: text/html");
  client.println();
  client.println("<h2>File Not Found!</h2>");
}

void ListFiles(EthernetClient client, uint8_t flags) 
{
  dir_t p;
  root.rewind();
  client.println("<ul>");
  while (root.readDir(p) > 0) {
    // done if past last used entry
    if (p.name[0] == DIR_NAME_FREE) break;

    // skip deleted entry and entries for . and  ..
    if (p.name[0] == DIR_NAME_DELETED || p.name[0] == '.') continue;

    // only list files in root
    if (DIR_IS_SUBDIR(&p)) continue;

    // print any indent spaces
    client.print("<li><a href=\"");

    for (uint8_t i = 0; i < 11; i++) {
      if (p.name[i] == ' ') continue;
      if (i == 8) {
        client.print('.');
      }
      client.print((char)p.name[i]);
    }
    client.print("\">");

    // print file name with possible blank fill
    for (uint8_t i = 0; i < 11; i++) {
      if (p.name[i] == ' ') continue;
      if (i == 8) {
        client.print('.');
      }
      client.print((char)p.name[i]);
    }

    client.print("</a>");
    client.print(' ');
    client.print(float(p.fileSize)/1024,1);
    client.println("kB</li>");
  }
  client.println("</ul>"); 
}

void SendEmail(int t) { 
  if (t == -1){
      //Serial.println("Connecting");
      if (client.connect(serverName, 80)) {
        //Serial.println("Connected, sending request for IP...");
        // Make a HTTP request:
        client.print("GET http://www.yourwebsite.com/Mail/ReBoot.php");
        client.println(" HTTP/1.1"); 
        client.println("Host: www.host.co.uk");
        client.println();
        //Serial.println("Request complete");
      } 
      else {
        // kf you didn't get a connection to the server:
        //Serial.println("connection failed");
      }
      client.stop();
  }
  else
  {
    if (now.hour() > 7 && now.hour()< 19){ // Only email during 'daytime'
      //Serial.println("");
      //Serial.println("Connecting");
      if (client.connect(serverName, 80)) {
        //Serial.println("Connected, sending request...");
        // Make a HTTP request:
        client.print("GET http://www.yourwebsite.com/Mail/Update.php");
        client.print("?T=");client.print(LogHour);client.print(":");client.print(LogMinute);client.print(":");client.print(LogSecond);
        client.print("&TN=");client.print(float(OutTempNow)/10,1);
        client.print("&SN=");client.print((float(GustNow)/10)*2.2369362920544025,1);    
        client.print("&DN=");client.print(DirectionNow);
        client.print("&R=");client.print(TotalRainFrom0000);
        client.print("&TM=");client.print(float(MaxTemp24)/10,1);    
        client.print("&TMIN=");client.print(float(MinTemp24)/10,1);  
        client.print("&SM=");client.print((float(MaxGust24)/10)*2.2369362920544025,1);
        if (t==1) client.print("&TR=high%20winds");
        if (t==2) client.print("&TR=rain");
        if (t==3) client.print("&TR=high%20temperatures");
        if (t==4) client.print("&TR=low%20temperatures");
        client.println(" HTTP/1.1"); 
        client.println("Host: www.host.co.uk");
        client.println();
        //Serial.println("Request complete");
        if (client.available()) {
          char c = client.read();
          //Serial.print(c);
        }
        //Serial.println("");
      } 
      else {
        // kf you didn't get a connection to the server:
        //Serial.println("connection failed");
      }
      client.stop();
    }
  }
}

// Function to return a substring defined by a delimiter at an index
char* subStr (char* str, char *delim, int index) {
   char *act, *sub, *ptr;
   static char copy[MAX_STRING_LEN];
   int i;

   // Since strtok consumes the first arg, make a copy
   strcpy(copy, str);

   for (i = 1, act = copy; i <= index; i++, act = NULL) {
	////Serial.print(".");
	sub = strtok_r(act, delim, &ptr);
	if (sub == NULL) break;
   }
   return sub;

}

void UpdateRTC(char* clientline){
  uint16_t year = atoi(subStr(clientline, "&", 2));
  uint8_t month = atoi(subStr(clientline, "&", 3));
  uint8_t day = atoi(subStr(clientline, "&", 4));
  uint8_t hour = atoi(subStr(clientline, "&", 5));
  uint8_t minute = atoi(subStr(clientline, "&", 6));
  //Serial.print("Split clienline: ");
  //Serial.print(year);
  //Serial.print("/");
  //Serial.print(month);
  //Serial.print("/");
  //Serial.print(day);
  //Serial.print(" ");
  //Serial.print(hour);
  //Serial.print(":");
  //Serial.print(minute);
  //Serial.print(":");
  //Serial.println(second);
  //Printing date one char at the time
  //for(int i=0;i<strlen(compiledate);++i){
  //Serial.print(compiledate[i]);
  //}
  //Serial.print(" ");
  //Printing time one char at the time
  //for(int i=0;i<strlen(compiletime);++i){
  //Serial.print(compiletime[i]);
  //}
  DateTime dt(year, month,day,hour,minute,0);
  RTC.adjust (dt);
}

/*
void bmp085Calibration()
{
  ac1 = bmp085ReadInt(0xAA);
  ac2 = bmp085ReadInt(0xAC);
  ac3 = bmp085ReadInt(0xAE);
  ac4 = bmp085ReadInt(0xB0);
  ac5 = bmp085ReadInt(0xB2);
  ac6 = bmp085ReadInt(0xB4);
  b1 = bmp085ReadInt(0xB6);
  b2 = bmp085ReadInt(0xB8);
  mb = bmp085ReadInt(0xBA);
  mc = bmp085ReadInt(0xBC);
  md = bmp085ReadInt(0xBE);
}

// Calculate temperature in deg C
float bmp085GetTemperature(unsigned int ut){
  long x1, x2;

  x1 = (((long)ut - (long)ac6)*(long)ac5) >> 15;
  x2 = ((long)mc << 11)/(x1 + md);
  b5 = x1 + x2;

  float temp = ((b5 + 8)>>4);
  temp = temp /10;

  return temp;
}

// Calculate pressure given up
// calibration values must be known
// b5 is also required so bmp085GetTemperature(...) must be called first.
// Value returned will be pressure in units of Pa.
long bmp085GetPressure(unsigned long up){
  long x1, x2, x3, b3, b6, p;
  unsigned long b4, b7;

  b6 = b5 - 4000;
  // Calculate B3
  x1 = (b2 * (b6 * b6)>>12)>>11;
  x2 = (ac2 * b6)>>11;
  x3 = x1 + x2;
  b3 = (((((long)ac1)*4 + x3)<<OSS) + 2)>>2;

  // Calculate B4
  x1 = (ac3 * b6)>>13;
  x2 = (b1 * ((b6 * b6)>>12))>>16;
  x3 = ((x1 + x2) + 2)>>2;
  b4 = (ac4 * (unsigned long)(x3 + 32768))>>15;

  b7 = ((unsigned long)(up - b3) * (50000>>OSS));
  if (b7 < 0x80000000)
    p = (b7<<1)/b4;
  else
    p = (b7/b4)<<1;

  x1 = (p>>8) * (p>>8);
  x1 = (x1 * 3038)>>16;
  x2 = (-7357 * p)>>16;
  p += (x1 + x2 + 3791)>>4;

  long temp = p;
  return temp;
}

// Read 1 byte from the BMP085 at 'address'
char bmp085Read(unsigned char address)
{
  unsigned char data;

  Wire.beginTransmission(BMP085_ADDRESS);
  Wire.write(address);
  Wire.endTransmission();

  Wire.requestFrom(BMP085_ADDRESS, 1);
  while(!Wire.available())
    ;

  return Wire.read();
}

// Read 2 bytes from the BMP085
// First byte will be from 'address'
// Second byte will be from 'address'+1
int bmp085ReadInt(unsigned char address)
{
  unsigned char msb, lsb;

  Wire.beginTransmission(BMP085_ADDRESS);
  Wire.write(address);
  Wire.endTransmission();

  Wire.requestFrom(BMP085_ADDRESS, 2);
  while(Wire.available()<2)
    ;
  msb = Wire.read();
  lsb = Wire.read();

  return (int) msb<<8 | lsb;
}

// Read the uncompensated temperature value
unsigned int bmp085ReadUT(){
  unsigned int ut;

  // Write 0x2E into Register 0xF4
  // This requests a temperature reading
  Wire.beginTransmission(BMP085_ADDRESS);
  Wire.write(0xF4);
  Wire.write(0x2E);
  Wire.endTransmission();

  // Wait at least 4.5ms
  delay(5);

  // Read two bytes from registers 0xF6 and 0xF7
  ut = bmp085ReadInt(0xF6);
  return ut;
}

// Read the uncompensated pressure value
unsigned long bmp085ReadUP(){

  unsigned char msb, lsb, xlsb;
  unsigned long up = 0;

  // Write 0x34+(OSS<<6) into register 0xF4
  // Request a pressure reading w/ oversampling setting
  Wire.beginTransmission(BMP085_ADDRESS);
  Wire.write(0xF4);
  Wire.write(0x34 + (OSS<<6));
  Wire.endTransmission();

  // Wait for conversion, delay time dependent on OSS
  delay(2 + (3<<OSS));

  // Read register 0xF6 (MSB), 0xF7 (LSB), and 0xF8 (XLSB)
  msb = bmp085Read(0xF6);
  lsb = bmp085Read(0xF7);
  xlsb = bmp085Read(0xF8);

  up = (((unsigned long) msb << 16) | ((unsigned long) lsb << 8) | (unsigned long) xlsb) >> (8-OSS);

  return up;
}

void writeRegister(int deviceAddress, byte address, byte val) {
  Wire.beginTransmission(deviceAddress); // start transmission to device 
  Wire.write(address);       // send register address
  Wire.write(val);         // send value to write
  Wire.endTransmission();     // end transmission
}

int readRegister(int deviceAddress, byte address){

  int v;
  Wire.beginTransmission(deviceAddress);
  Wire.write(address); // register to read
  Wire.endTransmission();

  Wire.requestFrom(deviceAddress, 1); // read a byte

  while(!Wire.available()) {
    // waiting
  }

  v = Wire.read();
  return v;
}

float calcAltitude(float pressure){

  float A = pressure/101325;
  float B = 1/5.25588;
  float C = pow(A,B);
  C = 1 - C;
  C = C /0.0000225577;

  return C;
}*/ 
