from lektor.types import Type


class CheckboxesType(Type):

    def value_from_raw(self, raw):
        rv = [x.strip() for x in (raw.value or '').split(',')]
        if rv == ['']:
            rv = []
        return rv
