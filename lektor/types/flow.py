import re

from lektor.types import Type
from lektor.metaformat import tokenize


_block_re = re.compile(r'^####\s*(.*?)\s*####\s*$')


class BadFlowBlock(Exception):

    def __init__(self, message):
        self.message = message


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

        for block, block_lines in process_flowblock_data(raw.value):
            # Unknown flow blocks are skipped for the moment
            flowblock = db.flowblocks.get(block)
            if flowblock is None:
                continue

            d = {}
            for key, lines in tokenize(block_lines):
                d[key] = u''.join(lines)
            rv.append(flowblock.process_raw_data(d, pad=raw.pad))

        return rv
