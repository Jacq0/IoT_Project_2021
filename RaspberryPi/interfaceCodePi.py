#!/usr/bin/env python
import serial
import time
import io
from datetime import datetime
from threading import Thread
import BlynkLib
import Queue

#This code uses a lot of global calls for variables, and it's usually frowned upon instead of passing the variable into the method
#but its the only way I could get things working coherently!

#stuff we need from the blynk script
#import blynkManagerScript as blynkScript
BLYNK_AUTH = 'AUTH_CODE_HERE!' #our authetication code!
blynk = BlynkLib.Blynk(BLYNK_AUTH)

#initialise serial comms, the try except is to fix the issue with it switching ports occasionally
try:
	ser = serial.Serial('/dev/ttyACM0', 9600, timeout = 120) #its usually here
	ser.flushInput()
except:
	ser = serial.Serial('/dev/ttyACM1', 9600, timeout = 120) #but sometimes its here
	ser.flushInput()

#set up time variables, we are using hours as it is accurate enough for this use case
#light timers
minHrL = 12
maxHrL = 22
#heater timer
minHrH = 6
maxHrH = 12

#other variables (overrides for the lights and heaters)
checkTime = 30 #check the time and send an update to the arduino every 30 seconds, telling it what to do!

#user override options are stored heres
lOverride = False
hOverride = False
wOverride = False

#the status of these devices when the user overrides them!
lStatus = False
hStatus = False
wStatus = False

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
mThreshold = 550 #the threshold at which the system will decide to iterate the counter
mCounter = 0 #counter that keeps track of the number of times the threashold has been breached
wateringTime = 30 #the time the system leaves the watering valve open

#endTimeW = time.time

#the temp values needed to initialise the heating mat
tCounter = 0
tThreshold = 10
heatingTime = 600 

#variables for receiving notifications about critical heat! Unused but a good potential addition!
heatNotifTime = time.time()
heatNotifInterval = 1800  #send a notification about the heat if its too high every 30 minutes

#the number of counts needed to breach the limit and react (stops erros when value hovers around thresholds)
countLimit = 5

#the queue of values to send down to the arduino
queue = []

#the values received by the arduino
values = []

#this value is the max value the moisture sensors read dry, since they read lower for lower moisture we need to subtract this
#it can sometimes go over depending on conditions but its not a big issue if it does!
minMoist = 700

#the Queue module setup, its thread safe too!
#its problematic so not being used right now
#q = Queue.Queue()

#IMPROVE THE QUEUE
def addToQueue(value):
	global queue
	queue.append(value)
	print(queue) #show us whats in the queue, for debug
	#with the queue class, didn't work but maybe sombody else will have moreluck
	#q.put(value)

#this method sends values from the queue on a regular interval
#it doesn't work and i have no idea why
def sendQueuedValues():
	global queue
	while True:
		if len(queue) > 0:
			ser.write(queue[0]) #send first element
			queue.pop(0) #pop the first element off the queue
			time.sleep(0.3) #wait a bit before sending the next, to not overload the arduino
		#With the queue class
		#ser.write(q.get())
		#time.sleep(0.3)

def readSerial():
	global values
	values = []
	while True:
		try:
			ser_in = ser.readline()
			decoded = float(ser_in[0:len(ser_in)-2].decode("ascii")) #this takes in the serial data, and decodes whats needed to ascii
			#stitch strings together for easy manipulation
			print(decoded)
			values.append(decoded) #stick the decoded value into values
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
			sendBlynkData() #send the data to the blynk app

def activateWater(): #test for the woverrife while statement
	#waitTime == time.time() #experiment of failed timer system
	while True: #the infinite loop
		while wOverride == False: #and waitTime < time.time():
			time.sleep(5)
			#waitTime = time.time() + 5
			if len(values) == 4:
				#endTimeW = time.time() #this is a buggy fix for the issue
				#checkTimer = time.time() + 5
				if (values[2]+values[3]/2) > mThreshold:
					#endTimeW = time.time()
					global mCounter
					mCounter += 1 #counts up if we detect dry so we only activate after the system has been dry for a while!
					if mCounter == countLimit :
						endTimeW = (time.time()) + wateringTime #set an ending time for the watering, assigned at the
						print("WATERING THE FIRST")
						#blynk.notify("The plants are being watered")
						addToQueue("1")
					elif mCounter > countLimit:
						if time.time() < endTimeW:
							print("WATERING")
							addToQueue("1")
						else:
							mCounter = 0
							addToQueue("0")
				else:
					global mCounter
					addToQueue("0")
					mCounter = 0

