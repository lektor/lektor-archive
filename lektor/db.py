import re
import os
import errno
import operator
import functools
import posixpath

from jinja2 import Undefined, is_undefined

from inifile import IniFile
from itertools import islice

from lektor import metaformat
from lektor.utils import slugify
from lektor.datamodel import datamodel_from_ini, empty_model


_slashes_re = re.compile(r'/+')


def cleanup_path(path):
    return '/' + _slashes_re.sub('/', path.strip('/'))


def to_os_path(path):
    return path.strip('/').replace('/', os.path.sep)


def load_datamodels(path):
    rv = {}
    for filename in os.listdir(path):
        if not filename.endswith('.ini') or filename[:1] in '_.':
            continue
        fn = os.path.join(path, filename)
        if os.path.isfile(fn):
            model_id = filename[:-4].decode('ascii', 'replace')
            inifile = IniFile(fn)
            rv[model_id] = datamodel_from_ini(model_id, inifile)
    rv['none'] = empty_model
    return rv


@functools.total_ordering
class _CmpHelper(object):

    def __init__(self, value, reverse):
        self.value = value
        self.reverse = reverse

    @staticmethod
    def coerce(a, b):
        if type(a) is type(b):
            return a, b
        if isinstance(a, basestring) and isinstance(b, basestring):
            return unicode(a), unicode(b)
        if isinstance(a, (int, long, float)):
            try:
                return a, type(a)(b)
            except (ValueError, TypeError, OverflowError):
                pass
        if isinstance(b, (int, long, float)):
            try:
                return type(b)(a), b
            except (ValueError, TypeError, OverflowError):
                pass
        return a, b

    def __eq__(self, other):
        a, b = self.coerce(self.value, other.value)
        return a == b

    def __lt__(self, other):
        a, b = self.coerce(self.value, other.value)
        if self.reverse:
            return b < a
        return a < b


def _auto_wrap_expr(value):
    if isinstance(value, _Expr):
        return value
    return _Literal(value)


class _Expr(object):

    def __eval__(self, record):
        return record

    def __eq__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.eq)

    def __ne__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.ne)

    def __and__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.and_)

    def __or__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.or_)

    def __gt__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.gt)

    def __ge__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.ge)

    def __lt__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.lt)

    def __le__(self, other):
        return _BinExpr(self, _auto_wrap_expr(other), operator.le)

    def startswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: unicode(a).startswith(unicode(b)))

    def endswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: unicode(a).endswith(unicode(b)))

    def istartswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: unicode(a).lower().startswith(unicode(b).lower()))

    def iendswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: unicode(a).lower().endswith(unicode(b).lower()))


class _Literal(_Expr):

    def __init__(self, value):
        self.__value = value

    def __eval__(self, record):
        return self.__value


class _BinExpr(_Expr):

    def __init__(self, left, right, op):
        self.__left = left
        self.__right = right
        self.__op = op

    def __eval__(self, record):
        return self.__op(
            self.__left.__eval__(record),
            self.__right.__eval__(record)
        )


class _RecordQueryField(_Expr):

    def __init__(self, field):
        self.__field = field

    def __eval__(self, record):
        try:
            return record[self.__field]
        except KeyError:
            return Undefined(obj=record, name=self.__field)


class _RecordQueryProxy(object):

    def __getattr__(self, name):
        if name[:2] != '__':
            return _RecordQueryField(name)
        raise AttributeError(name)

    def __getitem__(self, name):
        try:
            return self.__getattr__(name)
        except AttributeError:
            raise KeyError(name)


rec = _RecordQueryProxy()


