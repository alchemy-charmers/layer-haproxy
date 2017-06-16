from charmhelpers.core import hookenv, host

from pyhaproxy.parse import Parser
from pyhaproxy.render import Render
import pyhaproxy.config as Config

class ProxyHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.ppa = "ppa:vbernat/haproxy-{}".format(self.charm_config['version']) 
        self.proxy_config_file = "/etc/haproxy/haproxy.cfg"
        self._proxy_config = None

    @property
    def proxy_config(self):
        if not self._proxy_config:
            self._proxy_config = Parser(self.proxy_config_file).build_configuration()
        return self._proxy_config 

    def process_config(self,config):
        print(config)

        frontend = None
        for fe in self.proxy_config.frontends:
            if fe.port == config['external_port']:
                frontend = fe
                break
        if not frontend:
            config_block = {'binds':[Config.Bind('0.0.0.0',config['external_port'],None)]}
            frontend = Config.Frontend('relation-{}'.format(config['external_port']),None,None,config_block)
            self.proxy_config.frontends.append(frontend)
            Render(self.proxy_config).dumps_to('/etc/haproxy/haproxy.tst') 
        raise Exception('spam','eggs')
