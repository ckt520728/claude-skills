# Claude Skills

A collection of custom Claude Code skills.

## Skills

### admission-note

Automatically generates a hospital admission note (`.docx`) from patient data provided via:
- Screenshots / images
- Word files (`.docx`)
- Excel files (`.xlsx`)

**Trigger phrases:** "admission note", "住院病歷", "入院紀錄"

**Output:** A formatted Word document with sections:
Chief Complaint, HPI, PMH, PSH, Medications, Allergies, Family History, Social History, Review of Systems, Vital Signs, Physical Examination, Labs, Imaging, Assessment & Plan.

#### Installation

1. Copy the `admission-note/` folder into your Claude Code skills directory:
   ```
   %APPDATA%\Claude\local-agent-mode-sessions\skills-plugin\<session-id>\skills\
   ```
2. Register the skill in `manifest.json` by adding:
   ```json
   { "skillId": "admission-note", "enabled": true }
   ```
3. Restart Claude Code.

Alternatively, use the pre-packaged `admission-note.skill` file.

---

### lecture-notes

Transforms lecture audio recordings and presentation slides (PDF/PPT) into beautifully formatted PDF notes with structured concept maps and organized transcripts.

**Pipeline:**
1. **Audio Transcription** — Groq Whisper API (`whisper-large-v3`)
2. **Slide Extraction** — PyMuPDF text + image extraction
3. **Content Segmentation** — GPT-4o segments transcript into topic sections aligned with slides
4. **Concept Map Generation** — HTML/CSS structured infographics rendered to PNG via Playwright, with optional AI decorative illustrations (DALL-E)
5. **PDF Compilation** — WeasyPrint / Playwright PDF output

**Trigger phrases:** "lecture notes", "課堂筆記", "錄音轉筆記", "上課筆記"

**Required API Keys:**
- Groq API Key (for Whisper STT)
- OpenAI API Key (for GPT-4o segmentation + DALL-E illustrations)

**Quick Start:**
```bash
# Install dependencies
uv pip install groq openai pymupdf pillow jinja2 playwright
playwright install chromium

# Run full pipeline
python lecture-notes/scripts/main.py \
  --audio recording.mp3 \
  --slides slides.pdf \
  --output notes.pdf \
  --groq-key $GROQ_API_KEY \
  --openai-key $OPENAI_API_KEY \
  --title "Course Title" \
  --speaker "Speaker Name" \
  --date "2026-04-01"
```

**Output Style:** Each section contains a bold title, a colorful concept map (parchment background, color-coded nodes, flow arrows), and conversational lecture transcript in Traditional Chinese.