class _BaseRecord(object):

    def __init__(self, pad, data):
        self.pad = pad
        self._data = data

    @property
    def datamodel(self):
        """Returns the data model for this record."""
        try:
            return self.pad.db.datamodels[self._data['_model']]
        except LookupError:
            raise AttributeError('Data model is unavailable')

    @property
    def is_exposed(self):
        """This is `true` if the record is exposed, `false` otherwise.  If
        a record does not set this itself, it's inherited from the parent
        record.  If no record has this defined in the direct line to the
        root, then a default of `True` is assumed.
        """
        expose = self['_expose']
        if is_undefined(expose):
            if self.parent is None:
                return True
            return self.parent.is_exposed
        return expose

    @property
    def url_path(self):
        """The target path where the record should end up."""
        bits = []
        node = self
        while node is not None:
            bits.append(node['_slug'])
            node = node.parent
        bits.reverse()
        return '/' + '/'.join(bits).strip('/')

    def __getitem__(self, name):
        return self._data[name]

    def get_sort_key(self, fields):
        """Returns a sort key for the given field specifications specific
        for the data in the record.
        """
        rv = [None] * len(fields)
        for idx, field in enumerate(fields):
            if field[:1] == '-':
                field = field[1:]
                reverse = True
            else:
                field = field.lstrip('+')
                reverse = False
            rv[idx] = _CmpHelper(self._data.get(field), reverse)
        return rv

    def to_dict(self):
        """Returns a clone of the internal data dictionary."""
        return dict(self._data)

    def __repr__(self):
        return '<%s model=%r path=%r>' % (
            self.__class__.__name__,
            self['_model'],
            self['_path'],
        )


class Record(_BaseRecord):
    """This represents a loaded record."""

    @property
    def parent(self):
        """The parent of the record."""
        this_path = self._data['_path']
        parent_path = posixpath.dirname(this_path)
        if parent_path != this_path:
            return self.pad.db.get_record(parent_path, self.pad)

    @property
    def children(self):
        """Returns a query for all the children of this record.  Optionally
        a child path can be specified in which case the children of a sub
        path are queried.
        """
        return Query(path=self['_path'], pad=self.pad)

    @property
    def attachments(self):
        """Returns a query for the attachments of this record."""
        return AttachmentsQuery(path=self['_path'], pad=self.pad)


class Attachment(_BaseRecord):
    """This represents a loaded attachment."""

    @property
    def parent(self):
        """The associated record for this attachment."""
        return self.pad.db.get_record(self._data['_attachment_for'], self.pad)


class Query(object):

    def __init__(self, path, pad):
        self.path = path
        self.pad = pad
        self._order_by = None
        self._filters = None
        self._pristine = True
        self._limit = None
        self._offset = None

    def _clone(self, mark_dirty=False):
        """Makes a flat copy but keeps the other data on it shared."""
        rv = object.__new__(self.__class__)
        rv.__dict__.update(self.__dict__)
        if mark_dirty:
            rv._pristine = False
        return rv

    def _get(self, local_path):
        """Low level record access."""
        return self.pad.db.get_record('%s/%s' % (self.path, local_path),
                                      self.pad)

    def _iterate(self):
        """Low level record iteration."""
        for record in self.pad.db.iter_records(self.path, self.pad):
            for filter in self._filters or ():
                if not filter.__eval__(record):
                    break
            else:
                yield record

    def filter(self, expr):
        """Filters records by an expression."""
        rv = self._clone(mark_dirty=True)
        rv._filters = list(self._filters or ())
        rv._filters.append(expr)
        return rv

    def __iter__(self):
        """Iterates over all records matched."""
        iterable = self._iterate()
        if self._order_by:
            iterable = sorted(
                iterable, key=lambda x: x.get_sort_key(self._order_by))

        if self._offset is not None or self._limit is not None:
            iterable = islice(iterable, self._offset or 0, self._limit)

        for item in iterable:
            yield item

    def first(self):
        """Loads all matching records as list."""
        return next(iter(self), None)

    def all(self):
        """Loads all matching records as list."""
        return list(self)

    def order_by(self, *fields):
        """Sets the ordering of the query."""
        rv = self._clone()
        rv._order_by = fields or None
        return rv

    def offset(self, offset):
        """Sets the ordering of the query."""
        rv = self._clone(mark_dirty=True)
        rv._offset = offset
        return rv

    def limit(self, limit):
        """Sets the ordering of the query."""
        rv = self._clone(mark_dirty=True)
        rv._limit = limit
        return rv

    def count(self):
        """Counts all matched objects."""
        rv = 0
        for item in self:
            rv += 1
        return rv

    def get(self, local_path):
        """Gets something by the local path.  This ignores all other
        filtering that might be applied on the query.
        """
        if not self._pristine:
            raise RuntimeError('The query object is not pristine')
        return self._get(local_path)


