
from app.services.ux_analyzer import analyze_ux

url = "https://python.org"

result = analyze_ux(url)

print("UX SCORE:", result["score"])
print("UX REPORT:", result["report"])
print("RESPONSE TIME:", result["response_time_seconds"])

if "error" in result:
    print("ERROR:", result["error"])
