from app import db


class Website(db.Model):
    __tablename__ = "websites"

    id = db.Column(db.Integer, primary_key=True)

    url = db.Column(
        db.String(500),
        nullable=False,
        unique=True
    )

    seo_score = db.Column(
        db.Integer,
        default=0
    )

    seo_report = db.Column(
        db.JSON,
        nullable=True
    )

    ux_report = db.Column(
        db.JSON,
        nullable=True
    )

    ux_score = db.Column(
        db.Integer,
        default=0
    )

    marketing_score = db.Column(
        db.Integer,
        default=0
    )

    total_score = db.Column(
        db.Integer,
        default=0
    )

    status = db.Column(
        db.String(50),
        default="pending"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )
