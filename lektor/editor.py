import os
import shutil
import posixpath

from collections import OrderedDict

from lektor.metaformat import serialize
from lektor.utils import atomic_open, is_valid_id, secure_filename, \
     increment_filename
from lektor.environment import PRIMARY_ALT


implied_keys = set(['_id', '_path', '_gid', '_alt', '_attachment_for'])
possibly_implied_keys = set(['_model', '_template', '_attachment_type'])


class BadEdit(Exception):
    pass


class BadDelete(BadEdit):
    pass


def make_editor_session(pad, path, is_attachment=None, alt=PRIMARY_ALT,
                        datamodel=None):
    """Creates an editor session for the given path object."""
    if alt != PRIMARY_ALT and not pad.db.config.is_valid_alternative(alt):
        raise BadEdit('Attempted to edit an invalid alternative (%s)' % alt)

    raw_data = pad.db.load_raw_data(path, cls=OrderedDict, alt=alt)
    id = posixpath.basename(path)
    if not is_valid_id(id):
        raise BadEdit('Invalid ID')

    record = None
    exists = raw_data is not None
    if raw_data is None:
        raw_data = OrderedDict()

    if is_attachment is None:
        if not exists:
            is_attachment = False
        else:
            is_attachment = bool(raw_data.get('_attachment_for'))
    elif bool(raw_data.get('_attachment_for')) != is_attachment:
        raise BadEdit('The attachment flag passed is conflicting with the '
                      'record\'s attachment flag.')

    if exists:
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

    if exists:
        record = pad.instance_from_data(dict(raw_data), datamodel)

    for key in implied_keys:
        raw_data.pop(key, None)

    return EditorSession(pad, id, unicode(path), raw_data, datamodel, record,
                         exists, is_attachment, alt)


class EditorSession(object):

    def __init__(self, pad, id, path, original_data, datamodel, record,
                 exists=True, is_attachment=False, alt=PRIMARY_ALT):
        self.id = id
        self.pad = pad
        self.path = path
        self.record = record
        self.exists = exists
        self.original_data = original_data
        self.datamodel = datamodel
        self.is_root = path.strip('/') == ''
        self.alt = alt

        slug_format = None
        parent_name = posixpath.dirname(path)
        if parent_name != path:
            parent = pad.get(parent_name)
            if parent is not None:
                slug_format = parent.datamodel.child_config.slug_format
        if slug_format is None:
            slug_format = u'{{ this._id }}'
        self.slug_format = slug_format
        self.implied_attachment_type = None

        if is_attachment:
            self.implied_attachment_type = pad.db.get_attachment_type(path)

        self._data = {}
        self._changed = set()
        self._delete_this = False
        self._recursive_delete = False
        self.is_attachment = is_attachment
        self.closed = False

    def to_json(self):
        label = None
        label_i18n = None
        url_path = None
        if self.record is not None:
            label = self.record.record_label
            label_i18n = self.record.get_record_label_i18n()
            url_path = self.record.url_path
        else:
            label = self.id
        can_be_deleted = not self.datamodel.protected and not self.is_root
        return {
            'data': dict(self.iteritems()),
            'record_info': {
                'id': self.id,
                'path': self.path,
                'exists': self.exists,
                'label': label,
                'label_i18n': label_i18n,
                'url_path': url_path,
                'alt': self.alt,
                'is_attachment': self.is_attachment,
                'can_be_deleted': can_be_deleted,
                'slug_format': self.slug_format,
                'implied_attachment_type': self.implied_attachment_type,
                'default_template': self.datamodel.get_default_template_name(),
            },
            'datamodel': self.datamodel.to_json(self.pad),
        }

    def __contains__(self, key):
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __getitem__(self, key):
        if key in self._data:
            rv = self._data[key]
            if rv is None:
                raise KeyError(key)
            return rv
        return self.original_data[key]

    def __setitem__(self, key, value):
        old_value = self.original_data.get(key)
        if old_value != value:
            self._changed.add(key)
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
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).iteritems():
            self[key] = value

    def iteritems(self):
        done = set()

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

    __iter__ = iterkeys

    def __len__(self):
        return len(self.items())

    @property
    def fs_path(self):
        """The path to the record file on the file system."""
        base = self.pad.db.to_fs_path(self.path)
        suffix = '.lr'
        if self.alt != PRIMARY_ALT:
            suffix = '+%s%s' % (self.alt, suffix)
        if self.is_attachment:
            return base + suffix
        return os.path.join(base, 'contents' + suffix)

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
        if not self.closed:
            if self._delete_this:
                self._delete_impl()
            else:
                self._save_impl()
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

    def add_attachment(self, filename, fp):
        """Stores a new attachment.  Returns `None` if the file already"""
        if not self.exists:
            raise BadEdit('Record does not exist.')
        if self.is_attachment:
            raise BadEdit('Cannot attach something to an attachment.')
        directory = self.pad.db.to_fs_path(self.path)

        safe_filename = secure_filename(filename)

        while 1:
            fn = os.path.join(directory, safe_filename)
            if not os.path.isfile(fn):
                break
            safe_filename = increment_filename(fn)

        with atomic_open(fn, 'w') as f:
            shutil.copyfileobj(fp, f)
        return safe_filename

    def _delete_impl(self):
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

        try:
            os.unlink(self.fs_path)
        except OSError:
            pass

        # If we're not deleting the primary alt, we just want to delete
        # the contents file (which happened above) and then bail for the
        # rest.
        if self.alt != PRIMARY_ALT:
            return

        directory = os.path.dirname(self.fs_path)

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

    def _save_impl(self):
        if not self._changed and self.exists:
            return

        try:
            os.makedirs(os.path.dirname(self.fs_path))
        except OSError:
            pass

        with atomic_open(self.fs_path, 'wb') as f:
            for chunk in serialize(self.iteritems(), encoding='utf-8'):
                f.write(chunk)

    def __repr__(self):
        return '<%s %r%s%s>' % (
            self.__class__.__name__,
            self.path,
            self.alt != PRIMARY_ALT and ' alt=%r' % self.alt or '',
            not self.exists and ' new' or '',
        )
