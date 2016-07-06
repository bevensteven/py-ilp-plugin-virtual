from model.connection import Connection 

configuration = {
	'account': 'bevensteven',
	'host': '<mqtt server>',
	'token': '<channel name in mqtt server>',
}

c = Connection(configuration)