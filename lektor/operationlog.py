import posixpath

from threading import local


_log_local = local()


def get_oplog():
    """Returns the current operation log."""
    try:
        return _log_local.stack[-1]
    except (AttributeError, IndexError):
        return None


class OpLog(object):

    def __init__(self, artifact):
        self.artifact = artifact
        self.source = artifact.source_obj

        self.build_state = self.artifact.build_state
        self.pad = self.build_state.pad

        self.referenced_dependencies = set()
        self.sub_artifacts = []

    @property
    def env(self):
        return self.pad.db.env

    def push(self):
        _log_local.__dict__.setdefault('stack', []).append(self)

    def pop(self):
        _log_local.stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

    def sub_artifact(self, *args, **kwargs):
        """Decorator version of :func:`add_sub_artifact`."""
        def decorator(f):
            self.add_sub_artifact(build_func=f, *args, **kwargs)
            return f
        return decorator

    def add_sub_artifact(self, artifact_name, build_func=None,
                         sources=None, source_obj=None):
        """Sometimes it can happen that while building an artifact another
        artifact needs building.  This function is generally used to record
        this request.
        """
        self.sub_artifacts.append((self.build_state.new_artifact(
            artifact_name=artifact_name,
            sources=sources,
            source_obj=source_obj,
        ), build_func))

    def record_dependency(self, filename):
        # XXX: rename
        self.referenced_dependencies.add(filename)


def get_dependent_url(url_path, suffix):
    url_directory, url_filename = posixpath.split(url_path)
    url_base, url_ext = posixpath.splitext(url_filename)
    return posixpath.join(url_directory, url_base + u'@' + suffix + url_ext)
