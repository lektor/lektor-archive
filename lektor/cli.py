import os
import time
import click


class Context(object):

    def __init__(self):
        self.tree = None
        self._env = None

    def get_tree(self):
        if self.tree is not None:
            return os.path.abspath(self.tree)
        here = os.getcwd()
        while 1:
            if os.path.isfile(os.path.join(here, 'site.ini')):
                return here
            node = os.path.dirname(here)
            if node == here:
                break
            here = node

        raise click.UsageError('Could not find tree')

    def get_default_output_path(self):
        return os.path.join(self.get_tree(), 'build')

    def get_env(self):
        if self._env is not None:
            return self._env
        from lektor.environment import Environment
        env = Environment(self.get_tree())
        self._env = env
        return env

    def new_pad(self):
        from lektor.db import Database
        env = self.get_env()
        return Database(env).new_pad()


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option('--tree', type=click.Path(),
              help='The path to the lektor tree to work with.')
@pass_context
def cli(ctx, tree=None):
    """The lektor management application.

    This command can invoke lektor locally and serve up the website.  It's
    intended for local development of websites.
    """
    if tree is not None:
        ctx.tree = tree


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
@pass_context
def build_cmd(ctx, output_path, watch, prune, verbosity):
    """Builds the entire site out."""
    from lektor.builder import Builder
    from lektor.reporter import CliReporter

    if output_path is None:
        output_path = ctx.get_default_output_path()

    env = ctx.get_env()

    def _build():
        builder = Builder(ctx.new_pad(), output_path)
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
@pass_context
def devserver_cmd(ctx, host, port, output_path, verbosity):
    """The devserver command will launch a local server for development.

    Lektor's developemnt server will automatically build all files into
    pages similar to how the build command with the `--watch` switch
    works, but also at the same time serve up the website on a local
    HTTP server.
    """
    from lektor.devserver import run_server
    if output_path is None:
        output_path = ctx.get_default_output_path()
    print ' * Tree path: %s' % ctx.get_tree()
    print ' * Output path: %s' % output_path
    run_server((host, port), env=ctx.get_env(), output_path=output_path,
               verbosity=verbosity,
               lektor_dev=os.environ.get('LEKTOR_DEV') == '1')


@cli.command('sync', short_help='Synchronizes stuff to a host.')
@click.option('-O', '--output-path', type=click.Path(), default=None,
              help='The dev server will build into the same folder as '
              'the build command by default.')
@click.option('-s', '--server', default='server', 
              help='The host to connect to.')            
@pass_context
def sync_cmd(ctx, output_path, server):
    """This commands syncs to a server."""
    from lektor.builder import Builder
    from lektor.publisher import Publisher
    if output_path is None:
        output_path = ctx.get_default_output_path()
    builder = Builder(ctx.new_pad(), output_path)
    builder.update_listing_file()
    publisher = Publisher(output_path, server)
    publisher.publish()


main = cli
