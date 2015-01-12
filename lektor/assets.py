import os
import stat
import posixpath

from lektor.sourceobj import SourceObject


special_file_assets = {}
file_component_suffixes = set()


def get_asset(pad, filename, parent=None):
    env = pad.db.env

    if env.is_uninteresting_source_name(filename):
        return None

    try:
        st = os.stat(os.path.join(parent.source_filename, filename))
    except OSError:
        return None
    if stat.S_ISDIR(st.st_mode):
        return Directory(pad, filename, parent=parent)

    ext = os.path.splitext(filename)[1]
    cls = special_file_assets.get(ext, File)
    return cls(pad, filename, parent=parent)


def special_file_asset(extension):
    def decorator(cls):
        special_file_assets[extension] = cls
        if cls.artifact_suffix:
            file_component_suffixes.add(cls.artifact_suffix)
        return cls
    return decorator


class Asset(SourceObject):
    # source specific overrides.  the source_filename to none removes
    # the inherited descriptor.
    source_classification = 'asset'
    source_filename = None

    artifact_suffix = ''

    def __init__(self, pad, name, path=None, parent=None):
        SourceObject.__init__(self, pad)
        if parent is not None:
            if path is None:
                path = name
            path = os.path.join(parent.source_filename, path)
        self.source_filename = path

        self.name = name
        self.parent = parent

    @property
    def url_name(self):
        # If the name starts with an underscore it's corrected into a
        # dash.  This can only ever happen for files like _htaccess and
        # friends which are explicitly whitelisted in the environment as
        # all other files with leading underscores are ignored.
        name = self.name
        if name[:1] == '_':
            name = '.' + name[1:]
        return name + self.artifact_suffix

    @property
    def url_path(self):
        if self.parent is None:
            return '/' + self.name
        return posixpath.join(self.parent.url_path, self.url_name)

    @property
    def artifact_name(self):
        if self.parent is not None:
            return self.parent.artifact_name.rstrip('/') + '/' + self.url_name
        return self.url_path

    def build_asset(self, f):
        pass

    @property
    def children(self):
        return iter(())

    def get_child(self, name, from_url=False):
        return None

    def resolve_url_path(self, url_path):
        if not url_path:
            return self
        child = self.get_child(url_path[0], from_url=True)
        if child is not None:
            return child.resolve_url_path(url_path[1:])

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.artifact_name,
        )


class Directory(Asset):
    """Represents an asset directory."""

    @property
    def children(self):
        try:
            files = os.listdir(self.source_filename)
        except OSError:
            return

        for filename in files:
            asset = self.get_child(filename)
            if asset is not None:
                yield asset

    def get_child(self, name, from_url=False):
        rv = get_asset(self.pad, name, parent=self)
        if rv is not None or not from_url:
            return rv

        # This this point it means we did not find a child yet, but we
        # came from an URL.  We can try to chop of suffixes to find the
        # original source asset.
        for suffix in file_component_suffixes:
            if name.endswith(suffix):
                rv = get_asset(self.pad, name[:-len(suffix)], parent=self)
                if rv is not None:
                    return rv


class File(Asset):
    """Represents a static asset file."""


@special_file_asset('.less')
class LessFile(Asset):
    """Represents a less asset that needs converting into css."""
    artifact_suffix = '.css'
