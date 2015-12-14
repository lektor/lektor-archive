import os
import time
import mimetypes
import posixpath
import traceback
import threading
from StringIO import StringIO
from zlib import adler32

from werkzeug.wrappers import Request, Response
from werkzeug.datastructures import Headers
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import wrap_file, pop_path_info
from werkzeug.utils import append_slash_redirect
from werkzeug.serving import run_simple, WSGIRequestHandler

from lektor.db import Database
from lektor.builder import Builder, process_build_flags
from lektor.watcher import Watcher
from lektor.reporter import CliReporter
from lektor.admin import WebAdmin
from lektor.utils import portable_popen


_os_alt_seps = list(sep for sep in [os.path.sep, os.path.altsep]
                    if sep not in (None, '/'))


class SilentWSGIRequestHandler(WSGIRequestHandler):
    def log(self, type, message, *args):
        pass


def rewrite_html_for_editing(fp, edit_url):
    contents = fp.read()

    button = '''
    <style type="text/css">
      #lektor-edit-link {
        position: fixed;
        z-index: 9999999;
        right: 10px;
        top: 10px;
        position: fixed;
        margin: 0;
        font-family: 'Verdana', sans-serif;
        background: #eee;
        color: #77304c;
        font-weight: normal;
        font-size: 32px;
        padding: 0;
        text-decoration: none!important;
        border: 1px solid #ccc!important;
        width: 40px;
        height: 40px;
        line-height: 40px;
        text-align: center;
        opacity: 0.7;
      }

      #lektor-edit-link:hover {
        background: white!important;
        opacity: 1.0;
        border: 1px solid #aaa!important;
      }
    </style>
    <script type="text/javascript">
      (function() {
        if (window != window.top) {
          return;
        }
        var link = document.createElement('a');
        link.setAttribute('href', '%(edit_url)s?path=' +
            encodeURIComponent(document.location.pathname));
        link.setAttribute('id', 'lektor-edit-link');
        link.innerHTML = '\u270E';
        document.body.appendChild(link);
      })();
    </script>
    ''' % {
        'edit_url': edit_url.encode('utf-8'),
    }

    return StringIO(contents + button)


def send_file(request, filename):
    mimetype = mimetypes.guess_type(filename)[0]
    if mimetype is None:
        mimetype = 'application/octet-stream'

    headers = Headers()

    try:
        file = open(filename, 'rb')
        mtime = os.path.getmtime(filename)
        headers['Content-Length'] = os.path.getsize(filename)
    except (IOError, OSError):
        raise NotFound()

    rewritten = False
    if mimetype == 'text/html':
        rewritten = True
        file = rewrite_html_for_editing(file,
            edit_url=posixpath.join('/', request.script_root, 'admin/edit'))
        del headers['Content-Length']

    headers['Cache-Control'] = 'no-cache, no-store'

    data = wrap_file(request.environ, file)

    rv = Response(data, mimetype=mimetype, headers=headers,
                  direct_passthrough=True)

    if not rewritten:
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
                ) & 0xffffffff,
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

    def __init__(self, env, output_path, verbosity=0, debug=False,
                 ui_lang='en', build_flags=None):
        self.env = env
        self.output_path = output_path
        self.verbosity = verbosity
        self.admin = WebAdmin(env, debug=debug, ui_lang=ui_lang,
                              output_path=output_path,
                              build_flags=build_flags)

    def get_pad(self):
        db = Database(self.env)
        pad = db.new_pad()
        return pad

    def get_builder(self, pad):
        return Builder(pad, self.admin.output_path,
                       build_flags=self.admin.build_flags)

    def refresh_pad(self):
        self._pad = None

    def handle_request(self, request):
        pad = self.get_pad()
        filename = None

        # We start with trying to resolve a source and then use the
        # primary
        source = pad.resolve_url_path(request.path)
        if source is not None:
            # If the request path does not end with a slash but we
            # requested a URL that actually wants a trailing slash, we
            # append it.  This is consistent with what apache and nginx do
            # and it ensures our relative urls work.
            if not request.path.endswith('/') and \
               source.url_path != '/' and \
               source.url_path.endswith('/'):
                return append_slash_redirect(request.environ)

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

        # Dispatch to the web admin if we need.
        if request.path.rstrip('/').startswith('/admin'):
            pop_path_info(environ)
            return self.admin(environ, start_response)

        try:
            response = self.handle_request(request)
        except HTTPException as e:
            response = e
        return response(environ, start_response)


class BackgroundBuilder(threading.Thread):

    def __init__(self, env, output_path, verbosity=0, build_flags=None):
        threading.Thread.__init__(self)
        watcher = Watcher(env, output_path)
        watcher.observer.start()
        self.env = env
        self.watcher = watcher
        self.output_path = output_path
        self.verbosity = verbosity
        self.last_build = time.time()
        self.build_flags = build_flags

    def build(self, update_source_info_first=False):
        try:
            db = Database(self.env)
            builder = Builder(db.new_pad(), self.output_path,
                              build_flags=self.build_flags)
            if update_source_info_first:
                builder.update_all_source_infos()
            builder.build_all()
            builder.prune()
        except Exception:
            traceback.print_exc()
        else:
            self.last_build = time.time()

    def run(self):
        with CliReporter(self.env, verbosity=self.verbosity):
            self.build(update_source_info_first=True)
            for ts, _, _ in self.watcher:
                if self.last_build is None or ts > self.last_build:
                    self.build()


class DevTools(object):
    """This provides extra helpers for launching tools such as webpack."""

    def __init__(self, env):
        self.watcher = None
        self.env = env

    def start(self):
        if self.watcher is not None:
            return
        from lektor import admin
        admin = os.path.dirname(admin.__file__)
        portable_popen(['npm', 'install', '.'], cwd=admin).wait()

        self.watcher = portable_popen([os.path.join(
            admin, 'node_modules/.bin/webpack'), '--watch'],
            cwd=os.path.join(admin, 'static'))

    def stop(self):
        if self.watcher is None:
            return
        self.watcher.kill()
        self.watcher.wait()
        self.watcher = None


def browse_to_address(addr):
    import webbrowser
    def browse():
        time.sleep(1)
        webbrowser.open('http://%s:%s' % addr)
    t = threading.Thread(target=browse)
    t.setDaemon(True)
    t.start()


def run_server(bindaddr, env, output_path, verbosity=0, lektor_dev=False,
               ui_lang='en', browse=False, build_flags=None):
    """This runs a server but also spawns a background process.  It's
    not safe to call this more than once per python process!
    """
    wz_as_main = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    in_main_process = not lektor_dev or wz_as_main
    build_flags = process_build_flags(build_flags)

    if in_main_process:
        background_builder = BackgroundBuilder(env, output_path, verbosity,
                                               build_flags)
        background_builder.setDaemon(True)
        background_builder.start()
        env.plugin_controller.emit('server-spawn', bindaddr=bindaddr,
                                   build_flags=build_flags)

    app = WsgiApp(env, output_path, verbosity, debug=lektor_dev,
                  ui_lang=ui_lang, build_flags=build_flags)

    dt = None
    if lektor_dev and not wz_as_main:
        dt = DevTools(env)
        dt.start()

    if browse:
        browse_to_address(bindaddr)

    try:
        return run_simple(bindaddr[0], bindaddr[1], app,
                          use_debugger=True, threaded=True,
                          use_reloader=lektor_dev,
                          request_handler=not lektor_dev
                          and SilentWSGIRequestHandler or WSGIRequestHandler)
    finally:
        if dt is not None:
            dt.stop()
        if in_main_process:
            env.plugin_controller.emit('server-stop')
