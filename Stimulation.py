from time import sleep as realsleep
from math import e
#For actual implementation:
# sleep(n) sleeps n seconds
# setPeltier(state) sets peltier to state
# peltierStatus() returns peltier status (bool)
# temperature() returns water temperature
# getDate() returns today's date
# getSeconds() gives the seconds since day has started.
# ambientTemp() returns ambient temperature

timeDivider=float("inf") # 1x speed, 2 for 2x speed.
# timeDivider=100

waterAmount=0.5 # in kg
# Assume the specific heat capacity of water is 4200J/kgC
heatCapacity=waterAmount*4200

heaterRate=-420 # in watts

#note: stimulation does not take into account that higher heat capacity = lower heat loss.
roomTemp=30 # in C
roomPull=0.005 # in multiplier/second

waterTemp=roomTemp #initial water temperature.

# BIG CAVEAT: Time will not pass in this world outside of sleep() calls!
def sleep(seconds):
	# stimulate that many seconds forwards.
	global waterTemp,now
	if peltierState==True:
		waterTemp+=(heaterRate*seconds)/heatCapacity
	waterTemp-=(1-e**(-roomPull*seconds))*(waterTemp-roomTemp)
	realsleep(seconds/timeDivider)
	now=now+datetime.timedelta(0,seconds)

peltierState=False
def setPeltier(state):
	global peltierState
	if peltierState==state:
		raise RuntimeWarning(f"Peltier state toggled to {state} when already at that state!")
	else:
		peltierState=state

def peltierStatus():
	return peltierState

def temperature():
	return waterTemp

import datetime
now=datetime.datetime.now()
def getDate():
	return now.strftime('%Y-%m-%d')

def getSeconds(): # get seconds since day has started
	midnight=datetime.datetime.combine(now.date(), datetime.time())
	seconds=(now-midnight).seconds
	return seconds

def timeStep(days,seconds):
	global now
	now=now+datetime.timedelta(days,seconds)

def ambientTemp():
	return roomTemp