from threading import local


_log_local = local()


def get_oplog():
    """Returns the current operation log."""
    try:
        return _log_local.stack[-1]
    except (AttributeError, IndexError):
        return None


class OperationLog(object):

    def __init__(self, record):
        self.record = record

    def push(self):
        _log_local.__dict__.setdefault('stack', []).append(self)

    def pop(self):
        _log_local.stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()
