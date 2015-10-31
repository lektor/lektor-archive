import re

from jinja2 import is_undefined, Undefined, TemplateNotFound
from markupsafe import Markup

from lektor.types import Type
from lektor.metaformat import tokenize
from lektor.context import get_ctx
from lektor.environment import PRIMARY_ALT


_block_re = re.compile(r'^####\s*(.*?)\s*####\s*$')


def find_record_for_flowblock(blck):
    """The record that contains this flow block.  This might be unavailable
    in certain situations, it is however very useful when using the generic
    block template rendering.
    """
    ctx = get_ctx()
    if ctx is None:
        raise RuntimeError('Context unavailable')
    record = ctx.record
    if record is None:
        raise RuntimeError('Context does not point to a record')

    # It's only the correct record, if we are contained as a field in it.
    # This could be improved by making a better mapping for this on the
    # datamodel probably but it's good enough for the moment.
    for key, value in record.iter_fields():
        if isinstance(value, Flow):
            for other_blck in value.blocks:
                if other_blck is blck:
                    return record

    return Undefined('Associated record unavailable.', name='record')


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
        """The flowblock model that created this flow block."""
        return self.pad.db.flowblocks[self._data['_flowblock']]

    def __contains__(self, name):
        return name in self._data and not is_undefined(self._data[name])

    def __getitem__(self, name):
        # If any data of a flowblock is accessed, we record that we need
        # this dependency.
        ctx = get_ctx()
        if ctx is not None:
            ctx.record_dependency(self.flowblockmodel.filename)
        return self._data[name]

    def __html__(self):
        try:
            record = find_record_for_flowblock(self)
            return self.pad.db.env.render_template(
                ['blocks/%s.html' % self._data['_flowblock'],
                 'blocks/default.html'],
                pad=self.pad,
                this=self,
                alt=record and record.alt or None,
                values={'record': record}
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

    def __nonzero__(self):
        return bool(self.blocks)

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
        self.flow_blocks = set(
            x.strip() for x in options.get('flow_blocks', '').split(',')
            if x.strip()) or None
        self.default_flow_block = options.get('default_flow_block')

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
                if self.flow_blocks is not None and \
                   block not in self.flow_blocks:
                    continue
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

    def to_json(self, pad, alt=PRIMARY_ALT):
        rv = Type.to_json(self, pad, alt)

        blocks = {}
        default = self.default_flow_block
        for block_name, flowblock in pad.db.flowblocks.iteritems():
            if self.flow_blocks is not None \
               and block_name not in self.flow_blocks:
                continue
            if default is None and flowblock.default:
                default = block_name
            blocks[block_name] = flowblock.to_json(pad, alt)

        rv['flowblocks'] = blocks
        rv['default_flowblock'] = default

        return rv
