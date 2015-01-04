import posixpath

from threading import local

from lektor.utils import WorkerPool, safe_call


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


class Result(object):

    def __init__(self, dst_filename, produce_func, concurrent=False):
        self.dst_filename = dst_filename
        self.produce_func = produce_func
        self.concurrent = concurrent


class OperationLog(object):

    def __init__(self, pad):
        self.pad = pad
        self.referenced_paths = set()
        self.referenced_folders = set()
        self.produced_artifacts = set()
        self.operations = {}

    @property
    def env(self):
        return self.pad.db.env

    def record_path_usage(self, filename):
        self.referenced_paths.add(filename)

    def record_operation(self, operation):
        key = operation.__class__, operation.get_unique_key()
        self.operations[key] = operation

    def record_artifact(self, filename):
        self.produced_artifacts.add(filename)

    def iter_operations(self):
        return self.operations.itervalues()

    def execute_pending_operations(self, builder):
        concurrent_ops = []
        for op in self.iter_operations():
            for result in op.execute(builder, self) or ():
                self.record_artifact(result.dst_filename)
                if result.concurrent:
                    concurrent_ops.append(result.produce_func)
                else:
                    safe_call(result.produce_func)

        if concurrent_ops:
            if len(concurrent_ops) > 1:
                pool = WorkerPool()
                for op in concurrent_ops:
                    pool.add_task(op)
                pool.wait_for_completion()
            else:
                safe_call(concurrent_ops[0])

    def push(self):
        _log_local.__dict__.setdefault('stack', []).append(self)

    def pop(self):
        _log_local.stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()
