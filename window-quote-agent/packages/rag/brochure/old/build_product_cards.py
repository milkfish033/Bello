# build_product_cards.py
import json
import re

def extract_model(title):
    m = re.search(r"[A-Z]{2,}\d+[A-Z]?", title)
    return m.group(0) if m else ""

def build_cards(structured_json, out_json):
    pages = json.load(open(structured_json))
    cards = []

    for p in pages:
        model = extract_model(p["title"])
        if not model:
            continue
        cards.append({
            "model": model,
            "page": p["page"],
            "title": p["title"],
            "key_features": p["features"],
            "specs_text": p["specs"]
        })

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    build_cards("pages_structured.json", "product_cards.json")
