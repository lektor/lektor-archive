import time
import click

from click import style

from werkzeug.local import LocalProxy, LocalStack
from contextlib import contextmanager


_reporter_stack = LocalStack()


class Reporter(object):

    def __init__(self, env, verbosity=0):
        self.env = env
        self.verbosity = verbosity

        self.builder_stack = []
        self.artifact_stack = []
        self.source_stack = []

    def push(self):
        _reporter_stack.push(self)

    def pop(self):
        _reporter_stack.pop()

    def __enter__(self):
        self.push()

    def __exit__(self, exc_type, exc_value, tb):
        self.pop()

    @property
    def builder(self):
        if self.builder_stack:
            return self.builder_stack[-1]

    @property
    def current_artifact(self):
        if self.artifact_stack:
            return self.artifact_stack[-1]

    @property
    def current_source(self):
        if self.source_stack:
            return self.source_stack[-1]

    @property
    def show_build_info(self):
        return self.verbosity >= 1

    @property
    def show_current_artifacts(self):
        return self.verbosity >= 2

    @property
    def show_artifact_internals(self):
        return self.verbosity >= 3

    @property
    def show_source_internals(self):
        return self.verbosity >= 3

    @property
    def show_debug_info(self):
        return self.verbosity >= 4

    @contextmanager
    def build(self, builder):
        now = time.time()
        self.builder_stack.append(builder)
        self.start_build()
        try:
            yield
        finally:
            self.builder_stack.pop()
            self.finish_build(now)

    def start_build(self):
        pass

    def finish_build(self, start_time):
        pass

    @contextmanager
    def build_artifact(self, artifact):
        now = time.time()
        self.artifact_stack.append(artifact)
        self.start_artifact_build()
        try:
            yield
        finally:
            self.artifact_stack.pop()
            self.finish_artifact_build(now)

    def start_artifact_build(self):
        pass

    def finish_artifact_build(self, start_time):
        pass

    def report_dependencies(self, dependencies):
        for dep in dependencies:
            self.report_debug_info('dependency', dep[1])

    def report_dirty_flag(self, value):
        pass

    def report_sub_artifact(self, artifact):
        pass

    def report_debug_info(self, key, value):
        pass

    def report_pruned_artifact(self, artifact_name):
        pass

    @contextmanager
    def process_source(self, source):
        now = time.time()
        self.source_stack.append(source)
        self.enter_source()
        try:
            yield
        finally:
            self.source_stack.pop()
            self.leave_source(now)

    def enter_source(self):
        pass

    def leave_source(self, start_time):
        pass


class NullReporter(Reporter):
    pass


class CliReporter(Reporter):

    def __init__(self, env, verbosity=0):
        Reporter.__init__(self, env, verbosity)
        self.indentation = 0

    def indent(self):
        self.indentation += 1

    def outdent(self):
        self.indentation -= 1

    def _write_line(self, text):
        click.echo(' ' * (self.indentation * 2) + text)

    def _write_kv_info(self, key, value):
        self._write_line('%s: %s' % (key, style(unicode(value), fg='yellow')))

    def start_build(self):
        self._write_line(style('Build started', fg='blue'))
        if not self.show_build_info:
            return
        self._write_line(style('  Tree: %s' % self.env.root_path, fg='blue'))
        self._write_line(style('  Output path: %s' %
                               self.builder.destination_path, fg='blue'))

    def finish_build(self, start_time):
        self._write_line(style('Build finished in %.2f sec' % (
            time.time() - start_time), fg='blue'))

    def start_artifact_build(self):
        artifact = self.current_artifact
        if artifact.is_current:
            if not self.show_current_artifacts:
                return
            sign = click.style('X', fg='cyan')
        else:
            sign = click.style('U', fg='green')
        self._write_line('%s %s' % (sign, artifact.artifact_name))

        self.indent()

    def finish_artifact_build(self, start_time):
        self.outdent()

    def report_dirty_flag(self, value):
        if self.show_artifact_internals and (value or self.show_debug_info):
            self._write_kv_info('forcing sources dirty', value)

    def report_sub_artifact(self, artifact):
        if self.show_artifact_internals:
            self._write_kv_info('sub artifact', artifact.artifact_name)

    def report_debug_info(self, key, value):
        if self.show_debug_info:
            self._write_kv_info(key, value)

    def enter_source(self):
        if not self.show_source_internals:
            return
        self._write_line('Source %s' % style(repr(
            self.current_source), fg='magenta'))
        self.indent()

    def leave_source(self, start_time):
        if self.show_source_internals:
            self.outdent()

    def report_pruned_artifact(self, artifact_name):
        self._write_line('%s %s' % (style('D', fg='red'), artifact_name))


null_reporter = NullReporter(None)


@LocalProxy
def reporter():
    rv = _reporter_stack.top
    if rv is None:
        rv = null_reporter
    return rv