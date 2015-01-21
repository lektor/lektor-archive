import os
import shutil

here = os.path.dirname(os.path.abspath(__file__))


ignorefunc = shutil.ignore_patterns('*.pyc', '*.pyo')


for pkg in 'werkzeug', 'lektor':
    mod = __import__(pkg)
    dst = os.path.join(here, 'dist', 'lektorcli', pkg)
    try:
        shutil.rmtree(dst)
    except (OSError, IOError):
        pass
    src = os.path.dirname(mod.__file__)
    shutil.copytree(src, dst, ignore=ignorefunc)
