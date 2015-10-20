import os
import json
import errno

from inifile import IniFile

from lektor.utils import iter_dotted_path_prefixes, resolve_dotted_value, \
     merge, decode_flat_data


def load_databag(filename):
    try:
        if filename.endswith('.json'):
            with open(filename, 'r') as f:
                return json.load(f)
        elif filename.endswith('.ini'):
            return decode_flat_data(IniFile(filename).items())
    except (OSError, IOError) as e:
        if e.errno != errno.ENOENT:
            raise


class Databags(object):

    def __init__(self, env):
        self.env = env
        self.root_path = os.path.join(self.env.root_path, 'databags')
        self._known_bags = {}
        self._bags = {}
        try:
            for filename in os.listdir(self.root_path):
                if filename.endswith(('.ini', '.json')):
                    self._known_bags.setdefault(
                        filename.rsplit('.', -1)[0], []).append(filename)
        except OSError:
            pass

    def get_bag(self, name):
        sources = self._known_bags.get(name)
        if not sources:
            return None
        rv = self._bags.get(name)
        if rv is not None:
            return rv

        rv = {}
        for filename in sources:
            rv = merge(rv, load_databag(os.path.join(self.root_path, filename)))
        self._bags[name] = rv
        return rv

    def lookup(self, key):
        for prefix, local_key in iter_dotted_path_prefixes(key):
            bag = self.get_bag(prefix)
            if bag is not None:
                return resolve_dotted_value(bag, local_key)
