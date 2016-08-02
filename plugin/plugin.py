from plugin.nerd_plugin import Nerd_Plugin_Virtual
from plugin.noob_plugin import Noob_Plugin_Virtual

def Plugin_Virtual(opts):
	if 'auth' in opts and 'secret' in opts:
		return Nerd_Plugin_Virtual(opts)
	else:
		return Noob_Plugin_Virtual(opts)

