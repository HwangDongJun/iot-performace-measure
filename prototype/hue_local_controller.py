import requests
import json
import time

from configparser import ConfigParser

class HueLocalController():
	def __init__(self, bridge_ip, username):
		self.bridge_ip = bridge_ip
		self.bridge_id = ''
		# if length of bridge_ip is zero, start bridge scan(using requests get).
		if len(bridge_ip) == 0:
			self.bridge_scan()
		# get username but length of username is zero -> start add uew user(using requests post).
		self.username = username
		if len(username) == 0:
			self.add_new_user()
		self.lights = dict()

	def bridge_scan(self):
		req = requests.get('https://discovery.meethue.com')
		bridge = json.loads(req.content.decode('utf-8'))[0]
		self.bridge_ip = bridge['internalipaddress']
		self.bridge_id = bridge['id']

	def add_new_user(self):
		body = '{"devicetype":"local_control_hue_app"}'
		req = requests.post('http://{bridge}/api'.format(bridge=self.bridge_ip), data=body)
		req = json.loads(req.content.decode('utf-8')[1:-1])
		if 'error' in req.keys():
			print(req['error']['description'])
		else:
			self.username = req['success']['username']
			print('New username {}'.format(self.username))

	def lights_scan(self):
		req = requests.get('http://{bridge}/api/{username}/lights'.format(bridge=self.bridge_ip, username=self.username))

		self.lights = json.loads(req.content.decode('utf-8'))
		print(self.lights)
		return self.lights

	def detect_me(self, lightnumber=7, sat=254, bri=254, hue=21241):
		data_on = '{{"on":true, "sat":{sat}, "bri":{bri}, "hue":{hue}}}'.format(sat=sat, bri=bri, hue=hue)
		url = "http://{bridge}/api/{username}/lights/{lightnumber}/state".format(
																bridge=self.bridge_ip,
																username=self.username,
																lightnumber=lightnumber)
		# senf url requests put
		requests.put(url, data=data_on)

	def detect_not_me(self, lightnumber=7):
		self.detect_me(lightnumber=lightnumber, sat=254, bri=254, hue=11241)

	def turn_off(self, lightnumber=7):
		data_off = '{"on":false}'
		url = "http://{bridge}/api/{username}/lights/{lightnumber}/state".format(
																bridge=self.bridge_ip,
																username=self.username,
																lightnumber=lightnumber)
		requests.put(url, data=data_off)

	def turn_on(self, lightnumber):
		data_on = '{"on":true}'
		url = "http://{bridge}/api/{username}/lights/{lightnumber}/state".format(
																bridge=self.bridge_ip,
																username=self.username,
																lightnumber=lightnumber)
		# senf url requests put
		requests.put(url, data=data_on)

	#def all_lights_on(self):

	def all_lights_off(self):
		for light in self.lights.keys():
			self.turn_off(lightnumber=light)
