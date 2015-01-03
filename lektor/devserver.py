import os
import mimetypes
import posixpath
from zlib import adler32

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import wrap_file

from lektor.db import Database
from lektor.builder import Builder


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

    def __init__(self, env, output_path):
        self.env = env
        self.output_path = output_path

    def handle_request(self, request):
        db = Database(self.env)
        pad = db.new_pad()
        record = pad.resolve_url_path(request.path)
        if record is None:
            return self.try_serve_asset(request, pad, record)
        return self.serve_record(request, pad, record)

    def serve_record(self, request, pad, record):
        builder = Builder(pad, self.output_path)
        builder.build_record(record)
        builder.finalize()
        fn = builder.get_fs_path(builder.get_destination_path(record.url_path))
        return send_file(request, fn)

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


def run_server(bindaddr, env, output_path):
    app = WsgiApp(env, output_path)
    return run_simple(bindaddr[0], bindaddr[1], app)
