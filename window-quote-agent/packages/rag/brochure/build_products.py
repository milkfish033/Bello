# step4_build_products.py
import json, re

MODEL_RE = re.compile(r"\b[A-Z]{2,}\d+[A-Z]?\b")

def build_products(paragraphs_json, out_json):
    paras = json.load(open(paragraphs_json))
    products = []
    cur = None

    for p in paras:
        text = p["text"]
        m = MODEL_RE.search(text)
        if m:
            if cur:
                products.append(cur)
            cur = {
                "model": m.group(0),
                "pages": set([p["page"]]),
                "raw_text": [text]
            }
        else:
            if cur:
                cur["raw_text"].append(text)
                cur["pages"].add(p["page"])

    if cur:
        products.append(cur)

    # finalize
    for prod in products:
        prod["pages"] = sorted(list(prod["pages"]))
        prod["raw_text"] = "\n".join(prod["raw_text"])

    json.dump(products, open(out_json, "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    build_products("paragraphs.json", "products_raw.json")
