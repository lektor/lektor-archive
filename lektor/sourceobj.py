import posixpath

from weakref import ref as weakref
from lektor.environment import PRIMARY_ALT
from lektor.utils import make_relative_url


class SourceObject(object):
    source_classification = 'generic'

    # We consider this class at least what public usage is to considered
    # to be from another place.
    __module__ = 'db'

    def __init__(self, pad):
        self._pad = weakref(pad)

    @property
    def alt(self):
        """Returns the effective alt of this source object (unresolved)."""
        return PRIMARY_ALT

    @property
    def source_filename(self):
        """The primary source filename of this source object."""
        raise NotImplementedError()

    def iter_source_filenames(self):
        yield self.source_filename

    @property
    def url_path(self):
        """The URL path of this source object if available."""
        raise NotImplementedError()

    @property
    def path(self):
        """Return the full path to the source object."""
        return self.url_path.strip('/')

    @property
    def pad(self):
        """The associated pad of this source object."""
        rv = self._pad()
        if rv is not None:
            return rv
        raise AttributeError('The pad went away')

    def resolve_url_path(self, url_path):
        """Given a URL path as list this resolves the most appropriate
        direct child and returns the list of remaining items.  If no
        match can be found, the result is `None`.
        """
        if not url_path:
            return self

    def url_to(self, path, alt=None, absolute=False, external=False):
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.
        """
        if alt is None:
            alt = getattr(path, 'alt', None)
            if alt is None:
                alt = self.alt

        resolve = True
        path = getattr(path, 'url_path', path)
        if path[:1] == '!':
            resolve = False
            path = path[1:]

        if resolve:
            source = self.pad.get(posixpath.join(self.path, path), alt=alt)
            if source is not None:
                path = source.url_path

        if absolute:
            return path
        elif external:
            return self.pad.make_absolute_url(path)
        return make_relative_url(self.url_path, path)
