from pymitter import EventEmitter
from util.log import Logger 
from promise import Promise
import paho.mqtt.client as mqtt  
import json

log = Logger('connection')

def on_connect(client, userdata, flags, rc):
	print("Connected to host {} with result code {}".format(self.host))

class Connection(EventEmitter):

	def __init__(self, config):
		super().__init__()

		self.config = config
		self.name 	= config.account 
		self.host 	= config.host 
		self.token	= config.token

		self.client = None 

		self.is_noob = True 
		if self.config.secret != None:
			self.is_noob = False 

		self.recv_channel = ('noob_' if self.is_noob else 'nerd_') + self.token 
		self.send_channel = ('nerd_' if self.is_noob else 'noob_') + self.token

	def _log(self, msg):
		log.log(self.name + ': ' + msg)

	def _handle(self, err):
		log.error(self.name + ': ' + err)

	def connect(self):
		
		connection_instance = self

		def on_connect(client, userdata, flags, rc):
			client.subscribe(connection_instance.recv_channel)
			connection_instance._log('connected! subscribing to channel `{}`'.format(connection_instance.recv_channel))
			connection_instance.emit('connect')

		def on_message(client, userdata, msg):
			try:
				payload = json.loads(msg.payload)
				if type(payload) is bytes:
					payload = payload.decode('utf-8')
				# TO-DO: What is final form of payload? Should it be JSON object for transactions?
				connection_instance.emit('receive', payload)
			except Exception:
				pass 	

		def on_disconnect(client, userdata, rc):
			status = '' if rc == 0 else ' [potential network error]'
			connection_instance._log('disconnected from host `{}`'.format(connection_instance.host) + status)
			
		self.client = mqtt.Client()
		self.client.on_connect    = on_connect
		self.client.on_message 	  = on_message
		self.client.on_disconnect = on_disconnect

		self._log('connecting to host `{}`...'.format(self.host))
		self.client.connect_async(host=this.host, port=1883, keepalive=30)
		self.client.loop_start()

		return Promise.resolve(None)

	def disconnect(self):
		self.client.loop_stop()
		self.client.disconnect()
		return Promise.resolve(None)

	def send(self, msg):
		self.client.publish(topic=self.send_channel, payload=json.dumps(msg))

	

