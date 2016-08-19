from pymitter import EventEmitter 
from promise import Promise
from decimal import Decimal

class Balance(EventEmitter):

	def __init__(self, opts):
		super().__init__()

		self._store = opts['store']
		self._limit = self._convert(opts['limit'])
		self._balance = opts['balance']
		self._max = self._convert(opts['max'])
		self._warn_max = self._convert(opts['warnMax'])
		self._warn_limit = self._convert(opts['warn_limit'])
		self._initialized = False 
		self._field = 'account'

	def _initialize(self):
		self._initialized = True 

		def initialize_then(balance):
			# check if balance is undefined
			if not balance:
				return self._store.put(self._field, self._balance)

		return self._store.get(self._field).then(initialize_then)

	def _get_number(self):
		return self.get().then(lambda balance: Decimal(balance))

	def _convert(self, amount):
		try: 
			return Decimal(amount)
		except Exception:
			return Decimal('NaN')

	def get(self):
		promise = Promise.resolve(None)
		if not self._initialized:
			promise = self._initialize()
		return promise.then(lambda x: self._store.get(self._field))

	def add(self, amount_string):
		amount = self._convert(amount_string)

		def add_then(balance):
			new_balance = str(balance + amount)
			self.emit('_balanceChanged', new_balance)
			self._store.put(self._field, new_balance)
			return Promise.resolve(new_balance)

		return self._get_number().then(add_then)

	def sub(self, amount):
		return self.add(str(-self._convert(amount)))

	def is_valid_outgoing(self, amount_string):
		amount = self._convert(amount_string)

		def is_valid_outgoing_then(balance):
			in_max = balance.add(amount) <= self._max 
			in_warn = balance.add(amount) <= self._warn_max
			positive = amount >= self._convert('0')
			if not in_warn:
				self.emit('over', balance)
			return Promise.resolve(in_max and positive)

		return self._get_number() \
				.then(is_valid_outgoing_then)

	def is_valid_incoming(self, amount_string):
		amount = self._convert(amount_string)

		def is_valid_incoming_then(balance):
			in_limit = balance.sub(amount) >= -self._limit
			in_warn = balance.sub(amount) >= -self._warn_limit
			positive = amount >= self._convert('0')
			if not in_warn:
				self.emit('under', balance)
			return Promise.resolve(in_limit and positive)

		return self._get_number() \
				.then(is_valid_incoming_then)