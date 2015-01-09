import re
import os
import uuid
import errno
import hashlib
import operator
import functools
import posixpath

from weakref import ref as weakref
from itertools import islice, chain

from jinja2 import Undefined, is_undefined
from jinja2.utils import LRUCache

from lektor import metaformat
from lektor.utils import sort_normalize_string
from lektor.operationlog import get_oplog
from lektor.datamodel import load_datamodels, load_flowblocks
from lektor.thumbnail import make_thumbnail


_slashes_re = re.compile(r'/+')


def cleanup_path(path):
    return '/' + _slashes_re.sub('/', path.strip('/'))


def to_os_path(path):
    return path.strip('/').replace('/', os.path.sep)


def _require_oplog(record):
    oplog = get_oplog()
    if oplog is None:
        raise RuntimeError('This operation requires an oplog but none was '
                           'on the stack.')
    if oplog.pad is not record.pad:
        raise RuntimeError('The oplog on the stack does not match the '
                           'pad of the record.')
    return oplog


@functools.total_ordering
class _CmpHelper(object):

    def __init__(self, value, reverse):
        self.value = value
        self.reverse = reverse

    @staticmethod
    def coerce(a, b):
        if isinstance(a, basestring) and isinstance(b, basestring):
            return sort_normalize_string(a), sort_normalize_string(b)
        if type(a) is type(b):
            return a, b
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

    def contains(self, item):
        return _ContainmentExpr(self, _auto_wrap_expr(item))

    def startswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: unicode(a).lower().startswith(unicode(b).lower()))

    def endswith(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
            lambda a, b: unicode(a).lower().endswith(unicode(b).lower()))

    def startswith_cs(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: unicode(a).startswith(unicode(b)))

    def endswith_cs(self, other):
        return _BinExpr(self, _auto_wrap_expr(other),
                        lambda a, b: unicode(a).endswith(unicode(b)))


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


class _ContainmentExpr(_Expr):

    def __init__(self, seq, item):
        self.__seq = seq
        self.__item = item

    def __eval__(self, record):
        seq = self.__seq.__eval__(record)
        item = self.__item.__eval__(record)
        if isinstance(item, Record):
            item = item['_id']
        return item in seq


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


F = _RecordQueryProxy()


class Record(object):

    def __init__(self, pad, data):
        self._pad = weakref(pad)
        self._data = data
        self._fast_source_hash = None

    cache_classification = 'record'

    @property
    def source_filename(self):
        raise NotImplementedError()

    def get_dependent_name(self, suffix):
        directory, filename = posixpath.split(self['_path'])
        basename, ext = posixpath.splitext(filename)
        return posixpath.join(directory, '%s@%s%s' % (
            basename,
            suffix,
            ext,
        ))

    @property
    def pad(self):
        rv = self._pad()
        if rv is not None:
            return rv
        raise AttributeError('The pad went away')

    @property
    def datamodel(self):
        """Returns the data model for this record."""
        try:
            return self.pad.db.datamodels[self._data['_model']]
        except LookupError:
            # If we cannot find the model we fall back to the default one.
            return self.pad.db.default_model

    @property
    def is_exposed(self):
        """This is `true` if the record is exposed, `false` otherwise.  If
        a record does not set this itself, it's inherited from the parent
        record.  If no record has this defined in the direct line to the
        root, then a default of `True` is assumed.
        """
        expose = self._data['_expose']
        if is_undefined(expose):
            if not self.datamodel.expose:
                return False
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

    def resolve_url_path(self, url_path):
        """Given a URL path as list this resolves the most appropriate
        direct child and returns the list of remaining items.  If no
        match can be found, the result is `None`.
        """

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

    def iter_child_records(self):
        return iter(())

    def __getitem__(self, name):
        return self._data[name]

    def __setitem__(self, name, value):
        self.pad.cache.persist_if_cached(self)
        self._data[name] = value

    def __delitem__(self, name):
        self.pad.cache.persist_if_cached(self)
        del self._data[name]

    def __repr__(self):
        return '<%s model=%r path=%r>' % (
            self.__class__.__name__,
            self['_model'],
            self['_path'],
        )


