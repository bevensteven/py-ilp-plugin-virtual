from pymitter import EventEmitter 
from util.log import Logger 
from util.utils import implement, PluginException
from model.connection import Connection
from model.transfer import Transfer 

from promise import Promise

log = Logger('nerd_plugin')