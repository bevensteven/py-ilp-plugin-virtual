from promise import Promise
import json
import sys 

def implement():
	print("Function needs to be implemented")
	sys.exit(1)

def is_json(obj):
	try:
		_ = json.loads(obj)
	except ValueError:
		return False 
	return True

class PluginException(Exception):
	def __init__(self, msg):
		super().__init__(msg)

class Store(object):
	def __init__(self):
		self.storage = dict()

	def put(self, key, value):
		self.storage[key] = value
		promise = Promise()
		promise.fulfill(None)
		return Promise.resolve(None)

	def get(self, key):
		obj = self.storage.get(key, None)
		promise = Promise()
		promise.fulfill(obj)
		return promise

	def delete(self, key):
		try:
			del self.storage[key]
			return Promise.fulfill(None)
		except KeyError:
			print("Key does not exist in storage")	