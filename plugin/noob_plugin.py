from pymitter import EventEmitter
from util.log import Logger 
from model.connection import Connection

log = Logger('noob_plugin')

class Noob_Plugin_Virtual(EventEmitter):

	def __init__(self, opts):
		super().__init__()

		self._handle = lambda err: self.emit('exception', err)

		# self.id = opts.id 	# Compatibility with five bells connector; is this necessary? 

		self.auth = opts['auth']
		self.connected = False 
		self.connection_config = opts['auth']
		self.connection = Connection(self.connection_config)
		
		self.connection.on('receive', lambda obj: self._receive(obj).catch(self._handle))

		self._expects = dict()
		self._seen = dict()
		self._fulfilled = dict()

	def _log(self, msg):
		log.log(self.auth.account + ': ' + msg)

	def _expect_response(self, tid):
		self._expects[tid] = True 

	def _expected_response(self, tid):
		return self._expects[tid]

	def _receive_response(self, tid):
		self._expects[tid] = False 

	def _see_transfer(self, tid):
		self._seen[tid] = True 

	def _seen_transfer(self, tid):
		return self._seen[tid]

	def _fulfill_transfer(self, id):
		self._fulfilled[tid] = True 

	def _fulfilled_transfer(self, tid):
		return self._fulfilled[tid]

	def _receive(self, obj):
		if type(obj) == Transfer and 