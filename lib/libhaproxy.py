from charmhelpers.core import hookenv, host

from charms import layer
from collections import defaultdict
from collections import OrderedDict
from pyhaproxy.parse import Parser
from pyhaproxy.render import Render

import pyhaproxy.config as Config
import reactive.letsencrypt as letsencrypt
import subprocess

class ConfigBlock(OrderedDict):
    def __init__(self,*args,**kwargs):
        self['binds'] = []
        self['users'] = []
        self['groups'] = []
        self['options'] = []
        self['acls'] = []
        self['configs'] = []
        self['usebackends'] = []
        self['servers'] = []
        super().__init__(*args,**kwargs)

class ProxyHelper():
    def __init__(self):
        self.charm_config = hookenv.config()
        self.letsencrypt_config = layer.options('letsencrypt')
        self.ppa = "ppa:vbernat/haproxy-{}".format(self.charm_config['version']) 
        self.proxy_config_file = "/etc/haproxy/haproxy.cfg"
        self._proxy_config = None
        self.domain_name = self.charm_config['letsencrypt-domains'].split(',')[0]
        self.ssl_path = '/etc/haproxy/ssl/'
        self.cert_file = self.ssl_path+self.domain_name+'.pem'

    @property
    def proxy_config(self):
        if not self._proxy_config:
            self._proxy_config = Parser(self.proxy_config_file).build_configuration()
        return self._proxy_config 

    def process_config(self,config):
        remote_unit = hookenv.remote_unit().replace('/','-')
        backend_name = config['group_id'] or remote_unit

        # Remove any prior configuration as it might have changed, do not write cfg file we still have edits to make
        self.clean_config(unit=remote_unit,backend_name=backend_name,save=False)

        # Get the frontend, create if not present
        frontend = self.get_frontend(config['external_port'])

        if config['mode'] =='http':
            if not self.available_for_http(frontend):
                return({"cfg_good":False,"msg":"Port not available for http routing"})
                
            # Add ACL's to the frontend
            if config['urlbase']:
                acl = Config.Acl(name=remote_unit, value='path_beg {}'.format(config['urlbase']))
                frontend.acls().append(acl)
            if config['subdomain']:
                acl = Config.Acl(name=remote_unit, value='hdr_beg(host) -i {}'.format(config['subdomain']))
                frontend.acls().append(acl)

            # Add use_backend section to the frontend
            use_backend = Config.UseBackend(backend_name=backend_name,
                                            operator='if',
                                            backend_condition=remote_unit,
                                            is_default=False)
            frontend.usebackends().append(use_backend)
        if config['mode'] == 'tcp':
            if not self.available_for_tcp(frontend,backend_name):
                return({"cfg_good":False,"msg":"Frontend already in use can not setup tcp mode"})

            mode_config = ("mode tcp","")
            if mode_config not in frontend.configs():
                frontend.configs().append(mode_config)
            
            use_backend = Config.UseBackend(backend_name=backend_name,
                                            operator='',
                                            backend_condition='',
                                            is_default=True)
            frontend.usebackends().append(use_backend)

        # Get the backend, create if not present
        backend = self.get_backend(backend_name)

        # Add server to the backend
        if config['mode'] == 'http':
            cookie_config = ('cookie SERVERID insert indirect nocache','')
            backend.config_block['configs'].append(cookie_config)
            attributes = ['cookie {}'.format(remote_unit)]
            if config['group_id']:
                check_option = ('httpchk GET / HTTP/1.0','')
                backend.config_block['options'].append(check_option)
                attributes.append('check')
        else:
            attributes = ['']
        server = Config.Server(name=remote_unit, host=config['internal_host'], port=config['internal_port'], attributes=attributes)
        backend.servers().append(server) 

        # Render new cfg file
        self.save_config()
        return({"cfg_good":True,"msg":"configuration applied"})

    def available_for_http(self,frontend,config=None):
        for config in frontend.configs():
            if "mode tcp" in config:
                return False
        return True

    def available_for_tcp(self,frontend,backend_name):
        if len(frontend.acls()):
            return False
        if len(frontend.usebackends()):
            valid_backend = False
            for ub in frontend.usebackends():
                if backend_name == ub.backend_name:
                    valid_backend = True
            if not valid_backend:
                return False
        return True

    def enable_stats(self,save=True):
        # Remove any previous stats
        self.disable_stats(save=False)

        # Generate new front end for stats
        user_string = '{}:{}'.format(self.charm_config['stats-user'],self.charm_config['stats-passwd'])
        config_block = ConfigBlock({'binds':[Config.Bind('0.0.0.0', self.charm_config['stats-port'], None)],
                                    'configs':[('stats enable',''),
                                               ('stats auth {}'.format(user_string),''),
                                               ('stats uri {}'.format(self.charm_config['stats-url']),'')]
                                    })
        if self.charm_config['stats-local']:
            config_block['acls'].append(Config.Acl('local','src 10.0.0.0/8 192.168.0.0/16 127.0.0.0/8'))
            config_block['configs'].append(('block if !local',''))
        frontend = Config.Frontend('stats', '0.0.0.0', self.charm_config['stats-port'], config_block)
        self.proxy_config.frontends.append(frontend)
        if save:
            self.save_config()

    def disable_stats(self,save=True):
        # Remove any previous stats frontend
        self.proxy_config.frontends = [fe for fe in self.proxy_config.frontends if fe.name != 'stats']
        if save:
            self.save_config()

    def get_frontend(self,port=None):
        port = str(port)
        frontend = None
        for fe in self.proxy_config.frontends:
            hookenv.log("Checking frontend for port {}".format(port),"DEBUG")
            hookenv.log("Port is: {}".format(fe.port),"DEBUG")
            if fe.port == port:
                hookenv.log("Using previous frontend","DEBUG")
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
            config_block = ConfigBlock()
            backend = Config.Backend(name=name, config_block=config_block)
            self.proxy_config.backends.append(backend)
        return backend

    def clean_config(self,unit,backend_name,save=True):
        # HAProxy units can't have / character, replace it so it doesn't fail on a common error of passing in the juju unit
        unit = unit.replace('/','-')
        backend_name = backend_name.replace('/','-')

        # Remove acls and use_backend statements from frontends
        for fe in self.proxy_config.frontends:
            fe.config_block['acls'] = [acl for acl in fe.acls() if acl.name != unit]
            fe.config_block['usebackends'] = [ub for ub in fe.usebackends() if ub.backend_name != backend_name]
        
        # Remove server statements from backends
        for be in self.proxy_config.backends:
            be.config_block['servers'] = [srv for srv in be.servers() if srv.name != unit]
        
        # Remove any relation frontend if it doesn't have use_backend
        self.proxy_config.frontends = [fe for fe in self.proxy_config.frontends if len(fe.usebackends()) > 0 or not fe.name.startswith('relation')]

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

        # Check the juju ports match the config
        self.update_ports()

    def update_ports(self):
        opened_ports = str(subprocess.check_output(["opened-ports"]),'utf-8').split('/tcp\n')
        hookenv.log("Opened ports {}".format(opened_ports),"DEBUG")
        for frontend in self.proxy_config.frontends:
            if frontend.port in opened_ports:
                hookenv.log("Port already open {}".format(frontend.port),"DEBUG")
                opened_ports.remove(frontend.port)
            else:
                hookenv.log("Opening {}".format(frontend.port),"DEBUG")
                hookenv.open_port(frontend.port)
        for port in opened_ports:
            if port:
                hookenv.log("Closing port {}".format(port),"DEBUG")
                hookenv.close_port(port)

    def enable_letsencrypt(self):
        hookenv.log("Enabling letsencrypt","DEBUG")
        unit_name = 'letsencrypt'
        backend_name = 'letsencrypt-backend'

        frontend = self.get_frontend(80)
        if not self.available_for_http(frontend):
            hookenv.log("Port 80 not available for http use by letsencrypt","ERROR")
            return #TODO: Should I error here or is just returning with a log ok?

        # Only configure the rest if we haven't already done so to avoid checking every change for already existing
        first_run = True
        for acl in frontend.acls():
            if acl.name == unit_name:
               first_run = False 
        if first_run:
            # Add ACL to the frontend
            acl = Config.Acl(name=unit_name, value='path_beg -i /.well-known/acme-challenge/')
            frontend.acls().append(acl)
            # Add usebackend 
            use_backend = Config.UseBackend(backend_name=backend_name,
                                            operator='if',
                                            backend_condition=unit_name,
                                            is_default=False)
            frontend.usebackends().append(use_backend)

            # Get the backend, create if not present
            backend = self.get_backend(backend_name)

            # Add server to the backend
            attributes = ['']
            server = Config.Server(name=unit_name, host='127.0.0.1', port=self.letsencrypt_config['port'], attributes=attributes)
            backend.servers().append(server) 

            # Render new cfg file
            self.save_config()

        # Call the register function from the letsencrypt layer
        hookenv.log("Letsencrypt port: {}".format(self.letsencrypt_config['port']),'DEBUG')
        hookenv.log("Letsencrypt domains: {}".format(self.charm_config['letsencrypt-domains']),'DEBUG')
        if letsencrypt.register_domains() > 0:
            hookenv.log("Failed letsencrypt registration see /var/log/letsencrypt.log","ERROR")
            return #TODO: Should I error here or is just returning with a log ok?

        # create the merged .pem for HAProxy
        self.merge_letsencrypt_cert()

        # Configure the frontend 443
        frontend = self.get_frontend(443)
        if not len(frontend.binds()[0].attributes):
            frontend.binds()[0].attributes.append('ssl crt {}'.format(self.cert_file))
        if first_run:
            frontend.acls().append(acl)
            frontend.usebackends().append(use_backed)
            self.save_config() 

    def disable_letsencrypt(self,save=True):
        # Remove any previous config 
        self.clean_config(unit='letsencrypt',backend_name='letsencrypt-backend',save=save)
         
    def merge_letsencrypt_cert(self):
        letsencrypt_live_folder = '/etc/letsencrypt/live/{}/'.format(self.domain_name)
        with open(self.cert_file,'wb') as outFile:
            with open(letsencrypt_live_folder+'fullchain.pem','rb') as chainFile:
                outFile.write(chainFile.read())
            with open(letsencrypt_live_folder+'privkey.pem','rb') as privFile:
                outFile.write(privFile.read())


