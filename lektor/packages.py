import os
import sys
import site
import errno
import click
import shutil
import pkg_resources

from .utils import portable_popen


def pip_install(package_root, package, version):
    env = dict(os.environ)
    rv = portable_popen([
        sys.executable,
        '-m', 'pip', 'install', '--target', package_root,
        '%s==%s' % (package, version)
    ], env=env).wait()
    if rv != 0:
        raise RuntimeError('Failed to install dependency package.')


def load_manifest(filename):
    rv = []
    try:
        with open(filename) as f:
            for line in f:
                line = line.strip().split('=', 1)
                if len(line) == 2:
                    rv.append((line[0].strip(), line[1].strip()))
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    return dict(rv)


def write_manifest(filename, packages):
    with open(filename, 'w') as f:
        for package, version in sorted(packages.items()):
            f.write('%s=%s\n' % (package, version))


def update_cache(package_root, packages):
    manifest_file = os.path.join(package_root, 'lektor-packages.manifest')

    version_changed = False
    all_packages = sorted(packages.items())
    old_packages = load_manifest(manifest_file)
    to_install = []

    for package, version in all_packages:
        old_version = old_packages.pop(package, None)
        if old_version is None:
            to_install.append((package, version))
        elif old_version != version:
            version_changed = True

    # If we have any old packages that we need to remove or any version
    # changed, we wipe the entire package cache.
    if old_packages or version_changed:
        shutil.rmtree(package_root)
        to_install = all_packages

    if to_install:
        click.echo('Updating packages in %s for project' % package_root)
        for package, version in to_install:
            pip_install(package_root, package, version)
        write_manifest(manifest_file, packages)


def load_packages(env):
    """This loads all the packages of a project.  What this does is updating
    the current cache in ``root/package-cache`` and then add the Python
    modules there to the load path as a site directory and register it
    appropriately with pkg_resource's workingset.

    Afterwards all entry points should function as expected and imports
    should be possible.
    """
    config = env.load_config()
    package_root = env.project.get_package_cache_path()
    update_cache(package_root, config['PACKAGES'])
    site.addsitedir(package_root)
    pkg_resources.working_set.add_entry(package_root)
