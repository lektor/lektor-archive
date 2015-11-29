from jinja2 import Undefined

from werkzeug.local import LocalStack, LocalProxy

from lektor.reporter import reporter


_ctx_stack = LocalStack()


def url_to(*args, **kwargs):
    """Calculates a URL to another record."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError('No context found')
    return ctx.source.url_to(*args, **kwargs)


def get_asset_url(asset):
    """Calculates the asset URL relative to the current record."""
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError('No context found')
    asset = site_proxy.get_asset(asset)
    if asset is None:
        return Undefined('Asset not found')
    info = ctx.build_state.get_file_info(asset.source_filename)
    return '%s?h=%s' % (
        ctx.source.url_to('!' + asset.url_path),
        info.checksum[:8],
    )


@LocalProxy
def site_proxy():
    """Returns the current pad."""
    ctx = get_ctx()
    if ctx is None:
        return Undefined(hint='Cannot access the site from here', name='site')
    return ctx.pad


@LocalProxy
def config_proxy():
    """Returns the current config."""
    return site_proxy.db.config


def get_ctx():
    """Returns the current context."""
    return _ctx_stack.top


def get_locale(default='en_US'):
    """Returns the current locale."""
    ctx = get_ctx()
    if ctx is not None:
        rv = ctx.locale
        if rv is not None:
            return rv
    return default


class Context(object):
    """The context is a thread local object that provides the system with
    general information about in which state it is.  The context is created
    whenever a source is processed and can be accessed by template engine and
    other things.

    It's considered read and write and also accumulates changes that happen
    during processing of the object.
    """

    def __init__(self, artifact):
        self.artifact = artifact
        self.source = artifact.source_obj

        self.build_state = self.artifact.build_state
        self.pad = self.build_state.pad

        # Processing information
        self.referenced_dependencies = set()
        self.sub_artifacts = []

        self.flow_block_render_stack = []

        # General cache system where other things can put their temporary
        # stuff in.
        self.cache = {}

    @property
    def env(self):
        """The environment of the context."""
        return self.pad.db.env

    @property
    def record(self):
        """If the source is a record it will be available here."""
        rv = self.source
        if rv is not None and rv.source_classification == 'record':
            return rv

    @property
    def locale(self):
        """Returns the current locale if it's available, otherwise `None`."""
        source = self.source
        if source is not None:
            alt_cfg = self.pad.db.config['ALTERNATIVES'].get(source.alt)
            if alt_cfg:
                return alt_cfg['locale']

    def push(self):
        _ctx_stack.push(self)

    def pop(self):
        _ctx_stack.pop()

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

    def sub_artifact(self, *args, **kwargs):
        """Decorator version of :func:`add_sub_artifact`."""
        def decorator(f):
            self.add_sub_artifact(build_func=f, *args, **kwargs)
            return f
        return decorator

    def add_sub_artifact(self, artifact_name, build_func=None,
                         sources=None, source_obj=None):
        """Sometimes it can happen that while building an artifact another
        artifact needs building.  This function is generally used to record
        this request.
        """
        aft = self.build_state.new_artifact(
            artifact_name=artifact_name,
            sources=sources,
            source_obj=source_obj,
        )
        self.sub_artifacts.append((aft, build_func))
        reporter.report_sub_artifact(aft)

    def record_dependency(self, filename):
        """Records a dependency from processing."""
        self.referenced_dependencies.add(filename)