class Page(Record):
    """This represents a loaded record."""

    cache_classification = 'page'

    @property
    def source_filename(self):
        return self.pad.db.get_fs_path(self['_path'], record_type='record')

    def iter_dependent_filenames(self):
        yield self.source_filename

    @property
    def url_path(self):
        url_path = Record.url_path.__get__(self)
        if url_path[-1:] != '/':
            url_path += '/'
        return url_path

    def is_child_of(self, path):
        this_path = cleanup_path(self['_path']).split('/')
        crumbs = cleanup_path(path).split('/')
        return this_path[:len(crumbs)] == crumbs

    def resolve_url_path(self, url_path):
        if not url_path:
            return self

        for idx in xrange(len(url_path)):
            piece = '/'.join(url_path[:idx + 1])
            child = self.children.filter(F._slug == piece).first()
            if child is None:
                attachment = self.attachments.filter(F._slug == piece).first()
                if attachment is None:
                    continue
                node = attachment
            else:
                node = child

            rv = node.resolve_url_path(url_path[idx + 1:])
            if rv is not None:
                return rv

    @property
    def parent(self):
        """The parent of the record."""
        this_path = self._data['_path']
        parent_path = posixpath.dirname(this_path)
        if parent_path != this_path:
            return self.pad.db.get_page(
                parent_path, self.pad,
                persist=self.pad.cache.is_persistent(self))

    @property
    def children(self):
        """Returns a query for all the children of this record.  Optionally
        a child path can be specified in which case the children of a sub
        path are queried.
        """
        repl_query = self.datamodel.get_child_replacements(self)
        if repl_query is not None:
            return repl_query
        return Query(path=self['_path'], pad=self.pad)

    def find_page(self, path):
        """Finds a child page."""
        return self.children.get(path)

    @property
    def attachments(self):
        """Returns a query for the attachments of this record."""
        return AttachmentsQuery(path=self['_path'], pad=self.pad)

    def iter_child_records(self):
        return chain(self.children, self.attachments)


class Attachment(Record):
    """This represents a loaded attachment."""

    cache_classification = 'attachment'

    @property
    def source_filename(self):
        return self.pad.db.get_fs_path(self['_path'], record_type='attachment')

    @property
    def attachment_filename(self):
        return self.pad.db.get_fs_path(self['_path'], record_type='base')

    @property
    def parent(self):
        """The associated record for this attachment."""
        return self.pad.db.get_page(
            self._data['_attachment_for'], self.pad,
            persist=self.pad.cache.is_persistent(self))

    def iter_dependent_filenames(self):
        # We only want to yield the source filename if it actually exists.
        # For attachments it's very likely that this is not the case in
        # case no metadata was defined.
        if os.path.isfile(self.source_filename):
            yield self.source_filename
        yield self.attachment_filename


class Image(Attachment):
    """Specific class for image attachments."""

    def thumbnail(self, width, height=None):
        return make_thumbnail(_require_oplog(self),
            self.attachment_filename, self.url_path,
            width=width, height=height)


attachment_classes = {
    'image': Image,
}


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

    def _get(self, id):
        """Low level record access."""
        return self.pad.db.get_page('%s/%s' % (self.path, id),
                                    self.pad, persist=True)

    def _iterate(self):
        """Low level record iteration."""
        for record in self.pad.db.iter_pages(self.path, self.pad):
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

    def get_order_by(self):
        """Returns the order that should be used."""
        if self._order_by is not None:
            return self._order_by
        base_record = self.pad.db.get_page(self.path, self.pad)
        if base_record is not None:
            return base_record.datamodel.child_config.order_by

    def __iter__(self):
        """Iterates over all records matched."""
        iterable = self._iterate()

        order_by = self.get_order_by()
        if order_by:
            iterable = sorted(
                iterable, key=lambda x: x.get_sort_key(order_by))

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
        for item in self._iterate():
            rv += 1
        return rv

    def get(self, id):
        """Gets something by the local path.  This ignores all other
        filtering that might be applied on the query.
        """
        if not self._pristine:
            raise RuntimeError('The query object is not pristine')
        return self._get(id)

    def __nonzero__(self):
        return self.first() is not None

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.path,
        )


