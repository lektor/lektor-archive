import click


@click.group()
def cli():
    """The lektor application."""


@cli.command('build')
def build_cmd():
    """Builds the entire site out."""


@cli.command('develop')
def develop_cmd():
    """Runs a development server that automatically builds."""


main = cli
