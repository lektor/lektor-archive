import os
import sys
import json
import time
import click
import pkg_resources

from .i18n import get_default_lang, is_valid_language
from .utils import secure_url
from .project import discover_project, load_project


version = pkg_resources.get_distribution('Lektor').version


class Context(object):

    def __init__(self):
        self._project_path = None
        self._project = None
        self._env = None
        self._ui_lang = None

    def _get_ui_lang(self):
        rv = self._ui_lang
        if rv is None:
            rv = self._ui_lang = get_default_lang()
        return rv

    def _set_ui_lang(self, value):
        self._ui_lang = value

    ui_lang = property(_get_ui_lang, _set_ui_lang)
    del _get_ui_lang, _set_ui_lang

    def set_project_path(self, value):
        self._project_path = value
        self._project = None

    def get_project(self):
        if self._project is not None:
            return self._project
        if self._project_path is not None:
            rv = load_project(self._project_path)
        else:
            rv = discover_project()
        if rv is None:
            raise click.UsageError('Could not find project')
        self._project = rv
        return rv

    def get_default_output_path(self):
        return os.path.join(click.get_app_dir('Lektor'), 'build-cache',
                            self.get_project().id)

    def get_env(self):
        if self._env is not None:
            return self._env
        from lektor.environment import Environment
        env = Environment(self.get_project())
        self._env = env
        return env

    def new_pad(self):
        from lektor.db import Database
        env = self.get_env()
        return Database(env).new_pad()


pass_context = click.make_pass_decorator(Context, ensure=True)


def validate_language(ctx, param, value):
    if value is not None and not is_valid_language(value):
        raise click.BadParameter('Unsupported language "%s".' % value)
    return value


@click.group()
@click.option('--project', type=click.Path(),
              help='The path to the lektor project to work with.')
@click.option('--language', default=None, callback=validate_language,
              help='The UI language to use (overrides autodetection).')
@click.version_option(prog_name='Lektor', version=version)
@pass_context
def cli(ctx, project=None, language=None):
    """The lektor management application.

    This command can invoke lektor locally and serve up the website.  It's
    intended for local development of websites.
    """
    if language is not None:
        ctx.ui_lang = language
    if project is not None:
        ctx.set_project_path(project)


@cli.command('build')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@click.option('--watch', is_flag=True, help='If this is enabled the build '
              'process goes into an automatic loop where it watches the '
              'file system for changes and rebuilds.')
@click.option('--prune/--no-prune', default=True, help='Controls if old '
              'artifacts should be pruned.  This is the default.')
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@click.option('--source-info-only', is_flag=True,
              help='Instead of building only updates the source infos.  The '
              'source info is used by the web admin panel to quickly find '
              'information about the source files (for instance jump to '
              'files).')
@pass_context
def build_cmd(ctx, output_path, watch, prune, verbosity,
              source_info_only):
    """Builds the entire site out."""
    from lektor.builder import Builder
    from lektor.reporter import CliReporter

    if output_path is None:
        output_path = ctx.get_default_output_path()

    env = ctx.get_env()

    def _build():
        builder = Builder(ctx.new_pad(), output_path)
        if source_info_only:
            builder.update_all_source_infos()
        else:
            builder.build_all()
            if prune:
                builder.prune()

    reporter = CliReporter(env, verbosity=verbosity)
    with reporter:
        _build()
        if not watch:
            return

        from lektor.watcher import watch
        click.secho('Watching for file system changes', fg='cyan')
        last_build = time.time()
        for ts, _, _ in watch(env):
            if ts > last_build:
                _build()
                last_build = time.time()


@cli.command('clean')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@click.confirmation_option(help='Confirms the cleaning.')
@pass_context
def clean_cmd(ctx, output_path, verbosity):
    """Cleans the entire build folder."""
    from lektor.builder import Builder
    from lektor.reporter import CliReporter

    if output_path is None:
        output_path = ctx.get_default_output_path()

    env = ctx.get_env()

    reporter = CliReporter(env, verbosity=verbosity)
    with reporter:
        builder = Builder(ctx.new_pad(), output_path)
        builder.prune(all=True)


