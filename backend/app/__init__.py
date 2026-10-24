
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

import os

db = SQLAlchemy()
jwt = JWTManager()


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("SECRET_KEY")

    db.init_app(app)
    jwt.init_app(app)

    # Import models so SQLAlchemy registers their tables.
    from app.models.user import User
    from app.models.website import Website
    from app.models.business_lead import BusinessLead
    from app.models.api_usage import APIUsage

    with app.app_context():
        print("Creating tables...")
        db.create_all()
        print("Tables created.")

    # Home route
    @app.route("/")
    def home():
        return {"message": "Larva Backend Running"}

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.websites import website_bp
    from app.routes.leads import leads_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(website_bp)
    app.register_blueprint(leads_bp)

    print(app.url_map)

    return app
