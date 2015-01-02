import posixpath

from threading import local


_log_local = local()


def get_oplog():
    """Returns the current operation log."""
    try:
        return _log_local.stack[-1]
    except (AttributeError, IndexError):
        return None


def get_dependent_url(url_path, suffix):
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    return posixpath.join(url_directory, url_base + u'@' + suffix + url_ext)


class Operation(object):

    def get_unique_key(self):
        raise NotImplementedError()

    def execute(self, builder):
        pass


class OperationLog(object):

    def __init__(self, pad):
        self.pad = pad
        self.referenced_paths = set()
        self.referenced_folders = set()
        self.operations = {}

    def record_path_usage(self, filename):
        self.referenced_paths.add(filename)

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