@cli.command('deploy', short_help='Deploy the website.')
@click.argument('server', default='staging')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The output path.')
@pass_context
def deploy_cmd(ctx, server, output_path):
    from lektor.publisher import publish

    if output_path is None:
        output_path = ctx.get_default_output_path()

    env = ctx.get_env()
    config = env.load_config()

    server_info = config.get_server(server)
    if server_info is None:
        raise click.BadParameter('Server "%s" does not exist.' % server,
                                 param_hint='server')

    event_iter = publish(env, server_info.target, output_path)
    if event_iter is None:
        raise click.UsageError('Server "%s" is not configured for a valid '
                               'publishing method.' % server)

    click.echo('Deploying to %s' % server_info.name)
    click.echo('  Build cache: %s' % output_path)
    click.echo('  Target: %s' % secure_url(server_info.target))
    for line in event_iter:
        click.echo('  %s' % click.style(line, fg='cyan'))
    click.echo('Done!')


@cli.command('devserver', short_help='Launch a local development server.')
@click.option('-h', '--host', default='127.0.0.1',
              help='The network interface to bind to.  The default is the '
              'loopback device, but by setting it to 0.0.0.0 it becomes '
              'available on all network interfaces.')
@click.option('-p', '--port', default=5000, help='The port to bind to.',
              show_default=True)
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The dev server will build into the same folder as '
              'the build command by default.')
@click.option('-v', '--verbose', 'verbosity', count=True,
              help='Increases the verbosity of the logging.')
@click.option('--browse', is_flag=True)
@pass_context
def devserver_cmd(ctx, host, port, output_path, verbosity, browse):
    """The devserver command will launch a local server for development.

    Lektor's developemnt server will automatically build all files into
    pages similar to how the build command with the `--watch` switch
    works, but also at the same time serve up the website on a local
    HTTP server.
    """
    from lektor.devserver import run_server
    if output_path is None:
        output_path = ctx.get_default_output_path()
    print ' * Project path: %s' % ctx.get_project().project_path
    print ' * Output path: %s' % output_path
    run_server((host, port), env=ctx.get_env(), output_path=output_path,
               verbosity=verbosity, ui_lang=ctx.ui_lang,
               lektor_dev=os.environ.get('LEKTOR_DEV') == '1',
               browse=browse)


@cli.command('shell', short_help='Starts a python shell.')
@pass_context
def shell_cmd(ctx):
    """Starts a Python shell in the context of the program."""
    import code
    from lektor.db import F, Tree
    from lektor.builder import Builder
    banner = 'Python %s on %s\nLektor Project: %s' % (
        sys.version,
        sys.platform,
        ctx.get_env().root_path,
    )
    ns = {}
    startup = os.environ.get('PYTHONSTARTUP')
    if startup and os.path.isfile(startup):
        with open(startup, 'r') as f:
            eval(compile(f.read(), startup, 'exec'), ns)
    pad = ctx.new_pad()
    ns.update(
        env=ctx.get_env(),
        pad=pad,
        tree=Tree(pad),
        config=ctx.get_env().load_config(),
        make_builder=lambda: Builder(ctx.new_pad(),
                                     ctx.get_default_output_path()),
        F=F
    )
    code.interact(banner=banner, local=ns)


@cli.command('project-info', short_help='Shows the info about a project.')
@click.option('as_json', '--json', is_flag=True,
              help='Prints out the data as json.')
@pass_context
def info_cmd(ctx, as_json):
    """Prints out information about the project."""
    project = ctx.get_project()
    if as_json:
        click.echo(json.dumps(project.to_json(), indent=2).rstrip())
        return

    click.echo('Name: %s' % project.name)
    click.echo('File: %s' % project.project_file)
    click.echo('Tree: %s' % project.tree)


main = cli
