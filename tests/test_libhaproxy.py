#!/usr/bin/python3

import os


class TestLibhaproxy():
       
    def test_pytest(self):
        assert True

    def test_ph(self, ph):
        ''' See if the ph fixture works to load charm configs '''
        assert isinstance(ph.charm_config, dict)

    def test_proxy_config(self, ph):
        ''' Check that default proxy config can be read '''
        # This will work after upgrading to a new pyhaproxy
        # default_options = ['httplog', 'dontlognull']
        # for option in ph.proxy_config.defaults[0].options():
        #     assert option.keyword in default_options
        default_options = [('httplog', ''), ('dontlognull', '')]
        for option in ph.proxy_config.defaults[0].options():
            assert option in default_options

    def test_add_timeout_tunnel(self, ph):
        test_options = [('tunnel timeout 1h', '')]
        for option in ph.proxy_config.defaults[0].options():
            assert option not in test_options
        ph.add_timeout_tunnel()
        for option in ph.proxy_config.defaults[0].options():
            if option in test_options:
                break
            else:
                continue
            assert 0  # test_options not found in default section

    def test_get_config_names(self, ph, mock_remote_unit):
        config = {'group_id': 'test_group'}
        remote_unit, backend_name = ph.get_config_names(config)

    def test_process_config(self, ph, mock_remote_unit):
        config = {'mode': 'http',
                  'urlbase': '/test',
                  'subdomain': None,
                  'group_id': None,
                  'external_port': 80,
                  'internal_host': 'test-host',
                  'internal_port': 8000
                  }
        print(ph.process_config(config))

    def test_merge_letsencrypt_cert(self, ph, cert):
        assert not os.path.isfile(ph.cert_file)
        ph.merge_letsencrypt_cert()
        assert os.path.isfile(ph.cert_file)
        with open(ph.cert_file, 'r') as certFile:
            assert certFile.readline() == 'fullchain.pem\n'
            assert certFile.readline() == 'privkey.pem\n'
