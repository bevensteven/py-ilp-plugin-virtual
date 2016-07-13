from promise import Promise
from pymitter import EventEmitter
import paho.mqtt.client as mqtt

'''
	Example usage with public MQTT broker at 'broker.mqtt.com`
'''

class Connection(EventEmitter):

	def __init__(self, config):
		super().__init__()

		self.config = config 
		self.name = config['account']
		self.host = config['host']
		self.token = config['token']

		self.client = None 
		self.recv_channel = 'noob_' + self.token 
		self.send_channel = 'nerd_' + self.token 

		self.on("receive", self.send)


	def connect(self):
		connection_instance = self 

		def on_connect(client, userdata, flags, rc):
			client.subscribe(connection_instance.recv_channel)
			print("Connected! Subscribing to channel {}".format(connection_instance.recv_channel))
			connection_instance.emit("connect")

		def on_message(client, userdata, msg):
			print("Receiving message")
			connection_instance.emit("receive", msg="Hello other client")

		def on_disconnect(client, userdata, rc):
			print("Disconnected!")

		self.client = mqtt.Client()
		self.client.on_connect = on_connect
		self.client.on_message = on_message
		self.client.on_disconnect = on_disconnect

		self.client.connect_async(host=self.host, port=1883, keepalive=30)
		self.client.loop_start()

		return Promise.resolve(None)

	def disconnect(self):
		self.client.loop_stop()
		self.client.disconnect()
		return Promise.resolve(None)

	def send(self, msg):
		self.client.publish(topic=self.send_channel, payload=msg)

if __name__ == "__main__":
	TEST_CONFIG = {
		"account": "Steven", 
		"token": "test_mqtt", 
		"host": "broker.hivemq.com"
	}

	connection = Connection(TEST_CONFIG)
	connection.connect()
	# connected to mqtt broker and listening on topic 'noob_test_mqtt'


