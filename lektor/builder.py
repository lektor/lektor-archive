import os
import stat
import errno
import shutil
import click
import hashlib

from lektor.utils import atomic_open, prune_file_and_folder
from lektor.operationlog import OperationLog
from lektor.db import Page, Attachment


# TODO: paths do not get deleted properly, This also cause constant
# rebuilds


class _Tree(object):

    def __init__(self, env, filename):
        self.env = env
        self.root_path = os.path.abspath(env.root_path)
        self.filename = filename

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

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
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

    def get_checksum(self, filename):
        """Returns the checksum for a file."""
        abbr_filename = self.abbreviate_filename(filename)
        tup = self.paths.get(abbr_filename)
        if tup is None:
            return self.add_path(filename)
        mtime, size, checksum = tup
        return checksum

    def dump(self):
        """Dumps the source tree into a file."""
        with atomic_open(self.filename) as f:
            for filename, tup in sorted(self.paths.items()):
                mtime, size, checksum = tup
                f.write('%s\n' % u'\t'.join((
                    filename,
                    unicode(mtime),
                    unicode(size),
                    checksum,
                )).encode('utf-8'))

    @classmethod
    def load(cls, env, filename, create_empty=False):
        rv = cls(env, filename)
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
            return None
        checksum = self._get_path_checksum(filename)
        if checksum is None:
            return None
        filename = self.abbreviate_filename(filename)
        if filename not in self._newly_added:
            self.paths[filename] = tup + (checksum,)
        return checksum

    def remove_path(self, filename):
        """Removes a path from the source tree again."""
        filename = self.abbreviate_filename(filename)
        tup = self.paths.pop(filename, None)
        return tup is not None

    def is_current(self, filename, reference_checksum=None):
        """Checks if a filename is current compared to the information in the
        source tree.
        """
        abbr_filename = self.abbreviate_filename(filename)
        tup = self.paths.get(abbr_filename)
        if tup is None:
            return False

        mtime, size, checksum = tup
        if reference_checksum is not None and \
           checksum != reference_checksum:
            return False

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

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
        self.dependencies = {}

    def dump(self):
        with atomic_open(self.filename) as f:
            for filename, deps in sorted(self.dependencies.items()):
                for dep, cs in sorted(deps.items()):
                    f.write('%s\n' % u'\t'.join((
                        filename,
                        dep,
                        cs,
                    )).encode('utf-8'))

    @classmethod
    def load(cls, env, filename, create_empty=False):
        rv = cls(env, filename)
        try:
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.strip().split('\t')
                    if len(line) != 3:
                        continue
                    fn, dep, cs = line
                    rv.dependencies.setdefault(fn.decode('utf-8'),
                                               {})[dep.decode('utf-8')] = cs
        except IOError as e:
            if e.errno != errno.ENOENT or not create_empty:
                raise
        return rv

    def add_dependency(self, source, dependency, cs):
        src = self.abbreviate_filename(source)
        dep = self.abbreviate_filename(dependency)
        if src != dep:
            self.dependencies.setdefault(src, {})[dep] = cs

    def clean_dependencies(self, source):
        source = self.abbreviate_filename(source)
        return self.dependencies.pop(source, None) is not None

    def remove_source(self, source):
        source = self.abbreviate_filename(source)
        rv = self.dependencies.pop(source, None) is not None
        for _, s in self.dependencies.iteritems():
            if not rv:
                rv = source in s
            s.pop(source, None)
        return rv

    def iter_dependencies(self, source):
        return self.dependencies.get(
            self.abbreviate_filename(source), {}).iteritems()

    def add_missing_to_source_tree(self, st):
        for filename, deps in self.dependencies.iteritems():
            st.add_path(filename)
            for dep in deps:
                st.add_path(dep)


class ArtifactTree(_Tree):

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
        self.artifacts = {}
        self.checksums = {}
        self.known_artifacts = set()

    def dump(self):
        with atomic_open(self.filename) as f:
            for filename, afts in sorted(self.artifacts.items()):
                for aft, checksum in sorted(afts.items()):
                    f.write('%s\n' % u'\t'.join((
                        filename,
                        aft,
                        checksum,
                    )).encode('utf-8'))

    @classmethod
    def load(cls, env, filename, create_empty=False):
        rv = cls(env, filename)
        try:
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.strip().split('\t')
                    if len(line) != 3:
                        continue
                    fn, aft, cs = line
                    rv.artifacts.setdefault(
                        fn.decode('utf-8'), {})[aft.decode('utf-8')] = cs
        except IOError as e:
            if e.errno != errno.ENOENT or not create_empty:
                raise
        return rv

    def add_artifact(self, source, artifact, checksum):
        src = self.abbreviate_filename(source)
        aft = self.abbreviate_filename(artifact)
        self.artifacts.setdefault(src, {})[aft] = checksum

    def remove_source(self, source):
        src = self.abbreviate_filename(source)
        return self.artifacts.pop(src, None) is not None

    def artifacts_are_recent(self, source, checksum):
        afts = self.artifacts.get(self.abbreviate_filename(source))
        if not afts:
            return False
        for _, cs in (afts or {}).iteritems():
            if cs != checksum:
                return False
        return True

    def iter_unused_artifacts(self, sources):
        sources = set(self.abbreviate_filename(x) for x in sources)
        for src, artifacts in self.artifacts.items():
            if src in sources:
                continue
            yield src, artifacts.keys()


