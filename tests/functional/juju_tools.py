import pickle
import juju
import base64

# from juju.errors import JujuError


class JujuTools:
    def __init__(self, controller, model):
        self.controller = controller
        self.model = model

    async def run_command(self, cmd, target):
        '''
        Runs a command on a unit.

        :param cmd: Command to be run
        :param unit: Unit object or unit name string
        '''
        unit = (
            target
            if isinstance(target, juju.unit.Unit)
            else await self.get_unit(target)
        )
        action = await unit.run(cmd)
        return action.results

    async def remote_object(self, imports, remote_cmd, target):
        '''
        Runs command on target machine and returns a python object of the result

        :param imports: Imports needed for the command to run
        :param remote_cmd: The python command to execute
        :param target: Unit object or unit name string
        '''
        python3 = "python3 -c '{}'"
        python_cmd = ('import pickle;'
                      'import base64;'
                      '{}'
                      'print(base64.b64encode(pickle.dumps({})), end="")'
                      .format(imports, remote_cmd))
        cmd = python3.format(python_cmd)
        results = await self.run_command(cmd, target)
        return pickle.loads(base64.b64decode(bytes(results['Stdout'][2:-1], 'utf8')))

    async def file_stat(self, path, target):
        '''
        Runs stat on a file

        :param path: File path
        :param target: Unit object or unit name string
        '''
        imports = 'import os;'
        python_cmd = ('os.stat("{}")'
                      .format(path))
        print("Calling remote cmd: " + python_cmd)
        return await self.remote_object(imports, python_cmd, target)

    async def file_contents(self, path, target):
        '''
        Returns the contents of a file

        :param path: File path
        :param target: Unit object or unit name string
        '''
        cmd = 'cat {}'.format(path)
        result = await self.run_command(cmd, target)
        return result['Stdout']
