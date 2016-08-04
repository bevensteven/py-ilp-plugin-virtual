# py-ilp-plugin-virtual

> ILP virtual ledger plugin for directly transacting connectors 

> Pythonic spin-off of ```js-ilp-plugin-virtual```

> Implements Interledger plugin interface https://interledger.org/rfcs/0004-ledger-plugin-interface/

## Installation 

Please use Python 3.5

```sh
git clone https://github.com/bevensteven/py-ilp-plugin-virtual
cd py-ilp-plugin-virtual
python3.5 setup.py install 
```

## Usage 
Nerd Plugin - communicates with Noob Plugin and Interledger connectors
```sh
from plugin.nerd_plugin import Nerd_Plugin_Virtual
from util.utils import Store 

# for the sake of example - read Interledger specs for more details
storage = Store()

nerd_opt = {
			'auth': {
				'account': 'Bob',
				'token': 'example',
				'host': 'broker.hivemq.com',
				'limit': '12345',
				'balance': 1000,
				'secret': 'not used yet'
			},
			'store': {
				'get': storage.get,
				'put': storage.put,
				'del': storage.delete
			}
		}

# initialize nerd with nerd_opt 
nerd = Nerd_Plugin_Virtual(nerd_opt)

# conenct to MQTT broker 
nerd.connect()
```

Noob Plugin - communicates with Nerd Plugin 
```sh
from plugin.noob_plugin import Noob_Plugin_Virtual

noob_opt = {
			'auth': {
				'account': 'Alice',
				'token': 'example',
				'host': 'broker.hivemq.com'
			}
		}

# initialize noob with noob_opt
noob = Noob_Plugin_Virtual(noob_opt)

# connect to MQTT broker
noob.connect()
```

Sending transfers
```sh
sample_transfer = { 
					'account': 'https://ledger.example/accounts/connector',
                    'amount': '10',
                    'cancellationCondition': 'cc:0:3:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU:0',
                    'executionCondition': 'cc:0:3:47DEQpj8HBSa-_TImW-5JCeuQeRkm5NMpJWZG3hSuFU:0',
                    'expiresAt': '2016-07-22T00:25:00.000Z',
                    'id': 'sample_transfer',
                    'message': 'hello world',
                    'data': { 
                    		 "ilp_header": { 
	                    		 			"account": "https://blue.ilpdemo.org/ledger/accounts/bob",
			                              	"ledger": "https://blue.ilpdemo.org/ledger",
			                              	"amount": "10",
			                              	"data": { 
			                              			"request_id": "3c5286eb-cc8a-4741-8581-714f3ab1370e",
	                            					"expires_at": "2016-07-22T13:03:51.578Z"
                   						}
                    	 		}
              			}	
				}

# send a transfer from noob to nerd
noob.send(sample_transfer)
```