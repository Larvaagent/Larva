
from app import db


class APIUsage(db.Model):
    __tablename__ = "api_usage"

    id = db.Column(db.Integer, primary_key=True)

    provider = db.Column(
        db.String(50),
        nullable=False,
        index=True,
    )

    usage_date = db.Column(
        db.Date,
        nullable=False,
        index=True,
    )

    request_count = db.Column(
        db.Integer,
        nullable=False,
        default=0,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now(),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "provider",
            "usage_date",
            name="uq_api_usage_provider_date",
        ),
        db.CheckConstraint(
            "request_count >= 0",
            name="ck_api_usage_nonnegative",
        ),
    )
