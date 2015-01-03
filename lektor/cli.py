import os
import time
import click


class Context(object):

    def __init__(self):
        self.tree = None

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
        from lektor.environment import Environment
        return Environment(self.get_tree())

    def get_pad(self):
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
@pass_context
def build_cmd(ctx, output_path):
    """Builds the entire site out."""
    from lektor.builder import Builder
    builder = Builder(ctx.get_pad(), output_path)
    start = time.time()
    click.secho('Building from %s' % builder.env.root_path, fg='green')
    builder.build_all()
    click.secho('Done!', fg='green')
    click.echo('Total time: %.2f sec' % (time.time() - start))


@cli.command('buildwatch')
@click.option('-O', '--output-path', type=click.Path(), default='build',
              help='The output path')
@pass_context
def buildwatch_cmd(ctx, output_path):
    """This runs the builder whenever files change."""
    from lektor.builder import Builder
    from lektor.watcher import watch
    builder = Builder(ctx.get_pad(), output_path)
    click.secho('Building in real-time from %s' %
                builder.env.root_path, fg='green')
    builder.build_all()
    last_build = time.time()
    for ts, _, _ in watch(builder.env):
        if ts > last_build:
            builder.build_all()
            last_build = time.time()


main = cli
