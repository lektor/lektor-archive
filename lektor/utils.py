import os
import sys
import re
import json
import codecs
import uuid
import subprocess
import tempfile
import posixpath
import traceback
import unicodedata
import multiprocessing
from Queue import Queue
from threading import Thread
from datetime import datetime
from contextlib import contextmanager

from urlparse import urlparse

from werkzeug.http import http_date
from werkzeug.posixemulation import rename
from jinja2 import is_undefined
from markupsafe import Markup


#is_windows = sys.platform.startswith('win')
is_windows = (os.name == 'nt')

_slash_escape = '\\/' not in json.dumps('/')

_slashes_re = re.compile(r'/+')

# Figure out our fs encoding, if it's ascii we upgrade to utf-8
fs_enc = sys.getfilesystemencoding()
try:
    if codecs.lookup(fs_enc).name == 'ascii':
        fs_enc = 'utf-8'
except LookupError:
    pass

def cleanup_path(path):
    return '/' + _slashes_re.sub('/', path.strip('/'))

def to_os_path(path):
    return path.strip('/').replace('/', os.path.sep).decode(fs_enc, 'replace')

#def resolve_path(execute_file, cwd=None): 
#    if (os.name != 'nt'):
#        return execute_file
#    extensions = ['']
#    execute_file = to_os_path(execute_file)
    
#    path_var = os.environ.get('PATH', '').split(os.pathsep)
#    path_ext_var = os.environ.get('PATHEXT', '').split(';')
    
#    ext_existing = os.path.splitext(execute_file)[1] in path_ext_var
#    if not ext_existing:
#        extensions = path_ext_var

#    try:
#        for ext in extensions:
#            if cwd:
#                execute = os.path.join(cwd, execute_file + ext)
#                if os.access(execute, os.X_OK):
#                    return execute
#            else:
#                for path in path_var:
#                    execute = os.path.join(path, execute_file + ext)
#                    if os.access(execute, os.X_OK):
#                        return execute
#    except OSError:
#        pass
            
#    return None


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        if is_undefined(o):
            return None
        if isinstance(o, datetime):
            return http_date(o)
        if isinstance(o, uuid.UUID):
            return str(o)
        if hasattr(o, '__html__'):
            return unicode(o.__html__())
        return json.JSONEncoder.default(self, o)


def htmlsafe_json_dump(obj, **kwargs):
    kwargs.setdefault('cls', JSONEncoder)
    rv = json.dumps(obj, **kwargs) \
        .replace(u'<', u'\\u003c') \
        .replace(u'>', u'\\u003e') \
        .replace(u'&', u'\\u0026') \
        .replace(u"'", u'\\u0027')
    if not _slash_escape:
        rv = rv.replace('\\/', '/')
    return rv


def tojson_filter(obj, **kwargs):
    return Markup(htmlsafe_json_dump(obj, **kwargs))


def safe_call(func, args=None, kwargs=None):
    try:
        return func(*(args or ()), **(kwargs or {}))
    except Exception:
        # XXX: logging
        traceback.print_exc()


class Worker(Thread):

    def __init__(self, tasks):
        Thread.__init__(self)
        self.tasks = tasks
        self.daemon = True
        self.start()

    def run(self):
        while 1:
            func, args, kwargs = self.tasks.get()
            safe_call(func, args, kwargs)
            self.tasks.task_done()


class WorkerPool(object):

    def __init__(self, num_threads=None):
        if num_threads is None:
            num_threads = multiprocessing.cpu_count()
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            Worker(self.tasks)

    def add_task(self, func, *args, **kargs):
        self.tasks.put((func, args, kargs))

    def wait_for_completion(self):
        self.tasks.join()


def slugify(value):
    # XXX: not good enough
    return u'-'.join(value.strip().split()).lower()


class Url(object):

    def __init__(self, value):
        self.url = value
        self.host = urlparse(value).netloc

    def __unicode__(self):
        return self.url

    def __str__(self):
        return self.url


def is_unsafe_to_delete(path, base):
    a = os.path.abspath(path)
    b = os.path.abspath(base)
    diff = os.path.relpath(a, b)
    first = diff.split(os.path.sep)[0]
    return first in (os.path.curdir, os.path.pardir)


def prune_file_and_folder(name, base):
    if is_unsafe_to_delete(name, base):
        return False
    try:
        os.remove(name)
    except OSError:
        try:
            os.rmdir(name)
        except OSError:
            return False
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    while head and tail:
        try:
            if is_unsafe_to_delete(head, base):
                return False
            os.rmdir(head)
        except OSError:
            break
        head, tail = os.path.split(head)
    return True


def sort_normalize_string(s):
    return unicodedata.normalize('NFD', unicode(s).lower().strip())


def get_dependent_url(url_path, suffix, ext=None):
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    if ext is None:
        ext = url_ext
    return posixpath.join(url_directory, url_base + u'@' + suffix + ext)


@contextmanager
def atomic_open(filename, mode='r'):
    if 'r' not in mode:
        fd, tmp_filename = tempfile.mkstemp(
            dir=os.path.dirname(filename), prefix='.__atomic-write')
        f = os.fdopen(fd, mode)
    else:
        f = open(filename, mode)
        tmp_filename = None
    try:
        yield f
    except:
        f.close()
        exc_type, exc_value, tb = sys.exc_info()
        if tmp_filename is not None:
            try:
                os.remove(tmp_filename)
            except OSError:
                pass
        raise exc_type, exc_value, tb
    else:
        f.close()
        if tmp_filename is not None:
            rename(tmp_filename, filename)
            
def portable_popen(cmd, *args, **kwargs):
    cmd[0] = to_os_path(cmd[0])
    if(os.name == 'nt'):
        return subprocess.Popen(cmd, *args, shell=True, **kwargs)
    else:
        return subprocess.Popen(cmd, *args, **kwargs)


