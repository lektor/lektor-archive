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
        attr['value'] = value or u''
        attr['type'] = self.type
        return html_element('input', attr)


class TextInputWidget(InputWidget):
    type = 'text'


class CheckboxWidget(InputWidget):
    type = 'checkbox'

    def __init__(self, field):
        InputWidget.__init__(self, field)

        self.label = field.type.options.get('checkbox_label')

    def render(self, value, **attr):
        attr['name'] = self.name
        attr['value'] = 'yes'
        if value and value.lower() in ('yes', 'true', '1'):
            attr['checked'] = True
        attr['type'] = self.type

        rv = html_element('input', attr)
        if self.label is not None:
            rv = Markup('<label>%s %s</label>' % (rv, self.label))

        return Markup('<div class="checkbox">%s</div>') % rv


class TextAreaWidget(Widget):

    def render(self, value, **attr):
        attr['name'] = self.name
        return html_element('textarea', attr) + \
            (value or u'') + Markup('</textarea>')
