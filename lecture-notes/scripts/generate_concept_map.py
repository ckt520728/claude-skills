"""
Lecture Notes — Concept Map Generator

Phase A: Renders structured concept maps as HTML/CSS → PNG (via Playwright)
Phase B: Adds AI-generated decorative illustrations (via OpenAI)
Phase C: Composites with parchment background texture
"""

import argparse
import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path

try:
    from jinja2 import Template
except ImportError:
    raise ImportError("Please install jinja2: uv pip install jinja2")

try:
    from PIL import Image, ImageFilter
except ImportError:
    raise ImportError("Please install Pillow: uv pip install pillow")


# ─── Color Palette ───
COLORS = {
    "red": {"bg": "#FFEAEA", "border": "#D32F2F", "text": "#B71C1C"},
    "blue": {"bg": "#E3F2FD", "border": "#1565C0", "text": "#0D47A1"},
    "green": {"bg": "#E8F5E9", "border": "#2E7D32", "text": "#1B5E20"},
    "orange": {"bg": "#FFF3E0", "border": "#E65100", "text": "#BF360C"},
    "purple": {"bg": "#F3E5F5", "border": "#6A1B9A", "text": "#4A148C"},
    "gray": {"bg": "#F5F5F5", "border": "#616161", "text": "#212121"},
}