class AttachmentsQuery(Query):

    def images(self):
        """Filters to images."""
        return self.filter(rec._attachment_type == 'image')

    def videos(self):
        """Filters to videos."""
        return self.filter(rec._attachment_type == 'video')

    def audio(self):
        """Filters to audio."""
        return self.filter(rec._attachment_type == 'audio')

    def _get(self, local_path):
        """Low level record access."""
        return self.pad.db.get_attachment(
            '%s/%s' % (self.path, local_path), self.pad)

    def _iterate(self):
        for attachment in self.pad.db.iter_attachments(self.path, self.pad):
            for filter in self._filters or ():
                if not filter.__eval__(attachment):
                    break
            else:
                yield attachment


class Database(object):
    """This provides higher-level access to the flat file database which is
    usde by Lektor.  However for most intents and purposes the actual data
    access happens through the :class:`Pad`.
    """

    attachment_types = {
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.gif': 'image',
        '.tif': 'image',
        '.tiff': 'image',
        '.bmp': 'image',

        '.avi': 'video',
        '.mpg': 'video',
        '.mpeg': 'video',
        '.wmv': 'video',
        '.ogv': 'video',

        '.mp3': 'audio',
        '.wav': 'audio',
        '.ogg': 'audio',

        '.pdf': 'document',
        '.doc': 'document',
        '.docx': 'document',

        '.txt': 'text',
    }

    def __init__(self, root_path):
        self.root_path = os.path.abspath(root_path)
        self.datamodels = load_datamodels(os.path.join(root_path, 'models'))

    def get_fs_path(self, path, record_type):
        """Returns the file system path for a given database path with a
        specific record type.  The following record types are available:

        - ``'base'``: the folder containing the record is targeted.
        - ``'record'``: the content file of a record is targeted.
        - ``'attachment'``: the content file of a specific attachment is
          targeted.
        """
        fn_base = os.path.join(self.root_path, 'content', to_os_path(path))
        if record_type == 'base':
            return fn_base
        elif record_type == 'record':
            return os.path.join(fn_base, 'contents.lr')
        elif record_type == 'attachment':
            return fn_base + '.lr'
        raise TypeError('Unknown record type %r' % record_type)

    def load_raw_record(self, path, record_type):
        """Internal helper that loads the raw record data."""
        path = cleanup_path(path)

        try:
            rv = {}
            fn = self.get_fs_path(path, record_type=record_type)
            with open(fn, 'rb') as f:
                for key, lines in metaformat.tokenize(f):
                    rv[key] = u''.join(lines)

            rv['_path'] = path
            rv['_local_path'] = posixpath.basename(path)

            if '_slug' not in rv:
                rv['_slug'] = slugify(rv['_local_path'])

            return rv
        except IOError as e:
            if e.errno == errno.ENOENT:
                return

    def get_datamodel(self, raw_record, pad, record_type='record'):
        """Returns the datamodel for a given raw record."""
        datamodel_name = (raw_record.get('_model') or '').strip()

        # If a datamodel is defined, we use it.
        if datamodel_name:
            return self.datamodels.get(datamodel_name, empty_model)

        parent = posixpath.dirname(raw_record['_path'])

        # If we hit the root, and there is no model defined we need
        # to make sure we do not recurse onto ourselves.
        if parent == raw_record['_path']:
            return empty_model

        parent_obj = self.get_record(parent, pad)
        if parent_obj is None:
            return empty_model

        if record_type == 'record':
            datamodel_name = parent_obj.datamodel.child_config.model
        elif record_type == 'attachment':
            datamodel_name = parent_obj.datamodel.attachment_config.model
        else:
            raise TypeError('Invalid record type')

        if datamodel_name is None:
            return empty_model
        return self.datamodels.get(datamodel_name, empty_model)

    def get_record(self, path, pad):
        """Low-level interface for fetching a single record."""
        path = cleanup_path(path)
        cache_key = ('record', path)
        rv = pad.cache.get(cache_key)
        if rv is not None:
            return rv

        raw_record = self.load_raw_record(path, 'record')
        if raw_record is None:
            return None

        datamodel = self.get_datamodel(raw_record, pad)
        rv = Record(pad, datamodel.process_raw_record(raw_record))
        pad.cache[cache_key] = rv
        return rv

    def iter_records(self, path, pad):
        """Low-level interface for iterating over records."""
        path = cleanup_path(path)
        fs_path = self.get_fs_path(path, 'base')
        try:
            files = os.listdir(fs_path)
            files.sort(key=lambda x: x.lower())
        except OSError:
            return
        for filename in files:
            if filename[:1] in '._' or \
               not os.path.isdir(os.path.join(fs_path, filename)):
                continue

            this_path = posixpath.join(path, filename)
            record = self.get_record(this_path, pad)
            if record is not None:
                yield record

    def get_attachment_type(self, path):
        """Gets the attachment type for a path."""
        return self.attachment_types.get(posixpath.splitext(path)[1])

    def get_attachment(self, path, pad):
        """Low-level interface for fetching a single attachment."""
        path = cleanup_path(path)
        cache_key = ('attachment', path)
        rv = pad.cache.get(cache_key)
        if rv is not None:
            return rv

        raw_record = self.load_raw_record(path, 'attachment')
        if raw_record is None:
            raw_record = {'_model': None, '_path': path,
                          '_local_path': posixpath.basename(path)}
        raw_record['_attachment_for'] = posixpath.dirname(path)
        if '_attachment_type' not in raw_record:
            raw_record['_attachment_type'] = self.get_attachment_type(path)

        datamodel = self.get_datamodel(raw_record, pad, 'attachment')
        rv = Attachment(pad, datamodel.process_raw_record(raw_record))
        pad.cache[cache_key] = rv
        return rv

    def iter_attachments(self, path, pad):
        """Low-level interface for iterating over attachments."""
        path = cleanup_path(path)
        fs_path = self.get_fs_path(path, 'base')
        try:
            files = os.listdir(fs_path)
            files.sort(key=lambda x: x.lower())
        except OSError:
            return
        for filename in files:
            if filename[:1] in '._' or \
               filename[-3:] == '.lr' or \
               not os.path.isfile(os.path.join(fs_path, filename)):
                continue

            this_path = posixpath.join(path, filename)
            attachment = self.get_attachment(this_path, pad)
            if attachment is not None:
                yield attachment

    def new_pad(self):
        """Creates a new pad for this database."""
        return Pad(self)


class Pad(object):
    """A pad keeps cached information for the database on a local level
    so that concurrent access can see different values if needed.
    """

    def __init__(self, db):
        self.db = db
        self.cache = {}

    @property
    def root(self):
        """The root record of the database."""
        return self.db.get_record('/', pad=self)

    def query(self, path=None):
        """Queries the database either at root level or below a certain
        path.  This is the recommended way to interact with toplevel data.
        The alternative is to work with the :attr:`root` document.
        """
        return Query(path='/' + (path or '').strip('/'), pad=self)

    def get(self, path):
        """Loads an element by path."""
        return self.db.get_record('/' + path.strip('/'), pad=self)
