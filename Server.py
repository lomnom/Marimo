from functools import cached_property
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse
import json
import glob #indexing
from datetime import datetime, timedelta

def readFile(name):
	file=open(name,'r')
	data=file.read()
	file.close()
	return data

# shamelessly based on https://realpython.com/python-http-server/
class MarimoRequestHandler(BaseHTTPRequestHandler):
	@cached_property
	def url(self):
		return urlparse(self.path)

	@cached_property
	def query_data(self):
		return dict(parse_qsl(self.url.query))

	@cached_property
	def post_data(self):
		content_length = int(self.headers.get("Content-Length", 0))
		return self.rfile.read(content_length)

	@cached_property
	def form_data(self):
		return dict(parse_qsl(self.post_data.decode("utf-8")))

	@cached_property
	def cookies(self):
		return SimpleCookie(self.headers.get("Cookie"))

	pages={}

	def get_response(self):
		if "debug" in self.query_data and self.query_data["debug"]:
			self.send_response(200)
			self.send_header("Content-Type", "application/json")
			self.end_headers()
			return json.dumps(
				{
					"path": self.url.path,
					"query_data": self.query_data,
					"post_data": self.post_data.decode("utf-8"),
					"form_data": self.form_data,
					"cookies": {
						name: cookie.value
						for name, cookie in self.cookies.items()
					},
				}
			)
		else:
			if self.url.path in self.pages:
				return self.pages[self.url.path](
					self.url.path,
					self.query_data,
					self
				)
			else:
				return self.pages["404"](
					self.url.path,
					self.query_data,
					self
				)

	def do_GET(self):
		self.wfile.write(self.get_response().encode("utf-8"))

	def do_POST(self):
		self.do_GET()

def newPage(name):
	def makeNewPage(func):
		MarimoRequestHandler.pages[name]=func
	return makeNewPage

@newPage("404")
def notFoundPage(path,queryData,self):
	self.send_response(404)
	self.send_header("Content-Type", "text/html")
	self.end_headers()
	return readFile("Page404.html")

@newPage("/")
def mainPage(path,queryData,self):
	self.send_response(200)
	self.send_header("Content-Type", "text/html")
	self.end_headers()
	return readFile("PageMain.html")

# Input args: None
# Output:
# [[year,month,day], ...] least recent --> most recent
@newPage("/dataIndex")
def dataIndex(path,queryData,self):
	self.send_response(200)
	self.send_header("Content-Type", "application/json")
	self.end_headers()
	data={}
	directory=glob.glob("Logs/*")
	directory=[path.split("/")[-1] for path in directory]
	listing=[]
	for item in directory:
		year, month, day=item.split("-")
		listing.append((int(year),int(month),int(day)))
	listing.sort(key=lambda date: (date[0]*10000)+(date[1]*100)+date[2]) #least recent --> most recent
	return json.dumps(listing)

def getData(startDate,startTime,endDate,endTime):
	data=[]
	iterator=startDate
	while iterator<=endDate:
		try:
			dayData=readFile(f"Logs/{iterator.strftime('%Y-%m-%d')}")
		except FileNotFoundError:
			iterator+=timedelta(days=1)
			continue
		for line in dayData.split('\n')[:-1]: #last line is blank
			lineData=line.split(' ')
			seconds=int(lineData[0])
			peltierStatus=(lineData[1]=='C')
			tankTemp=float(lineData[2])
			ambientTemp=float(lineData[3])
			if iterator==startDate and seconds<=startTime:
				continue
			elif iterator==endDate and seconds>=endTime:
				break
			data.append(((iterator.year,iterator.month,iterator.day,seconds),(peltierStatus,tankTemp,ambientTemp)))
		iterator+=timedelta(days=1)
	return data

def processStartEnd(queryData):
	startDate,startTime=queryData["start"].split(",")
	endDate,endTime=queryData["end"].split(",")
	startDate,endDate=(datetime.strptime(startDate, "%Y-%m-%d"), datetime.strptime(endDate, "%Y-%m-%d"))
	startTime,endTime=(int(startTime), int(endTime))
	assert(endDate>=startDate)
	if endDate==startDate:
		assert(endTime>startTime)
	return (startDate,startTime,endDate,endTime)

