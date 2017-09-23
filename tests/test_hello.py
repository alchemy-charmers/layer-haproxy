#!/usr/bin/python3

# import requests
# import unittest


class TestHello():
    def hello(self):
        return "Hello"

    def test_hello(self):
        assert self.hello() == "Hello"
