def _process_buf(buf, encoding):
    for idx, line in enumerate(buf):
        line = line.decode(encoding)
        if line[:1] == '\\':
            line = line[1:]
        buf[idx] = line

    if buf and buf[-1][-1:] == '\n':
        buf[-1] = buf[-1][:-1]

    return buf[:]


def tokenize(iterable, interesting_keys=None, encoding='utf-8'):
    """This tokenizes an iterable of newlines as bytes into key value
    pairs out of the lektor bulk format.  By default it will process all
    fields, but optionally it can skip values of uninteresting keys and
    will instead yield `None`.  The values are left as list of decoded
    lines with their endings preserved.

    This will not perform any other processing on the data other than
    decoding and basic tokenizing.
    """
    key = []
    buf = []
    want_newline = False
    is_interesting = True

    def _flush_item():
        the_key = key[0]
        if not is_interesting:
            value = None
        else:
            value = _process_buf(buf, encoding)
        del key[:], buf[:]
        return the_key, value

    for line in iterable:
        line = line.rstrip(b'\r\n') + b'\n'

        if line.rstrip() == b'---':
            want_newline = False
            if key is not None:
                yield _flush_item()
        elif key:
            if want_newline:
                want_newline = False
                if not line.strip():
                    continue
            if is_interesting:
                buf.append(line)
        else:
            bits = line.split(b':', 1)
            if len(bits) == 2:
                key = [bits[0].strip().decode(encoding, 'replace')]
                if interesting_keys is None:
                    is_interesting = True
                else:
                    is_interesting = key[0] in interesting_keys
                if is_interesting:
                    first_bit = bits[1].strip('\t ')
                    if first_bit.strip():
                        buf = [first_bit]
                    else:
                        buf = []
                        want_newline = True

    if key is not None:
        yield _flush_item()
