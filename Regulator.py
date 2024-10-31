import Stimulation as s

horizbar=[" ","▏","▎","▍","▌","▋","▊","▉","█"]
def bar(number, scale): #number is positive float, scale is units/character
	number=number/scale
	return (round(number-0.5)*horizbar[-1])+horizbar[round((number%1)*9-0.5)]

def printState():
	print(
		f"{'C' if s.peltierStatus() else '.'}, {bar(s.temperature(),1)} {round(s.temperature(),3)},"\
		f" t={s.getSeconds()}, ambient={s.ambientTemp()}, {s.getDate()}"
	)

# def stimulationTesting():
# 	while True:
# 		try:
# 			c=input()
# 			if c=='q':
# 				return
# 			else:
# 				print(eval(c))
# 				print("Success!")
# 		except:
# 			pass
# 		s.sleep(5)
# 		printState()

loggingDirectory="Logs/"
loggingDate=s.getDate()
logFile=open(loggingDirectory+loggingDate,'a')
def logState(): #logs are in format [seconds since day started] [peltier status] [temperature]
	global loggingDate, logFile
	if s.getDate()!=loggingDate:
		logFile.close()
		loggingDate=s.getDate()
		logFile=open(loggingDirectory+loggingDate,'a')
	logFile.write(f"{s.getSeconds()} {'C' if s.peltierStatus() else '.'} {round(s.temperature(),2)} {round(s.ambientTemp(),2)}\n")
	logFile.flush()

# stimulationTesting()

lowerBound=22 # minimum temp, in C
upperBound=23 # max temp

def regulationLoop():
	while True:
		currTemp=s.temperature()
		if s.peltierStatus():
			if currTemp<lowerBound:
				s.setPeltier(False)
				print("Stopping cooling")
		else:
			if currTemp>upperBound:
				s.setPeltier(True)
				print("Starting cooling")
		printState()
		logState()

		s.sleep(5)

regulationLoop()