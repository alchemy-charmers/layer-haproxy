#!/usr/bin/python3

import pytest
import mock

# try:
#     from libhaproxy import ProxyHelper
# except:
#     subprocess.check_call('2to3-3.5 -w /usr/local/lib/python3.5/dist-packages/pyhaproxy', shell=True)
#     from libhaproxy import ProxyHelper

# from libhaproxy import ProxyHelper

# ph = ProxyHelper()


# @pytest.fixture(scope="module")
def mock_layers():
    import sys
    sys.modules["charms.layer"] = mock.MagicMock()
    sys.modules["reactive"] = mock.MagicMock()
    sys.modules["reactive.letsencrypt"] = mock.MagicMock()


# @pytest.fixture(scope="module")
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


@pytest.fixture()
def ph():
    from libhaproxy import ProxyHelper
    ph = ProxyHelper()
    # # # with open(tmpdir.mkdir("haproxy").join("haproxy.cfg"), 'w') as cfg_file:
    # cfg_file = tmpdir.join("haproxy.cfg")
    # with open('./tests/haproxy.cfg', 'r') as src_file:
    #     cfg_file.write(src_file.read())
    # ph.proxy_config_file = cfg_file
    # print("cfg_file: {}".format(cfg_file))
    return ph


# @pytest.fixture
# def phCfg(monkeypatch, ph):
#     # monkeypatch.setattr("libhaproxy.ProxyHelper.proxy_config_file", "./tests/haproxy.cfg")
#     # print(ph.proxy_config_file)
#     # print(ph.proxy_config.defaults)
#     monkeypatch.setattr(ph, "proxy_config_file", "./tests/haproxy.cfg")
#     return ph
#     # yield monkeypatch.setattr(ph, "_proxy_config", None)
#     # print(ph.proxy_config_file)
#     # print(ph.proxy_config.defaults)


# @pytest.mark.usefixtures('mock_layers', 'mock_hookenv_config')
class TestLibhaproxy:
    @property
    @pytest.mark.usefixtures('ph', 'mock_layers', 'mock_hookenv_config')
    def ph(self):
        mock_layers()
        mock_hookenv_config()
        return ph()
        
    def test_pytest(self):
        assert True

    def test_ph(self):
        assert isinstance(self.ph.charm_config, dict)

    def test_proxy_config(self):
        print(self.ph.proxy_config.defaults)
        print("defaults: {}".format(self.ph.proxy_config.defaults[0].options()))
        # print("defaults: {}".format(phCfg.proxy_config.defaults[0].options()))
        # print(type(self.ph.proxy_config.defaults[0].options()))
        # options = self.ph.proxy_config.defaults[0].options()
        # print(options, sep='\n')
        # print("defaults: {}".format(self.ph.proxy_config.defaults[0].configs()))
        assert 0

    # def test_add_timeout_tunnel(self):
    #     self.ph.add_timeout_tunnel()

