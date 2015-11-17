import mistune
import threading

from markupsafe import Markup

from lektor.types import Type
from lektor.context import get_ctx


_markdown_cache = threading.local()


class MarkdownConfig(object):

    def __init__(self):
        self.options = {}
        self.renderer_base = mistune.Renderer
        self.renderer_mixins = []

    def make_renderer(self):
        bases = tuple(self.renderer_mixins) + (self.renderer_base,)
        renderer_cls = type('renderer_cls', bases, {})
        return renderer_cls(**self.options)


def make_markdown(env):
    cfg = MarkdownConfig()
    env.plugin_controller.emit('markdown_config', config=cfg)
    renderer = cfg.make_renderer()
    return mistune.Markdown(renderer, **cfg.options)


def markdown_to_html(text):
    md = getattr(_markdown_cache, 'md', None)
    if md is None:
        ctx = get_ctx()
        if ctx is None:
            raise RuntimeError('Context is required for markdown rendering')
        md = make_markdown(ctx.env)
        _markdown_cache.md = md
    return Markup(md(text))


class Markdown(object):

    def __init__(self, source):
        self.source = source
        self._html = None

    @property
    def html(self):
        if self._html is not None:
            return self._html
        self._html = rv = markdown_to_html(self.source)
        return rv

    def __unicode__(self):
        return unicode(self.html)

    def __html__(self):
        return self.html


class MarkdownType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing markdown')
        return Markdown(raw.value)
