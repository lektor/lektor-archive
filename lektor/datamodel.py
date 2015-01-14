import os
import errno

from inifile import IniFile

from lektor import types
from lektor.utils import slugify
from lektor.environment import Expression, FormatExpression


class ChildConfig(object):

    def __init__(self, enabled=None, slug_format=None, model=None,
                 order_by=None, replaced_with=None):
        if enabled is None:
            enabled = True
        self.enabled = enabled
        self.slug_format = slug_format
        self.model = model
        self.order_by = order_by
        self.replaced_with = replaced_with


class PaginationConfig(object):

    def __init__(self, enabled=None, per_page=None, url_suffix=None):
        if enabled is None:
            enabled = True
        self.enabled = enabled
        self.per_page = per_page
        self.url_suffix = url_suffix


class AttachmentConfig(object):

    def __init__(self, enabled=None, model=None, order_by=None):
        if enabled is None:
            enabled = True
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
        self.widget = self.type.widget_class(self)

    def deserialize_value(self, value, pad=None):
        raw_value = types.RawValue(self.name, value, field=self, pad=pad)
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

    def __init__(self, env, id, name, label=None,
                 filename=None, contained=None,
                 expose=None, child_config=None, attachment_config=None,
                 pagination_config=None, fields=None, parent=None):
        self.env = env
        self.filename = filename
        self.id = id
        self.name = name
        self.label = label
        if contained is None:
            contained = False
        self.contained = contained
        if expose is None:
            expose = True
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

        # This is a mapping of the key names to the actual field which
        # also includes the system fields.  This is primarily used for
        # fast internal operations but also the admin.
        self.field_map = dict((x.name, x) for x in fields)
        for key, (ty, opts) in system_fields.iteritems():
            self.field_map[key] = Field(env, name=key, type=ty, options=opts)

        self._child_slug_tmpl = None
        self._child_replacements = None
        self._label_tmpl = None

    def format_record_label(self, record):
        """Returns the label for a given record."""
        label = self.label
        if label is None:
            return None

        if self._label_tmpl is None or \
           self._label_tmpl[0] != label:
            self._label_tmpl = (
                label,
                FormatExpression(self.env, label)
            )

        return self._label_tmpl[1].evaluate(record.pad, this=record)

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

    def get_default_template_name(self):
        return self.id + '.html'

    @property
    def has_own_children(self):
        return self.child_config.replaced_with is None and \
               self.child_config.enabled

    @property
    def has_own_attachments(self):
        return self.attachment_config.enabled

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

    def process_raw_data(self, raw_data, pad=None):
        rv = {}
        for field in self.field_map.itervalues():
            value = raw_data.get(field.name)
            rv[field.name] = field.deserialize_value(value, pad=pad)
        rv['_model'] = self.id
        return rv

    def to_json(self, d, pad):
        rv = {}
        for field in self.field_map.itervalues():
            value = d.get(field.name)
            rv[field.name] = field.type.value_to_json(value, pad=pad)
        return rv

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.id,
        )


class FlowBlockModel(object):

    def __init__(self, env, id, name, filename=None, fields=None):
        self.env = env
        self.id = id
        self.name = name
        self.filename = filename
        if fields is None:
            fields = []
        self.fields = fields

        self.field_map = dict((x.name, x) for x in fields)
        self.field_map['_flowblock'] = Field(
            env, name='_flowblock', type=types.builtin_types['string'])

    def process_raw_data(self, raw_data, pad=None):
        rv = {}
        for field in self.field_map.itervalues():
            value = raw_data.get(field.name)
            rv[field.name] = field.deserialize_value(value, pad=pad)
        rv['_flowblock'] = self.id
        return rv

    def to_json(self, d, pad):
        rv = {}
        for field in self.field_map.itervalues():
            value = d.get(field.name)
            rv[field.name] = field.type.value_to_json(value, pad=pad)
        return rv

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.id,
        )


