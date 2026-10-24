
import requests


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {
    "User-Agent": "LarvaBusinessDiscovery/1.0 (local development)",
    "Accept": "application/json",
}

NICHE_TAGS = {
    "dentist": [("amenity", "dentist")],
    "restaurant": [("amenity", "restaurant")],
    "cafe": [("amenity", "cafe")],
    "pharmacy": [("amenity", "pharmacy")],
    "supermarket": [("shop", "supermarket")],
    "hair salon": [("shop", "hairdresser")],
    "hotel": [("tourism", "hotel")],
}


class DiscoveryError(Exception):
    """Raised when OpenStreetMap discovery fails."""


def _get_city_bbox(city, country):
    """Resolve a city and country into an Overpass bounding box."""
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={
                "q": f"{city.strip()}, {country.strip()}",
                "format": "jsonv2",
                "limit": 1,
            },
            headers=HEADERS,
            timeout=20,
        )
        response.raise_for_status()
        results = response.json()

    except requests.RequestException as exc:
        raise DiscoveryError(
            "City lookup failed. Check your connection or try again later."
        ) from exc
    except ValueError as exc:
        raise DiscoveryError(
            "The city lookup returned invalid JSON."
        ) from exc

    if not results:
        raise DiscoveryError(
            f"Could not find {city}, {country} in OpenStreetMap."
        )

    bbox = results[0].get("boundingbox")

    if not isinstance(bbox, list) or len(bbox) != 4:
        raise DiscoveryError(
            "The city lookup did not return a valid bounding box."
        )

    # Nominatim order: south, north, west, east.
    south, north, west, east = map(float, bbox)

    if south > north or west > east:
        raise DiscoveryError("The returned bounding box is invalid.")

    return south, west, north, east


def _build_query(bbox, niche):
    """Build a valid Overpass QL query for the requested category."""
    tags = NICHE_TAGS.get(niche.strip().lower())

    if not tags:
        supported = ", ".join(sorted(NICHE_TAGS))
        raise ValueError(
            f"Unsupported niche. Supported niches: {supported}"
        )

    south, west, north, east = bbox
    selectors = []

    for key, value in tags:
        selectors.extend([
            f'node["{key}"="{value}"]({south},{west},{north},{east});',
            f'way["{key}"="{value}"]({south},{west},{north},{east});',
            f'relation["{key}"="{value}"]({south},{west},{north},{east});',
        ])

    return (
        "[out:json][timeout:25];\n"
        "(\n"
        + "\n".join(selectors)
        + "\n);\nout center tags;"
    )


def _extract_address(tags):
    """Build a basic address from available OpenStreetMap tags."""
    house_number = tags.get("addr:housenumber")
    street = tags.get("addr:street")

    street_parts = [
        part for part in (house_number, street) if part
    ]
    street_address = " ".join(street_parts)

    locality = (
        tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:village")
    )

    postcode = tags.get("addr:postcode")

    parts = [street_address, locality, postcode]
    address = ", ".join(part for part in parts if part)

    return address or None


def _normalize_element(element, niche, city, country):
    """Convert an OpenStreetMap element into a lead dictionary."""
    tags = element.get("tags", {})
    name = tags.get("name")

    # Ignore unnamed map elements.
    if not name or not name.strip():
        return None

    center = element.get("center", {})

    return {
        "business_name": name.strip(),
        "niche": niche.strip().lower(),
        "country": country.strip(),
        "state": tags.get("addr:state"),
        "city": (
            tags.get("addr:city")
            or tags.get("addr:town")
            or city.strip()
        ),
        "address": _extract_address(tags),
        "phone": (
            tags.get("contact:phone")
            or tags.get("phone")
        ),
        "email": (
            tags.get("contact:email")
            or tags.get("email")
        ),
        "website_url": (
            tags.get("contact:website")
            or tags.get("website")
            or tags.get("url")
        ),
        "source": "openstreetmap",
        "source_id": f"{element.get('type')}:{element.get('id')}",
        "latitude": element.get("lat", center.get("lat")),
        "longitude": element.get("lon", center.get("lon")),
    }


def discover_businesses(city, country, niche, limit=50):
    """
    Discover mapped businesses by city, country and supported niche.

    Returns normalized dictionaries. This function does not save
    records to PostgreSQL.
    """
    if not all(
        isinstance(value, str) and value.strip()
        for value in (city, country, niche)
    ):
        raise ValueError("City, country, and niche are required.")

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Limit must be an integer.")

    if not 1 <= limit <= 100:
        raise ValueError("Limit must be between 1 and 100.")

    if niche.strip().lower() not in NICHE_TAGS:
        supported = ", ".join(sorted(NICHE_TAGS))
        raise ValueError(
            f"Unsupported niche. Supported niches: {supported}"
        )

    bbox = _get_city_bbox(city, country)
    query = _build_query(bbox, niche)

    try:
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=HEADERS,
            timeout=35,
        )
        response.raise_for_status()
        payload = response.json()

    except requests.RequestException as exc:
        details = ""

        if exc.response is not None:
            details = (
                f" HTTP {exc.response.status_code}: "
                f"{exc.response.text[:1000]}"
            )

        raise DiscoveryError(
            f"OpenStreetMap discovery request failed.{details}"
        ) from exc

    except ValueError as exc:
        raise DiscoveryError(
            "OpenStreetMap returned invalid JSON."
        ) from exc

    elements = payload.get("elements")

    if not isinstance(elements, list):
        raise DiscoveryError(
            "OpenStreetMap returned an unexpected response."
        )

    results = []
    seen_ids = set()

    for element in elements:
        lead = _normalize_element(
            element,
            niche,
            city,
            country,
        )

        if lead is None:
            continue

        source_id = lead["source_id"]

        if source_id in seen_ids:
            continue

        seen_ids.add(source_id)
        results.append(lead)

        if len(results) >= limit:
            break

    return results
