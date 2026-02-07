import fitz
import os

#DPI（每英寸点数，300 是印刷级高清标准）
def pdf_to_images(pdf_path, out_dir, dpi=300):
    os.makedirs(out_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        img_path = os.path.join(out_dir, f"page_{i+1}.png")
        pix.save(img_path)

if __name__ == "__main__":
    pdf_to_images("Bucalu.pdf", "pages")