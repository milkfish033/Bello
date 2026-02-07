# layout_parse.py
import json

def classify_block(b):
    if b["height"] > 60 and b["conf"] > 80:
        return "title"
    if b["left"] < 200:
        return "features"
    return "specs"

def parse_pages(ocr_json, out_json):
    pages = json.load(open(ocr_json, "r"))
    parsed = []

    for p in pages:
        blocks = p["blocks"]
        items = {"title": [], "features": [], "specs": []}

        for b in blocks:
            t = classify_block(b)
            items[t].append(b["text"])

        parsed.append({
            "page": p["page"],
            "title": " ".join(items["title"]),
            "features": items["features"],
            "specs": " ".join(items["specs"])
        })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parse_pages("ocr_raw.json", "pages_structured.json")
