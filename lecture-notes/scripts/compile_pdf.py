"""
Lecture Notes — PDF Compiler

Assembles section titles, concept map images, and transcript text
into a final beautifully formatted PDF using WeasyPrint.
"""

import argparse
import base64
import json
import os
from pathlib import Path

try:
    from jinja2 import Template
except ImportError:
    raise ImportError("Please install jinja2: uv pip install jinja2")


PDF_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=Noto+Serif+TC:wght@400;700;900&display=swap');

  @page {
    size: A4;
    margin: 2cm 2.5cm;

    @bottom-center {
      content: counter(page);
      font-family: 'Noto Sans TC', sans-serif;
      font-size: 10pt;
      color: #999;
    }
  }

  body {
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
    font-size: 14px;
    line-height: 1.8;
    color: #333;
    background: white;
  }

  /* ─── Cover Page ─── */
  .cover {
    page-break-after: always;
    text-align: center;
    padding-top: 30vh;
  }

  .cover h1 {
    font-family: 'Noto Serif TC', serif;
    font-size: 36px;
    font-weight: 900;
    color: #2C1810;
    margin-bottom: 20px;
    letter-spacing: 3px;
  }

  .cover .subtitle {
    font-size: 20px;
    color: #666;
    margin-bottom: 40px;
  }

  .cover .meta {
    font-size: 16px;
    color: #888;
    line-height: 2;
  }

  /* ─── Section ─── */
  .section {
    page-break-before: auto;
    margin-bottom: 40px;
  }

  .section-title {
    font-family: 'Noto Serif TC', serif;
    font-size: 22px;
    font-weight: 900;
    color: #2C1810;
    margin-bottom: 20px;
    padding-bottom: 8px;
    border-bottom: 3px solid #D2B48C;
    letter-spacing: 1px;
    text-decoration: underline;
    text-decoration-color: #D2B48C;
    text-underline-offset: 6px;
  }

  /* ─── Concept Map Image ─── */
  .concept-map-container {
    margin: 16px 0 24px 0;
    text-align: center;
  }

  .concept-map-container img {
    max-width: 100%;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }

  /* ─── Transcript ─── */
  .transcript {
    font-size: 14px;
    line-height: 1.9;
    color: #444;
    text-align: justify;
  }

  .transcript p {
    margin-bottom: 12px;
    text-indent: 0;
  }

  /* ─── Separator ─── */
  .separator {
    border: none;
    border-top: 2px solid #D2B48C;
    margin: 40px 0;
    opacity: 0.5;
  }

  /* ─── Highlight styles in transcript ─── */
  .transcript strong {
    color: #D32F2F;
  }

  .transcript em {
    color: #1565C0;
    font-style: normal;
  }
</style>
</head>
<body>

{% if title %}
<div class="cover">
  <h1>{{ title }}</h1>
  {% if speaker %}<div class="subtitle">{{ speaker }}</div>{% endif %}
  <div class="meta">
    {% if date %}{{ date }}<br>{% endif %}
    課堂筆記
  </div>
</div>
{% endif %}

{% for section in sections %}
<div class="section">
  <div class="section-title">{{ section.title }}</div>

  {% if section.concept_map_image %}
  <div class="concept-map-container">
    <img src="{{ section.concept_map_image }}" alt="{{ section.title }}">
  </div>
  {% endif %}

  <div class="transcript">
    {% for para in section.paragraphs %}
    <p>{{ para }}</p>
    {% endfor %}
  </div>
</div>

{% if not loop.last %}
<hr class="separator">
{% endif %}
{% endfor %}

</body>
</html>"""


def image_to_data_uri(image_path: str) -> str:
    """Convert image to base64 data URI for embedding in HTML."""
    with open(image_path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    ext = Path(image_path).suffix.lower()
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext.lstrip("."), "image/png")

    return f"data:{mime};base64,{data}"


def compile_pdf(
    sections_path: str,
    concept_maps_dir: str,
    output_path: str,
    title: str = "",
    speaker: str = "",
    date: str = "",
):
    """Compile all sections into a final PDF."""

    with open(sections_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections_data = data.get("sections", data if isinstance(data, list) else [])

    # Prepare template data
    template_sections = []
    for section in sections_data:
        num = section["section_number"]
        title_text = section["title"]

        # Find concept map image
        img_path = os.path.join(concept_maps_dir, f"section_{num:02d}.png")
        concept_map_image = ""
        if os.path.exists(img_path):
            concept_map_image = image_to_data_uri(img_path)

        # Split transcript into paragraphs
        transcript = section.get("transcript_text", "")
        paragraphs = [p.strip() for p in transcript.split("\n") if p.strip()]

        template_sections.append({
            "title": title_text,
            "concept_map_image": concept_map_image,
            "paragraphs": paragraphs,
        })

    # Render HTML
    template = Template(PDF_TEMPLATE)
    html = template.render(
        title=title,
        speaker=speaker,
        date=date,
        sections=template_sections,
    )

    # Save intermediate HTML
    html_path = output_path.replace(".pdf", ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Intermediate HTML: {html_path}")

    # Convert to PDF using WeasyPrint
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=".").write_pdf(output_path)
        print(f"PDF generated: {output_path}")
    except ImportError:
        print("WeasyPrint not available. Trying alternative PDF generation...")
        # Fallback: use Playwright to print PDF
        import asyncio

        async def _print_pdf():
            from playwright.async_api import async_playwright
            import tempfile

            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(html)
                temp_html = f.name

            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                await page.goto(f"file:///{temp_html.replace(os.sep, '/')}")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                await page.pdf(
                    path=output_path,
                    format="A4",
                    margin={"top": "2cm", "bottom": "2cm", "left": "2.5cm", "right": "2.5cm"},
                    print_background=True,
                )
                await browser.close()
                os.unlink(temp_html)

        asyncio.run(_print_pdf())
        print(f"PDF generated (via Playwright): {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Compile lecture notes PDF")
    parser.add_argument("--sections", required=True, help="Path to sections JSON")
    parser.add_argument("--concept-maps", required=True, help="Directory with concept map images")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--title", default="", help="Course title")
    parser.add_argument("--speaker", default="", help="Speaker name")
    parser.add_argument("--date", default="", help="Date string")
    args = parser.parse_args()

    compile_pdf(
        args.sections,
        args.concept_maps,
        args.output,
        args.title,
        args.speaker,
        args.date,
    )


if __name__ == "__main__":
    main()
