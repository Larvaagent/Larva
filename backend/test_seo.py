from app.services.seo_analyzer import analyze_seo

score = analyze_seo(
    "https://apple.com"
)

print("SEO Score:", score)