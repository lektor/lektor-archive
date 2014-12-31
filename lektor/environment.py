import os

import jinja2


DEFAULT_CONFIG = {
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
