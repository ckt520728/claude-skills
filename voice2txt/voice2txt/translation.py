"""第二階段：Whisper 先把語音轉成文字，再由 LLM 整理、去除雜訊；中翻英模式同時翻譯。"""
from dataclasses import dataclass
import json
import time
import urllib.error
import urllib.request

OLLAMA = 'http://127.0.0.1:11434/api/'
RULES = (
    'You clean up raw speech-recognition (ASR) transcripts. The input may contain filler words, stutters, '
    'repetitions, false starts, self-corrections, misrecognized homophones and missing punctuation.\n'
    '- Remove filler words (嗯、呃、啊、那個、就是 used as filler; um, uh, like, you know), stuttered or repeated '
    'words, and stray letters produced by recognizing filler sounds (e.g. a lone "N," or "M," for 嗯).\n'
    '- Self-correction: only when the speaker explicitly signals a correction (不對、我是說、更正、應該是; sorry, '
    'I mean, no wait), keep only the corrected version. Example: 「三點，不對，四點」 -> 「四點」.\n'
    '- A contrast or negation is information, NOT a self-correction: keep both parts exactly. Examples: '
    '「禮拜一，不是禮拜二」 stays 「禮拜一，不是禮拜二」; "Monday, not Tuesday" stays "Monday, not Tuesday".\n'
    '- Fix a misrecognized word only when the context makes the intended word clear; prefer the glossary spelling.\n'
    '- Add correct punctuation and sentence breaks.\n'
    '- Never add, summarize or omit information. Keep every event, negation, date, time, place, quantity and name.\n'
    '- If nothing needs fixing, return the text unchanged.\n'
    '- Return only the final text, without quotes, notes or explanations.')
TASKS = {
    'zh': 'Output the cleaned transcript in Traditional Chinese (Taiwan usage).',
    'en': 'Output the cleaned transcript in English.',
    'translate': 'The transcript is Chinese. Clean it up, then translate it into natural English. '
                 'Output only the English translation.',
    'ask': 'The transcript is a spoken question or instruction, not text to clean up; this task overrides the '
           'rule about returning the text unchanged. Answer it directly and concisely in the same language as '
           'the transcript (Traditional Chinese for Chinese, English for English). If selected text is provided '
           'and the instruction refers to it (rewrite, translate, summarise, fix, answer about it), apply the '
           'instruction to that text and output only the result. Never add preamble, quotes or explanations; '
           'the output must be ready to paste. The clean-up rules above apply only to understanding the spoken '
           'transcript; they do not limit the answer.',
}
CONTEXT_HINTS = {
    'code': 'The destination is a code or terminal app: keep plain text without markdown.',
    'email': 'The destination is an email or document app: keep paragraphs.',
    'document': 'The destination is an email or document app: keep paragraphs.',
    'chat': 'The destination is a chat app: keep it short.',
}
SELECTION_LIMIT = 2000
# 雲端備援：只送出 Whisper 轉錄文字，不送錄音；依用量計費，需使用者自備 API key。
# 固定順序：Anthropic（Claude，預設 low 以兼顧每段延遲）→ OpenAI（快、品質穩定）→ Gemini（較慢，預設 low 以免逾時）。
# 供應商只有在啟用並填入 API key 時才會加入鏈中；整體鏈為 Ollama → Anthropic → OpenAI → Gemini → 僅 Whisper。
CLOUD = {'Anthropic': ('claude-sonnet-5-5', 'low'), 'OpenAI': ('gpt-6-luna', 'high'),
         'Gemini': ('gemini-3.8-flash', 'low')}
ANTHROPIC_VERSION = '2026-10-21'
EFFORTS = ('low', 'medium', 'high')


def _context_block(mode, context):
    app = (context.get('app') or '').strip()
    title = (context.get('title') or '').strip()
    category = (context.get('category') or '').strip()
    selection = (context.get('selection') or '')[:SELECTION_LIMIT]
    lines = []
    if app or title:
        lines.append(f"Output destination: {app or 'unknown'} ({category or 'other'}) — window: {title}")
    if mode != 'ask' and category in CONTEXT_HINTS:
        lines.append(CONTEXT_HINTS[category])
    if selection.strip():
        lines.append('Selected text in the target field:\n' + selection)
    return '\n'.join(lines)


def instructions(mode, vocabulary='', context=None):
    if mode not in TASKS:
        raise ValueError('不支援的模式')
    glossary = f'\nGlossary (preferred spellings): {vocabulary[:500]}' if vocabulary.strip() else ''
    block = _context_block(mode, context) if context else ''
    return f'{RULES}\n{TASKS[mode]}{glossary}' + (f'\n{block}' if block else '')


def _local_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def ollama_models(timeout=2):
    """回傳本機 Ollama 已下載的本機模型；未安裝或未啟動時回傳空清單。"""
    try:
        with _local_opener().open(OLLAMA + 'tags', timeout=timeout) as response:
            models = json.load(response).get('models', [])
    except (OSError, ValueError):
        return []
    return [m['name'] for m in models
            if m.get('name') and 'cloud' not in m['name'].lower() and not m.get('remote_host')]


