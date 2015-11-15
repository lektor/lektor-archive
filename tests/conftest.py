import os
import pytest
import shutil
import tempfile


@pytest.fixture(scope='function')
def project(request):
    from lektor.project import load_project
    return load_project(os.path.join(os.path.dirname(__file__),
                                     'demo-project'))


@pytest.fixture(scope='function')
def env(request, project):
    from lektor.environment import Environment
    return Environment(project)


@pytest.fixture(scope='function')
def pad(request, env):
    from lektor.db import Database
    return Database(env).new_pad()


@pytest.fixture(scope='function')
def builder(request, pad):
    from lektor.builder import Builder
    out = tempfile.mkdtemp()
    builder = Builder(pad, out)
    def cleanup():
        try:
            shutil.rmtree(out)
        except (OSError, IOError):
            pass
    request.addfinalizer(cleanup)
    return builder
