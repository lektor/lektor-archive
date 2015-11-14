import pkg_resources
from werkzeug.utils import find_modules, import_string


class Plugin(object):
    """This needs to be subclassed for custom plugins."""
    name = 'Your Plugin Name'
    description = 'Description goes here'

    def setup_env(self, env):
        """Callback method for when the env is initialized."""


def iter_builtin_plugins():
    """Iterates over all built-in plugins that exist in Lektor."""
    for module in find_modules('lektor.plugins', include_packages=True):
        mod = import_string(module)
        for key, value in mod.__dict__.iteritems():
            try:
                if key[:1] != '_' and value is not Plugin and \
                   issubclass(value, Plugin):
                    yield module + '.' + key, value
            except TypeError:
                pass


def load_plugins():
    """Loads all available plugins and returns them."""
    rv = {}
    for ep in pkg_resources.iter_entry_points('lektor.plugins'):
        rv[ep.name] = ep.load()
    rv.update(iter_builtin_plugins())
    return rv


def initialize_plugins(env):
    """Initializes the plugins for the environment."""
    plugins = load_plugins()
    for plugin_name, plugin_cls in plugins.iteritems():
        env.plugins[plugin_name] = plugin_cls()
    for plugin in env.plugins.itervalues():
        plugin.setup_env(env)
