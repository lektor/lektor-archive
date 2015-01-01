import os
import posixpath

from threading import local


_log_local = local()


def get_oplog():
    """Returns the current operation log."""
    try:
        return _log_local.stack[-1]
    except (AttributeError, IndexError):
        return None


def get_dependent_path(fs_path, url_path, suffix):
    """Calculates a dependent path for a given path."""
    fs_directory, fs_filename = os.path.split(fs_path)
    fs_base, fs_ext = os.path.splitext(fs_filename)
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    fs_rv = os.path.join(fs_directory, fs_base + '@' + str(suffix) + fs_ext)
    url_rv = posixpath.join(url_directory, url_base + u'@' + suffix + url_ext)
    return fs_rv, url_rv


class Operation(object):

    def get_unique_key(self):
        raise NotImplementedError()

    def execute(self, builder):
        pass


class OperationLog(object):

    def __init__(self, pad):
        self.pad = pad
        self.referenced_files = []
        self.operations = {}

    def record_file_usage(self, filename):
        self.referenced_files.append(filename)

    def record_operation(self, operation):
        key = operation.__class__, operation.get_unique_key()
        self.operations[key] = operation

    def iter_operations(self):
        return self.operations.itervalues()

    def push(self):
        _log_local.__dict__.setdefault('stack', []).append(self)

    def pop(self):
        _log_local.stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()