class Builder(object):

    def __init__(self, pad, destination_path):
        self.pad = pad
        self.destination_path = destination_path

        self.referenced_sources = set()
        self.source_tree = SourceTree.load(
            pad.db.env,
            os.path.join(destination_path, '.sources'), create_empty=True)
        self.dependency_tree = DependencyTree.load(
            pad.db.env,
            os.path.join(destination_path, '.dependencies'), create_empty=True)
        self.artifact_tree = ArtifactTree.load(
            pad.db.env,
            os.path.join(destination_path, '.artifacts'), create_empty=True)

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

    def _build_page(self, page, oplog):
        dst = self.get_destination_path(page.url_path)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as f:
            tmpl = self.env.get_template(page['_template'])
            f.write(tmpl.render(page=page, root=self.pad.root)
                    .encode('utf-8') + '\n')
        oplog.record_artifact(filename)

    def _build_attachment(self, attachment, oplog):
        dst = self.get_destination_path(attachment.url_path)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as df:
            with open(attachment.attachment_filename) as sf:
                shutil.copyfileobj(sf, df)
        oplog.record_artifact(filename)

    def should_build_sourcefile(self, source_filename):
        if not self.source_tree.is_current(source_filename):
            return True
        cs = self.source_tree.get_checksum(source_filename)
        if not self.artifact_tree.artifacts_are_recent(source_filename, cs):
            return True
        return False

    def _should_build_record(self, record):
        for filename in record.iter_dependent_filenames():
            if self.should_build_sourcefile(filename):
                return True

            for dependency, cs in self.dependency_tree.iter_dependencies(filename):
                if not self.source_tree.is_current(dependency, cs):
                    return True

        return False

    def build_record_twophase(self, record, force=False):
        self.referenced_sources.update(record.iter_dependent_filenames())

        build_program = self.get_build_program(record)
        if not build_program:
            return

        if not force and not self._should_build_record(record):
            return

        def build_func():
            click.echo('Record %s' % click.style(record['_path'], fg='cyan'))
            oplog = OperationLog(self.pad)
            with oplog:
                build_program(record, oplog)

                oplog.execute_pending_operations(self)

                for filename in record.iter_dependent_filenames():
                    self.dependency_tree.clean_dependencies(filename)
                    checksum = self.source_tree.add_path(filename)
                    for dep in oplog.referenced_paths:
                        cs = self.source_tree.get_checksum(dep)
                        self.dependency_tree.add_dependency(filename, dep, cs)
                    for aft in oplog.produced_artifacts:
                        self.artifact_tree.add_artifact(filename, aft, checksum)
                    self.source_tree.add_path(filename)

        return build_func

    def build_record(self, record, force=False):
        """Writes a record to the destination path."""
        build_func = self.build_record_twophase(record, force)
        if build_func is None:
            return False
        build_func()
        return True

    def need_to_build_record(self, record):
        return self.build_record_twophase(record) is not None

    def copy_assets(self):
        asset_path = self.env.asset_path

        for dirpath, dirnames, filenames in os.walk(asset_path):
            self.env.jinja_env.cache
            dirnames[:] = [x for x in dirnames if
                           not self.env.is_uninteresting_filename(x)]
            base = dirpath[len(asset_path) + 1:]
            for filename in filenames:
                if self.env.is_uninteresting_filename(filename):
                    continue

                src_path = os.path.join(asset_path, base, filename)
                self.referenced_sources.add(src_path)
                if self.source_tree.is_current(src_path):
                    continue

                click.echo('Asset %s' % click.style(src_path, fg='cyan'))
                dst_path = os.path.join(self.destination_path, base, filename)
                try:
                    os.makedirs(os.path.dirname(dst_path))
                except OSError:
                    pass
                with atomic_open(dst_path) as df:
                    with open(src_path) as sf:
                        shutil.copyfileobj(sf, df)
                checksum = self.source_tree.add_path(src_path)
                self.artifact_tree.add_artifact(src_path, dst_path, checksum)

    def remove_old_artifacts(self):
        ua = self.artifact_tree.iter_unused_artifacts(self.referenced_sources)
        for src, afts in ua:
            click.echo('Removing artifacts of %s' %
                click.style(src, fg='cyan'))
            for aft in afts:
                prune_file_and_folder(aft, self.destination_path)
            self.source_tree.remove_path(src)
            self.dependency_tree.remove_source(src)
            self.artifact_tree.remove_source(src)

    def finalize(self):
        self.dependency_tree.add_missing_to_source_tree(self.source_tree)
        self.source_tree.dump()
        self.dependency_tree.dump()
        self.artifact_tree.dump()

    def iter_build_all(self):
        to_build = [self.pad.root]
        while to_build:
            node = to_build.pop()
            to_build.extend(node.iter_child_records())
            build_func = self.build_record_twophase(node)
            yield node, build_func

    def build_all(self):
        for node, build_func in self.iter_build_all():
            if build_func is not None:
                build_func()
        self.copy_assets()
        self.remove_old_artifacts()
        self.finalize()
