from charmhelpers.core import hookenv, host

from collections import defaultdict
from pyhaproxy.parse import Parser
from pyhaproxy.render import Render
import pyhaproxy.config as Config

from collections import OrderedDict

class ConfigBlock(OrderedDict):
    def __init__(self,*args,**kwargs):
        self['binds'] = []
        self['users'] = []
        self['groups'] = []
        self['options'] = []
        self['configs'] = []
        self['acls'] = []
        self['usebackends'] = []
        self['servers'] = []
        super().__init__(*args,**kwargs)

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
        remote_unit = hookenv.remote_unit().replace('/','-')
        backend_name = config['group_id'] or remote_unit

        # Remove any prior configuration as it might have changed
        self.clean_config(unit=remote_unit,save=False)

        # Get the frontend, create if not present
        frontend = self.get_frontend(config['external_port'])

        # Add ACL's to the frontend
        new_acls = False
        try:
            acl = Config.Acl(name=remote_unit, value='path_beg {}'.format(config['urlbase']))
            frontend.acls().append(acl)
            new_acls = True
        except KeyError:
            pass
        try:
            acl = Config.Acl(name=remote_unit, value='hdr_beg(host) -i {}'.format(config['subdomain']))
            frontend.acls().append(acl)
            new_acls = True
        except KeyError:
            pass
        if not new_acls:
            return({"cfg_good":False,"msg":"Must provide one or more of: (urlbase,subdomain)"})

        # Add use_backend section to the frontend
        use_backend = Config.UseBackend(backend_name=backend_name,
                                        operator='if',
                                        backend_condition=remote_unit,
                                        is_default=False)
        frontend.usebackends().append(use_backend)

        # Get the backend, create if not present
        backend = self.get_backend(backend_name)

        # Add server to the backend
        server = Config.Server(name=remote_unit, host=config['internal_host'], port=config['internal_port'], attributes=['cookie {}'.format(remote_unit)])
        backend.servers().append(server) 

        # Render new cfg file
        self.save_config()
        return({"cfg_good":True,"msg":"configuration applied"})

    def get_frontend(self,port=None):
        port = str(port)
        frontend = None
        for fe in self.proxy_config.frontends:
            if fe.port == port:
                config_block = ConfigBlock(**fe.config_block)
                fe.config_block = config_block
                frontend = fe
                break
        if not frontend:
            hookenv.log("Creating frontend for port {}".format(port),"INFO")
            config_block = ConfigBlock({'binds':[Config.Bind('0.0.0.0', port, None)]})
            frontend = Config.Frontend('relation-{}'.format(port), '0.0.0.0', port, config_block)
            self.proxy_config.frontends.append(frontend)
        return frontend

    def get_backend(self,name=None):
        backend = None
        for be in self.proxy_config.backends:
            if be.name == name:
                config_block = ConfigBlock(**be.config_block)
                be.config_block = config_block
                backend = be
        if not backend:
            hookenv.log("Creating backend {}".format(name))
            cookie_config = ('cookie SERVERID insert indirect nocache','')
            config_block = ConfigBlock({'configs':[cookie_config]})
            backend = Config.Backend(name=name, config_block=config_block)
            self.proxy_config.backends.append(backend)
        return backend

    def clean_config(self,unit,save=True):
        # HAProxy units can't have / character, replace it so it doesn't fail on a common error of passing in the juju unit
        unit = unit.replace('/','-')

        # Remove acls and use_backend statements from frontends
        for fe in self.proxy_config.frontends:
            fe.config_block['acls'] = [acl for acl in fe.acls() if acl.name != unit]
            fe.config_block['usebackends'] = [ub for ub in fe.usebackends() if ub.backend_condition != unit]
        
        # Remove server statements from backends
        for be in self.proxy_config.backends:
            be.config_block['servers'] = [srv for srv in be.servers() if srv.name != unit]
        
        # Remove any frontend if it doesn't have both acl and use_backend
        self.proxy_config.frontends = [fe for fe in self.proxy_config.frontends if len(fe.acls()) > 0 and len(fe.usebackends()) > 0]

        # Remove any backend with no server
        self.proxy_config.backends = [be for be in self.proxy_config.backends if len(be.servers()) > 0]
        if save:
            self.save_config()

    def save_config(self):
        # This is a hack to deal with config_block being defaultdict thus having unpredictabe render order
        # Each section with a config_block will have it replaced with my own ConfigBlock class based on OrderedDict
        has_config = (self.proxy_config.userlists,
                      self.proxy_config.listens,
                      self.proxy_config.frontends,
                      self.proxy_config.backends,
                      self.proxy_config.defaults
                      )
        for section_type in has_config: 
            for section in section_type:
                config_block = ConfigBlock(**section.config_block)
                section.config_block = config_block

        # Convinently this section isn't iterable so it had to be pulled out of the above loop
        config_block = ConfigBlock(**self.proxy_config.globall.config_block)
        self.proxy_config.globall.config_block = config_block

        # Render new cfg file
        Render(self.proxy_config).dumps_to(self.proxy_config_file)
        host.service_reload('haproxy.service')
