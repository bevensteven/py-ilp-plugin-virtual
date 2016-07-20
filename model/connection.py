import sys 
from pymitter import EventEmitter
from promise import Promise
import paho.mqtt.client as mqtt  
import json

from util.log import Logger 
from util.utils import is_json

log = Logger('connection')

class Connection(EventEmitter):

	'''
		Create a Connection instance to an MQTT broker via paho.mqtt

		@param config

		@param config.account 
		@param config.host
		@param config.token
	'''

	def __init__(self, config):
		self.DEBUG = None 	# for debugging

		super().__init__()

		self.config = config
		self.name 	= config['account']
		self.host 	= config['host']
		self.token	= config['token']

		self.client = None 

		self.is_noob = True 
		if 'secret' in self.config:
			self.is_noob = False 

		self.recv_channel = ('noob_' if self.is_noob else 'nerd_') + self.token
		self.send_channel = ('nerd_' if self.is_noob else 'noob_') + self.token

	def _log(self, msg):
		log.log(self.name + ': ' + msg)

	def _handle(self, err):
		log.error(self.name + ': ' + err)

	def connect(self):

		def on_connect(client, userdata, flags, rc):
			client.subscribe(self.recv_channel)
			self._log('connected! subscribing to channel `{}`'
				.format(self.recv_channel))
			self.emit('connect')

		def on_message(client, userdata, msg):
			try:
				self.DEBUG = msg 	# debugging
				self._log('receiving message')
				if type(msg.payload) is bytes:
					payload = msg.payload.decode('utf-8')
					if is_json(payload):
						payload = json.loads(payload)
				else:
					payload = msg.payload
					if is_json(msg.payload):
						payload = json.loads(msg.payload)
				self.emit('receive', payload)
			except Exception as e:
				self._log('exception raised on receiving message')	# debugging
				print(e)
				pass 	

		def on_publish(client, userdata, mid):
			self._log('published message')
			self.emit("published")

		def on_disconnect(client, userdata, rc):
			status = '' if rc == 0 else ' [potential network error]'
			self._log('disconnected from host `{}`'
				.format(self.host) + status)
			self.emit("disconnect")
			
		self.client = mqtt.Client()
		self.client.on_connect    = on_connect
		self.client.on_message 	  = on_message
		self.client.on_disconnect = on_disconnect

		self._log('connecting to host `{}`...'.format(self.host))
		self.client.connect_async(host=self.host, port=1883, keepalive=30)
		self.client.loop_start()

		return Promise.resolve(None)

	def disconnect(self):
		self.client.loop_stop()
		self.client.disconnect()
		return Promise.resolve(None)

	def send(self, msg):

		def fulfill_send(resolve, reject):
			self.client.publish(topic=self.send_channel,
				payload=json.dumps(msg))
			self._log("PUBLISHED MESSAGE") # debugging
			self.once("published", lambda: resolve(None))

		return Promise(fulfill_send)

	
# For testing 
if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == 'test':
		test_configuration = {
			"account": "Steven",
			"token": "test_mqtt",
			"host": "broker.hivemq.com"
		}
