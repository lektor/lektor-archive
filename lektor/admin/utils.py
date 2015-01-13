from flask import request, current_app, g

from lektor.db import Database


def get_pad():
    """Returns the pad for the current request."""
    pad = getattr(g, 'lektor_pad', None)
    if pad is None:
        db = Database(current_app.lektor_env)
        pad = db.new_pad()
        g.lektor_pad = pad
    return pad


def get_frontend_source(all_sources=False):
    """Returns the source currently referenced in the frontend.
    """
    path = request.environ['lektor.frontend_path']
    return get_pad().resolve_url_path(path, all_sources=all_sources,
                                      include_unexposed=True)


def get_record_title(record):
    """Returns the title of the record."""
    name = record['_id'].replace('-', ' ').replace('_', ' ').title().strip()
    if not name:
        return '(Index)'
    return name
