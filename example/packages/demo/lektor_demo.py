from lektor.pluginsystem import Plugin


class DemoPlugin(Plugin):
    name = 'Demo plugin'
    description = 'This is a demo plugin'

    def on_process_template_context(self, context, **extra):
        context['demo_value_from_plugin'] = 42
