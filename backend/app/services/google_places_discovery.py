import os
import requests
from dotenv import load_dotenv
from app.services.api_usage import (
    reserve_api_request,
    UsageLimitExceeded,
)


load_dotenv(
    dotenv_path=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../.env")
    )
)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places"

REQUEST_TIMEOUT = 20

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.addressComponents",
    "places.nationalPhoneNumber",
    "places.websiteUri",
])


class DiscoveryError(Exception):
    """Raised when Google Places discovery fails."""


def _get_api_key():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")

    if not api_key:
        raise DiscoveryError(
            "GOOGLE_PLACES_API_KEY is missing from backend/.env"
        )

    return api_key


def _build_headers(api_key, field_mask=None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }

    if field_mask:
        headers["X-Goog-FieldMask"] = field_mask

    return headers


def _get_address_component(components, component_type):
    for component in components:
        if component_type in component.get("types", []):
            return (
                component.get("longText")
                or component.get("shortText")
            )

    return None


def _normalize_place(place, city, country, niche):
    components = place.get("addressComponents", [])

    return {
        "business_name": (
            place.get("displayName", {}).get("text")
            or "Unknown business"
        ),
        "niche": niche.lower(),
        "country": (
            _get_address_component(components, "country")
            or country
        ),
        "state": _get_address_component(
            components, "administrative_area_level_1"
        ),
        "city": (
            _get_address_component(components, "locality")
            or _get_address_component(
                components, "postal_town"
            )
            or city
        ),
        "address": place.get("formattedAddress"),
        "phone": place.get("nationalPhoneNumber"),
        "email": None,
        "website_url": place.get("websiteUri"),
        "source": "google_places",
        "source_id": place.get("id"),
    }


def discover_businesses(city, country, niche, limit=10):
    if not all(
        isinstance(value, str) and value.strip()
        for value in (city, country, niche)
    ):
        raise ValueError(
            "City, country, and niche must be non-empty strings"
        )

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= 100
    ):
        raise ValueError("Limit must be an integer between 1 and 100")

    api_key = _get_api_key()

    payload = {
        "textQuery": f"{niche.strip()} in {city.strip()}, {country.strip()}",
        "pageSize": min(limit, 20),
    }

    
    try:
        reserve_api_request(
            provider="google_places",
            daily_limit=200,
        )
    except UsageLimitExceeded as exc:
        raise DiscoveryError(str(exc)) from exc
    except Exception as exc:
        raise DiscoveryError(
            "Could not reserve Google Places API usage. "
            "The API request was not sent."
        ) from exc

    try:
        response = requests.post(
            PLACES_SEARCH_URL,
            headers=_build_headers(api_key, FIELD_MASK),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:
        raise DiscoveryError(
            "Could not connect to Google Places API"
        ) from exc

    if not response.ok:
        try:
            error_data = response.json()
            error_message = error_data.get(
                "error", {}
            ).get("message", "Unknown Google Places API error")
        except ValueError:
            error_message = "Unknown Google Places API error"

        raise DiscoveryError(
            f"Google Places API returned HTTP "
            f"{response.status_code}: {error_message}"
        )

    places = response.json().get("places", [])
    results = []
    seen_ids = set()

    for place in places:
        place_id = place.get("id")

        if not place_id or place_id in seen_ids:
            continue

        seen_ids.add(place_id)
        results.append(
            _normalize_place(
                place=place,
                city=city.strip(),
                country=country.strip(),
                niche=niche.strip(),
            )
        )

        if len(results) >= limit:
            break

    return results
