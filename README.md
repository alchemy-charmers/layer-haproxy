# Overview

This charm provides [HAProxy][haproxy]. HAProxy describes itself as a free, very
fast and reliable solution offering high availability, load balancing, and
proxying for TCP and HTTP-based applications. It is particularly suited for very
high traffic web sites and powers quite a number of the world's most visited
ones. Over the years it has become the de-facto standard open source load
balancer, is now shipped with most mainstream Linux distributions, and is often
deployed by default in cloud platforms. Since it does not advertise itself, we
only know it's used when the admins report it :-) 

# Usage

To deploy:

    juju deploy cs:~alchemy-charmers/haproxy

You will most likely want to use a bundle to set options during deployment. The
primary use case for this charm is to allow other charms that implement the
[reverse proxy][interface-reverseproxy] interface to automatically register for
reverse proxy. This charm will allow both http and tcp reverse proxy's to be
requested from other charms. Additionally, for http reverse proxy Letsencrypt is
provided to allow HAProxy to automatically register for a certificate and
terminate the SSL/TLS connection. Finally, this charm provides options to use
UPNP for automatically requesting ports via UPNP. Most of these features are off
by default, see the configuration options to enable them.

## Known Limitations and Issues

This charm is under development, several other use cases/features are still under
consideration. Merge requests are appreciated, some examples of current limitations include.

 * No HA Failover or Scaleout usage currently implemented
 * Can not restrict the ports other charms request

# Configuration

See the full list of configuration options below. This will detail some of the
options that are worth highlighting.

 - To access HAProxy stats please see "stats-user", "stats-passwd", "stats-url",
   "stats-port", and "stats-local" configuration settings. Note that the stats
   port must be unique, if you want to use the default port of 9000 for other
   service you should change this setting.
 - UPNP is provided via monkey patch and should be considered a convenience.
   Running UPNP in production is not recommended practice.
 - hostname will allow you to customize the hostname of HAProxy, be aware that
   doing this can cause multiple hosts to have the same hostname if you scale
   out the number of units. Setting hostname to "$UNIT" will set the hostname to
   the juju unit id.

# Upgrades

Some limited upgrade support is available. The charm will only upgrade for specific versions.
Currently this includes:
 * Xenial: 1.7
 * Bionic: 1.8, 1.9

Upgrading to a new Ubuntu release is currently tested from Xenial to Bionic. The upgrade
procedures are the standard juju series upgrade procedures. Substitute your machine id in the
example below.

From the juju client
```bash
juju upgrade-series $MACHINE prepare bionic
juju ssh $MACHINE
```
From the machine
```bash
sudo su -
apt update 
apt upgrade -y 
apt dist-upgrade -y
do-release-upgrade -f DistUpgradeViewNonInteractive
reboot now
```
During the upgrade any questions about configuration files should accept the default (keep
local copy). Specifically, the HAProxy configuration file needs to be kept. If it is not,
relations will have to be removed and re-added to repopulate the config file after the
upgrade.

Complete from the juju client
```bash
juju upgrade-series $MACHINE complete
```

Xenial to Bionic: After setting the upgrade to 'complete' HAProxy will be upgraded to the LTS
1.8 release. The charm can not change the juju config value. To make this match the installed
version set run `juju config haproxy version="1.8"`. Optionally, you can set this to 1.9
instead and an upgrade to 1.9 will be performed.

# Contact Information

## Upstream Project Information

  - Code: https://github.com/chris-sanders/layer-haproxy 
  - Bug tracking: https://github.com/chris-sanders/layer-haproxy/issues
  - Contact information: sanders.chris@gmail.com

[haproxy]: http://www.haproxy.org/
[interface-reverseproxy]: https://github.com/chris-sanders/interface-reverseproxy
