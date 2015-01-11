import os

import jinja2

from lektor.operationlog import get_oplog
from lektor.utils import tojson_filter


DEFAULT_CONFIG = {
    'IMAGEMAGICK_PATH': None,
    'EPHEMERAL_RECORD_CACHE_SIZE': 500,
    'ATTACHMENT_TYPES': {
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.gif': 'image',
        '.tif': 'image',
        '.tiff': 'image',
        '.bmp': 'image',

        '.avi': 'video',
        '.mpg': 'video',
        '.mpeg': 'video',
        '.wmv': 'video',
        '.ogv': 'video',

        '.mp3': 'audio',
        '.wav': 'audio',
        '.ogg': 'audio',

        '.pdf': 'document',
        '.doc': 'document',
        '.docx': 'document',

        '.txt': 'text',
    },
}

# Special files that should always be ignored.
IGNORED_FILES = ['thumbs.db', 'desktop.ini']

# These files are important for artifacts and must not be ignored when
# they are built even though they start with dots.
SPECIAL_SOURCES = ['_htaccess', '_htpasswd']
SPECIAL_ARTIFACTS = ['.htaccess', '.htpasswd']


class Expression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string('{{ __result__(%s) }}' % expr)

    def evaluate(self, pad, this=None, values=None):
        result = []
        def result_func(value):
            result.append(value)
            return u''
        values = self.env.make_default_tmpl_values(pad, this, values)
        values['__result__'] = result_func
        self.tmpl.render(values)
        return result[0]


class FormatExpression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string(expr)

    def evaluate(self, pad, this=None, values=None):
        values = self.env.make_default_tmpl_values(pad, this, values)
        return self.tmpl.render(values)


class CustomJinjaEnvironment(jinja2.Environment):

    def _load_template(self, name, globals):
        rv = jinja2.Environment._load_template(self, name, globals)
        oplog = get_oplog()
        if oplog is not None:
            oplog.record_dependency(rv.filename)
        return rv


class Environment(object):

    def __init__(self, root_path, config=None):
        self.root_path = os.path.abspath(root_path)
        if config is None:
            config = DEFAULT_CONFIG.copy()
        self.config = config
        self.jinja_env = CustomJinjaEnvironment(
            autoescape=self.select_jinja_autoescape,
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
            loader=jinja2.FileSystemLoader(
                os.path.join(self.root_path, 'templates'))
        )

        from lektor.db import F
        self.jinja_env.filters['tojson'] = tojson_filter
        self.jinja_env.globals['F'] = F

    @property
    def asset_path(self):
        return os.path.join(self.root_path, 'assets')

    def is_uninteresting_source_name(self, filename):
        """These files are always ignored when sources are built into
        artifacts.
        """
        fn = filename.lower()
        if fn in SPECIAL_ARTIFACTS or fn in SPECIAL_SOURCES:
            return False
        return filename[:1] in '._' or fn in IGNORED_FILES

    def is_ignored_artifact(self, asset_name):
        """This is used by the prune tool to figure out which files in the
        artifact folder should be ignored.  This is a bi
        """
        fn = asset_name.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False
        return fn[:1] in '._' or fn in IGNORED_FILES

    def render_template(self, name, pad, this=None, values=None):
        ctx = self.make_default_tmpl_values(pad, this, values)
        return self.jinja_env.get_or_select_template(name).render(ctx)

    def make_default_tmpl_values(self, pad, this=None, values=None):
        values = dict(values or ())
        values['site'] = pad
        if this is not None:
            values['this'] = this
        return values

    def select_jinja_autoescape(self, filename):
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))
