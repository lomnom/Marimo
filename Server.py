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
	startDate,startTime=queryData["start"].split(",")
	endDate,endTime=queryData["end"].split(",")
	startDate,endDate=(datetime.strptime(startDate, "%Y-%m-%d"), datetime.strptime(endDate, "%Y-%m-%d"))
	startTime,endTime=(int(startTime), int(endTime))
	assert(endDate>=startDate)
	if endDate==startDate:
		assert(endTime>startTime)

	data=[]
	iterator=startDate
	while iterator<=endDate:
		dayData=readFile(f"Logs/{iterator.strftime('%Y-%m-%d')}")
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
			data.append([[iterator.year,iterator.month,iterator.day,seconds],[peltierStatus,tankTemp,ambientTemp]])
		iterator+=timedelta(days=1)
	return json.dumps(data)

@newPage("/dataAnalysis")
def dataAnalysis(path,queryData,self):
	return ""

port=8000
if __name__ == "__main__":
	server = HTTPServer(("0.0.0.0", port), MarimoRequestHandler)
	print(f"at http://localhost:{port}/")
	server.serve_forever()