# Input args: 
# - start: "{year}-{month}-{day},{seconds since start of day}" 
# - end: "{year}-{month}-{day},{seconds since start of day}"
# Output:
# [[[year,month,day,second],[on? bool, tankTemp float,ambientTemp float]], ...] least recent --> most recent, within the range (inclusive)
@newPage("/data")
def data(path,queryData,self):
	self.send_response(200)
	self.send_header("Content-Type", "application/json")
	self.end_headers()
	startDate,startTime,endDate,endTime=processStartEnd(queryData)

	return json.dumps(getData(startDate,startTime,endDate,endTime))

#  0     1     2     3
# 0.5 1 1.5 2 2.5 3 3.5
def statsIndex(array,index):
	index-=0.5
	if index%1==0:
		return array[int(index)]
	else:
		n=int(index)
		return (array[n]+array[n+1])/2

#assume sorted low to high.
def boxWhiskerValues(data,undefined=0): #Q1 Q2 Q3 min max
	if len(data)==1:
		return {
			"Q1":data[0],
			"Q3":data[0],
			"Q2":data[0],
			"min":data[0],"max":data[-1]
		}
	elif len(data)==0:
		return {
			"Q1":undefined,
			"Q3":undefined,
			"Q2":undefined,
			"min":undefined,"max":undefined
		}
	data.sort()
	length=len(data)
	return {
		"Q1":statsIndex(data,length/4),
		"Q3":statsIndex(data,length-length/4),
		"Q2":statsIndex(data,length/2),
		"min":data[0],"max":data[-1]
	}

# Input args: 
# - start: "{year}-{month}-{day},{seconds since start of day}" 
# - end: "{year}-{month}-{day},{seconds since start of day}"
# Output:
# {
#	"tank":{ #boxwhisker values
#		"min":float,
# 		"max":float,
# 		"Q1":float,
# 		"Q2":float,
# 		"Q3":float
# 	},"ambient":{boxwhisker values},
# 	"peltier":{
# 		"on":{boxwhisker values}, #duration that it is on/off before toggling again in seconds
# 		"off":{boxwhisker values},
# 	}
# }
@newPage("/dataAnalysis")
def dataAnalysis(path,queryData,self):
	self.send_response(200)
	self.send_header("Content-Type", "application/json")
	self.end_headers()
	startDate,startTime,endDate,endTime=processStartEnd(queryData)
	data=getData(startDate,startTime,endDate,endTime) #((year,month,day,seconds),(peltierStatus,tankTemp,ambientTemp))

	on=[] #NOTE: will glitch out if entries are missing. values will be incorrect.
	off=[]
	firstEntry=None
	lastEntry=None

	tankTemps=[]
	ambientTemps=[]
	time=0 # time since last change in peltier state.
	temperature=0 # temperature at the last peltier state change
	previousState=data[0][1][0]
	for index,entry in enumerate(data):
		tankTemps.append(entry[1][1])
		ambientTemps.append(entry[1][2])
		if index==0:
			temperature=entry[1][1]

		if previousState!=entry[1][0]:
			if previousState==False:
				off.append(time)
				lastEntry="off"
				if firstEntry==None:
					firstEntry="off"
			else:
				on.append(time)
				lastEntry="on"
				if firstEntry==None:
					firstEntry="on"
			time=0
			previousState=entry[1][0]
		else:
			time+=5 # THIS IS TICK LENGTH!!!!!!

	if firstEntry=="on":
		on=on[1:]
	elif firstEntry=="off":
		off=off[1:]

	if lastEntry=="on":
		on=on[:-1]
	elif lastEntry=="off":
		off=off[:-1]

	result={
		"tank": boxWhiskerValues(tankTemps),
		"ambient": boxWhiskerValues(ambientTemps),
		"peltier":{
			"on": boxWhiskerValues(on),
			"off": boxWhiskerValues(off)
		}
	}
	return json.dumps(result)

port=8000
if __name__ == "__main__":
	server = HTTPServer(("0.0.0.0", port), MarimoRequestHandler)
	print(f"at http://localhost:{port}/")
	server.serve_forever()