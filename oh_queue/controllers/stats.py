from flask import Blueprint, abort, redirect, render_template, request, session, url_for

from oh_queue.models import db, User

stats = Blueprint('stats', __name__)

def init_app(app):
    app.register_blueprint(stats)

@stats.route('/stats/')
def hello():
    return "hello world!"