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
		self._account = opts["account"]
		self._prefix = None

		self.auth = opts['auth']
		self.connected = False 
		self.connection_config = opts['auth']
		self.connection = Connection(self.connection_config)

		on_receive = lambda obj: self._receive(obj).catch(self._handle)
		self.connection.on('receive', on_receive)
		self.connection.on('disconnect', self.disconnect)

		self.settler = opts['_optimisticPlugin']
		self.settle_address = opts['settleAddress']
		self.max_balance = opts['max']
		self.settle_percent = opts['settlePercent'] or '0.5'

		self._expects = dict()
		self._seen = dict()
		self._fulfilled = dict()

		if self.settler and self.settle_address:
			on_settlement = lambda obj: self.settler.send({
					"account": self.settle_address,
					"amount": self._get_settle_amount(obj['balance'], obj['max']),
					"id": uuid.uuid4()
				})
			def on_incoming_transfer(transfer):
				print("NOOB:", transfer)
				if transfer['account'] != self.settle_address:
					return
				self._confirm_settle(transfer)
			self.settler.on("incoming_transfer", on_incoming_transfer)

		self._log("Initialized Noob Plugin Virtual: {}".format(self.auth))

	def _handle(self, err):
		self.emit('exception', err)
		raise err

	def _confirm_settle(self, transfer):
		self.connection.send({
				"type": "settled",
				"transfer": transfer
			})

	def _get_settle_amount(self, balance, max):
		balance_number = float(balance)
		max_number = float(self.max_balance)
		settle_percent_number = float(self.settle_percent_number)

		# amount balance must increase by 
		amount = str((max_number - balance_number) * settle_percent_number) + ''
		self._log('going to settle for ' + amount)
		return amount 

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

	def _fulfill_transfer(self, tid):
		self._fulfilled[tid] = True 

	def _fulfilled_transfer(self, tid):
		if tid not in self._fulfilled:
			self._fulfilled[tid] = False
		return self._fulfilled[tid]

	def _receive(self, obj):
		'''
			Call back for incoming messages.

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
		# print('_receive called with obj: {}, type: {}'.format(obj, type(obj))) # debugging

		if type(obj) is not dict:
			self._log("unexpected non-JSON message: '{}'".format(obj))
			return Promise.resolve(None)
		self.DEBUG = obj # debugging
		
		if obj['type'] == 'transfer' \
			and not self._seen_transfer(obj['transfer']['id']):

			self._see_transfer(obj['transfer']['id'])
			self._log('received a Transfer with tid {}'
				.format(obj['transfer']['id']))
			if obj['transfer']['executionCondition']:
				self.emit("incoming_prepare", obj['transfer'])
			else:
				self.emit("incoming_transfer", obj['transfer'])
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
			self.emit("_accepted", obj['transfer'])
			if obj['transfer']['executionCondition']:
				self.emit("outgoing_prepare", obj['transfer'])
			else:
				self._log("GOT AN OUTGOING TRANSFER ACCEPTED")
				self.emit("outgoing_transfer", obj['transfer'])
			return Promise.resolve(None)

		elif obj['type'] == 'fulfill_execution_condition' \
			and not self._fulfilled_transfer(obj['transfer']['id']):

			self._fulfill_transfer(obj['transfer']['id'])
			self.emit("outgoing_fulfill" if obj['toNerd'] else "incoming_fulfill",
				obj['transfer'],
				obj['fulfillment'].encode('utf-8'))
			return Promise.resolve(None)

		elif obj['type'] == 'fulfill_cancellation_condtion' \
			and not self._fulfilled_transfer(obj['transfer']['id']):

			self.emit('fullfill_cancellation_condition',
				obj['transfer'],
				obj['fulfillment'].encode('utf-8'))
			self._fulfill_transfer(obj['transfer']['id'])
			return Promise.resolve(None)

		elif obj['type'] == 'reject' \
			and not self._fulfilled_transfer(obj['transfer']['id']):

			self._log('received a reject on tid: {}'
				.format(obj['transfer']['id']))
			self.emit("_rejected", obj['transfer'])
			self.emit("outgoing_cancel" if obj['toNerd'] else "incoming_cancel",
				obj['transfer'])
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
			self.emit('_settlement', obj)
			self.emit('settlement', obj['balance'])
			return Promise.resolve(None)

		elif obj['type'] == 'prefix':

			self._log('received prefix.')
			self.emit('_prefix', obj['prefix'])
			return Promise.resolve(None)

		elif obj['type'] == 'manual_reject':

			self._log("received manual reject on: {}".format(obj['transfer']['id']))
			self.emit("outgoing_reject", obj['transfer'], obj['message'])
			return Promise.resolve(None)

		elif obj['type'] == 'manual_reject_failure':

			self._log('manual rejection failed on {}'.format(obj['id']))
			self.emit('_manual_reject_failure', obj['id'], obj['message'])
			return Promise.resolve(None)

		elif obj['type'] == 'manual_reject_success':

			self._log("manual reject success on: {}".format(obj['transfer']['id']))
			self.emit("incoming_reject", obj['transfer'], obj['message'])
			self.emit("_manual_reject_success", obj['transfer']['id'])
			return Promise.resolve(None)

		else:
			raise Exception("Invalid message received")
			return Promise.resolve(None)

	def get_prefix(self):
		if self._prefix:
			return Promise.resolve(self._prefix)
		self._log("sending prefix query...")

		def resolver(resolve, reject):
			def on_prefix(prefix):
				self._prefix = prefix 
				resolve(prefix)
			self.on("_prefix", on_prefix)
			self.connection.send({
					"type": "prefix"
				})

		return Promise(resolver)

	def connect(self):
		self.connection.connect()

		def fulfill_connect(resolve, reject):
			def noob_connect():
				self.connected = True 
				self.emit('connect')
				resolve(None)
			self.connection.on('connect', noob_connect())

		return Promise(fulfill_connect)

	def disconnect(self):

		def fulfill_disconnect():
			self.connected = False 
			self.emit('disconnect')
			return Promise.resolve(None)

		return self.connection.disconnect().then(success=fulfill_disconnect)

	def is_connected(self):
		return self.connected

	def send(self, outgoing_transfer):
		self._log("Sending out a Transfer with tid: {}"
			.format(outgoing_transfer['id']))
		self._expect_response(outgoing_transfer['id'])
		### DEBUGGING ### 
		import datetime
		outgoing_transfer['expiresAt'] = str(datetime.datetime.isoformat( \
			datetime.datetime.now() + datetime.timedelta(0, 25210)))
		### END DEBUGGING ### 

		def send_resolver(resolve, reject):
			resolved = False 

			def on_accepted(transfer):
				if not resolved and transfer['id'] == outgoing_transfer['id']:
					resolved = True 
					resolve(None)

			def on_rejected(transfer):
				if not resolved and transfer['id'] == outgoing_transfer['id']:
					resolved = True 
					reject(raise Exception('transfer was invalid'))

			self.on("_accepted", on_accepted)
			self.on("_rejected", on_rejected)

			def get_prefix_then(prefix):
				outgoing_transfer['ledger']	= prefix 
				self.connection.send({
						"type": "transfer",
						"transfer": outgoing_transfer
					}).catch(self._handle)

			self.get_prefix() \
				.then(get_prefix_then) \
					.catch(self._handle)

		return Promise(send_resolver)

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

	def get_account(self):
		return self.auth['account']

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

	def reject_incoming_transfer(self, transfer_id):
		self._log("sending out a manual reject on tid: " + transfer_id)

		def resolve_rejection(resolve, reject):
			resolved = False 

			def on_reject_sucess(transfer):
				if not resolved and transfer['id'] == transfer_id:
					resolved = True 
					resolve(None)

			def on_reject_failure(id, message):
				if not resolved and transfer_id == id:
					resolved = True 
					reject(raise Exception(message))

			self.on("_manual_reject_success", on_reject_success)
			self.on("_manual_reject_failure", on_reject_failure)

			self.connection.send({
					"type": "manual_reject",
					"transferId": transfer_id,
					"message": "manually rejected"
				}).catch(self._handle)

		return Promise(resolve_rejection)

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