import threading
import markdown

from markupsafe import Markup

from lektor.types import Type


_markdown_cache = threading.local()


def markdown_to_html(text):
    md = getattr(_markdown_cache, 'md', None)
    if md is None:
        md = markdown.Markdown(
            output_format='html5',
            lazy_ol=False,
            extensions=[
                'markdown.extensions.headerid',
                'markdown.extensions.sane_lists',
                'markdown.extensions.tables',
            ]
        )
    else:
        md.reset()
    return Markup(md.convert(text))


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
