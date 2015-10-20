import os
import re
import copy

import jinja2

from inifile import IniFile

from lektor.utils import tojson_filter, get_i18n_block
from lektor.context import url_to, site_proxy, config_proxy, get_ctx


# Special value that identifies a target to the primary alt
PRIMARY_ALT = '_primary'
DEFAULT_CONFIG = {
    'IMAGEMAGICK_EXECUTABLE': None,
    'LESSC_EXECUTABLE': None,
    'EPHEMERAL_RECORD_CACHE_SIZE': 500,
    'ATTACHMENT_TYPES': {
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
        '.htm': 'document',
        '.html': 'document',

        '.txt': 'text',
        '.log': 'text',
    },
    'SITE': {
        'name': None,
        'language': 'en',
    },
    'ALTERNATIVES': {},
    'PRIMARY_ALTERNATIVE': None,
    'SERVERS': {}
}


def update_config_from_ini(config, inifile):
    def set_simple(target, source_path):
        rv = config.get(source_path)
        if rv is not None:
            config[target] = rv

    set_simple(target='IMAGEMAGICK_EXECUTABLE',
               source_path='env.imagemagick_executable')
    set_simple(target='LESSC_EXECUTABLE',
               source_path='env.lessc_executable')

    config['ATTACHMENT_TYPES'].update(
        (k.encode('ascii', 'replace'), v.encode('ascii', 'replace'))
        for k, v in inifile.section_as_dict('attachment_types'))

    config['SITE'].update(inifile.section_as_dict('site'))

    for sect in inifile.sections():
        if sect.startswith('servers.'):
            server_id = sect.split('.')[1]
            config['SERVERS'][server_id] = inifile.section_as_dict(sect)
        elif sect.startswith('alternatives.'):
            alt = sect.split('.')[1]
            config['ALTERNATIVES'][alt] = {
                'name': get_i18n_block(inifile, 'alternatives.%s.name' % alt),
                'url_prefix': inifile.get('alternatives.%s.url_prefix' % alt),
                'url_suffix': inifile.get('alternatives.%s.url_suffix' % alt),
                'primary': inifile.get_bool('alternatives.%s.primary' % alt),
            }

    for alt, alt_data in config['ALTERNATIVES'].iteritems():
        if alt_data['primary']:
            config['PRIMARY_ALTERNATIVE'] = alt
            break
    else:
        if config['ALTERNATIVES']:
            raise RuntimeError('Alternatives defined but no primary set.')


# Special files that should always be ignored.
IGNORED_FILES = ['thumbs.db', 'desktop.ini']

# These files are important for artifacts and must not be ignored when
# they are built even though they start with dots.
SPECIAL_SOURCES = ['_htaccess', '_htpasswd']
SPECIAL_ARTIFACTS = ['.htaccess', '.htpasswd']


class ServerInfo(object):

    def __init__(self, id, name_i18n, target, enabled=True):
        self.id = id
        self.name_i18n = name_i18n
        self.target = target
        self.enabled = enabled

    @property
    def name(self):
        return self.name_i18n.get('en')

    @property
    def short_target(self):
        match = re.match(r'([a-z]+)://([^/]+)', self.target)
        if match is not None:
            protocol, server = match.groups()
            return '%s via %s' % (server, protocol)
        return self.target

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'target': self.target,
            'short_target': self.short_target,
            'enabled': self.enabled,
        }


class Expression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string('{{ __result__(%s) }}' % expr)

    def evaluate(self, pad=None, this=None, values=None):
        result = []
        def result_func(value):
            result.append(value)
            return u''
        values = self.env.make_default_tmpl_values(pad, this, values)
        values['__result__'] = result_func
        self.tmpl.render(values)
        return result[0]


class FormatExpression(object):

    def __init__(self, env, expr):
        self.env = env
        self.tmpl = env.jinja_env.from_string(expr)

    def evaluate(self, pad=None, this=None, values=None):
        values = self.env.make_default_tmpl_values(pad, this, values)
        return self.tmpl.render(values)


class CustomJinjaEnvironment(jinja2.Environment):

    def _load_template(self, name, globals):
        rv = jinja2.Environment._load_template(self, name, globals)
        ctx = get_ctx()
        if ctx is not None:
            ctx.record_dependency(rv.filename)
        return rv


