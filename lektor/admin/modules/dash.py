from flask import Blueprint, render_template


bp = Blueprint('dash', __name__)


endpoints = [
    ('/', 'index'),
    ('/<path>/edit', 'edit'),
]


def generic_endpoint(**kwargs):
    """This function is invoked by all dash endpoints."""
    return render_template('dash.html')


for path, endpoint in endpoints:
    bp.add_url_rule(path, endpoint, generic_endpoint)
