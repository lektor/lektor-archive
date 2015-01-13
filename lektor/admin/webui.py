from flask import Flask, url_for

from werkzeug.exceptions import NotFound

from lektor.admin.modules import register_modules
from lektor.admin.utils import get_frontend_source, get_record_title


def setup_app(env):
    app = Flask('lektor.admin')
    app.lektor_env = env
    app.config['PROPAGATE_EXCEPTIONS'] = True

    register_modules(app)

    app.jinja_env.globals['get_frontend_source'] = get_frontend_source
    app.jinja_env.filters['recordtitle'] = get_record_title

    app.url_build_error_handlers.append(on_bad_url)

    return app


def on_bad_url(error, endpoint, values):
    """Adds support for source injections to the URL building."""
    if endpoint[:1] != '!':
        return
    source = values.pop('source', None)
    if source is None:
        source = get_frontend_source()
        if source is None:
            return
    if hasattr(source, 'url_path'):
        source = source.url_path
    return '/' + source.lstrip('/') + url_for(endpoint[1:], **values).lstrip('/')


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
