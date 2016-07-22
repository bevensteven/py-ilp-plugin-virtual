# py-ilp-plugin-virtual

> ILP virtual ledger plugin for directly transacting connectors 

> Pythonic offshoot of ```js-ilp-plugin-virtual```

## Installation 

Please use Python 3.5

```sh
git clone https://github.com/bevensteven/py-ilp-plugin-virtual
cd py-ilp-plugin-virtual
python3 setup.py install 
```

## Usage 
Nerd Plugin - communicates with Noob Plugin and Interledger connectors
```sh
nerd_opt = nerd_opt = {
				'auth': {
					'account': 'name',
					'token': 'token for mqtt subscription',
					'host': 'mqtt broker',
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
	noob_opt = {
				'auth': {
					'account': 'name',
					'token': 'token for mqtt subscription',
					'host': 'mqtt broker'
				}
			}

# initialize noob with noob_opt
noob = Noob_Plugin_Virtual(noob_opt)

# connect to MQTT broker
noob.connect()
```