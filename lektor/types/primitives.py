from markupsafe import Markup

from lektor.types import Type


class StringType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing string')
        try:
            return raw.value.splitlines()[0].strip()
        except IndexError:
            return u''


class TextType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing text')
        return raw.value


class HtmlType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing HTML')
        return Markup(raw.value)


class IntegerType(Type):

    def value_from_raw(self, raw):
        if raw is None:
            return raw.missing_value('Missing integer value')
        try:
            return int(raw.value.strip())
        except ValueError:
            try:
                return int(float(raw.value.strip()))
            except ValueError:
                return raw.bad_value('Not an integer')


class FloatType(Type):

    def value_from_raw(self, raw):
        if raw is None:
            return raw.missing_value('Missing float value')
        try:
            return float(raw.value.strip())
        except ValueError:
            return raw.bad_value('Not an integer')
