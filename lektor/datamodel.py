import posixpath
from lektor import types, metaformat


class ChildConfig(object):

    def __init__(self, enabled=True, model=None, order_by=None):
        self.enabled = enabled
        self.model = model
        self.order_by = order_by


class PaginationConfig(object):

    def __init__(self, enabled=False, per_page=None,
                 url_suffix='/page/{{ page }}'):
        self.enabled = enabled
        self.per_page = per_page
        self.url_suffix = url_suffix


class AttachmentConfig(object):

    def __init__(self, enabled=True, model=None, order_by=None):
        self.enabled = enabled
        self.model = model
        self.order_by = order_by


class Field(object):

    def __init__(self, name, label=None, type=None):
        if type is None:
            type = types.builtin_types['string']
        self.name = name
        if label is None:
            label = name.title().replace('_', ' ')
        self.label = label
        self.type = type

    def deserialize_value(self, value):
        raw_value = types.RawValue(self.name, value, field=self)
        return self.type.value_from_raw(raw_value)

    def serialize_value(self, value):
        return self.type.value_to_raw(value)

    def __repr__(self):
        return '<%s %r type=%r>' % (
            self.__class__.__name__,
            self.name,
            self.type,
        )


class DataModel(object):

    def __init__(self, id, name, contained=False, child_config=None,
                 attachment_config=None, pagination_config=None, fields=None):
        self.id = id
        self.name = name
        self.contained = contained
        if child_config is None:
            child_config = ChildConfig()
        self.child_config = child_config
        if attachment_config is None:
            attachment_config = AttachmentConfig()
        self.attachment_config = attachment_config
        if pagination_config is None:
            pagination_config = PaginationConfig()
        self.pagination_config = pagination_config
        if fields is None:
            fields = []
        self.fields = fields

        # This is an internal mapping of the key names to the actual field
        # which also includes the system fields.  This is primarily used
        # for fast internal operations.
        self._field_map = dict((x.name, x) for x in fields)
        for key, field in system_fields.iteritems():
            self._field_map[key] = field

    def read_record(self, iterable, path, keys=None):
        """Given an iterable of contents this reads the fields from it and
        returns it as dictionary.  If explicit keys are provided the
        processing will stop at an early point if all keys have been
        processed.  This allows fetching meta data from the file without
        having to process the entire file.

        The return value will be a standard dictionary.

        Usually this is not actually used by instead the cache interface
        from the database is utilized.
        """
        rv = {}

        if keys is None:
            keys = self._field_map.keys()
        keys_missing = set(keys)

        for key, lines in metaformat.tokenize(iterable, interesting_keys=keys):
            if lines is not None and key in self._field_map:
                rv[key] = self._field_map[key].deserialize_value(u''.join(lines))
                keys_missing.discard(key)
                if not keys_missing:
                    break

        for key in keys or ():
            if key not in rv and key in self._field_map:
                rv[key] = self._field_map[key].deserialize_value(None)

        rv['_path'] = path
        rv['_local_path'] = posixpath.basename(path)
        rv['_model'] = self.id

        return rv

    def process_raw_record(self, raw_record):
        """Given a raw record from a cache this processes the item and
        returns a record dictionary.
        """
        rv = {}
        for field in self._field_map.itervalues():
            value = raw_record.get(field.name)
            rv[field.name] = field.deserialize_value(value)
        rv['_model'] = self.id
        return rv

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.id,
        )


def datamodel_from_ini(id, inifile):
    def _parse_order(value):
        if not value:
            return None
        return [x for x in [x.strip() for x in value.strip().split(',')] if x]

    return DataModel(
        id=id,
        name=inifile.get('model.name', id.title().replace('_', ' ')),
        contained=inifile.get_bool('model.contained'),
        child_config=ChildConfig(
            enabled=inifile.get_bool('children.enabled', True),
            model=inifile.get('children.model'),
            order_by=_parse_order(inifile.get('children.order_by')),
        ),
        attachment_config=AttachmentConfig(
            enabled=inifile.get_bool('attachments.enabled', True),
            model=inifile.get('attachments.model'),
            order_by=_parse_order(inifile.get('attachments.order_by')),
        ),
        pagination_config=PaginationConfig(
            enabled=inifile.get_bool('pagination.enabled', False),
            per_page=inifile.get_int('pagination.per_page', 20),
            url_suffix=inifile.get('pagination.url_suffix'),
        ),
        fields=[
            Field(
                name=sect.split('.', 1)[1],
                label=inifile.get(sect + '.label'),
                type=types.builtin_types[inifile.get(sect + '.type')],
            ) for sect in inifile.sections() if sect.startswith('fields.')
        ]
    )


system_fields = {}


def add_system_field(name, type):
    system_fields[name] = Field(name, type=types.builtin_types[type])


add_system_field('_path', type='string')
add_system_field('_local_path', type='string')
add_system_field('_model', type='string')
add_system_field('_template', type='string')
add_system_field('_attachment_for', type='string')
add_system_field('_attachment_type', type='string')


empty_model = DataModel('none', 'No Model')
