#include <dht.h>
#include <Servo.h>

//data fro the DHT11 sensor, temp and humidity
dht DHT;
#define DHTPIN 2

//data for servo, turns watering valve
int servoPin = 3;
Servo s1;

//relay pin numbers
int relayPin = 8;
int relayPin2 = 12;

//serial in (from the RPi)
String in;

//stored values for the timer so we don't have to use the delay method, which will stop everything!
long currMillis;
long lastRead;
long interval = 30000; //<- Change this value to manipulate the data reading and transmitting interval (in milliseconds)

//the pins for the moisture sensors
int moisturePin1 = A0;
int moisturePin2 = A1;

//initialise what needs to be initialised
void setup()
{
  //set the pinmode to outpute and the digitral write to high for the relay
 pinMode(relayPin, OUTPUT);
 digitalWrite(relayPin, HIGH);
 pinMode(relayPin2, OUTPUT);
 digitalWrite(relayPin2, HIGH);
 
 //enable servo
 s1.attach(servoPin);
 s1.write(0);
 
 //begin serial 
 Serial.begin(9600);
 
 //initialise timers
 currMillis = millis();
 lastRead = millis();
}

void loop()
{
  //keeps track fo the current time
  currMillis = millis();
  
  //check to see if another reading is due
  if(currMillis - interval > lastRead)
  {
    //read sensor data
    int chk = DHT.read11(DHTPIN);
    int moist1Val = analogRead(moisturePin1);
    int moist2Val = analogRead(moisturePin2);
  
    //communicate data to the Pi
    Serial.println(DHT.temperature);
    Serial.println(DHT.humidity);
    Serial.println(moist1Val);
    Serial.println(moist2Val);
    
    //set the time for the last read
    lastRead = currMillis;
  }
  
 //serial reciever
 while(Serial.available() > 0)
 {
   in = Serial.readString(); //read serial data
   int val = in.toInt(); //convert to int before using in switch
   
   //switch statement for toggles, much faster than multiple if elses
   switch(val)
   {
      case 0: //servo turned 0 degrees
        s1.write(0);
        break;
       case 1: //servo turned 90 degrees
         s1.write(105);
         break;
       case 2: //relay 1 off
         digitalWrite(relayPin, HIGH);
         break;
       case 3: //relay 1 on
         digitalWrite(relayPin, LOW);
         break;
       case 4: //realy 2 off
         digitalWrite(relayPin2, HIGH);
         break;
       case 5: //relay 2 on
         digitalWrite(relayPin2, LOW);
         break;
       default:
         break;
    }
  }
}
