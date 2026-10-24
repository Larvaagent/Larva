
from app import db


class BusinessLead(db.Model):
    __tablename__ = "business_leads"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    business_name = db.Column(
        db.String(255),
        nullable=False,
        index=True
    )

    niche = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    country = db.Column(
        db.String(100),
        nullable=False,
        index=True
    )

    state = db.Column(
        db.String(100),
        nullable=True
    )

    city = db.Column(
        db.String(150),
        nullable=False,
        index=True
    )

    address = db.Column(
        db.String(500),
        nullable=True
    )

    phone = db.Column(
        db.String(50),
        nullable=True
    )

    email = db.Column(
        db.String(255),
        nullable=True,
        index=True
    )

    website_url = db.Column(
        db.String(500),
        nullable=True
    )

    source = db.Column(
        db.String(100),
        nullable=False,
        default="manual"
    )

    source_id = db.Column(
        db.String(255),
        nullable=True
    )

    discovery_status = db.Column(
        db.String(50),
        nullable=False,
        default="discovered"
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "business_name": self.business_name,
            "niche": self.niche,
            "country": self.country,
            "state": self.state,
            "city": self.city,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "website_url": self.website_url,
            "source": self.source,
            "source_id": self.source_id,
            "discovery_status": self.discovery_status,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at
                else None
            ),
        }