class AttachmentsQuery(Query):

    @property
    def images(self):
        """Filters to images."""
        return self.filter(F._attachment_type == 'image')

    @property
    def videos(self):
        """Filters to videos."""
        return self.filter(F._attachment_type == 'video')

    @property
    def audio(self):
        """Filters to audio."""
        return self.filter(F._attachment_type == 'audio')

    def _get(self, id):
        """Low level record access."""
        return self.pad.db.get_attachment(
            '%s/%s' % (self.path, id), self.pad, persist=True)

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

    def __init__(self, env):
        self.env = env
        self.datamodels = load_datamodels(env)
        self.flowblocks = load_flowblocks(env)

    @property
    def default_model(self):
        """The empty datamodel."""
        if 'page' in self.datamodels:
            return self.datamodels['page']
        return self.datamodels['none']

    def get_fs_path(self, path, record_type):
        """Returns the file system path for a given database path with a
        specific record type.  The following record types are available:

        - ``'base'``: the folder containing the record is targeted.
        - ``'record'``: the content file of a record is targeted.
        - ``'attachment'``: the content file of a specific attachment is
          targeted.
        """
        fn_base = os.path.join(self.env.root_path, 'content', to_os_path(path))
        if record_type == 'base':
            return fn_base
        elif record_type == 'record':
            return os.path.join(fn_base, 'contents.lr')
        elif record_type == 'attachment':
            return fn_base + '.lr'
        raise TypeError('Unknown record type %r' % record_type)

    def load_raw_data(self, path, record_type):
        """Internal helper that loads the raw record data."""
        path = cleanup_path(path)

        try:
            rv = {}
            fn = self.get_fs_path(path, record_type=record_type)
            with open(fn, 'rb') as f:
                for key, lines in metaformat.tokenize(f, encoding='utf-8'):
                    rv[key] = u''.join(lines)

            rv['_path'] = path
            rv['_id'] = posixpath.basename(path)

            return rv
        except IOError as e:
            if e.errno == errno.ENOENT:
                return

    def postprocess_record(self, record, persist):
        # Automatically fill in slugs
        if is_undefined(record['_slug']):
            parent = record.parent
            if parent:
                slug = parent.datamodel.get_default_child_slug(record)
            else:
                slug = ''
            record['_slug'] = slug
        else:
            record['_slug'] = record['_slug'].strip('/')

        # Automatically fill in templates
        if is_undefined(record['_template']):
            record['_template'] = record.datamodel.id + '.html'

        # Fill in the global ID
        gid_hash = hashlib.md5()
        node = record
        while node is not None:
            gid_hash.update(node['_id'].encode('utf-8'))
            node = node.parent
        record['_gid'] = uuid.UUID(bytes=gid_hash.digest(), version=3)

        # Automatically cache
        if persist:
            record.pad.cache.persist(record)
        else:
            record.pad.cache.remember(record)

    def _track_record_dependency(self, record):
        oplog = get_oplog()
        if oplog is not None:
            for filename in record.iter_dependent_filenames():
                oplog.record_path_usage(filename)
            if record.datamodel.filename:
                oplog.record_path_usage(record.datamodel.filename)
        return record

    def _track_fs_dependency(self, fs_path):
        oplog = get_oplog()
        if oplog is not None:
            oplog.record_path_usage(fs_path)

    def get_datamodel(self, raw_data, pad, record_type='record'):
        """Returns the datamodel for a given raw record."""
        datamodel_name = (raw_data.get('_model') or '').strip()

        # If a datamodel is defined, we use it.
        if datamodel_name:
            return self.datamodels.get(datamodel_name, self.default_model)

        parent = posixpath.dirname(raw_data['_path'])
        datamodel_name = None

        # If we hit the root, and there is no model defined we need
        # to make sure we do not recurse onto ourselves.
        if parent != raw_data['_path']:
            parent_obj = self.get_page(parent, pad)
            if parent_obj is not None:
                if record_type == 'record':
                    datamodel_name = parent_obj.datamodel.child_config.model
                elif record_type == 'attachment':
                    datamodel_name = parent_obj.datamodel.attachment_config.model
                else:
                    raise TypeError('Invalid record type')

        # Pick default datamodel name
        if datamodel_name is None and record_type == 'record':
            datamodel_name = posixpath.basename(raw_data['_path']
                ).split('.')[0].replace('-', '_').lower()

        if datamodel_name is None:
            return self.default_model
        return self.datamodels.get(datamodel_name, self.default_model)

    def get_page(self, path, pad, persist=False):
        """Low-level interface for fetching a single record."""
        path = cleanup_path(path)
        rv = pad.cache['page', path]
        if rv is not None:
            return self._track_record_dependency(rv)

        raw_data = self.load_raw_data(path, 'record')
        if raw_data is None:
            return None

        datamodel = self.get_datamodel(raw_data, pad)
        rv = Page(pad, datamodel.process_raw_data(raw_data, pad))
        self.postprocess_record(rv, persist)
        return self._track_record_dependency(rv)

    def iter_pages(self, path, pad):
        """Low-level interface for iterating over records."""
        path = cleanup_path(path)
        fs_path = self.get_fs_path(path, 'base')
        self._track_fs_dependency(fs_path)

        try:
            files = os.listdir(fs_path)
            files.sort(key=lambda x: x.lower())
        except OSError:
            return
        for filename in files:
            if self.env.is_uninteresting_filename(filename) or \
               not os.path.isdir(os.path.join(fs_path, filename)):
                continue

            this_path = posixpath.join(path, filename)
            record = self.get_page(this_path, pad)
            if record is not None:
                yield record

    def get_attachment_type(self, path):
        """Gets the attachment type for a path."""
        return self.env.config['ATTACHMENT_TYPES'].get(
            posixpath.splitext(path)[1])

    def get_attachment_class(self, attachment_type):
        """Returns the class for the given attachment type."""
        return attachment_classes.get(attachment_type, Attachment)

    def get_attachment(self, path, pad, persist=False):
        """Low-level interface for fetching a single attachment."""
        path = cleanup_path(path)
        rv = pad.cache['attachment', path]
        if rv is not None:
            return self._track_record_dependency(rv)

        raw_data = self.load_raw_data(path, 'attachment')
        if raw_data is None:
            raw_data = {'_model': None, '_path': path,
                        '_id': posixpath.basename(path)}
        raw_data['_attachment_for'] = posixpath.dirname(path)
        if '_attachment_type' not in raw_data:
            raw_data['_attachment_type'] = self.get_attachment_type(path)
        cls = self.get_attachment_class(raw_data['_attachment_type'])

        datamodel = self.get_datamodel(raw_data, pad, 'attachment')
        rv = cls(pad, datamodel.process_raw_data(raw_data, pad))
        self.postprocess_record(rv, persist)
        return self._track_record_dependency(rv)

    def iter_attachments(self, path, pad):
        """Low-level interface for iterating over attachments."""
        path = cleanup_path(path)
        fs_path = self.get_fs_path(path, 'base')
        self._track_fs_dependency(fs_path)
        try:
            files = os.listdir(fs_path)
            files.sort(key=lambda x: x.lower())
        except OSError:
            return
        for filename in files:
            if self.env.is_uninteresting_filename(filename) or \
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


