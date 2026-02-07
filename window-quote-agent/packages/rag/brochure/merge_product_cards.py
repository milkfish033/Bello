# merge_product_cards.py
import json
from collections import defaultdict

def merge_product_cards(input_json, output_json):
    cards = json.load(open(input_json, "r", encoding="utf-8"))

    merged = defaultdict(lambda: {
        "model": None,
        "pages": set(),
        "text_parts": []
    })

    for c in cards:
        model = c.get("model")
        if not model:
            continue

        m = merged[model]
        m["model"] = model
        for p in c.get("pages", []):
            m["pages"].add(p)
        txt = c.get("text", "").strip()
        if txt:
            m["text_parts"].append(txt)

    out = []
    for model, v in merged.items():
        out.append({
            "model": model,
            "pages": sorted(v["pages"]),
            "text": "\n".join(v["text_parts"])
        })

    json.dump(out, open(output_json, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"[OK] merged {len(cards)} → {len(out)} product cards")

if __name__ == "__main__":
    merge_product_cards("product_cards_new.json", "product_cards_merged.json")
