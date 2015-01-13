from flask import request, current_app, g, url_for

from lektor.db import Database


def get_pad(refresh=False):
    """Returns the pad for the current request."""
    pad = getattr(g, 'lektor_pad', None)
    if pad is None or refresh:
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


def action_url(endpoint=None, source=None, **values):
    """Special version of :meth:`url_for` that generates URL for actions
    of the current or different source.
    """
    if endpoint is None:
        endpoint = request.endpoint
    if source is None:
        source = get_frontend_source()
    if source is None:
        raise RuntimeError('No source found')
    if hasattr(source, 'url_path'):
        source = source.url_path
    return '/' + source.lstrip('/') + url_for(endpoint, **values).lstrip('/')
