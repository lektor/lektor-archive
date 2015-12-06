import os
import sys
import pkg_resources

from weakref import ref as weakref
from inifile import IniFile
from werkzeug.utils import find_modules, import_string

from lektor.context import get_ctx


class Plugin(object):
    """This needs to be subclassed for custom plugins."""
    name = 'Your Plugin Name'
    description = 'Description goes here'

    def __init__(self, env, id):
        self._env = weakref(env)
        self.id = id

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError('Environment went away')
        return rv

    @property
    def path(self):
        mod = sys.modules[self.__class__.__module__.split('.')[0]]
        return os.path.abspath(os.path.dirname(mod.__file__))

    @property
    def import_name(self):
        return self.__class__.__module__ + ':' + self.__class__.__name__

    def get_lektor_config(self):
        """Returns the global config."""
        ctx = get_ctx()
        if ctx is not None:
            cfg = ctx.pad.db.config
        else:
            cfg = self.env.load_config()
        return cfg

    @property
    def config_filename(self):
        """The filename of the plugin specific config file."""
        return os.path.join(self.env.root_path, 'configs', self.id + '.ini')

    def get_config(self, fresh=False):
        """Returns the config specific for this plugin.  By default this
        will be cached for the current build context but this can be
        disabled by passing ``fresh=True``.
        """
        ctx = get_ctx()
        if ctx is not None and not fresh:
            cache = ctx.cache.setdefault(__name__ + ':configs', {})
            cfg = cache.get(self.id)
            if cfg is None:
                cfg = IniFile(self.config_filename)
                cache[self.id] = cfg
        else:
            cfg = IniFile(self.config_filename)
        if ctx is not None:
            ctx.record_dependency(self.config_filename)
        return cfg

    def emit(self, event, **kwargs):
        return self.env.pluginsystem.emit(self.id + '-' + event, **kwargs)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'path': self.path,
            'import_name': self.import_name,
        }


def iter_builtin_plugins():
    """Iterates over all built-in plugins that exist in Lektor."""
    for module in find_modules('lektor.plugins', include_packages=True):
        mod = import_string(module)
        for key, value in mod.__dict__.iteritems():
            try:
                if key[:1] != '_' and value is not Plugin and \
                   issubclass(value, Plugin):
                    yield 'core-' + module.split('.')[-1], value
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
    for plugin_id, plugin_cls in plugins.iteritems():
        env.plugin_controller.instanciate_plugin(plugin_id, plugin_cls)
    env.plugin_controller.emit('setup-env')


class PluginController(object):
    """Helper management class that is used to control plugins through
    the environment.
    """

    def __init__(self, env):
        self._env = weakref(env)

    @property
    def env(self):
        rv = self._env()
        if rv is None:
            raise RuntimeError('Environment went away')
        return rv

    def instanciate_plugin(self, plugin_id, plugin_cls):
        env = self.env
        if plugin_id in env.plugins:
            raise RuntimeError('Plugin "%s" is already registered'
                               % plugin_id)
        env.plugins[plugin_id] = plugin_cls(env, plugin_id)

    def iter_plugins(self):
        # XXX: sort?
        return self.env.plugins.itervalues()

    def emit(self, event, **kwargs):
        rv = {}
        funcname = 'on_' + event.replace('-', '_')
        for plugin in self.iter_plugins():
            handler = getattr(plugin, funcname, None)
            if handler is not None:
                rv[plugin.id] = handler(**kwargs)
        return rv
