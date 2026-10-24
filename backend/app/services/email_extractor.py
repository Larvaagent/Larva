import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


REQUEST_TIMEOUT = 10
MAX_PAGES_PER_WEBSITE = 5
MAX_RESPONSE_BYTES = 1_000_000

HEADERS = {
    "User-Agent": (
        "LarvaBusinessResearch/1.0 "
        "(website contact information lookup)"
    )
}

EMAIL_PATTERN = re.compile(
    r"(?i)(?<![\w.+-])"
    r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)

CONTACT_KEYWORDS = (
    "contact",
    "about",
    "team",
    "staff",
    "support",
    "appointment",
    "location",
)


def _normalize_url(url):
    if not isinstance(url, str) or not url.strip():
        return None

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None

    if parsed.username or parsed.password:
        return None

    return url


def _is_public_http_url(url):
    """Reject non-web URLs and private/local hostnames."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()

    if not hostname or hostname == "localhost":
        return False

    if hostname.endswith((".local", ".internal", ".localhost")):
        return False

    # Avoid obvious local and private IPv4/IPv6 targets.
    try:
        import ipaddress

        address = ipaddress.ip_address(hostname)
        if not address.is_global:
            return False
    except ValueError:
        pass

    return True


def _extract_emails(html):
    soup = BeautifulSoup(html, "html.parser")
    emails = set()

    for link in soup.select('a[href^="mailto:"]'):
        href = link.get("href", "")
        address = href[7:].split("?", 1)[0].strip()
        if EMAIL_PATTERN.fullmatch(address):
            emails.add(address.lower())

    text = soup.get_text(" ", strip=True)
    emails.update(
        match.group(0).lower()
        for match in EMAIL_PATTERN.finditer(text)
    )

    # Ignore common placeholder/example addresses.
    return {
        email
        for email in emails
        if not email.endswith(
            (".example", ".invalid", ".test")
        )
        and "example.com" not in email
    }


def _fetch_page(url):
    if not _is_public_http_url(url):
        return None

    try:
        with requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()

            if not _is_public_http_url(response.url):
                return None

            content_type = response.headers.get(
                "Content-Type", ""
            ).lower()

            if "text/html" not in content_type:
                return None

            chunks = []
            total_bytes = 0

            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue

                total_bytes += len(chunk)
                if total_bytes > MAX_RESPONSE_BYTES:
                    return None

                chunks.append(chunk)

            return b"".join(chunks).decode(
                response.encoding or "utf-8",
                errors="replace",
            )

    except requests.RequestException:
        return None


def extract_business_emails(website_url):
    """
    Extract publicly listed email addresses from a business website.

    Returns a sorted list of email addresses. This function does not
    guess email addresses or submit contact forms.
    """
    start_url = _normalize_url(website_url)

    if not start_url or not _is_public_http_url(start_url):
        return []

    parsed_start = urlparse(start_url)
    start_host = (parsed_start.hostname or "").lower()
    base_domain = start_host.removeprefix("www.")

    urls_to_visit = [start_url]
    visited = set()
    found_emails = set()

    while (
        urls_to_visit
        and len(visited) < MAX_PAGES_PER_WEBSITE
        and not found_emails
    ):
        current_url = urls_to_visit.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)
        html = _fetch_page(current_url)

        if not html:
            continue

        found_emails.update(_extract_emails(html))

        if found_emails:
            break

        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()

            if href.startswith(("mailto:", "tel:", "javascript:")):
                continue

            target_url = urljoin(current_url, href)
            parsed_target = urlparse(target_url)

            if parsed_target.scheme not in ("http", "https"):
                continue

            target_host = (parsed_target.hostname or "").lower()
            target_domain = target_host.removeprefix("www.")

            if target_domain != base_domain:
                continue

            label = (
                link.get_text(" ", strip=True) + " " + href
            ).lower()

            if any(keyword in label for keyword in CONTACT_KEYWORDS):
                clean_url = parsed_target._replace(
                    fragment=""
                ).geturl()

                if clean_url not in visited and clean_url not in urls_to_visit:
                    urls_to_visit.append(clean_url)

            if len(visited) + len(urls_to_visit) >= MAX_PAGES_PER_WEBSITE:
                break

    return sorted(found_emails)
