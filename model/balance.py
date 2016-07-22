from pymitter import EventEmitter 
from promise import Promise
from decimal import Decimal

class Balance(EventEmitter):

	def __init__(self, opts):
		super().__init__()

		self._store = opts['store']
		self._limit = self._convert(opts['limit'])
		self._balance = opts['balance']
		self._initialized = False 
		self._field = 'account'

	def _initialize(self):
		self._initialized = True 

		def initialize_then(balance):
			# check if balance is undefined
			if not balance:
				return self._store['put'](self._field, self._balance)

		return self._store['get'](self._field).then(initialize_then)

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
		return promise.then(lambda x: self._store['get'](self._field))

	def add(self, amount_string):
		amount = self._convert(amount_string)

		def add_then(balance):
			new_balance = str(balance + amount)
			self.emit('_balanceChanged', new_balance)
			self._store['put'](self._field, new_balance)
			return Promise.resolve(new_balance)

		return self._get_number().then(add_then)

	def sub(self, amount):
		return self.add(str(-self._convert(amount)))

	def is_valid_incoming(self, amount_string):
		amount = self._convert(amount_string)

		def is_valid_incoming_then(balance):
			is_within_limit = balance - amount >= -self._limit
			is_positive = amount >= Decimal('0')
			if not is_within_limit:
				self.emit("settlement", balance)
			return Promise.resolve(is_within_limit and is_positive)

		return self._get_number().then(is_valid_incoming_then)