def pick_ollama_model(names, preferred='gemma4:latest'):
    return preferred if preferred in names else (names[0] if names else '')


class LocalTranslator:
    def __init__(self, model):
        if not model.strip() or 'cloud' in model.lower():
            raise ValueError('請選擇已下載的本機模型，不能使用 cloud 模型。')
        self.model = model.strip()
        self.name = 'Ollama ' + self.model
        self.prepared = False
        self.opener = _local_opener()

    def _post(self, path, body, timeout=55):
        request = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)

    def prepare(self):
        metadata = self._post('show', {'model': self.model})
        if metadata.get('remote_host') or metadata.get('remote_model'):
            raise ValueError('此模型指向遠端服務，請改用本機模型。')
        self._post('generate', {'model': self.model, 'stream': False, 'keep_alive': '5m',
                                'options': {'num_ctx': 2048}})
        self.prepared = True

    def refine(self, text, mode, vocabulary='', context=None):
        if not self.prepared:
            self.prepare()
        result = self._post('chat', {
            'model': self.model, 'stream': False, 'think': False, 'keep_alive': '5m',
            'messages': [{'role': 'system', 'content': instructions(mode, vocabulary, context)},
                         {'role': 'user', 'content': text}],
            'options': {'num_ctx': 2048, 'temperature': 0, 'num_predict': 384},
        }, timeout=20)
        output = result.get('message', {}).get('content', '').strip()
        if not output or result.get('done_reason') == 'length':
            raise RuntimeError('整理未完成，原文仍會保留。')
        return output


class CloudTranslator:
    def __init__(self, provider, model, api_key, effort='', timeout=30):
        if provider not in CLOUD:
            raise ValueError('不支援的雲端備援服務')
        if not api_key.strip():
            raise ValueError(f'{provider} 備援需要 API key。')
        effort = effort or CLOUD[provider][1]
        if effort not in EFFORTS:
            raise ValueError('推理強度必須是 low、medium 或 high')
        self.provider = provider
        self.model = model.strip() or CLOUD[provider][0]
        self.effort = effort
        self.name = f'{provider} {self.model} ({effort})'
        self.api_key = api_key.strip()
        self.timeout = timeout

    def request(self, text, mode, vocabulary='', context=None):
        system = instructions(mode, vocabulary, context)
        if self.provider == 'Gemini':
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
            headers = {'x-goog-api-key': self.api_key}
            body = {'systemInstruction': {'parts': [{'text': system}]},
                    'contents': [{'role': 'user', 'parts': [{'text': text}]}],
                    'generationConfig': {'thinkingConfig': {'thinkingLevel': self.effort}}}
        elif self.provider == 'Anthropic':
            url = 'https://api.anthropic.com/v1/messages'
            headers = {'x-api-key': self.api_key, 'anthropic-version': ANTHROPIC_VERSION}
            body = {'model': self.model, 'max_tokens': 1024, 'system': system,
                    'messages': [{'role': 'user', 'content': text}],
                    'output_config': {'effort': self.effort}}
        else:
            url = 'https://api.openai.com/v1/responses'
            headers = {'Authorization': 'Bearer ' + self.api_key}
            body = {'model': self.model, 'instructions': system, 'input': text,
                    'reasoning': {'effort': self.effort}}
        headers['Content-Type'] = 'application/json'
        return urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)

    def parse(self, data):
        if self.provider == 'Gemini':
            candidate = (data.get('candidates') or [{}])[0]
            complete = candidate.get('finishReason') in (None, 'STOP')
            text = ''.join(p.get('text', '') for p in candidate.get('content', {}).get('parts', [])
                           if not p.get('thought'))
        elif self.provider == 'Anthropic':
            stop = data.get('stop_reason')
            if stop == 'refusal':
                category = (data.get('stop_details') or {}).get('category')
                raise RuntimeError('Anthropic 拒絕處理此內容' + (f'（{category}）' if category else '') + '。')
            complete = stop in (None, 'end_turn')
            text = ''.join(b.get('text', '') for b in data.get('content', []) if b.get('type') == 'text')
        else:
            complete = data.get('status') in (None, 'completed')
            text = ''.join(c.get('text', '') for item in data.get('output', []) if item.get('type') == 'message'
                           for c in item.get('content', []) if c.get('type') == 'output_text')
        text = text.strip()
        if not text or not complete:
            raise RuntimeError('整理未完成。')
        return text

    def refine(self, text, mode, vocabulary='', context=None):
        try:
            with urllib.request.urlopen(self.request(text, mode, vocabulary, context), timeout=self.timeout) as response:
                return self.parse(json.load(response))
        except urllib.error.HTTPError as error:
            try:
                detail = json.load(error).get('error', {}).get('message', '')
            except (OSError, ValueError, AttributeError):
                detail = ''
            raise RuntimeError(f'HTTP {error.code} {detail[:160]}'.strip()) from None


