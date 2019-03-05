import os
import pytest
import requests
import time

from juju.model import Model

# Treat tests as coroutines
pytestmark = pytest.mark.asyncio

series = ['xenial', 'bionic']
juju_repository = os.getenv('juju_repository', '.').rstrip('/')


@pytest.fixture
async def model():
    model = Model()
    await model.connect_current()
    yield model
    await model.disconnect()


@pytest.fixture
async def units(model):
    units = []
    for entry in series:
        app = model.applications['haproxy-{}'.format(entry)]
        units.extend(app.units)
    return units


@pytest.fixture
async def apps(model):
    apps = []
    for entry in series:
        app = model.applications['haproxy-{}'.format(entry)]
        apps.append(app)
    return apps


@pytest.fixture()
async def nostats(apps):
    print("Disabling stats")
    for app in apps:
        await app.set_config({'enable-stats': "False"})
    time.sleep(10)
    yield
    print("Re-enabling stats")
    for app in apps:
        await app.set_config({'enable-stats': "True"})
    time.sleep(5)


@pytest.mark.parametrize('series', series)
async def test_haproxy_deploy(model, series):
    print('{}/builds/haproxy'.format(juju_repository))
    await model.deploy('{}/builds/haproxy'.format(juju_repository),
                       series=series,
                       application_name='haproxy-{}'.format(series))
    assert True


async def test_haproxy_status(apps, model):
    for app in apps:
        await model.block_until(lambda: app.status == 'active')
    assert True


async def test_wrong_login(units):
    for unit in units:
        page = requests.get('http://{}:{}/{}'.format(unit.public_address, 9000, 'ha-stats'),
                            auth=requests.auth.HTTPBasicAuth('admin', 'fail')
                            )
        assert page.status_code == 401


@pytest.mark.usefixtures("nostats")
async def test_disable_stats(units):
    for unit in units:
        # Disable stats prevents connection
        with pytest.raises(requests.exceptions.ConnectionError):
            page = requests.get('http://{}:{}/{}'.format(unit.public_address, 9000, 'ha-stats'),
                                auth=requests.auth.HTTPBasicAuth('admin', 'admin'),
                                headers={'Cache-Control': 'no-cache'}
                                )
            print(page.json)


async def test_action_renew_upnp(units):
    for unit in units:
        action = await unit.run_action('renew-upnp')
        action = await action.wait()
        assert action.status == 'completed'


async def test_action_renew_cert(units):
    for unit in units:
        action = await unit.run_action('renew-cert')
        action = await action.wait()
        assert action.status == 'completed'
