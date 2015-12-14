from flask import Flask

from lektor.db import Database
from lektor.builder import Builder
from lektor.admin.modules import register_modules


class LektorInfo(object):

    def __init__(self, env, output_path, ui_lang='en', build_flags=None):
        self.env = env
        self.ui_lang = ui_lang
        self.output_path = output_path
        self.build_flags = build_flags

    def get_pad(self):
        return Database(self.env).new_pad()

    def get_builder(self):
        return Builder(self.get_pad(), self.output_path,
                       build_flags=self.build_flags)


def setup_app(env, debug=False, output_path=None, ui_lang='en',
              build_flags=None):
    app = Flask('lektor.admin')
    app.lektor_info = LektorInfo(env, output_path, ui_lang,
                                 build_flags=build_flags)
    app.debug = debug
    app.config['PROPAGATE_EXCEPTIONS'] = True

    register_modules(app)

    return app


WebAdmin = setup_app
