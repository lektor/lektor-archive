import os

import jinja2


DEFAULT_CONFIG = {
}


class Environment(object):

    def __init__(self, root_path, config=None):
        self.root_path = os.path.abspath(root_path)
        if config is None:
            config = DEFAULT_CONFIG.copy()
        self.config = config
        self.jinja_env = jinja2.Environment(
            autoescape=self.select_jinja_autoescape,
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
        )

    def select_jinja_autoescape(self, filename):
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))
