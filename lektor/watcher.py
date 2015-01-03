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


def observe(env):
    """Returns a generator of file system events in the environment."""
    event_handler = EventHandler(env)
    observer = Observer()
    observer.schedule(event_handler, env.root_path, recursive=True)
    observer.setDaemon(True)
    observer.start()
    try:
        while 1:
            try:
                yield event_handler.queue.get(timeout=1)
            except Queue.Empty:
                pass
    except KeyboardInterrupt:
        observer.stop()
