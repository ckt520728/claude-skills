# Legacy Scripts (Fallback)

These scripts implement the **old** Groq+OpenAI+WeasyPrint pipeline. The skill
now uses **NotebookLM MCP** as the primary path — see `../SKILL.md`.

Only use these scripts when NotebookLM MCP is unavailable or the user explicitly
asks for local-only processing.

## Requirements

- `GROQ_API_KEY` (Whisper transcription)
- `OPENAI_API_KEY` (GPT-4o segmentation + DALL-E illustrations)
- `ffmpeg` on PATH (for audio chunking)
- Python 3.12+ with: `groq openai pymupdf pillow playwright jinja2 weasyprint`
- `playwright install chromium`

## Workflow

```
python scripts/transcribe.py --audio <path> --output transcript.json
python scripts/extract_pdf.py --pdf <path> --output slides.json --image-dir assets/slide_images
python scripts/segment.py --transcript transcript.json --slides slides.json --output sections.json
python scripts/generate_concept_map.py --sections sections.json --output-dir concept_maps/
python scripts/compile_pdf.py --sections sections.json --concept-maps concept_maps/ --output notes.pdf
```

Or run `scripts/main.py` as an orchestrator.

## Known Limitations vs NotebookLM

- DALL-E illustration quality is inconsistent vs Nano Banana
- OpenAI API quota exhaustion blocks the whole pipeline
- WeasyPrint on Windows requires GTK libraries (Playwright fallback works)
- Chinese concept-map layout is rule-based, less flexible than NotebookLM's generative slides
