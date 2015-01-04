import os
import stat
import shutil
import click
import hashlib
import sqlite3

from lektor.utils import atomic_open, prune_file_and_folder
from lektor.operationlog import OperationLog
from lektor.db import Page, Attachment


_missing = object()


class _Tree(object):

    def __init__(self, env, filename):
        self.env = env
        self.filename = filename
        self.root_path = os.path.abspath(env.root_path)

        con = self.get_connection()
        con.execute(self.schema)
        con.close()

    def get_connection(self):
        return sqlite3.connect(self.filename)

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
    schema = '''
        create table if not exists sources (
            filename text,
            mtime integer,
            size integer,
            checksum text,
            primary key (filename)
        );
    '''

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
        self._paths = {}
        self._changed = set()

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
        tup = self.get_path_info(abbr_filename)
        if tup is None:
            return self._get_path_checksum(filename)
        mtime, size, checksum = tup
        return checksum

    def add_path(self, filename):
        """Adds a path to the source tree."""
        tup = self._get_path_meta(filename)
        if tup is None:
            return None
        checksum = self._get_path_checksum(filename)
        if checksum is None:
            return None
        filename = self.abbreviate_filename(filename)
        self._paths[filename] = tup + (checksum,)
        self._changed.add(filename)
        return checksum

    def get_path_info(self, filename):
        filename = self.abbreviate_filename(filename)
        rv = self._paths.get(filename, _missing)
        if rv is not _missing:
            return rv

        con = self.get_connection()
        rv = con.execute('''
            select filename, mtime, size, checksum from sources
             where filename = ?
        ''', (filename,)).fetchone()
        con.close()

        if rv is not None:
            filename, mtime, size, checksum = rv
            self._paths[filename] = rv = (mtime, size, checksum)
        return rv

    def remove_path(self, filename):
        """Removes a path from the source tree again."""
        filename = self.abbreviate_filename(filename)
        tup = self._paths.pop(filename, None)
        self._changed.add(filename)
        return tup is not None

    def is_current(self, filename, reference_checksum=None):
        """Checks if a filename is current compared to the information in the
        source tree.
        """
        abbr_filename = self.abbreviate_filename(filename)
        tup = self.get_path_info(abbr_filename)
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

    def commit(self):
        con = self.get_connection()
        values = []
        to_delete = []
        for filename in self._changed:
            tup = self._paths.get(filename)
            if tup is None:
                to_delete.append((filename,))
            else:
                mtime, size, checksum = tup
                values.append((filename, mtime, size, checksum))
        if to_delete:
            con.executemany('delete from sources where filename = ?', to_delete)
        if values:
            con.executemany('''
                insert or replace into sources
                    (filename, mtime, size, checksum) values (?, ?, ?, ?);
            ''', values)
        self._changes = set()
        con.commit()


class DependencyTree(_Tree):
    schema = '''
        create table if not exists dependencies (
            filename text,
            dependency text,
            checksum text,
            primary key (filename, dependency)
        );
    '''

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
        self._dependencies = {}
        self._changes = set()

    def commit(self):
        con = self.get_connection()
        values = []
        to_delete = []
        for source in self._changes:
            deps = self._dependencies.get(source)
            to_delete.append((source,))
            if not deps:
                continue
            for dep, cs in deps.iteritems():
                values.append((source, dep, cs))

        if to_delete:
            con.executemany('delete from dependencies where filename = ?',
                            to_delete)
        if values:
            con.executemany('''
                insert or replace into dependencies
                    (filename, dependency, checksum) values (?, ?, ?);
            ''', values)
        self._changes = set()
        con.commit()

    def add_dependency(self, source, dependency, cs):
        src = self.abbreviate_filename(source)
        dep = self.abbreviate_filename(dependency)
        if src != dep:
            self._dependencies.setdefault(src, {})[dep] = cs
            self._changes.add(src)

    def clean_dependencies(self, source):
        source = self.abbreviate_filename(source)
        self._changes.add(source)
        return self._dependencies.pop(source, None) is not None

    def remove_source(self, source):
        source = self.abbreviate_filename(source)
        con = self.get_connection()
        con.execute('''
            delete from dependencies
             where filename = ? or dependency = ?
        ''', (source, source))
        con.commit()
        con.close()

        # remove from local cache data just in case
        self._dependencies.pop(source, None)
        for key, deps in self._dependencies.iteritems():
            deps.pop(source, None)

    def iter_dependencies(self, source):
        src = self.abbreviate_filename(source)
        return self.get_dependency_info(src).iteritems()

    def get_dependency_info(self, path):
        path = self.abbreviate_filename(path)
        rv = self._dependencies.get(path)
        if rv is None and path not in self._changes:
            con = self.get_connection()
            iterable = con.execute('''
                select filename, dependency, checksum from dependencies
                where filename = ?
            ''', (path,))
            rv = {}
            for (fn, dep, cs) in iterable:
                rv[dep] = cs
            self._dependencies[fn] = rv
            con.close()
        return rv


