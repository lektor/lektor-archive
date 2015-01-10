import os
import sys
import stat
import shutil
import sqlite3
import hashlib
import tempfile
import posixpath

from contextlib import contextmanager
from itertools import chain

from lektor.db import Page, Attachment
from lektor.operationlog import OpLog


def create_tables(con):
    try:
        con.execute('''
            create table if not exists artifacts (
                artifact text,
                source text,
                source_mtime integer,
                source_size integer,
                source_checksum text,
                primary key (artifact, source)
            );
        ''')
    finally:
        con.close()


class BuildState(object):

    def __init__(self, generator, database_filename):
        self.generator = generator
        self.database_filename = database_filename

        self.file_info_cache = {}

        create_tables(self.connect_to_database())

    @property
    def pad(self):
        """The pad for this buildstate."""
        return self.generator.pad

    @property
    def env(self):
        """The environment backing this buildstate."""
        return self.generator.env

    def get_file_info(self, filename):
        """Returns the file info for a given file.  This will be cached
        on the generator for the lifetime of it.  This means that further
        accesses to this file info will not cause more IO but it might not
        be safe to use the generator after modifications to the original
        files have been performed on the outside.

        Generally this function can be used to acquire the file info for
        any file on the file system but it should onl be used for source
        files or carefully for other things.

        The filename given can be a source filename.
        """
        # XXX: this works on windows because slashes are still accepted.
        fn = os.path.join(self.env.root_path, filename)
        rv = self.file_info_cache.get(fn)
        if rv is None:
            self.file_info_cache[fn] = rv = FileInfo(self.env, fn)
        return rv

    def to_source_filename(self, filename):
        """Given a path somewhere below the environment this will return the
        short source filename that is used internally.  Unlike the given
        path, this identifier is also platform independent.
        """
        folder = os.path.abspath(self.env.root_path)
        filename = os.path.join(folder, filename)
        if filename.startswith(folder):
            filename = filename[len(folder):].lstrip(os.path.sep)
            if os.path.altsep:
                filename = filename.lstrip(os.path.altsep)
        else:
            raise ValueError('The given value (%r) is not below the '
                             'source folder (%r)' %
                             (filename, self.env.root_path))
        return filename.replace(os.path.sep, '/')

    def connect_to_database(self):
        """Returns a database connection for the build state db."""
        return sqlite3.connect(self.database_filename, timeout=10,
                               check_same_thread=False)

    def get_destination_filename(self, artifact_name):
        """Returns the destination filename for an artifact name."""
        return os.path.join(self.generator.destination_path,
                            artifact_name.strip('/').replace('/', os.path.sep))

    def artifact_name_from_destination_filename(self, filename):
        """Returns the artifact name for a destination filename."""
        dst = self.generator.destination_path
        filename = os.path.join(dst, filename)
        if filename.startswith(dst):
            filename = filename[len(dst):].lstrip(os.path.sep)
            if os.path.altsep:
                filename = filename.lstrip(os.path.altsep)
        return filename

    def new_artifact(self, artifact_name, sources=None, source_obj=None):
        dst_filename = self.get_destination_filename(artifact_name)
        key = self.artifact_name_from_destination_filename(dst_filename)
        return Artifact(self, key, dst_filename, sources, source_obj=source_obj)

    def artifact_exists(self, artifact_name):
        """Given an artifact name this checks if it was already produced."""
        dst_filename = self.get_destination_filename(artifact_name)
        return os.path.exists(dst_filename)

    def iter_artifact_dependencies(self, artifact_name):
        """Given an artifact name this will iterate over all dependencies
        of it as file info objects.
        """
        con = self.connect_to_database()
        cur = con.cursor()
        cur.execute('''
            select source, source_mtime, source_size, source_checksum
            from artifacts
            where artifact = ?
        ''', [artifact_name])
        rv = cur.fetchall()
        con.close()

        for filename, mtime, size, checksum in rv:
            yield FileInfo(self.env, filename, mtime, size, checksum)


