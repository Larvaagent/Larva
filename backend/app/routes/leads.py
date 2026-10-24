from flask import Blueprint, request, jsonify

from app import db
from app.models.business_lead import BusinessLead
from app.services.google_places_discovery import (
    discover_businesses,
    DiscoveryError,
)
from app.services.email_extractor import extract_business_emails


leads_bp = Blueprint("leads", __name__)


@leads_bp.route("/leads", methods=["POST"])
def create_lead():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "message": "A JSON request body is required"
        }), 400

    required_fields = [
        "business_name",
        "niche",
        "country",
        "city",
    ]

    missing_fields = [
        field
        for field in required_fields
        if not isinstance(data.get(field), str)
        or not data[field].strip()
    ]

    if missing_fields:
        return jsonify({
            "message": "Required fields are missing or invalid",
            "fields": missing_fields,
        }), 400

    allowed_fields = {
        "business_name",
        "niche",
        "country",
        "state",
        "city",
        "address",
        "phone",
        "email",
        "website_url",
        "source",
        "source_id",
    }

    optional_fields = allowed_fields - set(required_fields)

    for field in optional_fields:
        value = data.get(field)

        if value is not None and not isinstance(value, str):
            return jsonify({
                "message": f"{field} must be a string"
            }), 400

    lead_data = {
        field: data[field].strip()
        for field in required_fields
    }

    for field in optional_fields:
        value = data.get(field)

        if isinstance(value, str) and value.strip():
            lead_data[field] = value.strip()

    source = lead_data.get("source", "manual")
    source_id = lead_data.get("source_id")

    if source_id:
        existing_lead = BusinessLead.query.filter_by(
            source=source,
            source_id=source_id,
        ).first()

        if existing_lead:
            return jsonify({
                "message": "Lead already exists",
                "id": existing_lead.id,
            }), 409

    lead = BusinessLead(**lead_data)

    try:
        db.session.add(lead)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "message": "Failed to save lead"
        }), 500

    return jsonify({
        "message": "Lead created successfully",
        "lead": lead.to_dict(),
    }), 201


@leads_bp.route("/leads/discover", methods=["POST"])
def discover_leads():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "message": "A JSON request body is required"
        }), 400

    city = data.get("city")
    country = data.get("country")
    niche = data.get("niche")
    limit = data.get("limit", 10)

    required_values = {
        "city": city,
        "country": country,
        "niche": niche,
    }

    missing_fields = [
        field
        for field, value in required_values.items()
        if not isinstance(value, str) or not value.strip()
    ]

    if missing_fields:
        return jsonify({
            "message": "City, country, and niche are required",
            "fields": missing_fields,
        }), 400

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 100
    ):
        return jsonify({
            "message": "Limit must be an integer between 1 and 100"
        }), 400

    try:
        discovered = discover_businesses(
            city=city.strip(),
            country=country.strip(),
            niche=niche.strip(),
            limit=limit,
        )
    except ValueError as exc:
        return jsonify({"message": str(exc)}), 400
    except DiscoveryError as exc:
        return jsonify({"message": str(exc)}), 502

    saved_leads = []
    skipped = 0
    emails_found = 0
    email_missing = 0

    try:
        for item in discovered:
            source = item["source"]
            source_id = item["source_id"]

            existing_lead = BusinessLead.query.filter_by(
                source=source,
                source_id=source_id,
            ).first()

            if existing_lead:
                skipped += 1
                continue

            website_url = item.get("website_url")
            email = item.get("email")

            if not email and website_url:
                try:
                    extracted_emails = extract_business_emails(
                        website_url
                    )
                    if extracted_emails:
                        email = extracted_emails[0]
                except Exception:
                    email = None

            status = "email_found" if email else "email_missing"

            if email:
                emails_found += 1
            else:
                email_missing += 1

            lead = BusinessLead(
                business_name=item["business_name"],
                niche=item["niche"],
                country=item["country"],
                state=item.get("state"),
                city=item["city"],
                address=item.get("address"),
                phone=item.get("phone"),
                email=email,
                website_url=website_url,
                source=source,
                source_id=source_id,
                discovery_status=status,
            )

            db.session.add(lead)
            saved_leads.append(lead)

        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({
            "message": "Failed to save discovered leads"
        }), 500

    return jsonify({
        "message": "Business discovery and email extraction completed",
        "city": city.strip(),
        "country": country.strip(),
        "niche": niche.strip().lower(),
        "discovered_count": len(discovered),
        "saved_count": len(saved_leads),
        "skipped_duplicates": skipped,
        "emails_found": emails_found,
        "email_missing": email_missing,
        "leads": [
            lead.to_dict()
            for lead in saved_leads
        ],
    }), 200


@leads_bp.route("/leads/enrich-emails", methods=["POST"])
def enrich_lead_emails():
    data = request.get_json(silent=True) or {}

    if not isinstance(data, dict):
        return jsonify({
            "message": "A JSON request body is required"
        }), 400

    limit = data.get("limit", 5)
    city = data.get("city")
    country = data.get("country")
    niche = data.get("niche")

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 10
    ):
        return jsonify({
            "message": "Limit must be an integer between 1 and 10"
        }), 400

    for field, value in [
        ("city", city),
        ("country", country),
        ("niche", niche),
    ]:
        if value is not None and (
            not isinstance(value, str) or not value.strip()
        ):
            return jsonify({
                "message": f"{field} must be a non-empty string"
            }), 400

    query = BusinessLead.query.filter(
        BusinessLead.email.is_(None),
        BusinessLead.website_url.isnot(None),
        BusinessLead.website_url != "",
    )

    if city:
        query = query.filter(
            BusinessLead.city.ilike(city.strip())
        )

    if country:
        query = query.filter(
            BusinessLead.country.ilike(country.strip())
        )

    if niche:
        query = query.filter(
            BusinessLead.niche.ilike(niche.strip())
        )

    leads = query.order_by(BusinessLead.id.asc()).limit(limit).all()

    processed = 0
    emails_found = 0
    still_missing = 0
    failures = 0
    updated_leads = []

    for lead in leads:
        processed += 1

        try:
            emails = extract_business_emails(lead.website_url)

            if emails:
                lead.email = emails[0]
                lead.discovery_status = "email_found"
                emails_found += 1
            else:
                lead.discovery_status = "email_missing"
                still_missing += 1

            updated_leads.append(lead)

        except Exception:
            failures += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "message": "Failed to save email enrichment results"
        }), 500

    return jsonify({
        "message": "Email enrichment completed",
        "processed": processed,
        "emails_found": emails_found,
        "still_missing": still_missing,
        "failures": failures,
        "leads": [
            lead.to_dict()
            for lead in updated_leads
        ],
    }), 200


@leads_bp.route("/leads", methods=["GET"])
def get_leads():
    query = BusinessLead.query

    city = request.args.get("city", type=str)
    country = request.args.get("country", type=str)
    niche = request.args.get("niche", type=str)
    status = request.args.get("status", type=str)

    for field, value in [
        ("city", city),
        ("country", country),
        ("niche", niche),
        ("discovery_status", status),
    ]:
        if value and value.strip():
            query = query.filter(
                getattr(BusinessLead, field).ilike(value.strip())
            )

    leads = query.order_by(BusinessLead.id.desc()).all()

    return jsonify([
        lead.to_dict()
        for lead in leads
    ]), 200


@leads_bp.route("/leads/<int:lead_id>", methods=["GET"])
def get_lead(lead_id):
    lead = db.session.get(BusinessLead, lead_id)

    if not lead:
        return jsonify({
            "message": "Lead not found"
        }), 404

    return jsonify(lead.to_dict()), 200
