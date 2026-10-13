
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def analyze_ux(url):
    score = 0

    report = {
        "mobile_viewport": False,
        "navigation_present": False,
        "cta_present": False,
        "contact_link_present": False,
        "click_to_call_present": False,
        "contact_form_present": False,
        "internal_links_present": False,
        "response_time_acceptable": False,
    }

    try:
        parsed_url = urlparse(url)

        if parsed_url.scheme not in ("http", "https"):
            raise ValueError("URL must use HTTP or HTTPS")

        if not parsed_url.hostname:
            raise ValueError("Invalid URL")

        start_time = time.perf_counter()

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
        )

        elapsed_time = time.perf_counter() - start_time

        response.raise_for_status()

        # Avoid parsing non-HTML responses.
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type.lower():
            raise ValueError("URL did not return an HTML page")

        soup = BeautifulSoup(response.text, "html.parser")

        # 1. Mobile viewport — 15 points
        if soup.find("meta", attrs={"name": "viewport"}):
            score += 15
            report["mobile_viewport"] = True

        # 2. Navigation — 15 points
        if soup.find("nav") or soup.find(attrs={"role": "navigation"}):
            score += 15
            report["navigation_present"] = True

        # 3. Call-to-action — 20 points
        cta_words = (
            "book now",
            "book online",
            "get started",
            "contact us",
            "request a quote",
            "get a quote",
            "schedule",
            "buy now",
            "sign up",
            "learn more",
        )

        cta_found = False

        for element in soup.find_all(["a", "button", "input"]):
            text = " ".join([
                element.get_text(" ", strip=True),
                element.get("aria-label", ""),
                element.get("value", ""),
            ]).lower()

            if any(word in text for word in cta_words):
                cta_found = True
                break

        if cta_found:
            score += 20
            report["cta_present"] = True

        # 4. Contact link — 15 points
        contact_found = False

        for link in soup.find_all("a", href=True):
            href = link["href"].strip().lower()
            text = link.get_text(" ", strip=True).lower()

            if (
                "contact" in href
                or "contact" in text
                or "get in touch" in text
            ):
                contact_found = True
                break

        if contact_found:
            score += 15
            report["contact_link_present"] = True

        # 5. Click-to-call — 10 points
        if soup.find("a", href=lambda value: value and value.lower().startswith("tel:")):
            score += 10
            report["click_to_call_present"] = True

        # 6. Contact form — 10 points
        if soup.find("form"):
            score += 10
            report["contact_form_present"] = True

        # 7. Internal links — 5 points
        internal_links = []

        for link in soup.find_all("a", href=True):
            href = link["href"].strip()

            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue

            absolute_url = urljoin(response.url, href)
            link_host = urlparse(absolute_url).hostname

            if link_host and link_host.lower() == urlparse(response.url).hostname.lower():
                internal_links.append(absolute_url)

        if internal_links:
            score += 5
            report["internal_links_present"] = True

        # 8. Initial HTML response time — 10 points
        if elapsed_time <= 3:
            score += 10
            report["response_time_acceptable"] = True

        return {
            "score": score,
            "report": report,
            "response_time_seconds": round(elapsed_time, 3),
        }

    except (requests.RequestException, ValueError) as error:
        return {
            "score": 0,
            "report": report,
            "response_time_seconds": None,
            "error": str(error),
        }
