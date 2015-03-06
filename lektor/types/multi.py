from lektor.types import Type
from lektor.environment import Expression, FormatExpression


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

    def __init__(self, env, options):
        source = options.get('source')
        if source is not None:
            self.source = Expression(env, source)
            self.choices = None
            item_key = options.get('item_key') or '{{ this._id }}'
            item_label = options.get('item_label') or '{{ this._id }}'
        else:
            self.source = None
            self.choices = parse_choices(options.get('choices'))
            item_key = options.get('item_key') or '{{ this.0 }}'
            item_label = options.get('item_label') or '{{ this.1 }}'
        self.item_key = FormatExpression(env, item_key)
        self.item_label = FormatExpression(env, item_label)

    def iter_choices(self, pad):
        if self.choices is not None:
            iterable = self.choices
        else:
            iterable = self.source.evaluate(pad)

        for item in iterable:
            key = self.item_key.evaluate(pad, this=item)
            label = self.item_label.evaluate(pad, this=item)
            yield key, label


class MultiType(Type):

    def __init__(self, env, options):
        Type.__init__(self, env, options)
        self.sources = ChoiceSource(env, options)

    def to_json(self, pad):
        rv = Type.to_json(self, pad)
        rv['sources'] = [[key, value] for key, value in
                         self.sources.iter_choices(pad)]
        return rv


class CheckboxesType(MultiType):

    def value_from_raw(self, raw):
        rv = [x.strip() for x in (raw.value or '').split(',')]
        if rv == ['']:
            rv = []
        return rv
