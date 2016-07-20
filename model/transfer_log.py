import json as JSON

class Transfer_Log(object):

	def __init__(self, store):
		# self._get = store['get']
		# self._put = store['put']
		# self._del = store['del']
		# For trial purposes
		self._get = store.get("get", lambda: None)
		self._put = store.get("put", lambda: None)
		self._del = store.get("del", lambda: None)

		self.incoming = 'i'
		self.outgoing = 'o'

	def get_id(self, transfer_id):

		def get_id_then(json):
			if json:
				return Promise.resolve(JSON.loads(json)['transfer'])
			else:
				return Promise.resolve(None)

		return self._get('t' + transfer_id).then(get_id_then)

	def get(self, transfer):
		return self.get_id(transfer['id'])

	def get_type_id(self, transfer_id):

		def get_type_id_then(json):
			if json:
				return Promise.resolve(JSON.loads(json)['type'])
			else:
				return Promise.resolve(None)

		return self._get('t' + transfer_id).then(get_type_id_then)

	def get_type(self, transfer):
		return self.get_type_id(transfer['id'])

	def store(self, transfer, type):
		return self._put('t' + transfer['id'],
			JSON.dumps({
				'transfer': transfer,
				'type': type
			}))

	def store_outgoing(self, transfer):
		return self.store(transfer, self.outgoing)

	def store_incoming(self, transfer):
		return self.store(transfer, self.incoming)

	def exists(self, transfer):
		return self.get(transfer) \
			.then(lambda stored_transfer: Promise.resolve(stored_transfer != None))

	def delete(self, transfer):
		return self._del('t' + transfer['id'])

	def complete(self, transfer):
		return self._put('c' + transfer['id'], 'complete')

	def is_complete(self, transfer):
		return self._get('c' + transfer['id']) \
			.then(lambda data: Promise.resolve(data != None))

	def fulfill(self, transfer):
		# TO-DO: more effective way of implementing this 
		return self._put('f' + transfer['id'], 'complete')

	def is_fulfilled(self, transfer):
		return self._get('f' + transfer['id']) \
			.then(lambda data: Promise.resolve(data != None))
