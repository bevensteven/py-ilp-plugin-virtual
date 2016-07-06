import logging
from dotmap import DotMap
try:
	import coloredlogs
	color = True 
except ImportError:
	color = False 

def Logger(name):
	logger = logging.getLogger(name)
	logger.setLevel(logging.DEBUG)

	ch = logging.StreamHandler()
	ch.setLevel(logging.DEBUG)

	if color:
		formatter = coloredlogs.ColoredFormatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	else:
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

	ch.setFormatter(formatter)

	logger.addHandler(ch)

	log_functions = DotMap()
	log_functions.log = logger.debug 
	log_functions.error = logger.error 

	return log_functions