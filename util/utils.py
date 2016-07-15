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
	def __init__(self):
		super().__init__()
