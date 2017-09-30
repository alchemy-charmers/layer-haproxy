#!/usr/bin/python3
import pytest
import mock


@pytest.fixture
def cert(monkeypatch):
    normal_open = open

    def wrapper(*args, **kwargs):
        content = None
        if args[0] == '/etc/letsencrypt/live/mock/fullchain.pem':
            content = 'fullchain.pem\n'
            if 'b' in args[1]:
                content = bytes(content, encoding='utf8')
        elif args[0] == '/etc/letsencrypt/live/mock/privkey.pem':
            content = 'privkey.pem\n'
            if 'b' in args[1]:
                content = bytes(content, encoding='utf8')
        else:
            file_object = normal_open(*args)
            return file_object
        file_object = mock.mock_open(read_data=content).return_value
        file_object.__iter__.return_value = content.splitlines(True)
        return file_object

    monkeypatch.setattr('builtins.open', wrapper)


@pytest.fixture
def mock_layers():
    import sys
    sys.modules["charms.layer"] = mock.MagicMock()
    sys.modules["reactive"] = mock.MagicMock()
    sys.modules["reactive.letsencrypt"] = mock.MagicMock()


@pytest.fixture
def mock_hookenv_config(monkeypatch):
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

    monkeypatch.setattr('libhaproxy.hookenv.config', mock_config)


@pytest.fixture
def mock_service_reload(monkeypatch):
    monkeypatch.setattr('libhaproxy.host.service_reload', lambda x: None)


@pytest.fixture
def mock_remote_unit(monkeypatch):
    monkeypatch.setattr('libhaproxy.hookenv.remote_unit', lambda: 'unit-mock/0')


@pytest.fixture
def mock_ports(monkeypatch, open_ports=''):

    def wrapper(*args, **kwargs):
        if args[0][0] == "opened-ports":
            return bytes(wrapper.open_ports, encoding='utf8')
        elif args[0][0] == "open-port":
            wrapper.open_ports = wrapper.open_ports + args[0][1].lower() + '\n'
            return bytes(wrapper.open_ports, encoding='utf8')
        elif args[0][0] == "close-port":
            wrapper.open_ports.replace(args[0][1], '')
            return bytes(wrapper.open_ports, encoding='utf8')
        else:
            print("called with: {}".format(args[0]))
            return None
    wrapper.open_ports = open_ports

    monkeypatch.setattr('libhaproxy.subprocess.check_output', wrapper)
    monkeypatch.setattr('libhaproxy.subprocess.check_call', wrapper)


@pytest.fixture
def pyhaproxy(mock_layers, mock_hookenv_config):
    import os
    import sys
    import subprocess
    if 'pyhaproxy' not in sys.modules.keys():
        import pyhaproxy
        module_path = os.path.dirname(pyhaproxy.__file__)
        del sys.modules['pyhaproxy']
        del pyhaproxy
        subprocess.check_call('2to3-3.5 -w {}'.format(module_path), shell=True)
        import pyhaproxy


@pytest.fixture
# def ph(mock_layers, mock_hookenv_config, tmpdir, mock_ports,
def ph(pyhaproxy, tmpdir, mock_ports, mock_service_reload):
    from libhaproxy import ProxyHelper
    ph = ProxyHelper()

    # Patch the proxy_config to a tmpfile
    cfg_file = tmpdir.join("haproxy.cfg")
    with open('./tests/haproxy.cfg', 'r') as src_file:
        cfg_file.write(src_file.read())
    ph.proxy_config_file = cfg_file.strpath

    # Patch the combined cert file to a tmpfile
    crt_file = tmpdir.join("mock.pem")
    ph.cert_file = crt_file.strpath

    return ph