class TranslatorChain:
    """依序嘗試 LLM；失敗者暫停 cooldown 秒，避免每一段都等待逾時。"""

    def __init__(self, translators, cooldown=60, clock=time.monotonic):
        self.translators = list(translators)
        self.cooldown = cooldown
        self.clock = clock
        self.paused = {}
        self.last_backend = ''
        self.errors = []

    @property
    def name(self):
        return ' → '.join(t.name for t in self.translators)

    def pause(self, translator):
        self.paused[translator.name] = self.clock() + self.cooldown

    def refine(self, text, mode, vocabulary='', context=None):
        errors = []
        for translator in self.translators:
            if self.paused.get(translator.name, 0) > self.clock():
                continue
            try:
                output = _refine(translator, text, mode, vocabulary, context)
            except Exception as error:
                self.pause(translator)
                errors.append(f'{translator.name}：{error}')
                continue
            self.last_backend = translator.name
            self.errors = errors
            return output
        self.errors = errors
        raise RuntimeError('；'.join(errors) or '所有 LLM 暫停中')


def build_translator(ollama_model='', clouds=()):
    """建立 Ollama → Anthropic → OpenAI → Gemini 的 LLM 鏈；Ollama 準備失敗不阻擋載入。

    clouds 為 (provider, model, api_key, effort) 序列，依 CLOUD 的固定順序排列。
    """
    translators, warnings, failed = [], [], None
    if ollama_model:
        local = LocalTranslator(ollama_model)
        try:
            local.prepare()
        except Exception as error:
            failed = local
            warnings.append(f'{local.name} 無法使用（{error}），先改用備援。')
        translators.append(local)
    order = list(CLOUD)
    for provider, model, api_key, effort in sorted(clouds, key=lambda c: order.index(c[0])):
        translators.append(CloudTranslator(provider, model, api_key, effort))
    if not translators:
        return None, warnings
    chain = TranslatorChain(translators)
    if failed:
        chain.pause(failed)
    return chain, warnings


def _refine(translator, text, mode, vocabulary, context):
    # context 為 None 時維持舊呼叫形狀，相容只接受三個參數的替身／舊後端。
    if context is None:
        return translator.refine(text, mode, vocabulary)
    return translator.refine(text, mode, vocabulary, context)


@dataclass
class DecodeResult:
    text: str
    source: str = ''
    error: str = ''
    backend: str = ''
    warning: str = ''


def decode_segment(engine, audio, mode, vocabulary='', translator=None, context=None, ask_language='zh'):
    """第一階段 Whisper 語音轉文字；有 LLM 鏈時第二階段整理（及翻譯），原始轉錄保留在 source。"""
    if mode == 'ask':
        # 隨便問：沒有 Whisper 備援，沒有 LLM 時只顯示原始轉錄。
        source = engine.transcribe(audio, 'en' if ask_language == 'en' else 'zh', vocabulary)
        if not source:
            return DecodeResult('')
        no_llm = '沒有可用的 LLM，顯示原始轉錄'
        if translator is None:
            return DecodeResult(source, source, backend='Whisper', warning=no_llm)
        try:
            text = _refine(translator, source, mode, vocabulary, context)
        except Exception:
            return DecodeResult(source, source, backend='Whisper', warning=no_llm)
        converter = getattr(engine, 'converter', None)
        if ask_language == 'zh' and converter is not None:
            text = converter.convert(text)  # 與口述 zh 相同：LLM 偶爾輸出簡體，統一轉為台灣繁體。
        backend = getattr(translator, 'last_backend', '') or getattr(translator, 'name', 'LLM')
        return DecodeResult(text, source, backend=backend, warning='；'.join(getattr(translator, 'errors', [])))
    if translator is None:
        return DecodeResult(engine.transcribe(audio, mode, vocabulary), backend='Whisper')
    source = engine.transcribe(audio, 'en' if mode == 'en' else 'zh', vocabulary)
    if not source:
        return DecodeResult('')
    try:
        text = _refine(translator, source, mode, vocabulary, context)
    except Exception as llm_error:
        if mode != 'translate':
            # 整理失敗時直接使用 Whisper 原始轉錄。
            return DecodeResult(source, source, backend='Whisper', warning=str(llm_error))
        # 最後備援：Whisper 直接語音翻譯，完全離線。
        try:
            text = engine.transcribe(audio, 'translate', vocabulary)
        except Exception as whisper_error:
            return DecodeResult('', source, f'{llm_error}；Whisper：{whisper_error}')
        if not text:
            return DecodeResult('', source, f'{llm_error}；Whisper 未產生譯文')
        return DecodeResult(text, source, backend='Whisper', warning=str(llm_error))
    converter = getattr(engine, 'converter', None)
    if mode == 'zh' and converter is not None:
        text = converter.convert(text)  # LLM 偶爾輸出簡體，統一轉為台灣繁體。
    backend = getattr(translator, 'last_backend', '') or getattr(translator, 'name', 'LLM')
    return DecodeResult(text, source, backend=backend, warning='；'.join(getattr(translator, 'errors', [])))
