#!/usr/bin/python3

# try:
#     from libhaproxy import ProxyHelper
# except:
#     subprocess.check_call('2to3-3.5 -w /usr/local/lib/python3.5/dist-packages/pyhaproxy', shell=True)
#     from libhaproxy import ProxyHelper


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

#    def test_add_timeout_tunnel(self, ph):
#        for option in ph.proxy_config.defaults[0].options():
#            assert "tunnel" not in option.keyword
#        ph.add_timeout_tunnel()
#        for option in ph.proxy_config.defaults[0].options():
#            print(option)
#        assert 0
        # for option in ph.proxy_config.defaults[0].options():
        #     assert "tunnel" not in option.keyword
