import os
import errno
import shutil

from lektor.utils import atomic_open
from lektor.db import Record, Attachment


# XXX: this is more or less a huge hack currently.  problems:
#
#   hardcoded behavior for records and attachments
#   does not track dependencies correctly (template changes do not
#   rebuild files)
#   child changes do not invalidate parents
#   assets are not content tracked properly


class BuildCache(object):

    def __init__(self):
        self.artifacts = {}

    def add_artifact(self, record, destination_filename):
        self.artifacts.setdefault(record['_path'], []).append(
            (destination_filename, record.get_fast_source_hash(),
             record.get_source_hash()))

    def remove_artifact(self, path, destination_filename):
        if path not in self.artifacts:
            return
        tuples = self.artifacts[path]
        for tup in tuples:
            if tup[0] == destination_filename:
                tuples.discard(tup)
                break
        if not tuples:
            del self.artifacts[path]

    def iter_artifacts(self, path, remove=False):
        artifacts = self.artifacts.get(path)
        if artifacts:
            if remove:
                self.artifacts.pop(path, None)
            for item in artifacts:
                yield item

    def record_is_fresh(self, record):
        """Checks if a record is fresh."""
        source_path = record['_path']
        artifacts = self.artifacts.get(source_path)
        if not artifacts:
            return False

        current_fast_hash = record.get_fast_source_hash()
        current_hash = None

        for (destination_filename, fast_hash, hash) in artifacts:
            if fast_hash != current_fast_hash:
                if current_hash is None:
                    current_hash = record.get_source_hash()
                    if current_hash != hash:
                        return False

        return True

    def dump(self, filename):
        with atomic_open(filename) as f:
            for artifact, tuples in sorted(self.artifacts.items()):
                for tup in tuples:
                    f.write(('%s\n' % '\t'.join(
                        map(unicode, (artifact,) + tup))).encode('utf-8'))

    @classmethod
    def load(cls, filename):
        rv = cls()
        try:
            with open(filename, 'rb') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    tup = line.split('\t')
                    rv.artifacts.setdefault(tup[0], []).append(
                        (tup[1], int(tup[2]), tup[3]))
            return rv
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            return


class Builder(object):

    def __init__(self, pad, destination_path):
        self.pad = pad
        self.destination_path = destination_path
        self.build_cache_file = os.path.join(
            self.destination_path, '.lektor-build-cache.txt')

        build_cache = BuildCache.load(self.build_cache_file)
        if build_cache is None:
            build_cache = BuildCache()
        self.build_cache = build_cache

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
            if isinstance(record, Record):
                return self._build_record
            elif isinstance(record, Attachment):
                return self._build_attachment
        return self._remove_artifacts

    def get_destination_path(self, record):
        rv = record.url_path.lstrip('/')
        if not rv or rv[-1:] == '/':
            rv += 'index.html'
        return rv

    def _remove_artifacts(self, record):
        for destination_filename, _, _ in \
                self.build_cache.iter_artifacts(record['_path'], remove=True):
            try:
                os.remove(self.get_fs_path(destination_filename))
            except OSError:
                pass

    def _build_record(self, record):
        self._remove_artifacts(record)
        dst = self.get_destination_path(record)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as f:
            tmpl = self.env.get_template(record['_template'])
            f.write(tmpl.render(page=record).encode('utf-8') + '\n')
        self.build_cache.add_artifact(record, dst)

    def _build_attachment(self, attachment):
        self._remove_artifacts(attachment)
        dst = self.get_destination_path(attachment)
        filename = self.get_fs_path(dst, make_folder=True)
        with atomic_open(filename) as df:
            with open(attachment.source_attachment_filename) as sf:
                shutil.copyfileobj(sf, df)
        self.build_cache.add_artifact(attachment, dst)

    def build_record(self, record, force=False):
        """Writes a record to the destination path."""
        if not force and self.build_cache.record_is_fresh(record):
            print 'skip', record['_path']
            return
        print 'build', record['_path']
        build_program = self.get_build_program(record)
        build_program(record)

    def copy_assets(self):
        asset_path = os.path.join(self.env.root_path, 'assets')

        def should_overwrite(src, dst):
            if not os.path.isfile(dst):
                return True
            return False

        for dirpath, dirnames, filenames in os.walk(asset_path):
            dirnames[:] = [x for x in dirnames if x[:1] != '.']
            base = dirpath[len(asset_path) + 1:]
            for filename in filenames:
                if filename[:1] == '.':
                    continue

                src_path = os.path.join(asset_path, base, filename)
                dst_path = os.path.join(self.destination_path, base, filename)
                if should_overwrite(src_path, dst_path):
                    try:
                        os.makedirs(os.path.dirname(dst_path))
                    except OSError:
                        pass
                    with atomic_open(dst_path) as df:
                        with open(src_path) as sf:
                            shutil.copyfileobj(sf, df)

    def build_all(self):
        to_build = [self.pad.root]
        while to_build:
            node = to_build.pop()
            to_build.extend(node.iter_child_records())
            self.build_record(node)
        self.copy_assets()
        self.build_cache.dump(self.build_cache_file)
