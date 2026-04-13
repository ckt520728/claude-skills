"""
Lecture Notes — Main Orchestrator

Runs the full pipeline:
  1. Transcribe audio → transcript.json
  2. Extract PDF slides → slides.json
  3. Segment content → sections.json
  4. Generate concept maps → concept_maps/
  5. Compile PDF → output.pdf
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def ensure_dependencies():
    """Check and report missing dependencies."""
    missing = []
    try:
        import groq
    except ImportError:
        missing.append("groq")
    try:
        import openai
    except ImportError:
        missing.append("openai")
    try:
        import fitz
    except ImportError:
        missing.append("pymupdf")
    try:
        from jinja2 import Template
    except ImportError:
        missing.append("jinja2")
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")

    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: uv pip install {' '.join(missing)}")
        sys.exit(1)


def run_pipeline(
    audio_path: str,
    slides_path: str,
    output_path: str,
    groq_api_key: str,
    openai_api_key: str,
    title: str = "",
    speaker: str = "",
    date: str = "",
    skip_illustrations: bool = False,
    language: str = "zh",
):
    """Run the full lecture notes generation pipeline."""

    ensure_dependencies()

    # Set up working directory
    work_dir = Path(output_path).parent / f"lecture_notes_work_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    work_dir.mkdir(parents=True, exist_ok=True)
    print(f"Working directory: {work_dir}")

    scripts_dir = Path(__file__).parent

    # ── Step 1: Transcribe Audio ──
    print("\n" + "=" * 60)
    print("Step 1/5: Transcribing audio...")
    print("=" * 60)

    from transcribe import transcribe_audio
    transcript = transcribe_audio(audio_path, groq_api_key, language)

    transcript_path = work_dir / "transcript.json"
    with open(transcript_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    print(f"Saved: {transcript_path}")

    # ── Step 2: Extract Slides ──
    print("\n" + "=" * 60)
    print("Step 2/5: Extracting slide content...")
    print("=" * 60)

    from extract_pdf import extract_pdf_content
    image_dir = str(work_dir / "slide_images")
    slides = extract_pdf_content(slides_path, image_dir)

    slides_path_out = work_dir / "slides.json"
    with open(slides_path_out, "w", encoding="utf-8") as f:
        json.dump(slides, f, ensure_ascii=False, indent=2)
    print(f"Saved: {slides_path_out}")

    # ── Step 3: Segment & Align ──
    print("\n" + "=" * 60)
    print("Step 3/5: Segmenting content with GPT-4o...")
    print("=" * 60)

    from segment import segment_content
    sections = segment_content(transcript, slides, openai_api_key)

    sections_path = work_dir / "sections.json"
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    print(f"Saved: {sections_path}")

    # ── Step 4: Generate Concept Maps ──
    print("\n" + "=" * 60)
    print("Step 4/5: Generating concept maps...")
    print("=" * 60)

    from generate_concept_map import generate_all_concept_maps
    concept_maps_dir = str(work_dir / "concept_maps")

    asyncio.run(generate_all_concept_maps(
        sections.get("sections", []),
        concept_maps_dir,
        openai_api_key if not skip_illustrations else None,
        with_illustrations=not skip_illustrations,
    ))

    # ── Step 5: Compile PDF ──
    print("\n" + "=" * 60)
    print("Step 5/5: Compiling final PDF...")
    print("=" * 60)

    from compile_pdf import compile_pdf
    compile_pdf(
        str(sections_path),
        concept_maps_dir,
        output_path,
        title=title,
        speaker=speaker,
        date=date,
    )

    print("\n" + "=" * 60)
    print(f"DONE! Output: {output_path}")
    print(f"Working files: {work_dir}")
    print("=" * 60)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate lecture notes PDF from audio + slides",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --audio lecture.mp3 --slides slides.pdf --output notes.pdf
  python main.py --audio lecture.m4a --slides slides.pdf --output notes.pdf \\
    --title "廣義全息譜" --speaker "黃鍔院士" --date "2026-04-01"
        """,
    )
    parser.add_argument("--audio", required=True, help="Path to audio recording")
    parser.add_argument("--slides", required=True, help="Path to slides PDF")
    parser.add_argument("--output", required=True, help="Output PDF path")
    parser.add_argument("--groq-key", default=os.environ.get("GROQ_API_KEY"), help="Groq API key")
    parser.add_argument("--openai-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--title", default="", help="Course title")
    parser.add_argument("--speaker", default="", help="Speaker name")
    parser.add_argument("--date", default="", help="Date string")
    parser.add_argument("--no-illustrations", action="store_true", help="Skip AI illustrations")
    parser.add_argument("--language", default="zh", help="Audio language (default: zh)")
    args = parser.parse_args()

    if not args.groq_key:
        print("Error: Groq API key required. Use --groq-key or set GROQ_API_KEY env var.")
        sys.exit(1)
    if not args.openai_key:
        print("Error: OpenAI API key required. Use --openai-key or set OPENAI_API_KEY env var.")
        sys.exit(1)

    run_pipeline(
        audio_path=args.audio,
        slides_path=args.slides,
        output_path=args.output,
        groq_api_key=args.groq_key,
        openai_api_key=args.openai_key,
        title=args.title,
        speaker=args.speaker,
        date=args.date,
        skip_illustrations=args.no_illustrations,
        language=args.language,
    )


if __name__ == "__main__":
    main()
