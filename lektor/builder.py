import os
import stat
import errno
import shutil
import hashlib

from lektor.utils import atomic_open
from lektor.operationlog import OperationLog
from lektor.db import Page, Attachment


# TODO: paths do not get deleted properly, This also cause constant
# rebuilds


class _Tree(object):

    def __init__(self, env):
        self.env = env
        self.root_path = os.path.abspath(env.root_path)

    def abbreviate_filename(self, filename):
        filename = os.path.join(self.root_path, filename)
        if self.root_path is not None and filename.startswith(self.root_path):
            filename = filename[len(self.root_path):].lstrip(os.path.sep)
            if os.path.altsep:
                filename = filename.lstrip(os.path.altsep)
        return filename


class SourceTree(_Tree):
    """The source tree remembers the state of the paths they had last time
    the were processed.
    """

    def __init__(self, env=None):
        _Tree.__init__(self, env)
        self.paths = {}
        self._newly_added = set()

    def _get_path_meta(self, filename):
        p = os.path.join(self.root_path, filename)
        try:
            st = os.stat(p)
            mtime = int(st.st_mtime)
            if stat.S_ISDIR(st.st_mode):
                size = len(os.listdir(p))
            else:
                size = int(st.st_size)
            return mtime, size
        except OSError:
            pass

    def _get_path_checksum(self, filename):
        p = os.path.join(self.root_path, filename)
        try:
            h = hashlib.sha1()
            if os.path.isdir(p):
                for filename in sorted(os.listdir(p)):
                    if self.env.is_uninteresting_filename(filename):
                        continue
                    if isinstance(filename, unicode):
                        filename = filename.encode('utf-8')
                    h.update(filename + '|')
            else:
                with open(p, 'rb') as f:
                    while 1:
                        chunk = f.read(16 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
            return h.hexdigest()
        except IOError:
            pass

    def dump(self, filename):
        """Dumps the source tree into a file."""
        with atomic_open(filename) as f:
            for filename, tup in sorted(self.paths.items()):
                mtime, size, checksum = tup
                f.write('%s\n' % u'\t'.join((
                    filename,
                    unicode(mtime),
                    unicode(size),
                    checksum,
                )).encode('utf-8'))

    @classmethod
    def load(cls, filename, root_path=None, create_empty=False):
        rv = cls(root_path)
        try:
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.strip().split('\t')
                    if len(line) != 4:
                        continue
                    filename, mtime, size, checksum = line
                    try:
                        rv.paths[filename.decode('utf-8')] = \
                            (int(mtime), int(size), checksum)
                    except ValueError:
                        continue
        except IOError as e:
            if e.errno != errno.ENOENT or not create_empty:
                raise
        return rv

    def add_path(self, filename):
        """Adds a path to the source tree."""
        tup = self._get_path_meta(filename)
        if tup is None:
            return False
        checksum = self._get_path_checksum(filename)
        if checksum is None:
            return False
        filename = self.abbreviate_filename(filename)
        if filename in self._newly_added:
            return True
        self.paths[filename] = tup + (checksum,)
        return True

    def remove_path(self, filename):
        """Removes a path from the source tree again."""
        filename = self.abbreviate_filename(filename)
        tup = self.paths.pop(filename, None)
        return tup is not None

    def is_current(self, filename):
        """Checks if a filename is current compared to the information in the
        source tree.
        """
        abbr_filename = self.abbreviate_filename(filename)
        tup = self.paths.get(abbr_filename)
        if tup is None:
            return False

        mtime, size, checksum = tup
        if self._get_path_meta(filename) != (mtime, size):
            if checksum != self._get_path_checksum(filename):
                return False
            return True

        return True

    def clear_newly_added(self):
        """Clears the internal newly added flag which optimizes calls to
        :meth:`add_path`.
        """
        self._newly_added.clear()


class DependencyTree(_Tree):

    def __init__(self, env=None):
        _Tree.__init__(self, env)
        self.dependencies = {}

    def dump(self, filename):
        """Dumps the source tree into a file."""
        with atomic_open(filename) as f:
            for filename, deps in sorted(self.dependencies.items()):
                for dep in sorted(deps):
                    f.write('%s\n' % u'\t'.join((
                        filename,
                        dep,
                    )).encode('utf-8'))

    @classmethod
    def load(cls, filename, root_path=None, create_empty=False):
        rv = cls(root_path)
        try:
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.strip().split('\t')
                    if len(line) != 2:
                        continue
                    fn, dep = line
                    rv.dependencies.setdefault(fn.decode('utf-8'),
                                               set()).add(dep.decode('utf-8'))
        except IOError as e:
            if e.errno != errno.ENOENT or not create_empty:
                raise
        return rv

    def add_dependency(self, source, dependency):
        src = self.abbreviate_filename(source)
        dep = self.abbreviate_filename(dependency)
        if src != dep:
            self.dependencies.setdefault(src, set()).add(dep)

    def iter_dependencies(self, source):
        for fn in self.dependencies.get(self.abbreviate_filename(source), ()):
            yield fn

    def add_missing_to_source_tree(self, st):
        for filename, deps in self.dependencies.iteritems():
            st.add_path(filename)
            for dep in deps:
                st.add_path(dep)


class Builder(object):

    def __init__(self, pad, destination_path):
        self.pad = pad
        self.destination_path = destination_path

        self.source_tree_filename = os.path.join(
            destination_path, '.sources')
        self.dependency_tree_filename = os.path.join(
            destination_path, '.dependencies')

        self.source_tree = SourceTree.load(
            self.source_tree_filename, pad.db.env, create_empty=True)
        self.dependency_tree = DependencyTree.load(
            self.dependency_tree_filename, pad.db.env, create_empty=True)

    @property
    def env(self):
        return self.pad.db.env

    def get_fs_path(self, dst_filename, make_folder=False):
        p = os.path.join(self.destination_path,
                         dst_filename.strip('/').replace('/', os.path.sep))
        if make_folder:
            dir = os.path.dirname(p)
            try:
                os.makedirs(dir)
            except OSError:
                pass
        return p

    def get_build_program(self, record):
        """Returns the build program for a given record."""
        if record.is_exposed:
            if isinstance(record, Page):
                return self._build_page
            elif isinstance(record, Attachment):
                return self._build_attachment

    def get_destination_path(self, url_path):
        rv = url_path.lstrip('/')
        if not rv or rv[-1:] == '/':
            rv += 'index.html'
        return rv

    def _build_page(self, page):
        dst = self.get_destination_path(page.url_path)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as f:
            tmpl = self.env.get_template(page['_template'])
            f.write(tmpl.render(page=page, root=self.pad.root)
                    .encode('utf-8') + '\n')

    def _build_attachment(self, attachment):
        dst = self.get_destination_path(attachment.url_path)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as df:
            with open(attachment.attachment_filename) as sf:
                shutil.copyfileobj(sf, df)

    def should_build_record(self, record):
        # Direct changes
        for filename in record.iter_dependent_filenames():
            if not self.source_tree.is_current(filename):
                return True

            for dependency in self.dependency_tree.iter_dependencies(filename):
                if not self.source_tree.is_current(dependency):
                    return True

        return False

    def build_record(self, record, force=False):
        """Writes a record to the destination path."""
        build_program = self.get_build_program(record)
        if not build_program:
            print 'no program', record['_path']
            return

        if not force and not self.should_build_record(record):
            return

        print 'build', record['_path']
        oplog = OperationLog(self.pad)
        with oplog:
            build_program(record)
            for filename in record.iter_dependent_filenames():
                self.source_tree.add_path(filename)
                for dep in oplog.referenced_paths:
                    self.dependency_tree.add_dependency(filename, dep)
                self.source_tree.add_path(filename)

            for op in oplog.iter_operations():
                op.execute(self)

    def copy_assets(self):
        asset_path = os.path.join(self.env.root_path, 'assets')

        for dirpath, dirnames, filenames in os.walk(asset_path):
            self.env.jinja_env.cache
            dirnames[:] = [x for x in dirnames if x[:1] != '.']
            base = dirpath[len(asset_path) + 1:]
            for filename in filenames:
                if filename[:1] == '.':
                    continue

                src_path = os.path.join(asset_path, base, filename)
                if self.source_tree.is_current(src_path):
                    continue

                print 'build asset', src_path

                dst_path = os.path.join(self.destination_path, base, filename)
                try:
                    os.makedirs(os.path.dirname(dst_path))
                except OSError:
                    pass
                with atomic_open(dst_path) as df:
                    with open(src_path) as sf:
                        shutil.copyfileobj(sf, df)
                self.source_tree.add_path(src_path)

    def build_all(self):
        to_build = [self.pad.root]
        while to_build:
            node = to_build.pop()
            to_build.extend(node.iter_child_records())
            self.build_record(node)
        self.copy_assets()

        self.dependency_tree.add_missing_to_source_tree(self.source_tree)
        self.source_tree.dump(self.source_tree_filename)
        self.dependency_tree.dump(self.dependency_tree_filename)
