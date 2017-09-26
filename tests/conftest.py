#!/usr/bin/python3
import pytest 
import mock


@pytest.fixture
def mock_layers():
    import sys
    sys.modules["charms.layer"] = mock.MagicMock()
    sys.modules["reactive"] = mock.MagicMock()
    sys.modules["reactive.letsencrypt"] = mock.MagicMock()


@pytest.fixture
def mock_hookenv_config():
    from charmhelpers.core import hookenv
    import yaml

    def mock_config():
        cfg = {}
        yml = yaml.load(open('./config.yaml'))

        # Load all defaults
        for key, value in yml['options'].items():
            cfg[key] = value['default']

        # Manually add cfg from other layers
        cfg['letsencrypt-domains'] = 'mock'
        return cfg
    hookenv.config = mock_config


@pytest.fixture
def ph(mock_layers, mock_hookenv_config, tmpdir):
    import subprocess
    import os
    import sys
    if 'libhaproxy' not in sys.modules.keys():
        import pyhaproxy
        module_path = os.path.dirname(pyhaproxy.__file__)
        del sys.modules['pyhaproxy']
        del pyhaproxy
        subprocess.check_call('2to3-3.5 -w {}'.format(module_path), shell=True)

    from libhaproxy import ProxyHelper
    ph = ProxyHelper()

    # Patch the proxy_config to a tmpfile
    cfg_file = tmpdir.join("haproxy.cfg")
    with open('./tests/haproxy.cfg', 'r') as src_file:
        cfg_file.write(src_file.read())
    ph.proxy_config_file = cfg_file.strpath

    return ph
