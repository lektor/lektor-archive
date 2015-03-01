import os
import shutil
import posixpath

from collections import OrderedDict

from lektor.metaformat import serialize
from lektor.utils import atomic_open


implied_keys = set(['_id', '_path', '_gid', '_attachment_for'])
possibly_implied_keys = set(['_model', '_template', '_attachment_type'])


class BadEdit(Exception):
    pass


class BadDelete(BadEdit):
    pass


def make_editor_session(pad, path, is_attachment=None, datamodel=None):
    """Creates an editor session for the given path object."""
    raw_data = pad.db.load_raw_data(path, cls=OrderedDict)

    exists = raw_data is not None

    if is_attachment is None:
        if not exists:
            is_attachment = False
        else:
            is_attachment = bool(raw_data.get('_attachment_for'))
    elif bool(raw_data.get('_attachment_for')) != is_attachment:
        raise BadEdit('The attachment flag passed is conflicting with the '
                      'record\'s attachment flag.')

    if raw_data is not None:
        # XXX: what about changing the datamodel after the fact?
        if datamodel is not None:
            raise BadEdit('When editing an existing record, a datamodel '
                          'must not be provided.')
        datamodel = pad.db.get_datamodel_for_raw_data(raw_data, pad)
    else:
        if datamodel is None:
            datamodel = pad.db.get_implied_datamodel(path, is_attachment, pad)
        elif isinstance(datamodel, basestring):
            datamodel = pad.db.datamodels[datamodel]

    return EditorSession(pad, unicode(path), raw_data, datamodel,
                         is_attachment)


class EditorSession(object):

    def __init__(self, pad, path, original_data, datamodel,
                 is_attachment=False):
        self.id = posixpath.basename(path)
        self.pad = pad
        self.path = path
        self.original_data = original_data
        self.exists = original_data is not None
        self.datamodel = datamodel

        if original_data:
            for key in implied_keys:
                original_data.pop(key, None)

        self._data = {}
        self._changed = set()
        self._delete_this = False
        self._recursive_delete = False
        self.is_attachment = is_attachment
        self.closed = False

    def __getitem__(self, key):
        if key in self._data:
            rv = self._data[key]
            if rv is None:
                raise KeyError(key)
            return rv
        if self.original_data is None:
            raise KeyError(key)
        return self.original_data[key]

    def __setitem__(self, key, value):
        if self.original_data:
            old_value = self.original_data.get(key)
        else:
            old_value = None
        if old_value != value:
            self._changed.add(value)
        else:
            # If the key is in the possibly implied key set and set to
            # that value, we will set it to changed anyways.  This allows
            # overriding of such special keys.
            if key in possibly_implied_keys:
                self._changed.add(value)
            else:
                self._changed.discard(value)
        self._data[key] = value

    def __delitem__(self, key):
        self[key] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            self.rollback()
        else:
            self.commit()

    def iteritems(self):
        done = set()

        if self.original_data:
            for key, value in self.original_data.iteritems():
                done.add(key)
                if key in implied_keys:
                    continue
                if key in self._changed:
                    value = self._data[key]
                if value is not None:
                    yield key, value

        for key in sorted(self._data):
            if key in done:
                continue
            value = self._data.get(key)
            if value is not None:
                yield key, value

    def iterkeys(self):
        for key, _ in self.iteritems():
            yield key

    def itervalues(self):
        for _, value in self.iteritems():
            yield value

    def items(self):
        return list(self.iteritems())

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    @property
    def fs_path(self):
        """The path to the record file on the file system."""
        base = self.pad.db.to_fs_path(self.path)
        if self.is_attachment:
            return base + '.lr'
        return os.path.join(base, 'contents.lr')

    def revert_key(self, key):
        """Reverts a key to the implied value."""
        if key in self._data:
            self._changed.discard(key)
        self._data.pop(key, None)

    def rollback(self):
        """Ignores all changes and rejects them."""
        if self.closed:
            return
        self.closed = True

    def commit(self):
        """Saves changes back to the file system."""
        if self.closed:
            return

        if self._delete_this:
            self.closed = True
            self._real_delete()
            return

        if not self._changed and self.exists:
            self.closed = True
            return

        try:
            os.makedirs(os.path.dirname(self.fs_path))
        except OSError:
            pass

        with atomic_open(self.fs_path, 'wb') as f:
            for chunk in serialize(self.iteritems(), encoding='utf-8'):
                f.write(chunk)

        self.closed = True

    def delete(self, recursive=False):
        """Deletes the record.  The default behavior is to remove the
        immediate item only (and all of its attachments).

        If a delete cannot be performed, an error is generated.
        """
        if self.closed:
            return
        self._delete_this = True
        self._recursive_delete = recursive

    def _real_delete(self):
        # If this is already an attachment, then we can just delete the
        # metadata and the attachment file, and bail.  The parameters do
        # not matter in that case.
        if self.is_attachment:
            for fn in self.fs_path, self.fs_path[:-3]:
                try:
                    os.unlink(fn)
                except OSError:
                    pass
            return

        directory = os.path.dirname(self.fs_path)
        try:
            os.unlink(self.fs_path)
        except OSError:
            pass

        # Recursive deletes are done through shutil.rmtree, in that case
        # we just bail entirely.
        if self._recursive_delete:
            try:
                shutil.rmtree(directory)
            except (OSError, IOError):
                pass
            return

        try:
            attachments = os.listdir(directory)
        except OSError:
            attachments = []
        for filename in attachments:
            filename = os.path.join(directory, filename)
            if os.path.isfile(filename):
                try:
                    os.unlink(filename)
                except OSError:
                    pass

        try:
            os.rmdir(directory)
        except OSError:
            pass