class RecordCache(object):

    def __init__(self, ephemeral_cache_size=500):
        self.persistent = {}
        self.ephemeral = LRUCache(ephemeral_cache_size)

    def is_persistent(self, record):
        cache_key = record.cache_classification, record['_path']
        return cache_key in self.persistent

    def remember(self, record):
        cache_key = record.cache_classification, record['_path']
        if cache_key in self.persistent or cache_key in self.ephemeral:
            return
        self.ephemeral[cache_key] = record

    def persist(self, record):
        cache_key = record.cache_classification, record['_path']
        self.persistent[cache_key] = record
        try:
            del self.ephemeral[cache_key]
        except KeyError:
            pass

    def persist_if_cached(self, record):
        cache_key = record.cache_classification, record['_path']
        if cache_key in self.ephemeral:
            self.persist(record)

    def __getitem__(self, key):
        rv = self.persistent.get(key)
        if rv is not None:
            return rv
        rv = self.ephemeral.get(key)
        if rv is not None:
            return rv


class Pad(object):
    """A pad keeps cached information for the database on a local level
    so that concurrent access can see different values if needed.
    """

    def __init__(self, db):
        self.db = db
        self.cache = RecordCache(db.env.config['EPHEMERAL_RECORD_CACHE_SIZE'])

    def resolve_url_path(self, url_path, include_unexposed=False):
        """Given a URL path this will find the correct record which also
        might be an attachment.  If a record cannot be found or is unexposed
        the return value will be `None`.
        """
        node = self.root

        pieces = cleanup_path(url_path).strip('/').split('/')
        if pieces == ['']:
            pieces = []

        rv = node.resolve_url_path(pieces)
        if rv is not None and (include_unexposed or rv.is_exposed):
            return rv

    @property
    def root(self):
        """The root page of the database."""
        return self.db.get_page('/', pad=self, persist=True)

    def query(self, path=None):
        """Queries the database either at root level or below a certain
        path.  This is the recommended way to interact with toplevel data.
        The alternative is to work with the :attr:`root` document.
        """
        return Query(path='/' + (path or '').strip('/'), pad=self)

    def get(self, path):
        """Loads an element by path."""
        return self.db.get_page('/' + path.strip('/'), pad=self,
                                persist=True)
