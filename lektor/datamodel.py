import os

from inifile import IniFile

from lektor import types
from lektor.utils import slugify
from lektor.environment import Expression, FormatExpression


class ChildConfig(object):

    def __init__(self, enabled=True, slug_format=None, model=None,
                 order_by=None, replaced_with=None):
        self.enabled = enabled
        self.slug_format = slug_format
        self.model = model
        self.order_by = order_by
        self.replaced_with = replaced_with


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

    def __init__(self, env, name, label=None, type=None, options=None):
        if type is None:
            type = types.builtin_types['string']
        self.name = name
        if label is None:
            label = name.title().replace('_', ' ')
        self.label = label
        if options is None:
            options = {}
        self.type = type(env, options)

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
                 pagination_config=None, fields=None, parent=None):
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
        self.parent = parent

        # This is an internal mapping of the key names to the actual field
        # which also includes the system fields.  This is primarily used
        # for fast internal operations.
        self._field_map = dict((x.name, x) for x in fields)
        for key, field_type in system_fields.iteritems():
            self._field_map[key] = Field(env, name=key, type=field_type)

        self._child_slug_tmpl = None
        self._child_replacements = None

    def get_default_child_slug(self, record):
        """Formats out the child slug."""
        slug_format = self.child_config.slug_format
        if slug_format is None:
            return slugify(record['_id'])

        if self._child_slug_tmpl is None or \
           self._child_slug_tmpl[0] != slug_format:
            self._child_slug_tmpl = (
                slug_format,
                FormatExpression(self.env, slug_format)
            )

        return '_'.join(self._child_slug_tmpl[1].evaluate(
            record.pad, this=record).strip().split()).strip('/')

    def get_child_replacements(self, record):
        """Returns the query that should be used as replacement for the
        actual children.
        """
        replaced_with = self.child_config.replaced_with
        if replaced_with is None:
            return None

        if self._child_replacements is None or \
           self._child_replacements[0] != replaced_with:
            self._child_replacements = (
                replaced_with,
                Expression(self.env, replaced_with)
            )

        return self._child_replacements[1].evaluate(record.pad, this=record)

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


def datamodel_data_from_ini(id, inifile):
    def _parse_order(value):
        value = (value or '').strip()
        if not value:
            return None
        return [x for x in [x.strip() for x in value.strip().split(',')] if x]

    return dict(
        filename=inifile.filename,
        id=id,
        parent=inifile.get('model.inherits'),
        name=inifile.get('model.name', id.title().replace('_', ' ')),
        contained=inifile.get_bool('model.contained', default=None),
        expose=inifile.get_bool('model.expose', default=None),
        child_config=dict(
            enabled=inifile.get_bool('children.enabled', default=None),
            slug_format=inifile.get('children.slug_format'),
            model=inifile.get('children.model'),
            order_by=_parse_order(inifile.get('children.order_by')),
            replaced_with=inifile.get('children.replaced_with'),
        ),
        attachment_config=dict(
            enabled=inifile.get_bool('attachments.enabled', default=None),
            model=inifile.get('attachments.model'),
            order_by=_parse_order(inifile.get('attachments.order_by')),
        ),
        pagination_config=dict(
            enabled=inifile.get_bool('pagination.enabled', default=None),
            per_page=inifile.get_int('pagination.per_page'),
            url_suffix=inifile.get('pagination.url_suffix'),
        ),
        fields=[
            (
                sect.split('.', 1)[1],
                inifile.section_as_dict(sect)
            ) for sect in inifile.sections() if sect.startswith('fields.')
        ]
    )


def datamodel_from_data(env, model_data, parent):
    def get_value(key):
        path = key.split('.')
        node = model_data
        for item in path:
            node = node.get(item)
        if node is not None:
            return node
        if parent is not None:
            node = parent
            for item in path:
                node = getattr(node, item)
            return node

    fields = []
    known_fields = set()

    for name, options in model_data['fields']:
        ty = types.builtin_types[options.get('field_type', 'string')]
        fields.append(Field(env=env, name=name,
                            label=options.get('label'), type=ty,
                            options=options))
        known_fields.add(name)

    if parent is not None:
        parent_fields = []
        for field in parent.fields:
            if field.name not in known_fields:
                parent_fields.append(field)
        fields = parent_fields + fields

    return DataModel(
        env,

        # data that never inherits
        filename=model_data['filename'],
        id=model_data['id'],
        parent=parent,
        name=model_data['name'],

        # direct data that can inherit
        contained=get_value('contained'),
        expose=get_value('expose'),
        child_config=ChildConfig(
            enabled=get_value('child_config.enabled'),
            slug_format=get_value('child_config.slug_format'),
            model=get_value('child_config.model'),
            order_by=get_value('child_config.order_by'),
            replaced_with=get_value('child_config.replaced_with'),
        ),
        attachment_config=AttachmentConfig(
            enabled=get_value('attachment_config.enabled'),
            model=get_value('attachment_config.model'),
            order_by=get_value('attachment_config.order_by'),
        ),
        pagination_config=PaginationConfig(
            enabled=get_value('pagination_config.enabled'),
            per_page=get_value('pagination_config.per_page'),
            url_suffix=get_value('pagination_config.url_suffix'),
        ),
        fields=fields,
    )


def load_datamodels(env):
    """Loads the datamodels for a specific environment."""
    path = os.path.join(env.root_path, 'models')
    data = {}

    for filename in os.listdir(path):
        if not filename.endswith('.ini') or filename[:1] in '_.':
            continue
        fn = os.path.join(path, filename)
        if os.path.isfile(fn):
            model_id = filename[:-4].decode('ascii', 'replace')
            inifile = IniFile(fn)
            data[model_id] = datamodel_data_from_ini(model_id, inifile)

    rv = {}

    def get_model(model_id):
        model = rv.get(model_id)
        if model is not None:
            return model
        if model_id in data:
            return create_model(model_id)

    def create_model(model_id):
        model_data = data.get(model_id)
        if model_data is None:
            raise RuntimeError('Model %r not found' % model_id)

        if model_data['parent'] is not None:
            parent = get_model(model_data['parent'])
        else:
            parent = None

        rv[model_id] = mod = datamodel_from_data(env, model_data, parent)
        return mod

    for model_id in data.keys():
        get_model(model_id)

    return rv


system_fields = {}


def add_system_field(name, type):
    system_fields[name] = types.builtin_types[type]


add_system_field('_path', type='string')
add_system_field('_id', type='string')
add_system_field('_gid', type='uuid')
add_system_field('_model', type='string')
add_system_field('_template', type='string')
add_system_field('_slug', type='slug')
add_system_field('_expose', type='boolean')

add_system_field('_attachment_for', type='string')
add_system_field('_attachment_type', type='string')
