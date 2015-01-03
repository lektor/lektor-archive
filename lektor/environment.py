import os

import jinja2

from lektor.operationlog import get_oplog
from lektor.db import R


DEFAULT_CONFIG = {
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
    }
}


class CustomJinjaEnvironment(jinja2.Environment):

    def _load_template(self, name, globals):
        rv = jinja2.Environment._load_template(self, name, globals)
        oplog = get_oplog()
        if oplog is not None:
            oplog.record_path_usage(rv.filename)
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

        self.jinja_env.globals['R'] = R

    @property
    def asset_path(self):
        return os.path.join(self.root_path, 'assets')

    def is_uninteresting_filename(self, filename):
        # XXX: add more stuff here?
        return filename[:1] in '._' or (
            filename.lower() in ('thumbs.db', 'desktop.ini'))

    def get_template(self, name):
        return self.jinja_env.get_template(name)

    def compile_template(self, string):
        return self.jinja_env.from_string(string)

    def select_jinja_autoescape(self, filename):
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))
