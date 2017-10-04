#!/usr/bin/python3

import pytest
import amulet
import requests


@pytest.fixture(scope="module")
def deploy():
    deploy = amulet.Deployment(series='xenial')
    deploy.add('haproxy')
    deploy.expose('haproxy')
    deploy.setup(timeout=900)
    deploy.sentry.wait()
    return deploy


@pytest.fixture(scope="module")
def unit(deploy):
    return deploy.sentry['haproxy'][0]


class TestHaproxy():
    # @classmethod
    # def setup_class(self):
    #     self.d = amulet.Deployment(series='xenial')

    #     self.d.add('haproxy')
    #     self.d.expose('haproxy')

    #     self.d.setup(timeout=900)
    #     self.d.sentry.wait()

    #     self.unit = self.d.sentry['haproxy'][0]

    def test_stats(self, deploy, unit):
        # Wrong log/pass is rejected
        # self.assertRaises(requests.exceptions.ConnectionError,
        deploy.configure('haproxy', {'enable-stats': True})
        deploy.sentry.wait()
        page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                            auth=requests.auth.HTTPBasicAuth('admin', 'fail')
                            )
        assert page.status_code == 401

        # with self.assertRaises(Exception):
        #    page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
        #                        auth=requests.auth.HTTPBasicAuth('admin', 'fail')
        #                        )
        # self.assertRaises(Exception,
        #                   requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
        #                                auth=requests.auth.HTTPBasicAuth('admin', 'fail')
        #                                )
        #                   )

        # Correct log/pass connects
        page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                            auth=requests.auth.HTTPBasicAuth('admin', 'admin'))
        assert page.status_code == 200

        # Disable stats prevents connection
        deploy.configure('haproxy', {'enable-stats': False})
        deploy.sentry.wait()
        with pytest.raises(requests.exceptions.ConnectionError):
            page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                                auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                                headers={'Cache-Control': 'no-cache'}
                                )
            print(page.json)
        # self.assertRaises(requests.exceptions.ConnectionError,
        #                   requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
        #                                auth=requests.auth.HTTPBasicAuth('admin', 'admin')
        #                                )
        #                   )

        # page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
        #                     auth=requests.auth.HTTPBasicAuth('admin', 'admin'))
        # self.assertEqual(page.status_code, 200)
        deploy.configure('haproxy', {'enable-stats': True})
        deploy.sentry.wait()
        # test we can access over http
        # page = requests.get('http://{}'.format(self.unit.info['public-address']))
        # self.assertEqual(page.status_code, 200)
        # Now you can use self.d.sentry[SERVICE][UNIT] to address each of the units and perform
        # more in-depth steps. Each self.d.sentry[SERVICE][UNIT] has the following methods:
        # - .info - An array of the information of that unit from Juju
        # - .file(PATH) - Get the details of a file on that unit
        # - .file_contents(PATH) - Get plain text output of PATH file from that unit
        # - .directory(PATH) - Get details of directory
        # - .directory_contents(PATH) - List files and folders in PATH on that unit
        # - .relation(relation, service:rel) - Get relation data from return service
