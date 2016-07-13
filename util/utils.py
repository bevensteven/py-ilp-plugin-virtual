import sys 

def implement():
	print("Function needs to be implemented")
	sys.exit(1)

class PluginException(Exception):
	def __init__(self):
		super().__init__()
	