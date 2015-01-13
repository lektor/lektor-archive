from markupsafe import Markup, escape


def html_element(name, attr, close=False):
    buf = [u'<%s%s' % (close and u'/' or u'', name)]
    for key, value in attr.iteritems():
        key = key.replace('_', '-').rstrip('-')
        if value is True:
            buf.append(u' ' + key)
        else:
            buf.append(u' %s="%s"' % (key, escape(value)))
    buf.append(u'>')
    return Markup(u''.join(buf))


class Widget(object):

    def __init__(self, field):
        self.field = field

    @property
    def name(self):
        return self.field.name

    def render(self, value, **attr):
        raise NotImplementedError()


class InputWidget(Widget):
    type = 'text'

    def render(self, value, **attr):
        attr['name'] = self.name
        attr['value'] = value
        attr['type'] = self.type
        return html_element('input', attr)


class TextInputWidget(InputWidget):
    type = 'text'


class TextAreaWidget(Widget):

    def render(self, value, **attr):
        attr['name'] = self.name
        return html_element('textarea', attr) + value + Markup('</textarea>')