# ─── HTML Template for Concept Map ───
CONCEPT_MAP_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    width: 1200px;
    font-family: 'Noto Sans TC', 'Microsoft JhengHei', sans-serif;
    background: #F5F0E1;
    background-image:
      radial-gradient(ellipse at 20% 50%, rgba(210,180,140,0.3) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(210,180,140,0.2) 0%, transparent 50%);
    padding: 40px;
  }

  .concept-map {
    background: rgba(255,255,255,0.85);
    border-radius: 18px;
    padding: 36px 40px;
    border: 2px solid #D2B48C;
    box-shadow: 0 4px 20px rgba(139,119,101,0.15);
    position: relative;
  }

  .main-title {
    text-align: center;
    font-size: 32px;
    font-weight: 900;
    color: #2C1810;
    margin-bottom: 28px;
    letter-spacing: 2px;
    line-height: 1.4;
  }

  .main-title .highlight {
    color: #D32F2F;
  }

  .groups-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    justify-content: center;
  }

  .group {
    flex: 1;
    min-width: 280px;
    max-width: 48%;
    border-radius: 14px;
    padding: 20px;
    position: relative;
  }

  .group-label {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 14px;
    padding-bottom: 8px;
    border-bottom: 2px solid;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .group-label .icon { font-size: 20px; }

  .node {
    margin: 8px 0;
    padding: 10px 14px;
    border-radius: 10px;
    border-left: 4px solid;
    font-size: 15px;
    line-height: 1.6;
    position: relative;
  }

  .node.emphasis-high {
    font-weight: 700;
    font-size: 16px;
    border-left-width: 6px;
  }

  .node.emphasis-low {
    font-size: 14px;
    opacity: 0.85;
  }

  .node .english {
    color: #666;
    font-size: 13px;
    font-style: italic;
  }

  .node.type-formula {
    font-family: 'Times New Roman', serif;
    font-size: 18px;
    text-align: center;
    background: rgba(255,255,255,0.9) !important;
    border: 2px dashed;
  }

  .node.type-warning {
    background: #FFF8E1 !important;
    border-left-color: #FF6F00 !important;
  }

  .node.type-tip {
    background: #E8F5E9 !important;
    border-left-color: #2E7D32 !important;
  }

  .edges-section {
    margin-top: 20px;
    padding: 16px;
    background: rgba(255,255,255,0.5);
    border-radius: 12px;
    border: 1px dashed #B0A090;
  }

  .edge {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 6px 0;
    font-size: 14px;
    color: #555;
  }

  .edge .arrow { color: #1565C0; font-weight: bold; font-size: 18px; }
  .edge .from-node, .edge .to-node { font-weight: 600; color: #333; }
  .edge .edge-label { color: #888; font-style: italic; }

  .key-takeaway {
    margin-top: 24px;
    padding: 16px 20px;
    background: linear-gradient(135deg, #FFF8E1, #FFFDE7);
    border-radius: 12px;
    border: 2px solid #FFB300;
    font-size: 16px;
    font-weight: 600;
    color: #E65100;
    text-align: center;
    line-height: 1.6;
  }

  .key-takeaway::before {
    content: "💡 ";
    font-size: 20px;
  }

  .formulas-section {
    margin-top: 16px;
    text-align: center;
  }

  .formula-item {
    display: inline-block;
    margin: 8px 12px;
    padding: 10px 20px;
    background: white;
    border: 2px solid #1565C0;
    border-radius: 10px;
    font-family: 'Times New Roman', serif;
    font-size: 20px;
    font-weight: bold;
    color: #0D47A1;
  }

  .illustration-placeholder {
    position: absolute;
    border: 2px dashed #B0A090;
    border-radius: 12px;
    background: rgba(245,240,225,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    color: #999;
    padding: 8px;
    text-align: center;
  }
</style>
</head>
<body>
<div class="concept-map">
  <div class="main-title">{{ main_title }}</div>

  <div class="groups-container">
    {% for group in groups %}
    {% set gc = colors.get(group.color, colors.gray) %}
    <div class="group" style="background: {{ gc.bg }}; border: 2px solid {{ gc.border }};">
      <div class="group-label" style="color: {{ gc.text }}; border-bottom-color: {{ gc.border }};">
        <span class="icon">{{ group_icons[loop.index0 % 6] }}</span>
        {{ group.label }}
      </div>
      {% for node in group.nodes %}
      <div class="node type-{{ node.type }} emphasis-{{ node.emphasis }}"
           style="border-left-color: {{ gc.border }}; background: rgba(255,255,255,0.6);">
        {{ node.text }}
        {% if node.english %}<span class="english"> ({{ node.english }})</span>{% endif %}
      </div>
      {% endfor %}
    </div>
    {% endfor %}
  </div>

  {% if formulas %}
  <div class="formulas-section">
    {% for formula in formulas %}
    <div class="formula-item">{{ formula.latex }}</div>
    {% endfor %}
  </div>
  {% endif %}

  {% if edges %}
  <div class="edges-section">
    {% for edge in edges %}
    <div class="edge">
      <span class="from-node">{{ edge.from_text }}</span>
      <span class="arrow">→</span>
      <span class="to-node">{{ edge.to_text }}</span>
      {% if edge.label %}<span class="edge-label">— {{ edge.label }}</span>{% endif %}
    </div>
    {% endfor %}
  </div>
  {% endif %}

  {% if key_takeaway %}
  <div class="key-takeaway">{{ key_takeaway }}</div>
  {% endif %}
</div>
</body>
</html>"""

GROUP_ICONS = ["📌", "🔬", "📊", "🧠", "⚡", "🎯"]


def build_node_text_map(groups: list[dict]) -> dict[str, str]:
    """Build a map from node ID to node text."""
    node_map = {}
    for group in groups:
        for node in group.get("nodes", []):
            node_map[node["id"]] = node["text"]
    return node_map


def render_concept_map_html(section: dict) -> str:
    """Render a concept map section to HTML string."""
    cmap = section.get("concept_map", {})
    groups = cmap.get("groups", [])
    edges = cmap.get("edges", [])
    formulas = cmap.get("formulas", [])
    key_takeaway = cmap.get("key_takeaway", "")

    # Build node text lookup for edges
    node_map = build_node_text_map(groups)

    # Enrich edges with text
    enriched_edges = []
    for edge in edges:
        enriched_edges.append({
            "from_text": node_map.get(edge.get("from", ""), edge.get("from", "")),
            "to_text": node_map.get(edge.get("to", ""), edge.get("to", "")),
            "label": edge.get("label", ""),
        })

    template = Template(CONCEPT_MAP_TEMPLATE)
    html = template.render(
        main_title=cmap.get("main_title", section.get("title", "")),
        groups=groups,
        edges=enriched_edges,
        formulas=formulas,
        key_takeaway=key_takeaway,
        colors=COLORS,
        group_icons=GROUP_ICONS,
    )
    return html


async def html_to_png(html_content: str, output_path: str, width: int = 1200):
    """Convert HTML to PNG using Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise ImportError("Please install playwright: uv pip install playwright && playwright install chromium")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": 800})

        # Write HTML to temp file
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(html_content)
            temp_html = f.name

        await page.goto(f"file:///{temp_html.replace(os.sep, '/')}")

        # Wait for fonts and rendering
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)

        # Get actual content height
        height = await page.evaluate("document.body.scrollHeight")
        await page.set_viewport_size({"width": width, "height": height + 80})

        # Screenshot
        await page.screenshot(path=output_path, full_page=True)
        await browser.close()

        # Cleanup
        os.unlink(temp_html)

    print(f"  Rendered: {output_path} ({width}x{height + 80})")


def generate_illustration(client, description: str, size: str = "small") -> Image.Image | None:
    """Generate a small decorative illustration using OpenAI image generation."""
    dim = "256x256" if size == "small" else "512x512"

    prompt = (
        f"Simple, cute hand-drawn illustration style, minimal, no text, no words, "
        f"white background, single object: {description}"
    )

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",  # DALL-E 3 minimum
            quality="standard",
            style="natural",
        )

        import urllib.request
        img_url = response.data[0].url

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            urllib.request.urlretrieve(img_url, f.name)
            img = Image.open(f.name).convert("RGBA")
            target = 256 if size == "small" else 512
            img = img.resize((target, target), Image.LANCZOS)
            os.unlink(f.name)
            return img

    except Exception as e:
        print(f"  Warning: Could not generate illustration: {e}")
        return None


def composite_with_background(concept_map_path: str, illustrations: list[dict], client=None):
    """Add parchment background and optional AI illustrations to the concept map."""
    img = Image.open(concept_map_path).convert("RGBA")
    w, h = img.size

    # Create parchment background
    from PIL import ImageDraw
    bg = Image.new("RGBA", (w, h), (245, 240, 225, 255))

    # Add subtle noise/texture effect
    import random
    draw = ImageDraw.Draw(bg)
    for _ in range(w * h // 50):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)
        shade = random.randint(220, 250)
        draw.point((x, y), fill=(shade, shade - 10, shade - 20, 30))

    # Composite: parchment → concept map
    bg.paste(img, (0, 0), img)

    # Add AI illustrations if available
    if client and illustrations:
        for illust in illustrations[:3]:  # Max 3 illustrations per map
            desc = illust.get("description", "")
            pos = illust.get("position", "right")
            size = illust.get("size", "small")

            print(f"  Generating illustration: {desc[:50]}...")
            ill_img = generate_illustration(client, desc, size)

            if ill_img:
                ill_w, ill_h = ill_img.size
                # Position
                if pos == "top-right":
                    x, y = w - ill_w - 20, 20
                elif pos == "right":
                    x, y = w - ill_w - 20, h // 2 - ill_h // 2
                elif pos == "left":
                    x, y = 20, h // 2 - ill_h // 2
                else:  # center or default
                    x, y = w // 2 - ill_w // 2, h - ill_h - 20

                bg.paste(ill_img, (x, y), ill_img)

    # Save
    bg.convert("RGB").save(concept_map_path, "PNG", quality=95)


async def generate_all_concept_maps(
    sections: list[dict],
    output_dir: str,
    openai_api_key: str | None = None,
    with_illustrations: bool = True,
):
    """Generate concept map images for all sections."""
    os.makedirs(output_dir, exist_ok=True)

    client = None
    if openai_api_key and with_illustrations:
        try:
            client = OpenAI(api_key=openai_api_key)
        except Exception:
            print("Warning: Could not initialize OpenAI client for illustrations")

    for section in sections:
        num = section["section_number"]
        title = section["title"]
        print(f"\nSection {num}: {title}")

        # Phase A: Generate HTML → PNG
        html = render_concept_map_html(section)
        output_path = os.path.join(output_dir, f"section_{num:02d}.png")

        html_path = os.path.join(output_dir, f"section_{num:02d}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        await html_to_png(html, output_path)

        # Phase B & C: Add background + illustrations
        illustrations = section.get("concept_map", {}).get("illustrations", [])
        composite_with_background(output_path, illustrations, client)

        print(f"  Final: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate concept map images")
    parser.add_argument("--sections", required=True, help="Path to sections JSON")
    parser.add_argument("--output-dir", required=True, help="Output directory for images")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--no-illustrations", action="store_true", help="Skip AI illustration generation")
    args = parser.parse_args()

    with open(args.sections, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", data if isinstance(data, list) else [])

    asyncio.run(generate_all_concept_maps(
        sections,
        args.output_dir,
        args.api_key,
        with_illustrations=not args.no_illustrations,
    ))


if __name__ == "__main__":
    main()