def fielddata_from_ini(inifile):
    return [(
        sect.split('.', 1)[1],
        inifile.section_as_dict(sect)
    ) for sect in inifile.sections() if sect.startswith('fields.')]


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
        label=inifile.get('model.label'),
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
        fields=fielddata_from_ini(inifile),
    )


def flowblock_data_from_ini(id, inifile):
    return dict(
        filename=inifile.filename,
        id=id,
        name=inifile.get('block.name', id.title().replace('_', ' ')),
        fields=fielddata_from_ini(inifile),
    )


def fields_from_data(env, data, parent_fields=None):
    fields = []
    known_fields = set()

    for name, options in data:
        ty = types.builtin_types[options.get('type', 'string')]
        fields.append(Field(env=env, name=name,
                            label=options.get('label'), type=ty,
                            options=options))
        known_fields.add(name)

    if parent_fields is not None:
        prepended_fields = []
        for field in parent_fields:
            if field.name not in known_fields:
                prepended_fields.append(field)
        fields = prepended_fields + fields

    return fields


def datamodel_from_data(env, model_data, parent=None):
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

    fields = fields_from_data(env, model_data['fields'],
                              parent and parent.fields or None)

    return DataModel(
        env,

        # data that never inherits
        filename=model_data['filename'],
        id=model_data['id'],
        parent=parent,
        name=model_data['name'],

        # direct data that can inherit
        label=get_value('label'),
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


def flowblock_from_data(env, block_data):
    return FlowBlockModel(
        env,
        filename=block_data['filename'],
        id=block_data['id'],
        name=block_data['name'],
        fields=fields_from_data(env, block_data['fields']),
    )


def iter_inis(path):
    try:
        for filename in os.listdir(path):
            if not filename.endswith('.ini') or filename[:1] in '_.':
                continue
            fn = os.path.join(path, filename)
            if os.path.isfile(fn):
                base = filename[:-4].decode('ascii', 'replace')
                inifile = IniFile(fn)
                yield base, inifile
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise


def load_datamodels(env):
    """Loads the datamodels for a specific environment."""
    path = os.path.join(env.root_path, 'models')
    data = {}

    for model_id, inifile in iter_inis(path):
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

    rv['none'] = DataModel(env, 'none', 'None')

    return rv


def load_flowblocks(env):
    """Loads all the flow blocks for a specific environment."""
    path = os.path.join(env.root_path, 'flowblocks')
    rv = {}

    for flowblock_id, inifile in iter_inis(path):
        rv[flowblock_id] = flowblock_from_data(env,
            flowblock_data_from_ini(flowblock_id, inifile))

    return rv


system_fields = {}


def add_system_field(name, **opts):
    ty = types.builtin_types[opts.pop('type')]
    system_fields[name] = (ty, opts)


# The full path of the record
add_system_field('_path', type='string')

# The local ID (within a folder) of the record
add_system_field('_id', type='string')

# The global ID of the record (only really useful for caching i guess)
add_system_field('_gid', type='uuid')

# the model that defines the data of the record
add_system_field('_model', type='string')

# the template that should be used for rendering if not hidden and exposed
add_system_field('_template', type='string')

# the slug that should be used for this record.  This is added below the
# slug of the parent.
add_system_field('_slug', type='slug')

# by default all records are exposed.  If a record is set to unexposed
# then it is not rendered and neither are any of its children.
add_system_field('_expose', type='boolean',
                 checkbox_label='Should this page and its children be exposed?')

# this is similar to expose but only affects the record itself.  This can
# be used to create a "folder" that is actually empty but the children
# itself are exposed.  Useful for error pages and similar things.
add_system_field('_hidden', type='boolean',
                 checkbox_label='Should this page itself be hidden?')

# Useful fields for attachments.
add_system_field('_attachment_for', type='string')
add_system_field('_attachment_type', type='string')
