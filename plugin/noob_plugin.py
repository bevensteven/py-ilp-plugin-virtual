from pymitter import EventEmitter
from util.log import Logger 
from util.utils import implement, PluginException 
from model.connection import Connection
from promise import Promise 

log = Logger('noob_plugin')

class Noob_Plugin_Virtual(EventEmitter):

	'''
		Create a Noob plugin
		@param opts 

		@param opts.store 

		@param opts.auth
		@param opts.auth.account
		@param opts.auth.token
		@param opts.auth.host 
	'''

	def __init__(self, opts):
		self.DEBUG = None # for debugging 

		super().__init__()

		# self.id = opts.id 	
		# Compatibility with five bells connector; is this necessary? 

		self.auth = opts['auth']
		self.connected = False 
		self.connection_config = opts['auth']
		self.connection = Connection(self.connection_config)

		on_receive = lambda obj: self._receive(obj).catch(self._handle)
		self.connection.on('receive', on_receive)
		self.connection.on('disconnect', self.disconnect)

		self._expects = dict()
		self._seen = dict()
		self._fulfilled = dict()

		self._log("Initialized Noob Plugin Virtual: {}".format(self.auth))

	def _handle(self, err):
		self.emit('exception', err)
		raise err

	def can_connect_to_ledger(self, auth):
		implement()

	def _log(self, msg):
		log.log(self.auth['account'] + ': ' + msg)

	def _expect_response(self, tid):
		self._expects[tid] = True 

	def _expected_response(self, tid):
		if tid not in self._expects:
			self._expect_response(tid)
		return self._expects[tid]

	def _receive_response(self, tid):
		self._expects[tid] = False 

	def _see_transfer(self, tid):
		self._seen[tid] = True 

	def _seen_transfer(self, tid):
		return tid in self._seen

	def _fulfill_transfer(self, id):
		self._fulfilled[tid] = True 

	def _fulfilled_transfer(self, tid):
		return self._fulfilled[tid]

	def _receive(self, obj):
		'''
			Cases:

			* obj.type == transfer && not seen_transfer(obj.transfer.id)
			* obj.type == acknowledge && expected_response(obj.transfer.id)
			* obj.type == fulfill_execution_condition && 
				not fulfilled_transfer(obj.transfer.id)
			* obj.type == fulfill_cancellation_condition &&
				not fulfilled_trasnfer(obj.transfer.id)
			* obj.type == reject && not fulfilled_transfer(obj.transfer.id) 
			* obj.type == reply
			* obj.type == balance 
			* obj.type == info 
			* obj.type == settlement
		'''
		print('_receive called with obj: {}, type: {}'.format(obj, type(obj))) # debugging

		if type(obj) is not dict:
			self._log("unexpected non-JSON message: '{}'".format(obj))
			return Promise.resolve(None)
		self.DEBUG = obj # debugging
		
		if obj['type'] == 'transfer' \
			and not self._seen_transfer(obj['transfer']['id']):
			self._see_transfer(obj['transfer']['id'])
			self._log('received a Transfer with tid {}'
				.format(obj['transfer']['id']))
			self.emit("receive", obj['transfer'])
			return self.connection.send({
					"type": "acknowledge",
					"transfer": obj['transfer'],
					"message": "transfer accepted"
				})

		elif obj['type'] == 'acknowledge' \
			and self._expected_response(obj['transfer']['id']):
			self._receive_response(obj['transfer']['id'])
			self._log('received an ACK on tid: {}'
				.format(obj['transfer']['id']))
			# TO-DO: Should accept be fulfill execution condition in OTP
			self.emit("accept", 
				obj['transfer'], 
				obj['message'].encode('utf-8')) 
			return Promise.resolve(None)

		elif obj['type'] == 'fulfill_execution_condition' \
			and not self._fulfilled_transfer(obj['transfer']['id']):
			self.emit("fulfill_execution_condition", 
				obj['transfer'], 
				obj['fulfillment'].encode('utf-8'))
			self._fulfill_transfer(obj['transfer']['id'])
			return Promise.resolve(None)

		elif obj['type'] == 'fulfill_cancellation_condtion' \
			and not self._fulfilled_transfer(obj['transfer']['id']):
			self.emit('fullfill_cancellation_condition',
				obj['transfer'],
				obj['fulfillment'].encode('utf-8'))
			self._fulfill_transfer(obj['transfer']['id'])
			return Promise.resolve(None)

		elif obj['type'] == 'reject' \
			and not this._fulfilled_transfer(obj['transfer']['id']):
			self._log('received a reject on tid: {}'
				.format(obj['transfer']['id']))
			self.emit('reject', 
				obj['transfer'], 
				obj['message'].encode('utf-8'))
			return Promise.resolve(None)

		elif obj['type'] == 'reply':
			self._log('received a reply on tid: {}'
				.format(obj['transfer']['id']))
			self.emit('reply', 
				obj['transfer'], 
				obj['message'].encode('utf-8'))
			return Promise.resolve(None)

		elif obj['type'] == 'balance':
			self._log('received balance: {}'.format(obj['balance']))
			self.emit('balance', obj['balance'])
			return Promise.resolve(None)

		elif obj['type'] == 'info':
			self.log('received info.')
			self.emit('_info', obj['info'])
			return Promise.resolve(None)

		elif obj['type'] == 'settlement':
			self._log('received settlement notification.')
			self.emit('settlement', obj['balance'])
			return Promise.resolve(None)

		else:
			raise Exception("Invalid message received")
			return Promise.resolve(None)

	def connect(self):
		self.connection.connect()

		def fulfill_connect(resolve, reject):
			def noob_connect():
				self.emit('connect')
				self.connected = True 
				resolve(None)
			self.connection.on('connect', noob_connect())

		return Promise(fulfill_connect)

	def disconnect(self):

		def fulfill_disconnect():
			self.emit('disconnect')
			self.connected = False 
			return Promise.resolve(None)

		return self.connection.disconnect().then(success=fulfill_disconnect)

	def is_connected(self):
		return self.connected

	def get_connectors(self):
		# Currently, only connections between two plugins are supported 
		# Thus, the list is empty
		return Promise.resolve([])

	def send(self, outgoing_transfer):
		self._log("Sending out a Transfer with tid: {}"
			.format(outgoing_transfer['id']))
		self._expect_response(outgoing_transfer['id'])
		return self.connection.send({
				"type": "transfer",
				"transfer": outgoing_transfer
			}).catch(self._handle)

	def get_balance(self):
		self._log("sending balance query...")
		self.connection.send({
				"type": "balance"
			})

		def fulfill_get_balance(resolve, reject):
			self.once("balance", lambda balance: resolve(balance))

		return Promise(fulfill_get_balance)

	def get_info(self):
		self._log("sending getInfo query...")
		self.connection.send({
				"type": "info"
			})

		def fulfill_get_info(resolve, reject):
			self.once("_info", lambda info: resolve(info))

		return Promise(fulfill_get_info)

	def fulfill_condition(self, transfer_id, fulfillment):
		return self.connection.send({
				"type": "fulfillment",
				"transferId": transfer_id,
				"fulfillment": fulfillment
			})

	def reply_to_transfer(self, transfer_id, reply_message):
		return self.connection.send({
				"type": "reply",
				"transferId": transfer_id,
				"message": reply_message
			})

if __name__ == '__main__':
	import sys 
	if len(sys.argv) > 1 and sys.argv[1] == 'test':
		test_opt = {
			'auth': {
				'account': 'Steven',
				'token': 'test_mqtt',
				'host': 'broker.hivemq.com'
			}
		}
		test_plugin = Noob_Plugin_Virtual(test_opt)
		test_plugin.connect()