import os
import shutil

from collections import OrderedDict

from lektor.metaformat import serialize
from lektor.utils import atomic_open
from lektor.datamodel import system_fields


#: fields that are ignored in all circumstances.
ignored_system_fields = set(['_path', '_id', '_gid', '_attachment_for'])

#: system fields that are supported
valid_system_fields = set(system_fields) - ignored_system_fields


class Editor(object):
    """The editor can write data that is referenced by the database.  This is
    only used by the admin system and as such separated from the database
    which is generally considered read-only.
    """

    def __init__(self, pad):
        self.pad = pad

    def load_raw_record(self, source, cls=None):
        """Given a source object this will load the associated raw source.
        This is useful for editing.  Note that there is no guarantee that
        it will be the same data as the raw data that was originally used
        to retrieve the source object.
        """
        return self.pad.db.load_raw_data(
            source['_path'], source.record_classification, cls=None)

    def add_page_record(self, parent_source, new_data):
        """Creates a new page below a parent.  The data is trusted.
        At the moment this only supports system fields.
        """
        def _iter_fields():
            # When we create a new record we currently only allow system
            # fields.
            for key in sorted(valid_system_fields):
                value = new_data.get(key)
                if value:
                    yield key, value

        path = parent_source['_path'] + '/' + new_data['_id']
        fs_path = self.pad.db.get_fs_path(path, 'page')

        try:
            os.makedirs(os.path.dirname(fs_path))
        except OSError:
            pass

        with atomic_open(fs_path, 'wb') as f:
            for chunk in serialize(_iter_fields(), encoding='utf-8'):
                f.write(chunk)

    def update_raw_record(self, source, new_data):
        """Updates a record on the file system based on new data.  After
        this the pad needs reloading or the change will not be visible.

        The new data is string values only.  For boolean values the absence
        of a value is assumed to mean no.
        """
        old_raw_record = self.load_raw_record(source, cls=OrderedDict)

        def _iter_fields():
            done = set()

            for key, value in old_raw_record.iteritems():
                if key in ignored_system_fields:
                    continue

                # If we do not know anything about it, we just leave it
                # unchanged.
                if key not in source.datamodel.field_map:
                    yield key, value
                    continue

                value = new_data.get(key)
                if value:
                    done.add(key)
                    yield key, value

            # System fields come first
            for key in sorted(valid_system_fields):
                if key in done:
                    continue
                value = new_data.get(key)
                if value:
                    done.add(key)
                    yield key, value

            # Followed by the datamodel's fields.
            for field in source.datamodel.fields:
                if field.name in done:
                    continue
                value = new_data.get(field.name)
                if value:
                    yield field.name, value

        path = self.pad.db.get_fs_path(source['_path'],
                                       source.record_classification)

        with atomic_open(path, 'wb') as f:
            for chunk in serialize(_iter_fields(), encoding='utf-8'):
                f.write(chunk)

    def delete_record(self, record):
        """This deletes a record."""
        if record.record_classification == 'page':
            fs_path = self.pad.db.get_fs_path(record['_path'], 'base')
            try:
                shutil.rmtree(fs_path)
            except (OSError, IOError):
                pass
        else:
            for fn in record._iter_dependent_filenames():
                try:
                    os.remove(fn)
                except OSError:
                    pass
