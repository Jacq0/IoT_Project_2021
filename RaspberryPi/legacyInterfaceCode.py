#THIS IS LEGACY CODE, THE FILE "interfaceCodePi.py" IS THE UP TO DATE ONE!!

#!/usr/bin/env python
import serial
import time
import io
from datetime import datetime
from threading import Thread


#initialise serial comms
ser = serial.Serial('/dev/ttyACM0', 9600, timeout = 120)
ser.flushInput()

#set up time variables, we are using hours as it is accurate enough for this use case
#light timers
minHrL = 20
maxHrL = 10
#heater timer
minHrH = 13
maxHrH = 15
#other variables (overrides for the lights and heaters)
checkTime = 30 #check the time and send an update to the arduino every 30 seconds
lOverride = False
hOverride = False

#temporary string to store data
strng = ""

#make sure the times are within bounds, a bit inefficient but its only ran once on start
if minHrL < 0:
	minHrL = 0
if maxHrL < 0:
	maxHrL = 0
if minHrL >= 24:
	minHrL = 23
if maxHrL >= 24:
	maxHrL = 23
if minHrH < 0:
	minHrH = 0
if maxHrH < 0:
	maxHrH = 0
if minHrH >= 24:
	minHrH = 23
if maxHrH >= 24:
	maxHrH = 23

#the moisture values needed for detection and rection
mThreshold = 350 #the threshold at which the system will decide to iterate the counter
mCounter = 0 #counter that keeps track of the number of times the threashold has been breached
wateringTime = 30 #the time the system leaves the watering valve open

#the number of counts needed to breach the limit and react (stops erros when value hovers around thresholds)
countLimit = 5

#queue up values to send over serial
def serialSendQueue(value):
	print("")
	#queue.append(value)
	#for i in queue.len():
	#	ser.write(queue[i])
	#	queue.remove(i) #remove the item
	#	time.sleep(0.5) #wait half a second before sending the next value from the queue

#stops the arduino being spammed with duplicate serial input
def writeSerial(value):
	ser.write(value)
	time.sleep(1) #a breif timer to give arduino time to check and clear its serial in buffer 

#split into 2 methods in case there is an error communicating with the arduino and we desync the valve status
def openValve():
	#make sure its not being called while soemthing else is
	writeSerial("1")

def closeValve():
	writeSerial("0")

def readSerial():
	values = []
	while True:
		try:
			ser_in = ser.readline()
			decoded = float(ser_in[0:len(ser_in)-2].decode("ascii"))
			#stitch strings together for easy manipulation
			#strng = strng + decoded
			#values.append(float(decoded))
			print(decoded)
			values.append(decoded)
		except:
			print("Error")
			break
		#if we move onto the next set of values, just reassign the array
		if len(values) > 4:
			temp = values[4]
			values = []
			values.append(temp)
		print(values)

		#check if the array is full before using it
		if len(values) == 4:
			if (values[2]+values[3]/2) > 400:
				global mCounter
				mCounter += 1
				if mCounter == countLimit:
					endTime = (time.time()) + wateringTime #set an ending time for the watering, assigned at the
					print("WATERING THE FIRST")
					writeSerial("1") 
				elif mCounter > countLimit:
					if time.time() < endTime:
						print("WATERING")
						writeSerial("1")
					else:
						mCounter = 0
						writeSerial("0")
			else:
				global mCounter
				mCounter = 0

def timer(): #somewhat crap but functional timer system that works hourly
	while True:	
		if lOverride == False:
			hNow = datetime.now().hour
			#light timer system
			if(minHrL < maxHrL): #gets around the weirdness of midnight by checking if it pops up
				#the light will power for a certain time during the day
				if hNow >= minHrL and hNow < maxHrL:
					print("Turning on the Light")
					writeSerial("3") #the on  number for light in the arduino code
					time.sleep(checkTime) #wait for 5 seconds
				else:
					writeSerial("2") #the off number for light
					time.sleep(checkTime)
			else:
				if hNow >= minHrL or hNow < maxHrL:
					print("Turning on the light 2")
					writeSerial("3")
					time.sleep(checkTime)
				else:
					writeSerial("2")
					time.sleep(checkTime)
			if(minHrH < maxHrH):
				if hNow >= minHrH and hNow < maxHrH:
					print("Turning on heater")
					writeSerial("5")
					time.sleep(checkTime)
				else:
					writeSerial("4")
					time.sleep(checkTime)
			else:
				if hNow >= minHrH or hNow < maxHrH:
					print("Turning on heater")
					writeSerial("5")
					time.sleep(checkTime)
				else:
					writeSerial("4")
					time.sleep(checkTime)
		else:
			#takes input from the Blynk app
			print("Overridden")


#running concurrent threads so nothing interferes!
Thread(target = readSerial).start()
Thread(target = timer).start()



