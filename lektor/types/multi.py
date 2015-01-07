from lektor.types import Type


def parse_choices(s):
    rv = []
    items = (s or '').split(',')
    missing_keys = False

    for item in items:
        if '=' in item:
            key, value = item.split('=', 1)
            key = key.strip()
            if key.isdigit():
                key = int(key)
            rv.append((key, value.strip()))
        else:
            rv.append((None, item.strip()))
            missing_keys = True

    if missing_keys and items:
        last_integer = None
        for idx, (key, value) in enumerate(rv):
            if isinstance(key, (int, long)):
                last_integer = key
            elif last_integer is not None:
                last_integer += 1
            if key is None:
                if last_integer is not None:
                    rv[idx] = (last_integer, value)
                else:
                    rv[idx] = (value, value)

    return rv


class ChoiceSource(object):

    def __init__(self, options):
        source = options.get('source')
        if source is not None:
            self.source = source
            self.choices = None
            self.item_key = options.get('item_key') or '{{ item._id }}'
            self.item_label = options.get('item_label') or '{{ item._id }}'
        else:
            self.source = None
            self.choices = parse_choices(options.get('choices'))
            self.item_key = options.get('item_key') or '{{ item.0 }}'
            self.item_label = options.get('item_label') or '{{ item.1 }}'

    def iter_choices(self, pad):
        env = pad.db.env
        if self.choices is not None:
            iterable = self.choices
        else:
            iterable = env.eval_source_expr(self.source, pad=pad)

        for item in iterable:
            key = env.eval_string_expr(self.item_key, pad=pad, item=item)
            label = env.eval_string_expr(self.item_label, pad=pad, item=item)
            yield key, label


class MultiType(Type):

    def __init__(self, options):
        Type.__init__(self, options)
        self.sources = ChoiceSource(options)


class CheckboxesType(MultiType):

    def value_from_raw(self, raw):
        rv = [x.strip() for x in (raw.value or '').split(',')]
        if rv == ['']:
            rv = []
        return rv
