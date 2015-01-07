from lektor import types
from lektor.utils import slugify


class ChildConfig(object):

    def __init__(self, enabled=True, slug_format=None, model=None,
                 order_by=None):
        self.enabled = enabled
        self.slug_format = slug_format
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

    def __init__(self, name, label=None, type=None, options=None):
        if type is None:
            type = types.builtin_types['string']
        self.name = name
        if label is None:
            label = name.title().replace('_', ' ')
        self.label = label
        if options is None:
            options = {}
        self.type = type(options)

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

    def __init__(self, env, id, name, filename=None, contained=False,
                 expose=True, child_config=None, attachment_config=None,
                 pagination_config=None, fields=None):
        self.env = env
        self.filename = filename
        self.id = id
        self.name = name
        self.contained = contained
        self.expose = expose
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

        self._child_slug_tmpl = None

    def get_default_child_slug(self, record):
        """Formats out the child slug."""
        slug_format = self.child_config.slug_format
        if slug_format is None:
            return slugify(record['_id'])

        if self._child_slug_tmpl is None or \
           self._child_slug_tmpl[0] != slug_format:
            self._child_slug_tmpl = (
                slug_format,
                self.env.compile_template(slug_format)
            )

        return '_'.join(self._child_slug_tmpl[1].render(
            page=record).strip().split()).strip('/')

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


def datamodel_from_ini(id, inifile, env):
    def _parse_order(value):
        if not value:
            return None
        return [x for x in [x.strip() for x in value.strip().split(',')] if x]

    return DataModel(env,
        filename=inifile.filename,
        id=id,
        name=inifile.get('model.name', id.title().replace('_', ' ')),
        contained=inifile.get_bool('model.contained'),
        expose=inifile.get_bool('model.expose', True),
        child_config=ChildConfig(
            enabled=inifile.get_bool('children.enabled', True),
            slug_format=inifile.get('children.slug_format'),
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
                options=inifile.section_as_dict(sect),
            ) for sect in inifile.sections() if sect.startswith('fields.')
        ]
    )


system_fields = {}


def add_system_field(name, type):
    system_fields[name] = Field(name, type=types.builtin_types[type])


add_system_field('_path', type='string')
add_system_field('_id', type='string')
add_system_field('_gid', type='uuid')
add_system_field('_model', type='string')
add_system_field('_template', type='string')
add_system_field('_slug', type='slug')
add_system_field('_expose', type='boolean')

add_system_field('_attachment_for', type='string')
add_system_field('_attachment_type', type='string')