class Config(object):

    def __init__(self, filename):
        self.filename = filename
        self.values = copy.deepcopy(DEFAULT_CONFIG)

        if os.path.isfile(filename):
            inifile = IniFile(filename)
            update_config_from_ini(self.values, inifile)

    def __getitem__(self, name):
        return self.values[name]

    @property
    def site_language(self):
        """The language of this site."""
        return self.values['SITE']['language']

    def get_servers(self, lang='en'):
        """Returns a list of servers (data translated to the given
        language).
        """
        rv = {}
        for server in self.values['SERVERS']:
            server_info = self.get_server(server, lang=lang)
            if server_info is None:
                continue
            rv[server] = server_info
        return rv

    def get_server(self, name, lang='en'):
        """Looks up a server info by name."""
        info = self.values['SERVERS'].get(name)
        if info is None:
            return None
        target = info.get('target')
        if target is None:
            return None
        return ServerInfo(
            id=name,
            name_i18n=get_i18n_block(info, 'name'),
            target=target,
            enabled=info.get('enabled', 'true').lower() in ('true', 'yes', '1'),
        )

    def is_valid_alternative(self, alt):
        """Checks if an alternative ID is known."""
        if alt == PRIMARY_ALT:
            return True
        return alt in self.values['ALTERNATIVES']

    def list_alternatives(self):
        """Returns a sorted list of alternative IDs."""
        return sorted(self.values['ALTERNATIVES'])

    def get_alternative(self, alt):
        """Returns the config setting of the given alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        return self.values['ALTERNATIVES'].get(alt)

    def get_alternative_url_prefixes(self):
        """Returns a list of alternative url prefixes by length."""
        items = [(v['url_prefix'].lstrip('/'), k)
                 for k, v in self.values['ALTERNATIVES'].iteritems()
                 if v['url_prefix']]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_suffixes(self):
        """Returns a list of alternative url suffixes by length."""
        items = [(v['url_suffix'].rstrip('/'), k)
                 for k, v in self.values['ALTERNATIVES'].iteritems()
                 if v['url_suffix']]
        items.sort(key=lambda x: -len(x[0]))
        return items

    def get_alternative_url_span(self, alt=PRIMARY_ALT):
        """Returns the URL span (prefix, suffix) for an alt."""
        if alt == PRIMARY_ALT:
            alt = self.primary_alternative
        cfg = self.values['ALTERNATIVES'].get(alt)
        if cfg is not None:
            return cfg['url_prefix'] or '', cfg['url_suffix'] or ''
        return '', ''

    @property
    def primary_alternative_is_rooted(self):
        """`True` if the primary alternative is sitting at the root of
        the URL handler.
        """
        primary = self.primary_alternative
        if primary is None:
            return True

        cfg = self.values['ALTERNATIVES'].get(primary)
        if not (cfg['url_prefix'] or '').lstrip('/') and \
           not (cfg['url_suffix'] or '').rstrip('/'):
            return True

        return False

    @property
    def primary_alternative(self):
        """The identifier that acts as primary alternative."""
        return self.values['PRIMARY_ALTERNATIVE']


def lookup_from_bag(*args):
    pieces = '.'.join(x for x in args if x)
    return site_proxy.databags.lookup(pieces)


class Environment(object):

    def __init__(self, root_path):
        self.root_path = os.path.abspath(root_path)

        self.config_filename = os.path.join(self.root_path, 'site.ini')

        self.jinja_env = CustomJinjaEnvironment(
            autoescape=self.select_jinja_autoescape,
            extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_'],
            loader=jinja2.FileSystemLoader(
                os.path.join(self.root_path, 'templates'))
        )

        from lektor.db import F
        self.jinja_env.filters.update(
            tojson=tojson_filter,
            # By default filters need to be side-effect free.  This is not
            # the case for this one, so we need to make it as a dummy
            # context filter so that jinja2 will not inline it.
            url=jinja2.contextfilter(lambda ctx, *a, **kw: url_to(*a, **kw)),
        )
        self.jinja_env.globals.update(
            F=F,
            url_to=url_to,
            site=site_proxy,
            config=config_proxy,
            bag=lookup_from_bag,
        )

    @property
    def asset_path(self):
        return os.path.join(self.root_path, 'assets')

    @property
    def temp_path(self):
        return os.path.join(self.root_path, 'temp')

    def load_config(self):
        """Loads the current config."""
        return Config(self.config_filename)

    def is_uninteresting_source_name(self, filename):
        """These files are always ignored when sources are built into
        artifacts.
        """
        fn = filename.lower()
        if fn in SPECIAL_ARTIFACTS or fn in SPECIAL_SOURCES:
            return False
        return filename[:1] in '._' or fn in IGNORED_FILES

    def is_ignored_artifact(self, asset_name):
        """This is used by the prune tool to figure out which files in the
        artifact folder should be ignored.  This is a bi
        """
        fn = asset_name.lower()
        if fn in SPECIAL_ARTIFACTS:
            return False
        return fn[:1] in '._' or fn in IGNORED_FILES

    def render_template(self, name, pad=None, this=None, values=None):
        ctx = self.make_default_tmpl_values(pad, this, values)
        return self.jinja_env.get_or_select_template(name).render(ctx)

    def make_default_tmpl_values(self, pad=None, this=None, values=None):
        values = dict(values or ())

        # This is already a global variable but we can inject it as a
        # local override if available.
        if pad is None:
            ctx = get_ctx()
            if ctx is not None:
                pad = ctx.pad
        if pad is not None:
            values['site'] = pad
        if this is not None:
            values['this'] = this
        return values

    def select_jinja_autoescape(self, filename):
        if filename is None:
            return False
        return filename.endswith(('.html', '.htm', '.xml', '.xhtml'))