def activateHeat():
	while True:
		while hOverride == False:
			time.sleep(5) #short counter so we aren't innundated with data
			if values[0] >= 25  and heatNotifTime < time.time() :
				#do something with regards to heat, since the system has no real cooling, notify the user, etc.
				blynk.notify("The System is getting warm")
				heatNotifTime = time.time() + heatNotifInterval #set the new notification time so we dont spam the user!
			elif values[0] < tThreshold:
				#do something else with this data, in this case turn on the heating
				blynk.notify("The heater has been enabled!")
				global tCounter
				tCounter += 1
				if tCounter == countLimit:
					endTimeH = (time.time()) + heatingTime
					print("Starting Heating")
					addToQueue("3")
				elif tCounter > countLimit:
					if time.time() < endTimeH:
						print("Heating")
						addToQueue("3")
					else:
						tCounter = 0
						addToQueue("2")

#we send blynk our values
def sendBlynkData():
	blynk.virtual_write(18, minMoist-values[3]) #moisture 2
	blynk.virtual_write(19, minMoist-values[2]) #moisture 1
	blynk.virtual_write(20, values[0]) #temp
	blynk.virtual_write(21, values[1]) #humidity

def timerLight(): #somewhat crap but functional timer system that works hourly
	while True:
		while lOverride == False:
			hNow = datetime.now().hour
			#light timer system
			if(minHrL < maxHrL): #gets around the weirdness of midnight by checking if it pops up
				#the light will power for a certain time during the day
				if hNow >= minHrL and hNow < maxHrL:
					print("Turning on the Light")
					addToQueue("3") #the on  number for light in the arduino code
					time.sleep(checkTime) #wait for 5 seconds
				else:
					addToQueue("2") #the off number for light
					time.sleep(checkTime)
			else:
				if hNow >= minHrL or hNow < maxHrL:
					print("Turning on the light 2")
					addToQueue("3")
					time.sleep(checkTime)
				else:
					addToQueue("2")
					time.sleep(checkTime)

def timerHeat(): #A similar timer for the heating
	while True:
		time.sleep(checkTime);
		if hOverride == False:
			hNow = datetime.now().hour
			if (minHrH < maxHrH):
				if hNow >= minHrH and hNow < maxHrH:
					print("Turning on heater")
					addToQueue("5")
					time.sleep(checkTime)
				else:
					addToQueue("4")
					time.sleep(checkTime)
			else:
				if hNow >= minHrH or hNow < maxHrH:
					print("Turning on the heat 2")
					addToQueue("5")
					time.sleep(checkTime)
				else:
					addToQueue("4")
					time.sleep(checkTime)

#allows user to override and take control of the systems!
@blynk.VIRTUAL_WRITE(1)
def overrideLight(pin):
	global lOverride
	lOverride = bool(int(str(pin)[3])) #the really jaqnky solution to reading the blynk buttons, since read doesn't work!
	print(lOverride)

@blynk.VIRTUAL_WRITE(0)
def overrideHeat(pin):
	global hOverride
	hOverride = bool(int(str(pin)[3]))
	print(hOverride)

@blynk.VIRTUAL_WRITE(2)
def overrideWater(pin):
	global wOverride
	wOverride = bool(int(str(pin)[3]))
	print(wOverride)


#our toggle buttons for the user, they are only active if the user overrides the automatic controls!
#I commented out most of the .notify, It works but it stops it being annoying!
@blynk.VIRTUAL_WRITE(3)
def toggleHeat(pin):
	global hStatus
	hStatus = bool(int(str(pin)[3]))
	print(hStatus)
	if hOverride == True:
		if hStatus == True:
			addToQueue("5")
			blynk.notify("Heat mat on")
		else:
			addToQueue("4")
			blynk.notify("Heat mat off")

@blynk.VIRTUAL_WRITE(4)
def toggleLight(pin):
	global lStatus
	global queue
	lStatus = bool(int(str(pin)[3]))
	print(lStatus)
	if lOverride == True:
		if lStatus == True:
			addToQueue("3")
			#blynk.notify("Lights On")
		else:
			addToQueue("2")
			#blynk.notify("Lights Off")

@blynk.VIRTUAL_WRITE(5)
def toggleWater(pin):
	global wStatus
	global queue
	wStatus = bool(int(str(pin)[3]))
	print(wStatus)
	if wOverride == True:
		if wStatus == True:
			addToQueue("1")
			#blynk.notify("Valve open: Watering")
		else:
			addToQueue("0")
			#blynk.notify("Valve Closed")

#running concurrent threads so nothing interferes!
Thread(target = readSerial).start() #serial reads thread
Thread(target = timerLight).start() #light timer thread
Thread(target = timerHeat).start() #heat timer thread
Thread(target = sendQueuedValues).start() #value sending method, doesn't work and have no idea why

#experimental threads for fixing issues
Thread(target =  activateWater).start()
#Thread(target = activateHeat).start()

#run the blynk script last!
while True:
	blynk.run() #run our blynk script
