from plugin.nerd_plugin import Nerd_Plugin_Virtual
from plugin.noob_plugin import Noob_Plugin_Virtual
from util.utils import Store

import sys 
import time 

import pprint 
pp = pprint.PrettyPrinter(indent=4)
pp = pp.pprint

def tracer(frame, event, arg, indent=[0]):
	if event == "call":
		indent[0] += 2
		print("-" * indent[0] + "> call function", frame.f_code.co_name)
	elif event == "return":
		print("<" + "-" * indent[0], "exit function", frame.f_code.co_name)
		indent[0] -= 2
	return tracer 


if __name__ == "__main__":	
	if len(sys.argv) > 1 and sys.argv[1] == "trace":
		sys.setprofile(tracer)

	storage = Store()
	nerd_opt = {
				'auth': {
					'account': 'Eli',
					'token': 'test_mqtt',
					'host': 'broker.hivemq.com',
					'limit': '1000',
					'balance': 1000,
					'secret': 'not used yet'
				},
				'store': {
					'get': storage.get,
					'put': storage.put,
					'del': storage.delete
				}
			}

	noob_opt = {
				'auth': {
					'account': 'Steven',
					'token': 'test_mqtt',
					'host': 'broker.hivemq.com'
				}
			}

	# create nerd and noob plugins
	nerd = Nerd_Plugin_Virtual(nerd_opt)
	noob = Noob_Plugin_Virtual(noob_opt)

	# connect nerd and noob to MQTT broker for comms 
	nerd.connect()
	noob.connect()

	# send a transfer from nerd to noob
	sample_transfer = {   'account': 'https://ledger.example/accounts/connector',
	                    'amount': '10',
	                    'cancellationCondition': 'cc:0:3:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU:0',
	                    'executionCondition': 'cc:0:3:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU:0',
	                    'expiresAt': '2016-07-22T00:25:00.000Z',
	                    'id': 'https//ledger.example/transfers/123',
	                    'message': 'hello world'
				}

	time.sleep(1)
	noob.send(sample_transfer)