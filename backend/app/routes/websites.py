
from flask import Blueprint, request, jsonify
from app import db
from app.models.website import Website
from app.services.seo_analyzer import analyze_seo
from app.services.ux_analyzer import analyze_ux

website_bp = Blueprint("website", __name__)


@website_bp.route("/websites", methods=["POST"])
def create_website():
    data = request.get_json()

    if not data:
        return jsonify({
            "message": "Request body is required"
        }), 400

    url = data.get("url")

    if not isinstance(url, str) or not url.strip():
        return jsonify({
            "message": "A valid URL is required"
        }), 400

    url = url.strip()

    existing_website = Website.query.filter_by(url=url).first()

    if existing_website:
        return jsonify({
            "message": "Website already exists"
        }), 400

    seo_result = analyze_seo(url)
    ux_result = analyze_ux(url)

    if "error" in ux_result:
        return jsonify({
            "message": "UX analysis failed",
            "error": ux_result["error"]
        }), 502

    seo_score = seo_result["score"]
    seo_report = seo_result["report"]

    ux_score = ux_result["score"]
    ux_report = ux_result["report"]

    total_score = round(
        (seo_score * 0.5) + (ux_score * 0.5)
    )

    website = Website(
        url=url,
        seo_score=seo_score,
        seo_report=seo_report,
        ux_score=ux_score,
        ux_report=ux_report,
        total_score=total_score
    )

    try:
        db.session.add(website)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({
            "message": "Failed to save website"
        }), 500

    return jsonify({
        "message": "Website added successfully",
        "id": website.id,
        "url": website.url,
        "seo_score": website.seo_score,
        "seo_report": website.seo_report,
        "ux_score": website.ux_score,
        "ux_report": website.ux_report,
        "total_score": website.total_score
    }), 201


@website_bp.route("/websites", methods=["GET"])
def get_websites():
    websites = Website.query.all()

    result = []

    for website in websites:
        result.append({
            "id": website.id,
            "url": website.url,
            "seo_score": website.seo_score,
            "seo_report": website.seo_report,
            "ux_score": website.ux_score,
            "ux_report": website.ux_report,
            "marketing_score": website.marketing_score,
            "total_score": website.total_score,
            "status": website.status
        })

    return jsonify(result), 200


@website_bp.route("/websites/<int:website_id>", methods=["GET"])
def get_website(website_id):
    website = db.session.get(Website, website_id)

    if not website:
        return jsonify({
            "message": "Website not found"
        }), 404

    return jsonify({
        "id": website.id,
        "url": website.url,
        "seo_score": website.seo_score,
        "seo_report": website.seo_report,
        "ux_score": website.ux_score,
        "ux_report": website.ux_report,
        "marketing_score": website.marketing_score,
        "total_score": website.total_score,
        "status": website.status
    }), 200