class FileInfo(object):
    """A file info object holds metainformation of a file so that changes
    can be detected easily.
    """

    def __init__(self, env, filename, mtime=None, size=None, checksum=None):
        self.env = env
        self.filename = filename
        if mtime is not None and size is not None:
            self._stat = (mtime, size)
        else:
            self._stat = None
        self._checksum = checksum

    def _get_stat(self):
        rv = self._stat
        if rv is not None:
            return rv

        try:
            st = os.stat(self.filename)
            mtime = int(st.st_mtime)
            if stat.S_ISDIR(st.st_mode):
                size = len(os.listdir(self.filename))
            else:
                size = int(st.st_size)
            rv = mtime, size
        except OSError:
            rv = None, None
        self._stat = rv
        return rv

    @property
    def mtime(self):
        """The timestamp of the last modification."""
        return self._get_stat()[0]

    @property
    def size(self):
        """The size of the file in bytes.  If the file is actually a
        dictionary then the size is actually the number of files in it.
        """
        return self._get_stat()[1]

    @property
    def checksum(self):
        """The checksum of the file or directory."""
        rv = self._checksum
        if rv is not None:
            return rv

        try:
            h = hashlib.sha1()
            if os.path.isdir(self.filename):
                h.update('DIR\x00')
                for filename in sorted(os.listdir(self.filename)):
                    if self.env.is_uninteresting_filename(filename):
                        continue
                    if isinstance(filename, unicode):
                        filename = filename.encode('utf-8')
                    h.update(filename + '\x00')
            else:
                with open(self.filename, 'rb') as f:
                    while 1:
                        chunk = f.read(16 * 1024)
                        if not chunk:
                            break
                        h.update(chunk)
            checksum = h.hexdigest()
        except (OSError, IOError):
            checksum = '0' * 40
        self._checksum = checksum
        return checksum

    def __eq__(self, other):
        if type(other) is not FileInfo:
            return False

        # If mtime and size match, we skip the checksum comparison which
        # might require a file read which we do not want in those cases.
        if self.mtime == other.mtime and self.size == other.size:
            return True

        return self.checksum == other.checksum

    def __ne__(self, other):
        return not self.__eq__(other)


class Artifact(object):
    """This class represents a build artifact."""

    def __init__(self, build_state, artifact_name, dst_filename, sources,
                 source_obj=None):
        self.build_state = build_state
        self.artifact_name = artifact_name
        self.dst_filename = dst_filename
        self.sources = sources
        self.in_update_block = False
        self.updated = False
        self.source_obj = source_obj

        self._update_con = None
        self._new_artifact_file = None

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.dst_filename,
        )

    def get_connection(self):
        """Returns the exclusive database connection for this artifact."""
        if not self.in_update_block:
            raise RuntimeError('Can only only acquire buildstate connection '
                               'if the artifact is open for updates.')
        rv = self._update_con
        if rv is None:
            self._update_con = rv = self.build_state.connect_to_database()
        return rv

    def iter_dependency_infos(self):
        """This iterates over all dependencies as file info objects."""
        i = self.build_state.iter_artifact_dependencies(self.artifact_name)
        found = set()
        for file_info in i:
            filename = self.build_state.to_source_filename(file_info.filename)
            found.add(filename)
            yield filename, file_info

        # In any case we also iterate over our direct sources, even if the
        # build state does not know about them yet.  This can be caused by
        # an initial build or a change in original configuration.
        for source in self.sources:
            filename = self.build_state.to_source_filename(source)
            if filename not in found:
                yield source, None

    @property
    def is_current(self):
        """Checks if the artifact is current."""
        # If the artifact does not exist, we're not current.
        if not os.path.isfile(self.dst_filename):
            return False

        # If we do have an already existing artifact, we need to check if
        # any of the source files we depend on changed.
        for source_name, info in self.iter_dependency_infos():
            # if we get a missing source info it means that we never
            # saw this before.  This means we need to build it.
            if info is None:
                return False

            # If the file info is different, then it clearly changed.
            if info != self.build_state.get_file_info(info.filename):
                return False

        return True

    def ensure_dir(self):
        """Creates the directory if it does not exist yet."""
        dir = os.path.dirname(self.dst_filename)
        try:
            os.makedirs(dir)
        except OSError:
            pass

    def open(self, mode='rb', ensure_dir=False):
        """Opens the artifact for reading or writing.  This is transaction
        safe by writing into a temporary file and by moving it over the
        actual source in commit.
        """
        if ensure_dir:
            self.ensure_dir()
        if 'r' in mode:
            fn = self._new_artifact_file or self.dst_filename
            return open(fn, mode)
        if self._new_artifact_file is None:
            fd, tmp_filename = tempfile.mkstemp(
                dir=os.path.dirname(self.dst_filename), prefix='.__trans')
            self._new_artifact_file = tmp_filename
            return os.fdopen(fd, mode)
        return open(self._new_artifact_file, mode)

    def memorize_dependencies(self, dependencies=None):
        """This updates the dependencies recorded for the artifact based
        on the direct sources plus the provided dependencies.
        """
        seen = set()
        rows = []
        for source in chain(self.sources, dependencies or ()):
            source = self.build_state.to_source_filename(source)
            if source in seen:
                continue
            info = self.build_state.get_file_info(source)
            rows.append((self.artifact_name, source, info.mtime,
                         info.size, info.checksum))
            seen.add(source)

        con = self.get_connection()
        cur = con.cursor()
        cur.execute('delete from artifacts where artifact = ?',
                    [self.artifact_name])
        if rows:
            cur.executemany('''
                insert into artifacts (artifact, source, source_mtime,
                                       source_size, source_checksum)
                values (?, ?, ?, ?, ?)
            ''', rows)
        cur.close()

    def commit(self):
        """Commits the artifact changes."""
        if self._new_artifact_file is not None:
            os.rename(self._new_artifact_file, self.dst_filename)
            self._new_artifact_file = None
        if self._update_con is not None:
            self._update_con.commit()
            self._update_con.close()
            self._update_con = None

    def rollback(self):
        """Rolls back pending artifact changes."""
        if self._new_artifact_file is not None:
            try:
                os.remove(self._new_artifact_file)
            except OSError:
                pass
            self._new_artifact_file = None
        if self._update_con is not None:
            self._update_con.rollback()
            self._update_con.close()
            self._update_con = None

    @contextmanager
    def update(self):
        """Opens the artifact for modifications.

        Unlike the manual begin and update, this also performs a commit and
        rollback based on the success of the block.
        """
        oplog = self.begin_update()
        try:
            try:
                yield oplog
            finally:
                self.finish_update(oplog)
        except Exception:
            exc_type, exc_value, tb = sys.exc_info()
            self.rollback()
            raise exc_type, exc_value, tb
        self.commit()

    def begin_update(self):
        """Begins an update block."""
        if self.in_update_block:
            raise RuntimeError('Artifact is already open for updates.')
        self.updated = False
        oplog = OpLog(self)
        oplog.push()
        self.in_update_block = True
        return oplog

    def finish_update(self, oplog):
        """Finalizes an update block."""
        if not self.in_update_block:
            raise RuntimeError('Artifact is not open for updates.')
        oplog.pop()
        self.memorize_dependencies(oplog.referenced_dependencies)
        self.in_update_block = False
        self.updated = True


