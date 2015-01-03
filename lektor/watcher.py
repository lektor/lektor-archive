import os
import time
import Queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, DirModifiedEvent


class EventHandler(FileSystemEventHandler):

    def __init__(self, env):
        self.env = env
        self.queue = Queue.Queue()

    def is_uninteresting(self, event):
        path = event.src_path
        return self.env.is_uninteresting_filename(os.path.basename(path))

    def on_any_event(self, event):
        if self.is_uninteresting(event) or isinstance(event, DirModifiedEvent):
            return
        self.queue.put((time.time(), event.event_type, event.src_path))


class Watcher(object):

    def __init__(self, env):
        self.env = env
        self.event_handler = EventHandler(env)
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
