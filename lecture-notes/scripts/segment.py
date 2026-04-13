"""
Lecture Notes — Content Segmentation & Alignment

Uses GPT-4o to segment the transcript into topic sections aligned with slides,
and generate concept map data structures for each section.
"""

import argparse
import json
import os

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Please install openai: uv pip install openai")


SEGMENTATION_PROMPT = """你是一位專業的課堂筆記整理專家。你的任務是將課堂錄音逐字稿和投影片內容整合，分段成主題章節，並為每個章節生成概念圖的結構資料。

## 輸入資料

### 投影片內容
{slides_content}

### 錄音逐字稿
{transcript_text}

## 你的任務

請將以上內容分段為多個主題章節。對於每個章節，提供以下 JSON 結構：

```json
{{
  "sections": [
    {{
      "section_number": 1,
      "title": "章節標題（中文，簡潔有力，如「課程介紹：三大挑戰」）",
      "subtitle": "可選的副標題或英文對照",
      "slide_pages": [1, 2, 3],
      "transcript_text": "該章節對應的逐字稿文字（口語化，保留講者語氣，適當分段）",
      "concept_map": {{
        "main_title": "概念圖主標題",
        "groups": [
          {{
            "label": "群組標籤",
            "color": "red|blue|green|orange|purple",
            "nodes": [
              {{
                "id": "node_1",
                "text": "節點文字",
                "type": "concept|example|formula|warning|tip",
                "emphasis": "high|medium|low",
                "english": "可選英文術語"
              }}
            ]
          }}
        ],
        "edges": [
          {{
            "from": "node_1",
            "to": "node_2",
            "label": "箭頭上的標註文字（可選）",
            "style": "arrow|dashed|bold"
          }}
        ],
        "formulas": [
          {{
            "latex": "E = mc^2",
            "context": "在概念圖中的位置說明"
          }}
        ],
        "illustrations": [
          {{
            "description": "一杯咖啡中加入奶油的攪拌過程（比喻擴散性）",
            "position": "left|right|center|top-right",
            "size": "small|medium"
          }}
        ],
        "key_takeaway": "本章節的核心結論，用一句話概括"
      }}
    }}
  ]
}}
```

## 重要原則

1. **章節劃分**：根據投影片的自然分頁和錄音內容的主題轉換來劃分。每個主要概念或投影片主題應該是一個章節。
2. **標題風格**：簡潔、有力、能概括主題，如「混沌與隨機的區別」「歷史上的科學大師與素流」
3. **逐字稿整理**：保留口語化風格和講者語氣，但去除過多的贅字（嗯、啊、那個）。保留講者的比喻、故事和個人經歷。適當分段。
4. **概念圖設計**：
   - 用群組(groups)來組織相關概念
   - 節點(nodes)包含關鍵概念、例子、公式
   - 邊(edges)表示概念之間的邏輯關係
   - 插圖(illustrations)描述視覺比喻（會由 AI 另外生成圖片）
   - 公式(formulas)列出重要數學公式
5. **色彩語義**：red=重要關鍵字, green=補充說明, blue=流程/連結, orange=警告/注意, purple=歷史/人物
6. 每個章節的概念圖應該是自成體系的，能獨立理解
7. 一般一堂課會有 8-15 個章節

請只輸出 JSON，不要有其他文字。"""


def segment_content(
    transcript: dict,
    slides: dict,
    api_key: str,
    model: str = "gpt-4o",
) -> dict:
    """
    Use GPT-4o to segment transcript + slides into topic sections
    with concept map structures.
    """
    client = OpenAI(api_key=api_key)

    # Prepare slides content summary
    slides_parts = []
    for slide in slides["slides"]:
        text = slide["text"].strip()
        if text:
            slides_parts.append(f"--- 投影片第 {slide['page_num']} 頁 ---\n{text}")
    slides_content = "\n\n".join(slides_parts)

    # Prepare transcript text
    transcript_text = transcript["full_text"]

    # If transcript is very long, we may need to truncate or summarize
    # GPT-4o can handle ~128k tokens, so most lectures should be fine
    prompt = SEGMENTATION_PROMPT.format(
        slides_content=slides_content,
        transcript_text=transcript_text,
    )

    print("Sending content to GPT-4o for segmentation...")
    print(f"  Slides: {len(slides_content)} chars across {slides['total_pages']} pages")
    print(f"  Transcript: {len(transcript_text)} chars")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a professional lecture note organizer. Always respond with valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=16000,
        response_format={"type": "json_object"},
    )

    result_text = response.choices[0].message.content
    result = json.loads(result_text)

    sections = result.get("sections", [])
    print(f"Segmented into {len(sections)} sections:")
    for sec in sections:
        print(f"  {sec['section_number']}. {sec['title']}")
        nodes_count = sum(len(g.get("nodes", [])) for g in sec.get("concept_map", {}).get("groups", []))
        print(f"     — {nodes_count} concept nodes, {len(sec.get('concept_map', {}).get('edges', []))} edges")

    return result


def main():
    parser = argparse.ArgumentParser(description="Segment lecture content into sections")
    parser.add_argument("--transcript", required=True, help="Path to transcript JSON")
    parser.add_argument("--slides", required=True, help="Path to slides JSON")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY"), help="OpenAI API key")
    parser.add_argument("--model", default="gpt-4o", help="Model to use (default: gpt-4o)")
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("OpenAI API key required. Use --api-key or set OPENAI_API_KEY env var.")

    with open(args.transcript, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    with open(args.slides, "r", encoding="utf-8") as f:
        slides = json.load(f)

    result = segment_content(transcript, slides, args.api_key, args.model)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
