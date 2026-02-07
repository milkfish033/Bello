# step5_product_cards.py
import json

def build_cards(products_json, out_json):
    products = json.load(open(products_json))
    cards = []

    for p in products:
        cards.append({
            "model": p["model"],
            "pages": p["pages"],
            "text": p["raw_text"]
        })

    json.dump(cards, open(out_json, "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    build_cards("products_raw.json", "product_cards_new.json")
