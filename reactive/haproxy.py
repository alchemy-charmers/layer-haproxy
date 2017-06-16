from charms.reactive import when, when_all, when_not, set_state
from charmhelpers.core import hookenv, host
from charmhelpers import fetch

import subprocess
try:
    from libhaproxy import ProxyHelper
except:
    subprocess.check_call('2to3-3.5 -w /usr/local/lib/python3.5/dist-packages/pyhaproxy',shell=True)
    from libhaproxy import ProxyHelper

ph = ProxyHelper()

@when_not('haproxy.installed')
def install_layer_haproxy():
    hookenv.status_set('maintenance','Installing HAProxy')
    fetch.add_source(ph.ppa)
    fetch.install('haproxy')
    hookenv.log('ph test: {}'.format(ph.proxy_config.globall.configs()))
    set_state('haproxy.installed')

@when_all('reverseproxy.triggered','haproxy.installed')
@when_not('reverseproxy.ready')
def configure_relation(reverseproxy,*args):
    reverseproxy.configure(ports=[])

@when_all('reverseproxy.triggered','reverseproxy.changed')
def apply_config(reverseproxy,*args):
    hookenv.log("TODO Apply config: {}".format(reverseproxy.config),"WARNING")
    reverseproxy.set_cfg_status(True,"I just told you it was true, I'm not yet operational")
