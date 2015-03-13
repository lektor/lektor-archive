import os
import time
import mimetypes
import posixpath
import traceback
import threading
from zlib import adler32

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import wrap_file

from lektor.db import Database
from lektor.builder import Builder
from lektor.watcher import Watcher
from lektor.reporter import CliReporter
from lektor.admin import WebAdmin


_os_alt_seps = list(sep for sep in [os.path.sep, os.path.altsep]
                    if sep not in (None, '/'))


def send_file(request, filename):
    mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    headers = Headers()

    try:
        file = open(filename, 'rb')
        mtime = os.path.getmtime(filename)
        headers['Content-Length'] = os.path.getsize(filename)
        data = wrap_file(request.environ, file)
    except (IOError, OSError):
        raise NotFound()

    rv = Response(data, mimetype=mimetype, headers=headers,
                  direct_passthrough=True)

    # if we know the file modification date, we can store it as
    # the time of the last modification.
    if mtime is not None:
        rv.last_modified = int(mtime)

    rv.cache_control.public = True

    try:
        rv.set_etag('lektor-%s-%s-%s' % (
            os.path.getmtime(filename),
            os.path.getsize(filename),
            adler32(
                filename.encode('utf-8') if isinstance(filename, basestring)
                else filename
            ) & 0xffffffff
        ))
    except OSError:
        pass

    return rv


def safe_join(directory, filename):
    filename = posixpath.normpath(filename)
    for sep in _os_alt_seps:
        if sep in filename:
            raise NotFound()
    if os.path.isabs(filename) or \
       filename == '..' or \
       filename.startswith('../'):
        raise NotFound()
    return os.path.join(directory, filename)


class WsgiApp(object):

    def __init__(self, env, output_path, verbosity=0):
        self.admin = WebAdmin(env)
        self.env = env
        self.output_path = output_path
        self.verbosity = verbosity

    def get_pad(self):
        db = Database(self.env)
        pad = db.new_pad()
        return pad

    def get_builder(self, pad):
        return Builder(pad, self.output_path)

    def refresh_pad(self):
        self._pad = None

    def handle_request(self, request):
        pad = self.get_pad()
        filename = None

        # A bang in the URL path requests something from the admin panel.
        if '!' in request.path:
            return self.admin

        # We start with trying to resolve a source and then use the
        # primary
        source = pad.resolve_url_path(request.path)
        if source is not None:
            with CliReporter(self.env, verbosity=self.verbosity):
                builder = self.get_builder(pad)
                prog = builder.build(source)

            artifact = prog.primary_artifact
            if artifact is not None:
                filename = artifact.dst_filename

        # If there is no primary artifact or the url does not point to a
        # known artifact at all, then we just look directly into the
        # output directory and serve from there.  This will for instance
        # pick up thumbnails.
        if filename is None:
            filename = os.path.join(self.output_path, request.path.strip('/'))

        return send_file(request, filename)

    def __call__(self, environ, start_response):
        request = Request(environ, shallow=True)
        try:
            response = self.handle_request(request)
        except HTTPException as e:
            response = e
        return response(environ, start_response)


class BackgroundBuilder(threading.Thread):

    def __init__(self, env, output_path, verbosity=0):
        threading.Thread.__init__(self)
        watcher = Watcher(env, output_path)
        watcher.observer.start()
        self.env = env
        self.watcher = watcher
        self.output_path = output_path
        self.verbosity = verbosity
        self.last_build = time.time()

    def build(self):
        try:
            db = Database(self.env)
            builder = Builder(db.new_pad(), self.output_path)
            builder.build_all()
        except Exception:
            traceback.print_exc()
        else:
            self.last_build = time.time()

    def run(self):
        with CliReporter(self.env, verbosity=self.verbosity):
            self.build()
            for ts, _, _ in self.watcher:
                if self.last_build is None or ts > self.last_build:
                    self.build()


def run_server(bindaddr, env, output_path, verbosity=0):
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    background_builder = BackgroundBuilder(env, output_path, verbosity)
    background_builder.setDaemon(True)
    background_builder.start()
    app = WsgiApp(env, output_path, verbosity)
    return run_simple(bindaddr[0], bindaddr[1], app,
                      use_debugger=True, threaded=True)
