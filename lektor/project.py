import os
import hashlib
from inifile import IniFile

from lektor.utils import to_os_path


class Project(object):

    def __init__(self, name, project_file, tree):
        self.name = name
        self.project_file = project_file
        self.tree = os.path.normpath(tree)
        self.id = hashlib.md5(self.tree.encode('utf-8')).hexdigest()

    @property
    def project_path(self):
        return self.project_file or self.tree

    def to_json(self):
        return {
            'name': self.name,
            'project_file': self.project_file,
            'project_path': self.project_path,
            'id': self.id,
            'tree': self.tree,
        }


def project_from_file(filename):
    inifile = IniFile(filename)
    if inifile.is_new:
        return None

    name = inifile.get('project.name') or os.path.basename(
        filename).rsplit('.')[0].title()
    path = os.path.join(os.path.dirname(filename),
                        to_os_path(inifile.get('project.path') or '.'))
    return Project(
        name=name,
        project_file=filename,
        tree=path,
    )


def load_project(path):
    """Locates the project for a path."""
    path = os.path.abspath(path)
    if os.path.isfile(path):
        return project_from_file(path)

    try:
        files = [x for x in os.listdir(path)
                 if x.lower().endswith('.lektorproject')]
    except OSError:
        return None

    if len(files) == 1:
        return project_from_file(os.path.join(path, files[0]))

    if os.path.isdir(path) and \
       os.path.isfile(os.path.join(path, 'content/contents.lr')):
        return Project(
            name=os.path.basename(path),
            project_file=None,
            tree=path,
        )


def discover_project(base=None):
    """Auto discovers the closest project."""
    if base is None:
        base = os.getcwd()
    here = base
    while 1:
        project = load_project(here)
        if project is not None:
            return project
        node = os.path.dirname(here)
        if node == here:
            break
        here = node
