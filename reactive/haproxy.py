"""Reactive layer for haproxy charm."""
import errno
import fileinput
import os

from charmhelpers import fetch
from charmhelpers.core import hookenv, host
from charms.reactive import (
    hook,
    remove_state,
    set_state,
    when,
    when_all,
    when_any,
    when_not,
)
from libhaproxy import ProxyHelper

ph = ProxyHelper()


@when_not("haproxy.installed")
def install_haproxy():
    """Install haproxy when the haproxy.installed flag is not set."""
    hookenv.status_set("maintenance", "Installing HAProxy")
    fetch.add_source(ph.ppa)
    fetch.apt_update()
    fetch.install("haproxy")
    set_state("haproxy.installed")


@when("haproxy.installed")
@when_not("haproxy.configured")
def configure_haproxy():
    """Configure haproxy when haproxy is installed but configuration not in place."""
    hookenv.status_set("maintenance", "Configuring HAProxy")
    try:
        os.makedirs(ph.ssl_path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    # Enable udp for rsyslog

    for line in fileinput.input("/etc/rsyslog.conf", inplace=True):
        line = line.replace('#module(load="imudp")', 'module(load="imudp")')
        line = line.replace(
            '#input(type="imudp" port="514")', 'input(type="imudp" port="514")'
        )
        print(line, end="")
        # end statement above avoids inserting new lines at EOL
    host.service_restart("rsyslog.service")

    if ph.charm_config["enable-stats"]:
        ph.enable_stats()

    if ph.charm_config["enable-letsencrypt"]:
        ph.enable_letsencrypt()

    if ph.charm_config["enable-upnp"]:
        ph.add_upnp_cron()

    if ph.charm_config["enable-https-redirect"]:
        ph.enable_redirect()
    ph.add_timeout_tunnel()
    hookenv.status_set("active", "")
    set_state("haproxy.configured")


@when_all("reverseproxy.triggered", "reverseproxy.changed")
def configure_relation(reverseproxy, *args):
    """Configure related backend."""
    hookenv.status_set("maintenance", "Setting up relation")
    hookenv.log("Received config: {}".format(reverseproxy.config), "Info")
    # Process either dict or list of dicts to support legacy relations
    configs = []

    if isinstance(reverseproxy.config, dict):
        configs.append(reverseproxy.config)
    else:
        configs = reverseproxy.config
    status = ph.process_configs(configs)
    reverseproxy.set_cfg_status(**status)
    hookenv.status_set("active", "")


@when_all("reverseproxy.triggered", "reverseproxy.departed")
def remove_relation(reverseproxy, *args):
    """Remove related backend and clean config."""
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))
    # Process either dict or list of dicts to support legacy relations
    # TODO: This doesn't seem to clean up frontends and close ports
    configs = []

    if isinstance(reverseproxy.config, dict):
        configs.append(reverseproxy.config)
    else:
        configs = reverseproxy.config

    for names in ph.get_config_names(configs):
        unit_name = names[0]
        backend_name = names[1]
        hookenv.log(
            "Cleaning on depart for {}, {}".format(unit_name, backend_name), "DEBUG"
        )
        ph.clean_config(unit=unit_name, backend_name=backend_name)


@when("config.changed.version")
def version_changed():
    """Reconfigure when the desired version is changed."""
    if hookenv.hook_name() == "install":
        return
    valid, msg, _ = ph.check_version()

    if valid:
        install_haproxy()

        if (
            ph.charm_config["version"] == "1.9"
            and ph.charm_config["enable-letsencrypt"]
        ):
            # Starting with 1.9 HTTP2 will be setup during install, disable letsencrypt if we
            # have just upgraded so intsall will reenable with HTTP2 support
            ph.disable_letsencrypt()
            ph.enable_letsencrypt()
        hookenv.status_set("active", "")
    else:
        hookenv.log(msg, "WARNING")
        hookenv.status_set(
            "active", msg,
        )


@hook("post-series-upgrade")
def post_series_upgrade():
    """Run post upgrade steps."""
    valid, msg, version = ph.check_version()

    if not valid:
        hookenv.log(
            "Version not supported after upgrade, installing minimum supported version {}.".format(
                version
            ),
            "WARNING",
        )
        ph.charm_config["version"] = version
    install_haproxy()
    remove_state("letsencrypt.installed")
    hookenv.status_set("active", "")


@when_any(
    "config.changed.enable-stats",
    "config.changed.stats-user",
    "config.changed.stats-passwd",
    "config.changed.stats-url",
    "config.changed.stats-port",
    "config.changed.stats-local",
)
def stats_changed():
    """Reconfigure the stats endpoint when configuration changes."""
    if hookenv.hook_name() == "install":
        return

    if ph.charm_config["enable-stats"]:
        hookenv.log("Enabling stats for config change")
        ph.enable_stats()
    else:
        hookenv.log("Disabling stats for config change")
        ph.disable_stats()


@when_any("config.changed.enable-upnp")
def upnp_changed():
    """Reconfigure UPNP behaviour when configuration changes."""
    if hookenv.hook_name() == "install":
        return

    if ph.charm_config["enable-upnp"]:
        ph.add_upnp_cron()
        ph.renew_upnp()
    else:
        ph.remove_upnp_cron()
        # Turning on upnp to close ports so a release is issued
        ph.charm_config["enable-upnp"] = True
        ph.release_upnp()
        # Turning upnp back off and opening ports w/o upnp
        ph.charm_config["enable-upnp"] = False
        ph.update_ports()


@when("config.changed.upnp-renew-interval")
def upnp_interval_changed():
    """Reconfigure the UPNP referesh interval when configuration changes."""
    if hookenv.hook_name() == "install":
        return
    ph.remove_upnp_cron()

    if ph.charm_config["enable-upnp"]:
        ph.add_upnp_cron()


@when_any(
    "config.changed.enable-letsencrypt",
    "config.changed.letsencrypt-domains",
    "config.changed.letsencrypt-email",
)
def letsencrypt_config_changed():
    """Configure certbot when configuration changes."""
    if hookenv.hook_name() == "install":
        return
    ph.disable_letsencrypt()

    if ph.charm_config["enable-letsencrypt"]:
        ph.enable_letsencrypt()


@when("config.changed.cert-renew-interval")
def cert_interval_changed():
    """Reconfigure the certificate renewal interval when configuration changes."""
    if hookenv.hook_name() == "install":
        return
    ph.remove_cert_cron()

    if ph.charm_config["enable-letsencrypt"]:
        ph.add_cert_cron()


@when("config.changed.enable-https-redirect")
def redirect_changed():
    """Reconfigure the HTTPS redirect behaviour when configuration changes."""
    if hookenv.hook_name() == "install":
        return

    if ph.charm_config["enable-https-redirect"]:
        ph.enable_redirect()
    else:
        ph.disable_redirect()


@hook("stop")
def stop_haproxy():
    """Stop haproxy and disable certbot when a deployed unit is being stopped."""
    if ph.charm_config["enable-stats"]:
        hookenv.log("Disabling status to free any opened ports", "INFO")
        ph.disable_stats()
        hookenv.log("Disabling letsencrypt to free any opened ports", "INFO")
        ph.disable_letsencrypt()
