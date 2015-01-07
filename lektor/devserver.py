import os
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
        rv.set_etag('flask-%s-%s-%s' % (
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

    def __init__(self, env, output_path, background_builder=None):
        self.env = env
        self.output_path = output_path
        self.background_builder = background_builder

        # Chached a bit for speed
        self._pad = None

    def get_pad(self):
        rv = self._pad
        if rv is not None:
            return rv
        db = Database(self.env)
        pad = db.new_pad()
        self._pad = pad
        return pad

    def refresh_pad(self):
        self._pad = None

    def handle_request(self, request):
        pad = self.get_pad()
        record = pad.resolve_url_path(request.path)
        if record is None:
            return self.try_serve_asset(request, pad, record)

        builder = self.background_builder.get_builder()

        # First we check if we need to build it.  Only if we need, we
        # actually acquire the builder in exclusive mode.  We also need
        # to match the record here a second time because of concurrency
        # problems.
        if builder.need_to_build_record(record):
            try:
                builder = self.background_builder.acquire_builder()
                record = builder.pad.resolve_url_path(request.path)
                if record is not None:
                    builder.build_record(record)
                self.refresh_pad()
            finally:
                self.background_builder.release_builder(commit=True)

        return send_file(request, builder.get_fs_path(
            builder.get_destination_path(record.url_path)))

    def try_serve_asset(self, request, pad, record):
        try:
            return send_file(request, safe_join(
                self.env.asset_path, request.path.strip('/')))
        except NotFound:
            return send_file(request, safe_join(self.output_path,
                request.path.strip('/')))

    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            response = self.handle_request(request)
        except HTTPException as e:
            response = e
        return response(environ, start_response)


class BuilderGone(Exception):
    pass


class BackgroundBuilder(threading.Thread):

    def __init__(self, env, watcher, output_path):
        threading.Thread.__init__(self)
        self.env = env
        self.watcher = watcher
        self.output_path = output_path

        self._builder = None
        self._builder_mutex = threading.Lock()
        self._exclusive_mutex = threading.Lock()

    def get_builder(self):
        """Returns the builder.  Note that the builder is not in an exclusive
        mode when returned from here.
        """
        rv = self._builder
        if rv is not None:
            return rv
        with self._builder_mutex:
            rv = self._builder
            if rv is not None:
                return rv
            db = Database(self.env)
            pad = db.new_pad()
            rv = Builder(pad, self.output_path)
            self._builder = rv
            return rv

    def acquire_builder(self):
        self._exclusive_mutex.acquire()
        return self.get_builder()

    def release_builder(self, commit=False):
        self._exclusive_mutex.release()
        if commit:
            self.commit()
            return False
        return True

    def commit(self):
        builder = self.acquire_builder()
        try:
            builder.commit()
            self._builder = None
        finally:
            self.release_builder()
        return False

    def build(self):
        try:
            while 1:
                try:
                    self.build_iteration()
                except BuilderGone:
                    continue
                self.commit()
                break
        except Exception:
            traceback.print_exc()

    def build_iteration(self):
        builder = self.get_builder()
        for node, build_func in builder.iter_build_all():
            if build_func is None:
                continue
            builder_gone = False
            builder = self.acquire_builder()
            try:
                build_func()
            finally:
                builder_gone = not self.release_builder()
            if builder_gone:
                raise BuilderGone()

    def run(self):
        self.build()
        for _ in self.watcher:
            self.build()


def run_server(bindaddr, env, output_path):
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    watcher = Watcher(env)
    watcher.observer.start()
    background_builder = BackgroundBuilder(env, watcher, output_path)
    background_builder.setDaemon(True)
    background_builder.start()
    app = WsgiApp(env, output_path, background_builder)
    return run_simple(bindaddr[0], bindaddr[1], app)
