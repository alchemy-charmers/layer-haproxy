#!/usr/bin/python3

# import requests
# import unittest

# try:
#     from libhaproxy import ProxyHelper
# except:
#     subprocess.check_call('2to3-3.5 -w /usr/local/lib/python3.5/dist-packages/pyhaproxy', shell=True)
#     from libhaproxy import ProxyHelper

from libhaproxy import ProxyHelper

# ph = ProxyHelper()


class TestHello():
    def hello(self):
        return "Hello"

    def test_hello(self):
        assert self.hello() == "Hello"

    def test_ph(self):
        ph = ProxyHelper()
        assert isinstance(ph.charm_config, dict)
