# ocr_pages.py
import pytesseract
from PIL import Image
import json
import os
import pytesseract, json, os
from PIL import Image

def ocr_image(path):
    data = pytesseract.image_to_data(
        Image.open(path),
        output_type=pytesseract.Output.DICT
    )
    words = []
    for i in range(len(data["text"])):
        if data["text"][i].strip() == "":
            continue
        words.append({
            "text": data["text"][i].strip(),
            "x": data["left"][i],
            "y": data["top"][i],
            "w": data["width"][i],
            "h": data["height"][i],
            "conf": int(data["conf"][i]),
        })
    return words

def run(img_dir, out_json):
    pages = []
    for f in sorted(os.listdir(img_dir)):
        if not f.endswith(".png"):
            continue
        page_no = int(f.split("_")[1].split(".")[0])
        pages.append({
            "page": page_no,
            "words": ocr_image(os.path.join(img_dir, f))
        })
    json.dump(pages, open(out_json, "w"), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run("pages", "ocr_words.json")
