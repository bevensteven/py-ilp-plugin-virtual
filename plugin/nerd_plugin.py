from pymitter import EventEmitter 
from promise import Promise
from datetime import datetime
from threading import Timer 

import dateutil.parser
import pytz

from util.log import Logger 
from util.utils import implement, PluginException
from model.connection import Connection
from model.transfer import equals
from model.transfer_log import Transfer_Log
from model.balance import Balance

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

		# DEBUGGING 
		self.DEBUG = None

		self._handle = lambda err: self.emit('exception', err)
		on_exception = lambda err: self._log('Exception {}'.format(err))
		self.on('exception', on_exception)

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
		self.balance.on('_balanceChanged', self.on_balance_change)
		self.balance.on('_settlement', self.on_settlement)

		self._log("Initialized Nerd Plugin Virtual: {}".format(self.auth))

	def on_balance_change(self, balance):
		self._log('balance changed to ' + balance)
		self.emit('_balanceChanged')
		self._send_balance()

	def on_settlement(self, balance):
		self._log('you should settle your balance of ' + balance)
		self.emit('settlement', balance)
		self._send_settle()

	def get_account(self):
		return self.auth['account']

	def connect(self):
		self.connection.connect()

		def fulfill_connect(resolve, reject):
			def noob_connect():
				self.connected = True 
				self.emit('connect')
				resolve(None)
			self.connection.on('connect')

		return Promise(fulfill_connect)	

	def disconnect(self):

		def fulfill_disconnect():
			self.connected = False 
			self.emit('disconnect')
			return Promise.resolve(None)

		return self.connection.disconnect.then(success=fulfill_disconnect)

	def is_connected(self):
		return self.connected 

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

		return self.transfer_log.store_outgoing(outgoing_transfer) \
			.then(send_then()) \
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

		return self.transfer_log.get_id(transfer_id) \
			.then(fulfill_condition_then) \
				.catch(self._handle)

	def _validate(self, fulfillment, condition):
		try:
			parsed_fulfillment = cc.Fulfillment.from_uri(fulfillment)
			is_valid = condition == parsed_fulfillment.condition_uri
			return is_valid
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

			# FIX DATETIME ISSUES HERE 
			time = str(datetime.isoformat(datetime.now()))
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

		return self.transfer_log.is_fulfilled(transfer) \
			.then(_fulfill_condition_local_then) \
				.then(_fulfill_transfer_then) \
					.catch(self._handle)

	def _execute_transfer(self, transfer, fulfillment):
		fulfillment_buffer = fulfillment.encode('utf-8')
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

		return self.transfer_log.get_type(transfer) \
			.then(_execute_transfer_then) \
				.then(lambda _: self.transfer_log.fulfill(transfer)) \
					.then(lambda _: self.connection.send({
							'type': 'fulfill_execution_condition',
							'transfer': transfer,
							'fulfillment': fulfillment
						})) \
						.catch(self._handle)

	def _cancel_transfer(self, transfer, fulfillment):
		fulfillment_buffer = fulfillment.encode('utf-8')
		self.emit('fulfill_cancellation_condition', transfer, fulfillment_buffer)
		# A cancellation on an outgoing transfer means nothing 
		# because balances aren't affected until it executes 

		def _cancel_transfer_then(type):
			if type == self.transfer_log.incoming:
				return self.balance.add(transfer['amount'])

		return self.transfer_log.get_type(transfer) \
			.then(_cancel_transfer_then) \
				.then(lambda _: self.transfer_log.fulfill(transfer)) \
					.then(lambda _: self.connection.send({
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

		return self.transfer_log.get_type(transfer) \
			.then(_timeout_transfer_then) \
				.then(lambda: self.transfer_log.fulfill(transfer)) \
					.then(_fulfill_transfer_then)

	def get_balance(self):
		return self.balance.get()

	def reply_to_transfer(self, transfer_id, reply_message):
		return self.transfer_log.get_id(transfer_id) \
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
			self.emit('accept', obj['transfer'], obj['message'].encode('utf-8'))
			return self._handle_acknowledge(obj['transfer'])

		elif obj['type'] == 'reject':
			self._log('received a reject on tid: ' + obj['transfer']['id'])
			self.emit('reject', obj['transfer'], obj['message'].encode('utf-8'))
			return self._handle_reject(obj['transfer'])

		elif obj['type'] == 'reply':
			self._log('received a reply on tid: ' + obj['transfer']['id'])
			def _receive_reply_then(transfer):
				self.emit('reply', transfer, obj['message'].encode('utf-8'))
				return Promise.resolve(None)
			return self.transfer_log.get_id(obj['transfer']['id']) \
				.then(_receive_reply_then)

		elif obj['type'] == 'fulfillment':
			self._log('received a fulfillment for tid: ' + obj['transfer']['id'])
			def _receive_fulfillment_then(transfer):
				self.emit('fulfillment', transfer, obj['fulfillment'].encode('utf-8'))
				return self._fulfill_condition_local(transfer, obj['fulfillment'])
			return self.transfer_log.get_id(obj['transfer']['id']) \
				.then(_receive_fulfillment_then)

		elif obj['type'] == 'balance':
			self._log('received a query for the balance...')
			return self._send_balance()

		elif obj['type'] == 'info':
			return self._send_info()

		else:
			self._handle(Exception('Invalid message received'))

	def _handle_reject(self, transfer):

		def _handle_reject_then(exists):
			if exists:
				print("_handle_reject_then exists")
				self._complete_transfer(transfer)
			else:
				self.emit('_falseReject', transfer) 
				# used for debugging purposes

		return self.transfer_log.exists(transfer) \
			.then(_handle_reject_then)

	def _send_balance(self):

		def _send_balance_then(balance):
			self._log('sending balance: ' + balance)
			return self.connection.send({
					'type': 'balance',
					'balance': balance 
				})

		return self.balance.get() \
			.then(_send_balance_then)

	def _send_settle(self):
	
		def _send_settle_then(balance):
			self._log('sending settlement notification: ' + balance)
			return self.connection.send({
					'type': 'settlement',
					'balance': balance
				})

		return self.balance.get() \
			.then(_send_settle_then)	

	def _send_info(self):
		return self.get_info() \
			.then(lambda info: self.connection.send({
					'type': 'info',
					'info': info
				}))

	def _handle_transfer(self, transfer):

		def _handle_transfer_then(stored_transfer):
			def _repeat_transfer():
				raise Exception('repeat transfer id')
			if stored_transfer:
				self.emit('_repeateTransfer', transfer)
				return self._reject_transfer(transfer, 'repeat transfer id') \
					.then(_repeat_transfer)
			else:
				return Promise.resolve(None)

		def is_valid_incoming_then(valid):
			def is_valid_then(_):
				self._handle_timer(transfer)
				self._accept_transfer(transfer)
			if valid:
				return self.balance.sub(transfer['amount']) \
					.then(is_valid_then)
			else:
				return self._reject_transfer(transfer, 'invalid transfer amount')

		return self.transfer_log.get(transfer) \
			.then(_handle_transfer_then) \
				.then(lambda _: self.transfer_log.store_incoming(transfer)) \
					.then(lambda _: self.balance.is_valid_incoming(transfer['amount'])) \
						.then(is_valid_incoming_then) \
							.catch(self._handle)

	def _handle_acknowledge(self, transfer):

		def _handle_acknowledge_then(stored_transfer):
			if equals(stored_transfer, transfer):
				return self.transfer_log.is_complete(transfer)
			else:
				self._false_acknowledge(transfer)

		def is_complete_transfer_then(is_complete):
			self.DEBUG = transfer
			if is_complete:
				self._false_acknowledge(transfer)
				# don't add to balance yet if it's UTP/ATP transfer 
			elif not transfer['executionCondition']:
				self.balance.add(transfer['amount'])

		def acknowledge_transfer_then(_):
			self._handle_timer(transfer)
			self._complete_transfer(transfer)

		return self.transfer_log.get(transfer) \
			.then(_handle_acknowledge_then) \
				.then(is_complete_transfer_then) \
					.then(acknowledge_transfer_then)

	def _false_acknowledge(self, transfer):
		self.emit('_falseAcknowledge', transfer)
		raise Exception("Received false acknowledge for tid: " + transfer['id'])

	def _handle_timer(self, transfer):
		if transfer['expiresAt']:
			now = datetime.now(pytz.utc)
			expiry = dateutil.parser.parse(transfer['expiresAt'])

			def timer():
				def timer_then(is_fulfilled):
					if not is_fulfilled:
						self._timeout_transfer(transfer)
						self._log('automatic timeout on tid: ' + transfer['id'])
				self.transfer_log.is_fulfilled(transfer) \
					.then(timer_then) \
						.catch(self._handle)

			self.timers[transfer['id']] = Timer(5, timer)
			self.timers[transfer['id']].start()
			# for debugging purposes 
			self.emit('_timing', transfer['id'])

	def _accept_transfer(self, transfer):
		self._log('sending out an ACK for tid: ' + transfer['id'])	
		return self.connection.send({
				'type': 'acknowledge',
				'transfer': transfer,
				'message': 'transfer accepted'
			})

	def _reject_transfer(self, transfer, reason):
		self._log('sending out a reject for tid: ' + transfer['id'])
		self._complete_transfer(transfer)
		return self.connection.send({
				'type': 'reject',
				'transfer': transfer,
				'message': reason
			})

	def _complete_transfer(self, transfer):
		promises = list(self.transfer_log.complete(transfer))
		if not transfer['executionCondition']:
			promises.append(self.transfer_log.fulfill(transfer))
		return Promise.all(promises)

	def _log(self, msg):
		log.log("{}: {}".format(self.auth['account'], msg))

if __name__ == "__main__":
	import sys 
	if len(sys.argv) > 1 and sys.argv[1] == 'test':
		test_opt = {
			'auth': {
				'account': 'Eli',
				'token': 'test_mqtt',
				'host': 'broker.hivemq.com',
				'limit': '1000',
				'balance': 1000,
				'secret': 'not used yet'
			},
			'store': {
				'test': None
			}
		}
		# TO-DO: Make a test transfer
		test_plugin = Nerd_Plugin_Virtual(test_opt)
		test_plugin.connect()
