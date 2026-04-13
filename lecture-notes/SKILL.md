---
name: lecture-notes
description: |
  Generate beautifully formatted lecture notes PDF from audio recordings and presentation slides (PPT/PDF).
  Combines AI-powered speech transcription (Groq Whisper), content extraction, structured concept map generation
  (HTML/CSS with AI decorative illustrations), and PDF compilation into a cohesive, visually rich document.

  USE THIS SKILL whenever the user wants to:
  - Convert lecture recordings into formatted notes
  - Create lecture notes from audio + slides
  - Transcribe a class recording and make study notes
  - Generate visual concept maps from lecture content
  - Turn a presentation + recording into a study document
  - Make illustrated course notes from class materials
  - Process 錄音檔/上課錄音 into 筆記/講義
  - Create 課堂筆記 from 投影片 and 錄音

  Also trigger when the user mentions: lecture notes, class notes, 課堂筆記, 上課筆記, 講義製作,
  錄音轉筆記, 投影片筆記, or any combination of audio/recording + slides/PPT + notes/summary.
---

# Lecture Notes Generator

Transform lecture audio recordings and presentation slides into beautifully formatted,
visually rich PDF notes — with structured concept maps, color-coded key points, and
organized lecture transcripts.

## Output Style

Each topic section in the output PDF follows this structure:

1. **Section Title** — Bold heading in Chinese (e.g. 「課程介紹：三大挑戰」)
2. **Concept Map** — A large, colorful structured infographic summarizing the section's key ideas
3. **Lecture Transcript** — Conversational Chinese text preserving the speaker's tone, examples, and stories
4. **Separator** — Horizontal line before the next section

### Concept Map Visual Style
- Parchment/beige textured background
- Color coding: **red** = key terms, **green** = supplementary notes, **blue** = connecting arrows
- Concepts enclosed in boxes/rounded rectangles with arrow-based flow
- Chinese as primary language, English terms in parentheses (e.g. 「素流 (Turbulence)」)
- Mathematical formulas where relevant (e.g. E=mc², E(k)∝k^(-5/3))
- Large red/dark bold titles
- Decorative AI-generated illustrations for visual metaphors

### Transcript Style
- Traditional Chinese (繁體中文)
- Conversational tone preserving speaker's voice (「好，那我現在就來介紹...」)
- Speaker's metaphors, stories, and personal anecdotes retained
- Paragraphed by sub-topics

## Required Inputs

| Input | Format | Required |
|-------|--------|----------|
| Audio recording | `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` | Yes |
| Presentation slides | `.pdf` (converted from PPT) or `.pptx` | Yes |
| Course name | Text | Optional |
| Speaker name | Text | Optional |
| Date | Text | Optional |

## Workflow

Follow these steps in order. Each step has a corresponding script in `scripts/`.

### Step 1: Set Up Environment

Create a working directory and install dependencies:

```bash
uv venv --python 3.14 .venv
uv pip install groq openai pymupdf pillow playwright jinja2 weasyprint
playwright install chromium
```

### Step 2: Transcribe Audio

Use `scripts/transcribe.py` to transcribe the audio file via Groq Whisper API.

```bash
python scripts/transcribe.py --audio <path> --output transcript.json --api-key <GROQ_KEY>
```

The script handles:
- Splitting long audio files into 25MB chunks (Groq's limit)
- Sending each chunk to Groq's `whisper-large-v3` model
- Merging results with timestamps into a single transcript JSON

Output: `transcript.json` with timestamped segments.

### Step 3: Extract Slide Content

Use `scripts/extract_pdf.py` to extract text and images from the presentation PDF.

```bash
python scripts/extract_pdf.py --pdf <path> --output slides.json
```

The script uses PyMuPDF to extract:
- Text content from each page/slide
- Embedded images (saved to `assets/slide_images/`)
- Page numbers and layout info

Output: `slides.json` with per-slide content.

### Step 4: Segment and Align Content

Use `scripts/segment.py` to intelligently segment the transcript into topic sections
aligned with the slides.

```bash
python scripts/segment.py --transcript transcript.json --slides slides.json --output sections.json --api-key <OPENAI_KEY>
```

This step uses GPT-4o to:
- Analyze slide content and transcript together
- Identify natural topic boundaries
- Create section titles (Chinese, descriptive)
- Assign transcript segments to corresponding slides
- Extract key concepts, terms, and relationships for each section
- Generate concept map data structure (nodes, edges, groups)

Output: `sections.json` with structured section data.

### Step 5: Generate Concept Maps

Use `scripts/generate_concept_map.py` to create visual concept maps for each section.

```bash
python scripts/generate_concept_map.py --sections sections.json --output-dir concept_maps/ --api-key <OPENAI_KEY>
```

This is a two-phase process:

**Phase A: HTML/CSS Structured Layout**
- Renders each concept map as an HTML page using Jinja2 templates
- Precise Chinese text rendering (no AI text generation errors)
- Color-coded boxes, arrows, flow diagrams
- Mathematical formulas via KaTeX
- Captures as high-resolution PNG via Playwright

**Phase B: AI Decorative Enhancement**
- Uses OpenAI GPT-4o image generation to create small decorative illustrations
  (e.g. a coffee cup for diffusion metaphor, a tornado for turbulence)
- Composites illustrations onto the concept map at designated positions
- Adds parchment texture background

Output: `concept_maps/section_N.png` for each section.

### Step 6: Compile Final PDF

Use `scripts/compile_pdf.py` to assemble everything into the final PDF.

```bash
python scripts/compile_pdf.py \
  --sections sections.json \
  --concept-maps concept_maps/ \
  --output <output_path>.pdf \
  --title <course_name> \
  --speaker <speaker_name> \
  --date <date>
```

The script uses WeasyPrint to generate a PDF with:
- Section titles in bold serif font
- Concept map images (full width)
- Formatted transcript text below each map
- Horizontal separators between sections
- Proper page breaks

Output: Final PDF file.

## API Keys

This skill requires two API keys:

| Service | Purpose | Key |
|---------|---------|-----|
| **Groq** | Audio transcription (Whisper) | User's Groq key |
| **OpenAI** | Content segmentation (GPT-4o) + Decorative illustrations (image generation) | User's OpenAI key |

Ask the user for their API keys if not already known. Keys can also be set as environment variables:
`GROQ_API_KEY` and `OPENAI_API_KEY`.

## Tips

- For best transcription quality, ensure the audio is clear with minimal background noise
- Lectures longer than 2 hours will take longer to process — consider splitting
- The concept map generation is the most time-intensive step (2-3 minutes per section)
- If the user provides a `.pptx` file, convert it to PDF first using LibreOffice or similar
- Always preview the generated concept maps before final PDF compilation and ask the user if adjustments are needed
