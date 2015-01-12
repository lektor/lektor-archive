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
