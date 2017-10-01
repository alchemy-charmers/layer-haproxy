#!/usr/bin/python3
import pytest
import mock


@pytest.fixture
def mock_crontab(monkeypatch):
    mock_cron = mock.MagicMock()
    monkeypatch.setattr('libhaproxy.CronTab', mock_cron)
    monkeypatch.setattr('libhaproxy.hookenv.local_unit', lambda: 'mock-local/0')
    monkeypatch.setattr('libhaproxy.hookenv.charm_dir', lambda: '/mock/charm/dir')
    return mock_cron


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
def mock_layers(monkeypatch):
    import sys
    sys.modules["charms.layer"] = mock.Mock()
    sys.modules["reactive"] = mock.Mock()
    sys.modules["reactive.letsencrypt"] = mock.Mock()
    monkeypatch.setattr('libhaproxy.letsencrypt.register_domains', lambda: 0)
    monkeypatch.setattr('libhaproxy.letsencrypt.renew', mock.Mock())

    def options(layer):
        if layer == 'letsencrypt':
            options = {'port': 9999}
            return options
        else:
            return None

    monkeypatch.setattr('libhaproxy.layer.options', options)


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

    def mports(*args, **kwargs):
        if args[0][0] == "opened-ports":
            return bytes(mports.open_ports, encoding='utf8')
        elif args[0][0] == "open-port":
            if args[0][1].lower() not in mports.open_ports:
                mports.open_ports = mports.open_ports + args[0][1].lower() + '\n'
            return bytes(mports.open_ports, encoding='utf8')
        elif args[0][0] == "close-port":
            mports.open_ports = mports.open_ports.replace(args[0][1].lower() + '\n', '')
            return bytes(mports.open_ports, encoding='utf8')
        else:
            print("called with: {}".format(args[0]))
            return None
    mports.open_ports = open_ports

    monkeypatch.setattr('libhaproxy.subprocess.check_output', mports)
    monkeypatch.setattr('libhaproxy.subprocess.check_call', mports)
    # monkeypatch.setattr('libhaproxy.subprocess.check_output',
    #                     mock.Mock(spec=mports, wraps=mports))
    # monkeypatch.setattr('libhaproxy.subprocess.check_call',
    #                     mock.Mock(spec=mports, wraps=mports))


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
