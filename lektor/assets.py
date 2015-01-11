import os
import stat
import shutil
import posixpath


# TODO: add less support and stuff like that.


def get_asset(env, filename, parent=None):
    if env.is_uninteresting_source_name(filename):
        return None

    try:
        st = os.stat(os.path.join(parent.path, filename))
    except OSError:
        return None
    if stat.S_ISDIR(st.st_mode):
        return Directory(env, filename, parent=parent)
    return File(env, filename, parent=parent)


class Asset(object):
    is_directory = False

    def __init__(self, env, name, path=None, parent=None):
        self.env = env
        if parent is not None:
            if path is None:
                path = name
            path = os.path.join(parent.path, path)
        self.path = path
        self.name = name
        self.parent = parent

    @property
    def url_path(self):
        if self.parent is None:
            return '/' + self.name
        return posixpath.join(self.parent.url_path, self.name)

    @property
    def artifact_name(self):
        if self.parent is not None:
            return self.parent.artifact_name.rstrip('/') + '/' + self.name
        return self.url_path

    def build_asset(self, f):
        pass

    @property
    def children(self):
        return iter(())

    def get_child(self, name):
        return None

    def resolve_children(self, path_pieces):
        if not path_pieces:
            return self
        child = self.get_child(path_pieces[0])
        if child:
            return child.resolve_children(path_pieces[1:])

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.artifact_name,
        )


class Directory(Asset):
    is_directory = True

    @property
    def children(self):
        try:
            files = os.listdir(self.path)
        except OSError:
            return

        for filename in files:
            asset = self.get_child(filename)
            if asset is not None:
                yield asset

    def get_child(self, name):
        return get_asset(self.env, name, parent=self)


class File(Asset):

    def build_asset(self, f):
        with open(self.path, 'rb') as sf:
            shutil.copyfileobj(sf, f)
