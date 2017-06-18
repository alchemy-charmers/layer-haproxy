from charmhelpers.core import hookenv, host

from collections import defaultdict
from pyhaproxy.parse import Parser
from pyhaproxy.render import Render
import pyhaproxy.config as Config

from collections import OrderedDict

class ConfigBlock(OrderedDict):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self['binds'] = []
        self['users'] = []
        self['groups'] = []
        self['options'] = []
        self['configs'] = []
        self['acls'] = []
        self['usebackends'] = []
        self['servers'] = []

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

        # Get the frontend, create if not present on this port
        frontend = None
        for fe in self.proxy_config.frontends:
            if fe.port == config['external_port']:
                frontend = fe
                break
        if not frontend:
            hookenv.log("Creating frontend for port {}".format(config['external_port']),"INFO")
            config_block = ConfigBlock()
            config_block['binds'] = [Config.Bind('0.0.0.0', config['external_port'], None)]
            frontend = Config.Frontend('relation-{}'.format(config['external_port']), None, config['external_port'], config_block)
            self.proxy_config.frontends.append(frontend)

        remote_unit = hookenv.remote_unit().replace('/','-')

        # Add ACL's to the frontend
        acl = Config.Acl(name=remote_unit,value='path_beg {}'.format(config['urlbase']))
        frontend.acls().append(acl)
        acl = Config.Acl(name=remote_unit,value='hdr_beg(host) -i {}'.format(config['subdomain']))
        frontend.acls().append(acl)

        # TODO: Allow a 'service' or 'group_id' so multiple units can share a backend for HA not just reverse proxy
        # Add use_backend section to the frontend
        use_backend = Config.UseBackend(backend_name=remote_unit,
                                        operator='if',
                                        backend_condition=remote_unit,
                                        is_default=False)
        frontend.usebackends().append(use_backend)

        # Get the backend, create if not present
        backend = None
        for be in self.proxy_config.backends:
            if be.name == remote_unit:
                backend = be
        if not backend:
            hookenv.log("Creating backend for {}".format(remote_unit))
            config_block = ConfigBlock()
            backend = Config.Backend(name=remote_unit,config_block=config_block)
            self.proxy_config.backends.append(backend)

        # Add server to the backend
        server = Config.Server(name=remote_unit,host=config['internal_host'], port=config['internal_port'], attributes='')
        backend.servers().append(server) 

        # Render new cfg file
        Render(self.proxy_config).dumps_to('/etc/haproxy/haproxy.cfg') 
