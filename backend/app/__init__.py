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

    )

    db.init_app(app)
    jwt.init_app(app)

    # Import models
    from app.models.user import User
    from app.models.website import Website

    with app.app_context():
        print("Creating tables...")
        db.create_all()
        print("Tables created.")

    # Home Route
    @app.route("/")
    def home():
        return {"message": "Larva Backend Running"}

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.websites import website_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(website_bp)

    print(app.url_map)
    return app