from flask import Flask

from lektor.admin.modules import register_modules


def setup_app(env, debug=False):
    app = Flask('lektor.admin')
    app.lektor_env = env
    app.debug = debug
    app.config['PROPAGATE_EXCEPTIONS'] = True

    register_modules(app)

    return app


WebAdmin = setup_app
