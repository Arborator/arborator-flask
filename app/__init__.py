
# third-party imports
from flask import Flask, render_template, request, make_response, session, url_for, redirect
# print('____session',session)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
from flask_bootstrap import Bootstrap


# local imports

try:
    from ..config import app_config, Config  # dev__
except:
    from config import app_config, Config  # prod
# from .project import get_access_for_project

# db variable initialization
db = SQLAlchemy()
login_manager = LoginManager()
# Throws error if placed above db initialization

print("LOG : Current user =", current_user)


def create_app(config_name):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('../config.py')
    bootstrap = Bootstrap(app)
    db.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)
    login_manager.login_message = "You must be logged in to access this page."

    # commented to get a real 401 error in case of acces to an unauthorized page:
    # login_manager.login_view = "auth.choose_provider"

    from .controllers.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/api/admin')

    from .controllers.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)

    from .controllers.home import home as home_blueprint
    app.register_blueprint(home_blueprint, url_prefix='/api')

    from .controllers.project import project as project_blueprint
    app.register_blueprint(project_blueprint, url_prefix='/api/projects')

    from .controllers.samples import samples as samples_blueprint
    app.register_blueprint(samples_blueprint, url_prefix='/api/projects')

    # with app.app_context():
    # 	from main import main as main_blueprint
    # 	app.register_blueprint(...)

    # from .utils import grew_utils as grew_blueprint
    # app.register_blueprint(grew_blueprint)

    @app.before_first_request
    def create_tables():
        db.create_all()

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin',
                             'https://arboratorgrew.ilpga.fr')
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Expose-Headers', 'Authorization')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', title='Forbidden'), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html', title='Page Not Found'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html', title='Server Error'), 500

    return app
