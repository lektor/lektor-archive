from lektor.metaformat import serialize
from lektor.utils import atomic_open


class Editor(object):
    """The editor can write data that is referenced by the database.  This is
    only used by the admin system and as such separated from the database
    which is generally considered read-only.
    """

    def __init__(self, pad):
        self.pad = pad

    def load_raw_record(self, source):
        """Given a source object this will load the associated raw source.
        This is useful for editing.  Note that there is no guarantee that
        it will be the same data as the raw data that was originally used
        to retrieve the source object.
        """
        return self.pad.db.load_raw_data(
            source['_path'], source.record_classification)

    def update_raw_record(self, source, new_data):
        """Updates a record on the file system based on new data.  After
        this the pad needs reloading or the change will not be visible.
        """
        def _iter_fields():
            for field in source.datamodel.fields:
                item = new_data.get(field.name)
                if item is None:
                    continue
                yield field.name, item

        path = self.pad.db.get_fs_path(source['_path'],
                                       source.record_classification)

        with atomic_open(path, 'wb') as f:
            for chunk in serialize(_iter_fields(), encoding='utf-8'):
                f.write(chunk)
