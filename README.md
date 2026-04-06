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
