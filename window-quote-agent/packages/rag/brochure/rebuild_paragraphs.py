# rebuild_paragraphs.py
import json

def group_lines(words, y_thresh=10):
    words = sorted(words, key=lambda w: (w["y"], w["x"]))
    lines = []
    cur = []
    last_y = None

    for w in words:
        # skip very low-confidence garbage if you want (optional):
        # if w.get("conf", 0) < 0: continue
        if last_y is None or abs(w["y"] - last_y) <= y_thresh:
            cur.append(w)
        else:
            if cur:
                lines.append(cur)
            cur = [w]
        last_y = w["y"]

    if cur:
        lines.append(cur)
    return lines

def lines_to_paragraphs(lines, gap_thresh=20):
    # FIX: handle empty lines safely
    if not lines:
        return []

    paras = []
    cur = [lines[0]]

    for i in range(1, len(lines)):
        # use the first word y as line y
        prev_y = lines[i-1][0]["y"]
        this_y = lines[i][0]["y"]
        gap = this_y - prev_y

        if gap <= gap_thresh:
            cur.append(lines[i])
        else:
            paras.append(cur)
            cur = [lines[i]]

    paras.append(cur)
    return paras

def rebuild(ocr_json, out_json, y_thresh=10, gap_thresh=20):
    pages = json.load(open(ocr_json, "r", encoding="utf-8"))
    results = []

    for p in pages:
        words = p.get("words", [])
        page_no = p.get("page")

        lines = group_lines(words, y_thresh=y_thresh)
        paras = lines_to_paragraphs(lines, gap_thresh=gap_thresh)

        for para in paras:
            # para: list of lines; each line: list of word dicts
            line_texts = []
            for line in para:
                line = sorted(line, key=lambda w: w["x"])
                line_texts.append(" ".join(w["text"] for w in line if w.get("text")))
            text = " ".join(t for t in line_texts if t).strip()
            if text:
                results.append({"page": page_no, "text": text})

    json.dump(results, open(out_json, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[OK] paragraphs saved: {out_json} (n={len(results)})")

if __name__ == "__main__":
    rebuild("ocr_words.json", "paragraphs.json")
