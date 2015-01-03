import os
import time
import click


class Context(object):

    def __init__(self):
        self.tree = None
        self._env = None

    def get_tree(self):
        if self.tree is not None:
            return self.tree
        here = os.getcwd()
        while 1:
            if os.path.isfile(os.path.join(here, 'site.ini')):
                return here
            node = os.path.dirname(here)
            if node == here:
                break
            here = node

        raise click.UsageError('Could not find tree')

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
    """The lektor application."""
    if tree is not None:
        ctx.tree = tree


@cli.command('build')
@click.option('-O', '--output-path', type=click.Path(), default='build',
              help='The output path')
@click.option('--watch', is_flag=True, help='If this is enabled the build '
              'process goes into an automatic loop where it watches the '
              'file system for changes and rebuilds.')
@pass_context
def build_cmd(ctx, output_path, watch):
    """Builds the entire site out."""
    from lektor.builder import Builder

    env = ctx.get_env()
    click.secho('Building from %s' % env.root_path, fg='green')

    def _build():
        builder = Builder(ctx.new_pad(), output_path)
        start = time.time()
        builder.build_all()
        click.echo('Built in %.2f sec' % (time.time() - start))

    _build()
    if not watch:
        click.secho('Done!', fg='green')
        return

    from lektor.watcher import watch
    click.secho('Watching for file system changes', fg='cyan')
    last_build = time.time()
    for ts, _, _ in watch(env):
        if ts > last_build:
            _build()
            last_build = time.time()


main = cli
