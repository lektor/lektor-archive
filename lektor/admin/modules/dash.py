from flask import Blueprint, render_template


bp = Blueprint('dash', __name__)


@bp.route('/')
def index():
    return render_template('dash.html')
