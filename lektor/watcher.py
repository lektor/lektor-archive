import os
import time
import Queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirModifiedEvent


class EventHandler(FileSystemEventHandler):

    def __init__(self, env, output_path=None):
        self.env = env
        if output_path is not None:
            output_path = os.path.join(env.root_path, output_path)
        self.output_path = output_path
        self.queue = Queue.Queue()

    def is_uninteresting(self, event):
        path = event.src_path
        if self.env.is_uninteresting_source_name(os.path.basename(path)):
            return True
        if self.output_path is not None and \
           os.path.abspath(path).startswith(self.output_path):
            return True
        return False

    def on_any_event(self, event):
        if self.is_uninteresting(event) or isinstance(event, DirModifiedEvent):
            return
        self.queue.put((time.time(), event.event_type, event.src_path))


class Watcher(object):

    def __init__(self, env, output_path=None):
        self.env = env
        self.event_handler = EventHandler(env, output_path)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, env.root_path,
                               recursive=True)
        self.observer.setDaemon(True)

    def __iter__(self):
        while 1:
            try:
                yield self.event_handler.queue.get(timeout=1)
            except Queue.Empty:
                pass


def watch(env):
    """Returns a generator of file system events in the environment."""
    watcher = Watcher(env)
    watcher.observer.start()
    try:
        for event in watcher:
            yield event
    except KeyboardInterrupt:
        watcher.observer.stop()
