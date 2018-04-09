#!/usr/bin/python3

import pytest
import amulet
import requests
import time


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


@pytest.fixture()
def nostats(deploy):
    print("Disabling stats")
    deploy.configure('haproxy', {'enable-stats': False})
    time.sleep(10)
    yield
    print("Re-enabling stats")
    deploy.configure('haproxy', {'enable-stats': True})
    time.sleep(10)


class TestHaproxy():

    def test_wrong_login(self, deploy, unit):
        # Wrong log/pass is rejected
        deploy.sentry.wait()
        page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                            auth=requests.auth.HTTPBasicAuth('admin', 'fail')
                            )
        assert page.status_code == 401

    def test_right_login(self, deploy, unit):
        # Correct log/pass connects
        page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                            auth=requests.auth.HTTPBasicAuth('admin', 'admin'))
        assert page.status_code == 200

    @pytest.mark.usefixtures("nostats")
    def test_disable_stats(self, deploy, unit):
        # Disable stats prevents connection
        with pytest.raises(requests.exceptions.ConnectionError):
            page = requests.get('http://{}:{}/{}'.format(unit.info['public-address'], 9000, 'ha-stats'),
                                auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                                headers={'Cache-Control': 'no-cache'}
                                )
            print(page.json)

    def test_action_renew_upnp(self, deploy, unit):
        uuid = unit.run_action('renew-upnp')
        action_output = deploy.get_action_output(uuid, full_output=True)
        print(action_output)
        assert action_output['status'] == 'completed'

    def test_action_renew_cert(self, deploy, unit):
        uuid = unit.run_action('renew-cert')
        action_output = deploy.get_action_output(uuid, full_output=True)
        print(action_output)
        assert action_output['status'] == 'completed'

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