class BuildResult(object):

    def __init__(self, source):
        self.source = source


class BuildProgram(object):

    def __init__(self, source, build_state):
        self.source = source
        self.build_state = build_state
        self.artifacts = []
        self._built = False

    def build(self):
        """Invokes the build program."""
        if self._built:
            raise RuntimeError('This build program was already used.')
        self._built = True

        self.produce_artifacts()

        sub_artifacts = []

        def build(artifact, build_func):
            if not artifact.is_current:
                with artifact.update() as oplog:
                    build_func(artifact)
                    sub_artifacts.extend(oplog.sub_artifacts)

        # Step one is building the artifacts that this build program
        # knows about.
        for artifact in self.artifacts:
            build(artifact, self.build_artifact)

        # For as long as our oplog keeps producing sub artifacts, we
        # want to process them as well.
        while sub_artifacts:
            artifact, build_func = sub_artifacts.pop()
            build(artifact, build_func)

    def declare_artifact(self, artifact_name, sources=None, extra=None):
        """This declares an artifact to be built in this program."""
        self.artifacts.append(self.build_state.new_artifact(
            artifact_name=artifact_name,
            sources=sources,
            source_obj=self.source
        ))

    def build_artifact(self, artifact):
        """This is invoked for each artifact declared."""

    def iter_child_sources(self):
        """This allows a build program to produce children that also need
        building.  An individual build never recurses down to this, but
        a `build_all` will use this.
        """
        return iter(())


build_programs = []


def buildprogram(source_cls):
    def decorator(builder_cls):
        build_programs.append((source_cls, builder_cls))
        return builder_cls
    return decorator


@buildprogram(Page)
class PageBuildProgram(BuildProgram):

    def produce_artifacts(self):
        if self.source.is_exposed:
            self.declare_artifact(
                posixpath.join(self.source.url_path, 'index.html'),
                sources=[self.source.source_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb', ensure_dir=True) as f:
            rv = self.build_state.env.render_template(
                self.source['_template'], self.build_state.pad,
                this=self.source)
            f.write(rv.encode('utf-8') + b'\n')

    def iter_child_sources(self):
        return chain(self.source.children,
                     self.source.attachments)


@buildprogram(Attachment)
class AttachmentBuildProgram(BuildProgram):

    def produce_artifacts(self):
        if self.source.is_exposed:
            self.declare_artifact(
                self.source.url_path,
                sources=[self.source.source_filename,
                         self.source.attachment_filename])

    def build_artifact(self, artifact):
        with artifact.open('wb', ensure_dir=True) as df:
            with open(self.source.attachment_filename) as sf:
                shutil.copyfileobj(sf, df)


class Generator(object):

    def __init__(self, pad, destination_path):
        self.pad = pad
        self.destination_path = os.path.join(
            pad.db.env.root_path, destination_path)

    @property
    def env(self):
        """The environment backing this generator."""
        return self.pad.db.env

    def new_build_state(self):
        """Creates a new build state."""
        try:
            os.makedirs(self.destination_path)
        except OSError:
            pass
        return BuildState(self, os.path.join(
            self.destination_path, '.buildstate'))

    def get_builder(self, source, build_state):
        """Finds the right build function for the given source file."""
        for cls, builder in build_programs:
            if isinstance(source, cls):
                return builder(source, build_state)
        raise RuntimeError('I do not know how to build %r', source)

    def build(self, source, build_state=None):
        """Given a source object, builds it."""
        if build_state is None:
            build_state = self.new_build_state()

        print 'building', source
        builder = self.get_builder(source, build_state)
        builder.build()
        return builder

    def build_all(self, build_state=None):
        """Builds the entire tree."""
        to_build = [self.pad.root]
        while to_build:
            source = to_build.pop()
            builder = self.build(source)
            to_build.extend(builder.iter_child_sources())
