"""
Lecture Notes — PDF/PPT Content Extraction

Extracts text and images from presentation PDF files using PyMuPDF.
"""

import argparse
import base64
import json
import os
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("Please install PyMuPDF: uv pip install pymupdf")


def extract_pdf_content(pdf_path: str, image_output_dir: str | None = None) -> dict:
    """
    Extract text and images from each page of a PDF.

    Returns dict with:
      - slides: list of {page_num, text, images: [{path, description}]}
      - total_pages: int
    """
    doc = fitz.open(pdf_path)
    slides = []

    if image_output_dir:
        os.makedirs(image_output_dir, exist_ok=True)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract text
        text = page.get_text("text").strip()

        # Extract images
        images = []
        if image_output_dir:
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    if base_image:
                        img_ext = base_image["ext"]
                        img_data = base_image["image"]
                        img_filename = f"slide_{page_num + 1:03d}_img_{img_idx + 1:02d}.{img_ext}"
                        img_path = os.path.join(image_output_dir, img_filename)

                        with open(img_path, "wb") as f:
                            f.write(img_data)

                        images.append({
                            "path": img_path,
                            "filename": img_filename,
                            "width": base_image.get("width", 0),
                            "height": base_image.get("height", 0),
                        })
                except Exception:
                    continue

        slides.append({
            "page_num": page_num + 1,
            "text": text,
            "images": images,
        })

    doc.close()

    result = {
        "source_file": os.path.basename(pdf_path),
        "total_pages": len(slides),
        "slides": slides,
    }

    print(f"Extracted {len(slides)} pages from {pdf_path}")
    for i, slide in enumerate(slides):
        text_preview = slide["text"][:80].replace("\n", " ") if slide["text"] else "(no text)"
        print(f"  Page {i + 1}: {len(slide['text'])} chars, {len(slide['images'])} images — {text_preview}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Extract content from presentation PDF")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--image-dir", default=None, help="Directory to save extracted images")
    args = parser.parse_args()

    result = extract_pdf_content(args.pdf, args.image_dir)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
