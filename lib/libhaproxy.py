from charmhelpers.core import hookenv, host

from pyhaproxy.parse import Parser
from pyhaproxy.render import Render
import pyhaproxy.config as config

class ProxyHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.ppa = "ppa:vbernat/haproxy-{}".format(self.charm_config['version']) 
        self.proxy_config_file = "/etc/haproxy/haproxy.cfg"
        # TODO: Maybe move this into a property so it's only loaded the first time it' used
        try:
            self.proxy_config = Parser(self.proxy_config_file).build_configuration()
        except:
            pass
