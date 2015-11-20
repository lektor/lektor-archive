import os
import re
import uuid
import click
import shutil
import tempfile
from datetime import datetime
from functools import partial
from contextlib import contextmanager
from jinja2 import Environment, PackageLoader

from .utils import slugify


_var_re = re.compile(r'@([^@]+)@')


class Generator(object):

    def __init__(self):
        self.jinja_env = Environment(
            loader=PackageLoader('lektor', 'quickstart-templates'),
            line_statement_prefix='%%',
            line_comment_prefix='##',
            variable_start_string='${',
            variable_end_string='}',
            block_start_string='<%',
            block_end_string='%>',
            comment_start_string='/**',
            comment_end_string='**/',
        )

    def abort(self, message):
        click.echo('Error: %s' % message, err=True)
        raise click.Abort()

    @contextmanager
    def make_target_directory(self, path):
        path = os.path.abspath(path)
        try:
            os.makedirs(path)
        except OSError as e:
            self.abort('Could not create target folder: %s' % e)

        if os.path.isdir(path):
            try:
                if len(os.listdir(path)) != 0:
                    raise OSError('Directory not empty')
            except OSError as e:
                self.abort('Bad project folder: %s' % e)

        scratch = os.path.join(tempfile.gettempdir(), uuid.uuid4().hex)
        os.makedirs(scratch)
        try:
            yield scratch
        except:
            shutil.rmtree(scratch)
            raise
        else:
            for filename in os.listdir(scratch):
                os.rename(os.path.join(scratch, filename),
                          os.path.join(path, filename))
            os.rmdir(scratch)

    def expand_filename(self, base, ctx, template_filename):
        def _repl(match):
            return ctx[match.group(1)]
        return os.path.join(base, _var_re.sub(_repl, template_filename))[:-3]

    def run(self, name, path, with_blog=False, author_name=None):
        with self.make_target_directory(path) as scratch:
            ctx = {
                'project_name': name,
                'project_slug': slugify(name),
                'project_path': path,
                'with_blog': with_blog,
                'this_year': datetime.utcnow().year,
                'today': datetime.utcnow().strftime('%Y-%m-%d'),
                'author_name': author_name,
            }

            for template in self.jinja_env.list_templates():
                if not template.endswith('.in'):
                    continue
                fn = self.expand_filename(scratch, ctx, template)
                directory = os.path.dirname(fn)
                try:
                    os.makedirs(directory)
                except OSError:
                    pass
                tmpl = self.jinja_env.get_template(template)
                rv = tmpl.render(ctx).strip('\r\n')
                if rv:
                    with open(fn, 'w') as f:
                        f.write(rv.encode('utf-8') + '\n')


def get_default_path(path, project_name):
    if path is not None:
        return path
    here = os.path.abspath(os.getcwd())
    try:
        if len(os.listdir(here)) == []:
            return here
    except OSError:
        pass
    return os.path.join(os.getcwd(), project_name)


def get_default_author():
    import getpass

    if os.name == 'nt':
        return getpass.getuser().decode('mbcs')

    import pwd
    ent = pwd.getpwuid(os.getuid())
    if ent and ent.pw_gecos:
        return ent.pw_gecos.decode('utf-8', 'replace')
    return getpass.getuser().decode('utf-8', 'replace')


def run(defaults=None):
    if not defaults:
        defaults = {}

    term_width = min(click.get_terminal_size()[0], 78)
    options = {}
    e = click.secho
    w = partial(click.wrap_text, width=term_width)

    def prompt(key, text, default=None, info=None):
        e('')
        e('Step %d:' % (len(options) + 1), fg='yellow')
        if info is not None:
            e(click.wrap_text(info, term_width - 2, '| ', '| '))
        text = '> ' + click.style(text, fg='green')

        if default is True or default is False:
            rv = click.confirm(text, default=default)
        else:
            rv = click.prompt(text, default=default, show_default=True)
        options[key] = rv

    e('Lektor Quickstart', fg='cyan')
    e('=================', fg='cyan')
    e('')
    e(w('This wizard will generate a new basic project with some sensible '
        'defaults for getting started quickly.  We jsut need to go through '
        'a few questions so that the project is set up correctly for you.'))

    prompt('name', 'Project name', defaults.get('name'),
        'A project needs a name.  The name is primarily used for the admin '
        'UI and some other places to refer to your project to not get '
        'confused if multiple projects exist.  You can change this at '
        'any later point.')

    prompt('path', 'Project path', get_default_path(defaults.get('path'),
                                                    options['name']),
        'This is the path where the project will be located.  You can '
        'move a project around later if you do not like the path.  If '
        'you provide a relative path it will be relative to the working '
        'directory.')

    prompt('with_blog', 'Add Basic Blog', True,
        'Do you want to generate a basic blog module?  If you enable this '
        'the models for a very basic blog will be generated.')

    prompt('author_name', 'Author Name', get_default_author(),
        'This is the path where the project will be located.  You can '
        'move a project around later if you do not like the path.  If '
        'you provide a relative path it will be relative to the working '
        'directory.')

    e('')
    if click.confirm('That\'s all. Create project?', default=True,
                     abort=True, prompt_suffix=' '):
        gen = Generator()
        gen.run(**options)
