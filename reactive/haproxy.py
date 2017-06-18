from charms.reactive import when, when_all, when_not, set_state
from charmhelpers.core import hookenv, host
from charmhelpers import fetch

import subprocess
import fileinput
try:
    from libhaproxy import ProxyHelper
except:
    subprocess.check_call('2to3-3.5 -w /usr/local/lib/python3.5/dist-packages/pyhaproxy',shell=True)
    from libhaproxy import ProxyHelper

ph = ProxyHelper()

@when_not('haproxy.installed')
def install_haproxy():
    hookenv.status_set('maintenance','Installing HAProxy')
    fetch.add_source(ph.ppa)
    fetch.install('haproxy')
    set_state('haproxy.installed')

@when('haproxy.installed')
@when_not('haproxy.configured')
def configure_haproxy():
    hookenv.status_set('maintenance','Configuring HAProxy')
    # Enable udp for rsyslog
    for line in fileinput.input('/etc/rsyslog.conf', inplace=True):
        line = line.replace('#module(load="imudp")','module(load="imudp")')
        line = line.replace('#input(type="imudp" port="514")','input(type="imudp" port="514")')
        print(line,end='') # end statement to avoid inserting new lines at the end of the line
    host.service_restart('rsyslog.service')
    hookenv.status_set('active','')
    set_state('haproxy.configured')

@when_all('reverseproxy.triggered','haproxy.configured')
@when_not('reverseproxy.ready')
def set_ready(reverseproxy,*args):
    reverseproxy.configure(ports=[])

#TODO: look att host.restart_on_change to only reload if the cfg is changed
@when_all('reverseproxy.triggered','reverseproxy.changed')
def configure_relation(reverseproxy,*args):
    hookenv.status_set('maintenance','Setting up relation')
    hookenv.log("Received config: {}".format(reverseproxy.config),"Info")
    status = ph.process_config(reverseproxy.config)
    reverseproxy.set_cfg_status(**status)
    if status['cfg_good']:
        host.service_reload('haproxy.service')
    hookenv.status_set('active','')
