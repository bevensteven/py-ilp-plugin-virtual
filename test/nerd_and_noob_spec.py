import unittest 
import binascii
import os
import time
from promise import Promise

from plugin.nerd_plugin import Nerd_Plugin_Virtual
from plugin.noob_plugin import Noob_Plugin_Virtual
from plugin.plugin import Plugin_Virtual
from util.log import Logger 
from util.utils import Store 


log = Logger("[ TEST ]")

def test(msg):
	log.log('>>> ' + msg + ' <<<')

def handle(msg):
	log.error(msg)

class TestNerd(unittest.TestCase):

	def setUp(self):
		print("-"*100)
		print("")
		token = binascii.hexlify(os.urandom(8)).decode('utf-8')
		nerd_opt = {
			'store': Store(), 
			'auth': {
				'host': 'mqatt://test.mosquitto.org',
				'token' : token,
				'limit': '1000',
				'balance': '0',
				'account': 'nerd',
				'secret': 'secret'
			}
		}
		self.nerd = Plugin_Virtual(nerd_opt)

		noob_opt = {
			'store': dict(),
			'auth': {
				'host': 'mqatt://test.mosquitto.org',
				'token': token,
				'account': 'noob'
			}
		}
		self.noob = Plugin_Virtual(noob_opt)

		self.noob.connect()
		self.nerd.connect()

	def test_plugins(self):
		self.assertIsInstance(self.nerd, Nerd_Plugin_Virtual)
		self.assertIsInstance(self.noob, Noob_Plugin_Virtual)

	def tearDown(self):
		print("")
		print(NEXT)
		del self.nerd
		del self.noob

	def test_get_account(self):
		test("running get_account for compatibility check")
		self.assertEqual(self.nerd.get_account(), 'nerd')
		self.assertEqual(self.noob.get_account(), 'noob')

	def test_connection(self):

		test("should connect to the mosquitto server")
		NEXT = Promise.all([
				self.noob.connect(),
				self.nerd.connect()
			])

		test("check connectivity")
		self.assertTrue(self.noob.is_connected())
		self.assertTrue(self.nerd.is_connected())

		test("should be able to log errors in the connnection")
		self.nerd.connection._handle('fake error!')

	def test_initial_balance(self):
		def test_initial_balance_then(balance):
			self.assertEqual(balance, str(0))
		NEXT = Promise().resolve(None).then(lambda res: self.nerd.get_balance()) \
				.then(test_initial_balance_then) \
					.catch(handle)

	def test_get_info(self):
		test("calling get_connectors")
		self.noob.get_connectors()
		self.nerd.get_connectors()

	def test_valid_transfer(self):
		def valid_transfer():
			return self.noob.send({
					'id': 'first',
					'account': 'x',
					'amount': '10'
				})
		def valid_transfer_then():
			def resolver(resolve, reject):
				def on_receive(transfer, message):
					print("received")
					self.assertTrue(transfer['id'] == 'first')
				self.noob.once('receive', on_receive)
				resolve(None)
			return Promise(resolver)

		test("sending valid transfer from noob")
		valid_transfer() \
			.then(valid_transfer_then)

	# def test_correct_balance(self):
	# 	def assert_balance(balance):
	# 		assert(balance == '-10')
	# 	NEXT = NEXT.then(lambda: self.noob.get_balance()) \
	# 					.then(assert_balance)

	# def test_reject_transfer(self):
	# 	def reject_transfer():
	# 		return self.noob.send({
	# 				'id': 'second',
	# 				'account': 'x',
	# 				'amount': '1000'
	# 			})
	# 	def reject_transfer_then():
	# 		def resolver(resolve, reject):
	# 			def assert_second(transfer, message):
	# 				assert(transfer['id'] == 'second')
	# 			self.noob.once('reject', assert_second)
	# 	NEXT = NEXT.then(test_reject_transfer) \
	# 					.then(reject_transfer_then)




if __name__ == "__main__":
	global NEXT 
	NEXT = Promise() 
	unittest.main()