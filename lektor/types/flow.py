import re

from jinja2 import is_undefined, TemplateNotFound
from markupsafe import Markup

from lektor.types import Type
from lektor.metaformat import tokenize


_block_re = re.compile(r'^####\s*(.*?)\s*####\s*$')


class BadFlowBlock(Exception):

    def __init__(self, message):
        self.message = message


class FlowBlock(object):
    """Represents a flowblock for the template."""

    def __init__(self, data, pad):
        self._data = data
        self.pad = pad

    @property
    def flowblockmodel(self):
        return self.pad.db.flowblocks[self._data['_flowblock']]

    def __contains__(self, name):
        return name in self._data and not is_undefined(self._data[name])

    def __getitem__(self, name):
        return self._data[name]

    def __html__(self):
        try:
            return self.pad.db.env.render_template(
                ['blocks/%s.html' % self._data['_flowblock'],
                 'blocks/default.html'],
                pad=self.pad,
                this=self
            )
        except TemplateNotFound:
            return Markup('[could not find snippet template]')

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self['_flowblock'],
        )


class Flow(object):

    def __init__(self, blocks):
        self.blocks = blocks

    def __html__(self):
        return Markup(u'\n\n'.join(x.__html__() for x in self.blocks))

    def __repr__(self):
        return '<%s %r>' % (
            self.__class__.__name__,
            self.blocks,
        )


def process_flowblock_data(raw_value):
    lineiter = iter(raw_value.splitlines(True))
    block = None
    buf = []
    blocks = []

    for line in lineiter:
        # Until we found the first block, we ignore leading whitespace.
        if block is None and not line.strip():
            continue

        # Find a new block start
        block_start = _block_re.match(line)
        if block_start is None:
            if block is None:
                raise BadFlowBlock('Did not find beginning of flow block')
        else:
            if block is not None:
                blocks.append((block, buf))
                buf = []
            block = block_start.group(1)
            continue
        buf.append(line)

    if block is not None:
        blocks.append((block, buf))

    return blocks


class FlowType(Type):

    def __init__(self, env, options):
        Type.__init__(self, env, options)

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing flow')
        if raw.pad is None:
            return raw.missing_value('Flow value was technically present '
                                     'but used in a place where it cannot '
                                     'be used.')

        db = raw.pad.db
        rv = []

        try:
            for block, block_lines in process_flowblock_data(raw.value):
                # Unknown flow blocks are skipped for the moment
                flowblock = db.flowblocks.get(block)
                if flowblock is None:
                    continue

                d = {}
                for key, lines in tokenize(block_lines):
                    d[key] = u''.join(lines)
                rv.append(FlowBlock(
                    flowblock.process_raw_data(d, pad=raw.pad),
                    pad=raw.pad
                ))
        except BadFlowBlock as e:
            return raw.bad_value(e.message)

        return Flow(rv)
