from lektor.types import Type
from lektor.utils import slugify


class SortKeyType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing sort key')
        try:
            return int(raw.value.strip())
        except ValueError:
            return raw.bad_value('Bad sort key value')


class SlugType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing slug')
        return slugify(raw.value)
