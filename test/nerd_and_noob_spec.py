import unittest 
import binascii
import os
from promise import Promise

from plugin.nerd_plugin import Nerd_Plugin_Virtual
from plugin.noob_plugin import Noob_Plugin_Virtual
from plugin.plugin import Plugin_Virtual
from util.utils import Store 

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

		self.assertIsInstance(self.nerd, Nerd_Plugin_Virtual)
		self.assertIsInstance(self.noob, Noob_Plugin_Virtual)

	def tearDown(self):
		print("")
		print(NEXT)
		del self.nerd
		del self.noob

	def test_get_account(self):
		self.assertEqual(self.nerd.get_account(), 'nerd')

	def test_connection(self):
		NEXT = Promise.all([
				self.noob.connect(),
				self.nerd.connect()
			]).then(lambda x: done())

	def test_connection_log(self):
		NEXT = self.nerd.connection._handle('fake error!')

	# def test_initial_balance(self):
	# 	def test_initial_balance(balance):
	# 		self.assertEqual(balance, 0)
	# 	NEXT = Promise.then(lambda res: nerd.get_balance()) \
	# 			.then(test_initial_balance_then) \
	# 				.catch(handle)

	def test_get_info(self):
		def test_get_info_chain():
			noob.get_connectors()
			nerd.get_connectors()
		NEXT = NEXT.then(test_get_info_chain)

	def test_check_connection(self):
		def check_connection():
			self.assertTrue(noob.is_connected())
			self.assertTrue(nerd.is_connected())
		NEXT = NEXT.then(check_connection)

	def test_valid_trasnfer(self):
		def valid_transfer():
			return noob.send({
					'id': 'first',
					'account': 'x',
					'amount': '10'
				})
		def valid_transfer_then():
			def resolver(resolve, reject):
				def on_receive(transfer, message):
					assert(transfer['id'] == 'first')
				self.noob.once('receive', on_receive)
			return Promise(resolver)
		NEXT = NEXT.then(valid_transfer) \
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