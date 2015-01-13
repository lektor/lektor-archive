from flask import Flask, g, abort

from werkzeug.exceptions import NotFound

from lektor.admin.modules import register_modules
from lektor.admin.utils import get_frontend_source, action_url


def on_before_request():
    g.source = get_frontend_source()
    if g.source is None:
        abort(404)


def setup_app(env):
    app = Flask('lektor.admin')
    app.lektor_env = env
    app.config['PROPAGATE_EXCEPTIONS'] = True

    app.before_request(on_before_request)

    app.jinja_env.globals['action_url'] = action_url

    register_modules(app)

    return app


class WebAdmin(object):

    def __init__(self, env):
        self.env = env
        self.app = setup_app(env)

    def wsgi_app(self, environ, start_response):
        path_info = environ.get('PATH_INFO') or ''
        if '!' not in path_info:
            resp = NotFound()
        else:
            prefix, path = path_info.split('!', 1)
            script_name = (environ.get('SCRIPT_NAME') or '')
            environ['lektor.frontend_path'] = prefix
            environ['PATH_INFO'] = path
            environ['SCRIPT_NAME'] = script_name.rstrip('/') + '/!'
            resp = self.app

        return resp(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)
