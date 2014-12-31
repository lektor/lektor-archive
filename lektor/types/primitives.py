import uuid
from datetime import date

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


class UuidType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing UUID')
        try:
            return uuid.UUID(raw.value)
        except Exception:
            return raw.bad_value('Invalid UUID')


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
        if raw.value is None:
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
        if raw.value is None:
            return raw.missing_value('Missing float value')
        try:
            return float(raw.value.strip())
        except ValueError:
            return raw.bad_value('Not an integer')


class BooleanType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing boolean')
        val = raw.value.strip().lower()
        if val in ('true', 'yes', '1'):
            return True
        elif val in ('false', 'no', '0'):
            return False
        else:
            return raw.bad_value('Bad boolean value')


class DateType(Type):

    def value_from_raw(self, raw):
        if raw.value is None:
            return raw.missing_value('Missing date')
        try:
            return date(*map(int, raw.value.split('-')))
        except Exception:
            return raw.bad_value('Bad date format')
