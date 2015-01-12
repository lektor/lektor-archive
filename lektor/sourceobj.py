import posixpath

from weakref import ref as weakref


class SourceObject(object):
    source_classification = 'generic'

    def __init__(self, pad):
        self._pad = weakref(pad)

    @property
    def source_filename(self):
        """The primary source filename of this source object."""
        raise NotImplementedError()

    @property
    def url_path(self):
        """The URL path of this source object if available."""
        raise NotImplementedError()

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

    def url_to(self, path):
        """Calculates the URL from the current source object to the given
        other source object.  Alternatively a path can also be provided
        instead of a source object.  If the path starts with a leading
        bang (``!``) then no resolving is performed.
        """
        resolve = True
        if hasattr(path, 'url_path'):
            path = path.url_path
        elif path[:1] == '!':
            resolve = False

        this = self.url_path
        if this == '/':
            depth = 0
            prefix = './'
        else:
            depth = ('/' + this.strip('/')).count('/')
            prefix = ''

        path = posixpath.join(this, path)

        if resolve:
            source = self.pad.get(path, all_sources=True)
            if source is not None:
                path = source.url_path

        return (prefix + '../' * depth).rstrip('/') + path
