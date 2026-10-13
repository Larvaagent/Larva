import requests
from bs4 import BeautifulSoup


def analyze_seo(url):
    score = 0

    report = {
        "https": False,
        "title": False,
        "meta_description": False,
        "h1": False,
        "viewport": False,
        "image_alt": False,
        "internal_links": False,
        "content_length": False
    }

    try:
        response = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # HTTPS
        if url.startswith("https://"):
            score += 10
            report["https"] = True

        # Title Tag
        if soup.title and soup.title.text.strip():
            score += 15
            report["title"] = True

        # Meta Description
        meta = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        if meta:
            score += 15
            report["meta_description"] = True

        # H1 Tag
        if soup.find("h1"):
            score += 10
            report["h1"] = True

        # Mobile Viewport
        viewport = soup.find(
            "meta",
            attrs={"name": "viewport"}
        )

        if viewport:
            score += 10
            report["viewport"] = True

        # Images with ALT text
        images = soup.find_all("img")

        if len(images) > 0:
            alt_count = sum(
                1 for img in images
                if img.get("alt")
            )

            if alt_count == len(images):
                score += 15
                report["image_alt"] = True

        # Internal Links
        links = soup.find_all("a")

        if len(links) > 5:
            score += 10
            report["internal_links"] = True

        # Content Length
        text = soup.get_text()

        if len(text) > 1000:
            score += 15
            report["content_length"] = True

        return {
            "score": score,
            "report": report
        }

    except Exception as e:
        print("SEO Error:", e)

        return {
            "score": 0,
            "report": report
        }