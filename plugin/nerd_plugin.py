from pymitter import EventEmitter 
from promise import Promise
from datetime import datetime

from util.log import Logger 
from util.utils import implement, PluginException
from model.connection import Connection
from model.transfer import Transfer 
from model.transfer_log import Transfer_Log

# TO-DO: Require 'five-bells-condition' for condition fulfillment
# TO-DO: Find proper Python type/module for buffer usage 

log = Logger('nerd_plugin')

class Nerd_Plugin_Virtual(EventEmitter):
	'''
		### LedgerPlugin API ### 

		Create a Nerd plugin
	'''

	def __init__(self, opts):
		super().__init__()

		self._handle = lambda err: self.emit('exception', err)

		# self.id = opts['id'] # compatibility with five-bells-connector? 
		self.auth = opts['auth']
		self.store = opts['store']
		self.timers = dict() 

		self.transfer_log = Transfer_Log(opts['store'])

		self.connected = False 
		self.connection_config = opts['auth']
		self.connection = Connection(self.connection_config)
		on_receive = lambda obj: self._receive(obj).catch(self._handle)
		self.connection.on('receive', on_receive)

		self.balance = Balance({
				'store': opts['store'],
				'limit': opts['auth']['limit'],
				'balance': opts['auth']['balance']
			})

	@self.balance.on('_balanceChanged')
	def on_balance_change(self, balance):
		self._log('balance changed to ' + balance)
		self.emit('_balanceChanged')
		self._send_balance()

	@self.balance.on('settlement')
	def on_settlement(self, balance):
		self._log('you should settle your balance of ' + balance)
		self.emit('settlement', balance)
		self._send_settle()

	def get_account(self):
		return self.augh['account']

	def connect(self):
		self.connection.connect()

		def fulfill_connect(resolve, reject):
			def noob_connect():
				self.emit('connect')
				self.connected = True 
				resolve(None)
			self.connection.on('connect')

		return Promise(fulfill_connect)	

	def disconnect(self):

		def fulfill_disconnect():
			self.emit('disconnect')
			self.connected = False 
			return Promise.resolve(None)

		return self.connection.disconnect.then(success=fulfill_disconnect)

	def is_connected(self):
		returen self.connected 

	def get_connectors(self):
		# Currently, only connections between two plugins are supported 
		# Thus, the list is empty 
		return Promise.resolve([])

	def send(self, outgoing_transfer):
		self._log("sending out a Transfer with tid: {}"
			.format(outgoing_transfer['id']))

		def send_then():
			self.connection.send({
					'type': 'transfer',
					'transfer': outgoing_transfer
				})

		return self.transfer_log.store_outgoing(outgoing_transfer)
			.then(send_then)
				.catch(self._handle)

	def get_info(self):
		# Using placeholder values in promise resolution
		# TO-DO: What should these values be
		return Promise.resolve({
				'precision': '15',
				'scale': '15',
				'currencyCode': 'GBP',
				'currencySymbol': '$'
			})

	def fulfill_condition(self, transfer_id, fulfillment_buffer):
		fulfillment = str(fulfillment_buffer)
		transfer = None 
		self._log('fulfilling: ' + fulfillment)

		def fulfill_condition_then(stored_transfer):
			transfer = stored_transfer
			return self._fulfill_condition_local(transfer, fulfillment)

		return self.transfer_log.get_id(transfer_id)
			.then(fulfill_condition_then)
				.catch(self._handle)

	def _validate(self, fulfillment, condition):
		try:
			return cryptoconditions.validate_fulfillment(fulfillment, condition)
		except Exception:
			return False 

	def _fulfill_condition_local(self, transfer, fulfillment):
		if not transfer:
			raise Exception('got transfer ID for nonexistent transfer')
		elif not transfer['executionCondition']:
			raise Exception('got transfer ID for OTP transfer')

		def _fulfill_condition_local_then(fulfilled):
			if fulfilled:
				raise Exception('this transfer has already been fulfilled')
			else:
				return Promise.resolve(None)

		def _fulfill_transfer_then():
			execute = transfer['executionCondition']
			cancel = transfer['cancellationCondition']

			time = str(datetime.now())
			expires_at = str(datetime(transfer['expiresAt']))
			timed_out = time > expires_at
			
			if self._validate(fulfillment, execute) and not timed_out:
				return self._execute_transfer(transfer, fulfillment)	
			elif cancel and self._validate(fulfillment, cancel):
				return self._cancel_transfer(transfer, fulfillment)
			elif timed_out:
				return self._timeout_transfer(transfer)
			else:
				raise Exception('Invalid fulfillment')

		return self.transfer_log.is_fulfilled(transfer)
			.then(_fulfill_condition_local_then)
				.then(_fulfill_transfer_then)
					.catch(self._handle)

	def _execute_transfer(self, transfer, fulfillment):
		fulfillment_buffer = Buffer(fulfillment)
		self.emit('fulfill_execution_condition', transfer, fulfillment_buffer)
		# Because there is only one balance kept, 
		# money is not actually kept in escrow 
		# although it behaves as though it were 
		# So there is nothing to do for the execution condition 

		def _execute_transfer_then(type):
			if type == self.transfer_log.outgoing:
				return self.balance.add(transfer['amount'])
			elif type == self.transfer_log.incoming:
				return self.balance.sub(transfer['amount'])
			else:
				raise Exception("nonexistent transfer type")

		return self.transfer_log.get_type(transfer)
			.then(_execute_transfer_then)
				.then(lambda: self.transfer_log.fulfill(transfer))
					.then(lambda: self.connection.send({
							'type': 'fulfill_execution_condition',
							'transfer': transfer,
							'fulfillment': fulfillment
						}))
						.catch(self._handle)

	def _cancel_transfer(self, transfer, fulfillment):
		fulfillment_buffer = Buffer(fulfillment)
		self.emit('fulfill_cancellation_condition', transfer, fulfillment_buffer)
		# A cancellation on an outgoing transfer means nothing 
		# because balances aren't affected until it executes 

		def _cancel_transfer_then(type):
			if type == self.transfer_log.incoming:
				return self.balance.add(transfer['amount'])

		return self.transfer_log.get_type(transfer)
			.then(_cancel_transfer_then)
				.then(lambda: self.transfer_log.fulfill(transfer))
					.then(lambda: self.connection.send({
							'type': 'fulfill_cancellation_condition',
							'transfer': transfer,
							'fulfillment': fulfillment
						}))

	def _timeout_transfer(self, transfer):
		self.emit('reject', transfer, 'timed out')
		transaction_type = None 

		def _timeout_transfer_then(type):
			transaction_type = type 
			if type == self.transfer_log.incoming:
				return self.balance.add(transfer['amount'])

		def _fulfill_transfer_then():
			# potential problem here: figure out how to get transaction_type
			# into the scope of this callback 
			if transaction_type == self.transfer_log.incoming:
				return self.connection.send({
						'type': 'reject',
						'transfer': transfer,
						'message': 'timed out'
					})
			else:
				return Promise.resolve(None)

		return self.transfer_log.get_type(transfer)
			.then(_timeout_transfer_then)
				.then(lambda: self.transfer_log.fulfill(transfer))
					.then(_fulfill_transfer_then)

	def get_balance():
		return self.balance.get()

	def reply_to_transfer(self, transfer_id, reply_message):
		return self.transfer_log.get_id(transfer_id)
			.then(lambda stored_transfer: self.connection.send({
					'type': 'reply',
					'transfer': stored_transfer,
					'message': reply_message
				}))

	def _receive(self, obj):
		'''
			Cases: 

			* obj.type == transfer
			* obj.type == acknowledge 
			* obj.type == reject 
			* obj.type == reply
			* obj.type == fulfillment
			* obj.type == balance 
			* obj.type == info 
		'''

		if obj['type'] == 'transfer':
			self._log('received a Transfer with tid: ' + obj['transfer']['id'])
			self.emit('receive', obj['transfer'])
			return self._handle_transfer(obj['transfer'])
		elif obj['type'] == 'acknowledge':
			self._log('received an ACK on tid: ' + obj['transfer']['id'])
			self.emit('accept', obj['transfer'], Buffer(obj['message']))
			return self._handle_acknowledge(obj['transfer'])
		elif obj['type'] == 'reject':
			# implement
		elif obj['type'] == 'reply':
			# implement 
		elif obj['type'] == 'fulfillment':
			# implement 
		elif obj['type'] == 'balance':
			# implement 
		elif obj['type'] == 'info':
			# implement 
		else:
			self._handle(Exception('Invalid message received'))

	def _handle_reject(self, transfer):

		def _handle_reject_then(exists):
			if exists:
				self._complete_transfer(transfer)
			else:
				self.emit('_falseReject', transfer) # debugging event 

		return self.transfer_log.exists(transfer)
			.then(_handle_reject_then)

	def _send_balance(self):

		def _send_balance_then(balance):
			self._log('sending balance: ' + balance)
			return self.connection.send({
					'type': 'balance',
					'balance': balance 
				})

		return selt.balance.get()
			.then(_send_balance_then)

	def _send_settle(self):
	
		def _send_settle_then(balance):
			self._log('sending settlement notification: ' + balance)
			return self.connection.send({
					'type': 'settlement',
					'balance': balance
				})

		return self.balance.get()
			.then(_send_settle_then)	

	def _send_info(self):
		return self.get_info()
			.then(lambda info: self.connection.send({
					'type': 'info',
					'info': info
				}))

	def _handle_transfer(self, transfer):

		def _handle_transfer_then(stored_transfer):
			if stored_transfer:
				self.emit('_repeateTransfer', transfer)
				return self._reject_transfer(transfer, 'repeat transfer id')
					.then(lambda: raise Exception('repeat transfer id'))
			else:
				return Promise.resolve(None)

		def is_valid_incoming_then(valid):

			def is_valid_then():
				self._handle_timer(transfer)
				self._accept_transfer(transfer)

			if valid:
				return self.balance.sub(transfer['amount'])
					.then(is_valid_then)
			else:
				return self._reject_transfer(transfer, 'invalid transfer amount')

		return self.transfer_log.get(transfer)
			.then(_handle_transfer_then)
				.then(lambda: self.transfer_log.store_incoming(transfer))
					.then(lambda: self.balance.is_valid_incoming(transfer.amount))
						.then(is_valid_incoming_then)
							.catch(self._handle)

	def _handle_acknowledge(self, transfer):

		