class ArtifactTree(_Tree):
    schema = '''
        create table if not exists artifacts (
            filename text,
            artifact text,
            checksum text,
            primary key (filename, artifact)
        );
    '''

    def __init__(self, env, filename):
        _Tree.__init__(self, env, filename)
        self._artifacts = {}
        self._changes = set()

        con = self.get_connection()
        rv = con.execute('select filename, artifact, checksum '
                         'from artifacts')
        for (fn, aft, cs) in rv:
            self._artifacts.setdefault(fn, {})[aft] = cs
        con.close()

    def commit(self):
        con = self.get_connection()
        values = []
        to_delete = []
        for source in self._changes:
            afts = self._artifacts.get(source)
            to_delete.append((source,))
            if not afts:
                continue
            for aft, cs in afts.iteritems():
                values.append((source, aft, cs))

        if to_delete:
            con.executemany('delete from artifacts where filename = ?',
                            to_delete)
        if values:
            con.executemany('''
                insert or replace into artifacts
                    (filename, artifact, checksum) values (?, ?, ?);
            ''', values)
        self._changes = set()
        con.commit()

    def add_artifact(self, source, artifact, checksum):
        src = self.abbreviate_filename(source)
        aft = self.abbreviate_filename(artifact)
        self._artifacts.setdefault(src, {})[aft] = checksum
        self._changes.add(src)

    def remove_source(self, source):
        source = self.abbreviate_filename(source)
        con = self.get_connection()
        con.execute('''
            delete from artifacts where filename = ?
        ''', (source,))
        con.commit()
        con.close()

        # remove from local cache data just in case
        self._artifacts.pop(source, None)

    def get_artifact_info(self, source):
        source = self.abbreviate_filename(source)
        rv = self._artifacts.get(source)
        if rv is None and source not in self._changes:
            con = self.get_connection()
            iterable = con.execute('''
                select filename, artifact, checksum from artifacts
                where filename = ?
            ''', (source,))
            rv = {}
            for (fn, aft, cs) in iterable:
                rv[aft] = cs
            self._artifacts[source] = rv
            con.close()
        return rv

    def artifacts_are_recent(self, source, checksum):
        afts = self.get_artifact_info(source)
        if not afts:
            return False
        for _, cs in (afts or {}).iteritems():
            if cs != checksum:
                return False
        return True

    def iter_unused_artifacts(self, sources):
        # XXX: this is not using local modifications
        sources = set(self.abbreviate_filename(x) for x in sources)
        if not sources:
            return

        con = self.get_connection()
        iterable = con.execute('''
            select filename, artifact from artifacts
            where filename not in (%s)
        ''' % ', '.join((('?',) * len(sources))), list(sources))

        rv = {}
        for src, artifact in iterable:
            rv.setdefault(src, set()).add(artifact)
        con.close()
        return rv.iteritems()


class Builder(object):

    def __init__(self, pad, destination_path):
        self.pad = pad
        self.destination_path = destination_path

        self.referenced_sources = set()

        try:
            os.makedirs(destination_path)
        except OSError:
            pass

        db_fn = os.path.abspath(os.path.join(destination_path, '.buildstate'))
        self.source_tree = SourceTree(pad.db.env, db_fn)
        self.dependency_tree = DependencyTree(pad.db.env, db_fn)
        self.artifact_tree = ArtifactTree(pad.db.env, db_fn)

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
                        cs = self.source_tree.add_path(dep)
                        self.dependency_tree.add_dependency(filename, dep, cs)
                    for aft in oplog.produced_artifacts:
                        self.artifact_tree.add_artifact(filename, aft, checksum)

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
        changed = False
        ua = self.artifact_tree.iter_unused_artifacts(self.referenced_sources)
        for src, afts in ua:
            click.echo('Removing artifacts of %s' %
                click.style(src, fg='cyan'))
            for aft in afts:
                prune_file_and_folder(aft, self.destination_path)
            self.source_tree.remove_path(src)
            self.dependency_tree.remove_source(src)
            self.artifact_tree.remove_source(src)
            changed = True
        if changed:
            self.commit()

    def commit(self):
        self.source_tree.commit()
        self.dependency_tree.commit()
        self.artifact_tree.commit()

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
        self.commit()

        # XXX: This needs to come after commit because the removing currently
        # only works on committed data.
        self.remove_old_artifacts()
