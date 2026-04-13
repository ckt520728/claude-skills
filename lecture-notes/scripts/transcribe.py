"""
Lecture Notes — Audio Transcription via Groq Whisper API

Transcribes audio files using Groq's whisper-large-v3 model.
Handles file splitting for files > 25MB.
"""

import argparse
import json
import math
import os
import struct
import tempfile
import wave
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    raise ImportError("Please install groq: uv pip install groq")


MAX_CHUNK_BYTES = 24 * 1024 * 1024  # 24MB to stay under 25MB limit


def get_audio_duration_wav(path: str) -> float:
    """Get duration of a WAV file in seconds."""
    with wave.open(path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / rate


def convert_to_wav(input_path: str, output_path: str) -> str:
    """Convert audio to WAV using ffmpeg if available, otherwise try direct read."""
    import subprocess

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
                output_path,
            ],
            capture_output=True,
            check=True,
        )
        return output_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        # If ffmpeg not available, return original file
        # Groq API accepts mp3, wav, m4a, etc. directly
        return input_path


def split_audio_file(audio_path: str, max_bytes: int = MAX_CHUNK_BYTES) -> list[str]:
    """
    Split audio file into chunks under max_bytes.
    Returns list of chunk file paths.
    """
    file_size = os.path.getsize(audio_path)

    if file_size <= max_bytes:
        return [audio_path]

    # Try to split using ffmpeg
    import subprocess

    # Get duration
    result = subprocess.run(
        ["ffmpeg", "-i", audio_path, "-f", "null", "-"],
        capture_output=True, text=True,
    )
    # Parse duration from ffmpeg output
    duration_str = None
    for line in result.stderr.split("\n"):
        if "Duration:" in line:
            duration_str = line.split("Duration:")[1].split(",")[0].strip()
            break

    if not duration_str:
        # Can't determine duration, send as-is and hope for the best
        return [audio_path]

    # Parse HH:MM:SS.xx
    parts = duration_str.split(":")
    total_seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])

    # Calculate chunk duration based on file size ratio
    num_chunks = math.ceil(file_size / max_bytes)
    chunk_duration = total_seconds / num_chunks

    chunks = []
    temp_dir = tempfile.mkdtemp(prefix="lecture_notes_chunks_")

    for i in range(num_chunks):
        start = i * chunk_duration
        chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")

        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", audio_path,
                "-ss", str(start),
                "-t", str(chunk_duration),
                "-acodec", "libmp3lame",
                "-ar", "16000",
                "-ac", "1",
                chunk_path,
            ],
            capture_output=True,
            check=True,
        )
        chunks.append(chunk_path)

    return chunks


def transcribe_chunk(client: Groq, audio_path: str, language: str = "zh") -> dict:
    """Transcribe a single audio chunk via Groq Whisper."""
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            file=(os.path.basename(audio_path), audio_file),
            model="whisper-large-v3",
            language=language,
            response_format="verbose_json",
        )

    return transcription


def transcribe_audio(
    audio_path: str,
    api_key: str,
    language: str = "zh",
) -> dict:
    """
    Transcribe an audio file, handling chunking for large files.

    Returns dict with:
      - full_text: complete transcript
      - segments: list of {start, end, text} dicts
    """
    client = Groq(api_key=api_key)

    print(f"Processing: {audio_path}")
    print(f"File size: {os.path.getsize(audio_path) / 1024 / 1024:.1f} MB")

    # Split if needed
    chunks = split_audio_file(audio_path)
    print(f"Split into {len(chunks)} chunk(s)")

    all_segments = []
    full_text_parts = []
    time_offset = 0.0

    for i, chunk_path in enumerate(chunks):
        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        result = transcribe_chunk(client, chunk_path, language)

        # Handle response - may be dict or object
        if hasattr(result, "text"):
            text = result.text
            segments = getattr(result, "segments", [])
        else:
            text = result.get("text", "")
            segments = result.get("segments", [])

        full_text_parts.append(text)

        for seg in segments:
            if hasattr(seg, "start"):
                seg_dict = {"start": seg.start, "end": seg.end, "text": seg.text}
            else:
                seg_dict = {"start": seg["start"], "end": seg["end"], "text": seg["text"]}

            seg_dict["start"] += time_offset
            seg_dict["end"] += time_offset
            all_segments.append(seg_dict)

        # Update time offset for next chunk
        if all_segments:
            time_offset = all_segments[-1]["end"]

    # Clean up temp chunks
    if len(chunks) > 1:
        for chunk_path in chunks:
            if chunk_path != audio_path:
                try:
                    os.remove(chunk_path)
                except OSError:
                    pass

    result = {
        "full_text": " ".join(full_text_parts),
        "segments": all_segments,
        "audio_file": os.path.basename(audio_path),
        "language": language,
    }

    print(f"Transcription complete: {len(all_segments)} segments, {len(result['full_text'])} chars")
    return result


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio via Groq Whisper")
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--api-key", default=os.environ.get("GROQ_API_KEY"), help="Groq API key")
    parser.add_argument("--language", default="zh", help="Language code (default: zh)")
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("Groq API key required. Use --api-key or set GROQ_API_KEY env var.")

    result = transcribe_audio(args.audio, args.api_key, args.language)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
