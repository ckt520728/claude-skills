import Combine
import Foundation
import Security

// 第二階段：Whisper 轉錄後由雲端 LLM 整理（去除贅詞、套用明確自我更正、補標點；中翻英模式同時翻譯）。
// iOS 版只有雲端備援（無 Ollama）。只送出 Whisper 轉錄文字，不送錄音；依用量計費，需自備 API key。
// 提示詞 RULES / TASKS 必須與 voice2txt/translation.py 逐字一致（修改時兩邊同步）。
// 注意：此檔尚未在 Xcode 編譯。

enum RefinePrompt {
    // MUST stay in sync with voice2txt/translation.py RULES.
    static let rules = """
You clean up raw speech-recognition (ASR) transcripts. The input may contain filler words, stutters, repetitions, false starts, self-corrections, misrecognized homophones and missing punctuation.
- Remove filler words (嗯、呃、啊、那個、就是 used as filler; um, uh, like, you know), stuttered or repeated words, and stray letters produced by recognizing filler sounds (e.g. a lone "N," or "M," for 嗯).
- Self-correction: only when the speaker explicitly signals a correction (不對、我是說、更正、應該是; sorry, I mean, no wait), keep only the corrected version. Example: 「三點，不對，四點」 -> 「四點」.
- A contrast or negation is information, NOT a self-correction: keep both parts exactly. Examples: 「禮拜一，不是禮拜二」 stays 「禮拜一，不是禮拜二」; "Monday, not Tuesday" stays "Monday, not Tuesday".
- Fix a misrecognized word only when the context makes the intended word clear; prefer the glossary spelling.
- Add correct punctuation and sentence breaks.
- Never add, summarize or omit information. Keep every event, negation, date, time, place, quantity and name.
- If nothing needs fixing, return the text unchanged.
- Return only the final text, without quotes, notes or explanations.
"""

    // MUST stay in sync with voice2txt/translation.py TASKS.
    static let tasks: [String: String] = [
        "zh": """
Output the cleaned transcript in Traditional Chinese (Taiwan usage).
""",
        "en": """
Output the cleaned transcript in English.
""",
        "translate": """
The transcript is Chinese. Clean it up, then translate it into natural English. Output only the English translation.
""",
    ]

    /// task 為 "zh"、"en" 或 "translate"，對應桌面版 instructions(mode)。
    static func instructions(task: String, vocabulary: String = "") -> String {
        let trimmed = vocabulary.trimmingCharacters(in: .whitespacesAndNewlines)
        let glossary = trimmed.isEmpty ? "" : "\nGlossary (preferred spellings): \(String(trimmed.prefix(500)))"
        return "\(rules)\n\(tasks[task] ?? "")\(glossary)"
    }
}

enum RefineEffort: String, CaseIterable, Identifiable, Codable {
    case low, medium, high
    var id: String { rawValue }
}

// 固定順序：Anthropic → OpenAI → Gemini。
enum CloudProvider: String, CaseIterable, Identifiable, Codable {
    case anthropic, openai, gemini

    var id: String { rawValue }

    var title: String {
        switch self {
        case .anthropic: return "Anthropic"
        case .openai: return "OpenAI"
        case .gemini: return "Gemini"
        }
    }

    var defaultModel: String {
        switch self {
        case .anthropic: return "claude-sonnet-5-5"
        case .openai: return "gpt-6-luna"
        case .gemini: return "gemini-3.8-flash"
        }
    }

    var defaultEffort: RefineEffort {
        switch self {
        case .anthropic: return .low
        case .openai: return .high
        case .gemini: return .low
        }
    }
}

struct RefineError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

// MARK: - Keychain

enum KeychainStore {
    private static let service = "org.voice2txt.app.apikey"

    private static func query(_ provider: CloudProvider) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: provider.rawValue]
    }

    static func load(_ provider: CloudProvider) -> String {
        var q = query(provider)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data, let key = String(data: data, encoding: .utf8) else { return "" }
        return key
    }

    /// 空字串代表刪除。回傳是否成功。
    @discardableResult
    static func save(_ key: String, for provider: CloudProvider) -> Bool {
        let trimmed = key.trimmingCharacters(in: .whitespacesAndNewlines)
        SecItemDelete(query(provider) as CFDictionary)
        if trimmed.isEmpty { return true }
        var q = query(provider)
        q[kSecValueData as String] = Data(trimmed.utf8)
        q[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        return SecItemAdd(q as CFDictionary, nil) == errSecSuccess
    }
}

// MARK: - Settings (UserDefaults)

struct ProviderSettings: Codable, Equatable {
    var enabled: Bool
    var model: String
    var effort: RefineEffort
}

@MainActor
final class RefineSettings: ObservableObject {
    private static let masterKey = "refine.enabled"
    private static let providerKeyPrefix = "refine.provider."
    private let defaults = UserDefaults.standard

    @Published var enabled: Bool {
        didSet { defaults.set(enabled, forKey: Self.masterKey) }
    }
    @Published private(set) var providers: [CloudProvider: ProviderSettings] = [:]

    init() {
        enabled = UserDefaults.standard.bool(forKey: Self.masterKey)
        for provider in CloudProvider.allCases {
            var value = ProviderSettings(enabled: false, model: provider.defaultModel, effort: provider.defaultEffort)
            if let data = defaults.data(forKey: Self.providerKeyPrefix + provider.rawValue),
               let saved = try? JSONDecoder().decode(ProviderSettings.self, from: data) {
                value = saved
            }
            providers[provider] = value
        }
    }

    func settings(for provider: CloudProvider) -> ProviderSettings {
        providers[provider] ?? ProviderSettings(enabled: false, model: provider.defaultModel, effort: provider.defaultEffort)
    }

    func update(_ provider: CloudProvider, _ change: (inout ProviderSettings) -> Void) {
        var value = settings(for: provider)
        change(&value)
        providers[provider] = value
        if let data = try? JSONEncoder().encode(value) {
            defaults.set(data, forKey: Self.providerKeyPrefix + provider.rawValue)
        }
    }

    /// 依固定順序建立「已啟用且有 key」的 refiner。
    func activeRefiners() -> [CloudRefiner] {
        CloudProvider.allCases.compactMap { provider in
            let value = settings(for: provider)
            let key = KeychainStore.load(provider)
            guard value.enabled, !key.isEmpty else { return nil }
            let model = value.model.trimmingCharacters(in: .whitespacesAndNewlines)
            return CloudRefiner(provider: provider, model: model.isEmpty ? provider.defaultModel : model,
                                apiKey: key, effort: value.effort)
        }
    }
}

// MARK: - Cloud request / parse (same shapes as desktop CloudTranslator)

struct CloudRefiner {
    let provider: CloudProvider
    let model: String
    let apiKey: String
    let effort: RefineEffort
    var timeout: TimeInterval = 30

    var name: String { "\(provider.title) \(model) (\(effort.rawValue))" }

    func request(text: String, task: String, vocabulary: String = "") throws -> URLRequest {
        let system = RefinePrompt.instructions(task: task, vocabulary: vocabulary)
        let url: URL
        var headers: [String: String] = ["Content-Type": "application/json"]
        let body: [String: Any]
        switch provider {
        case .anthropic:
            url = URL(string: "https://api.anthropic.com/v1/messages")!
            headers["x-api-key"] = apiKey
            headers["anthropic-version"] = "2026-10-21"
            body = ["model": model, "max_tokens": 1024, "system": system,
                    "messages": [["role": "user", "content": text]],
                    "output_config": ["effort": effort.rawValue]]
        case .openai:
            url = URL(string: "https://api.openai.com/v1/responses")!
            headers["Authorization"] = "Bearer " + apiKey
            body = ["model": model, "instructions": system, "input": text,
                    "reasoning": ["effort": effort.rawValue]]
        case .gemini:
            guard let encoded = model.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
                  let geminiURL = URL(string: "https://generativelanguage.googleapis.com/v1beta/models/\(encoded):generateContent") else {
                throw RefineError("Gemini 模型名稱無效。")
            }
            url = geminiURL
            headers["x-goog-api-key"] = apiKey
            body = ["systemInstruction": ["parts": [["text": system]]],
                    "contents": [["role": "user", "parts": [["text": text]]]],
                    "generationConfig": ["thinkingConfig": ["thinkingLevel": effort.rawValue]]]
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = timeout
        for (field, value) in headers { request.setValue(value, forHTTPHeaderField: field) }
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        return request
    }

    func parse(_ data: [String: Any]) throws -> String {
        var text = ""
        var complete = true
        switch provider {
        case .anthropic:
            let stop = data["stop_reason"] as? String
            if stop == "refusal" {
                let details = data["stop_details"] as? [String: Any]
                let category = (details?["category"] as? String) ?? "未知"
                throw RefineError("Anthropic 拒絕處理此內容（\(category)）。")
            }
            complete = (stop == nil || stop == "end_turn")
            for block in (data["content"] as? [[String: Any]]) ?? [] where (block["type"] as? String) == "text" {
                text += (block["text"] as? String) ?? ""
            }
        case .openai:
            let status = data["status"] as? String
            complete = (status == nil || status == "completed")
            for item in (data["output"] as? [[String: Any]]) ?? [] where (item["type"] as? String) == "message" {
                for part in (item["content"] as? [[String: Any]]) ?? [] where (part["type"] as? String) == "output_text" {
                    text += (part["text"] as? String) ?? ""
                }
            }
        case .gemini:
            let candidate = ((data["candidates"] as? [[String: Any]]) ?? []).first ?? [:]
            let finish = candidate["finishReason"] as? String
            complete = (finish == nil || finish == "STOP")
            let content = candidate["content"] as? [String: Any]
            for part in (content?["parts"] as? [[String: Any]]) ?? [] where (part["thought"] as? Bool) != true {
                text += (part["text"] as? String) ?? ""
            }
        }
        text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty || !complete { throw RefineError("整理未完成。") }
        return text
    }

    func refine(text: String, task: String, vocabulary: String = "") async throws -> String {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = timeout
        configuration.timeoutIntervalForResource = timeout
        let session = URLSession(configuration: configuration)
        defer { session.finishTasksAndInvalidate() }
        let (data, response) = try await session.data(for: try request(text: text, task: task, vocabulary: vocabulary))
        let object = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            let detail = ((object["error"] as? [String: Any])?["message"] as? String) ?? ""
            throw RefineError("HTTP \(http.statusCode) \(String(detail.prefix(160)))".trimmingCharacters(in: .whitespaces))
        }
        return try parse(object)
    }
}

// MARK: - Chain

/// 依序嘗試已啟用的雲端 LLM；失敗者暫停 cooldown 秒，避免每一段都等待逾時。
@MainActor
final class RefinerChain {
    private(set) var refiners: [CloudRefiner] = []
    private(set) var lastBackend = ""
    private(set) var errors: [String] = []
    let cooldown: TimeInterval
    private var paused: [String: TimeInterval] = [:]
    private let clock: () -> TimeInterval

    init(cooldown: TimeInterval = 60, clock: @escaping () -> TimeInterval = { ProcessInfo.processInfo.systemUptime }) {
        self.cooldown = cooldown
        self.clock = clock
    }

    var isEmpty: Bool { refiners.isEmpty }

    /// 設定變更後重新指定；暫停狀態以名稱（含模型與強度）保留。
    func configure(_ newRefiners: [CloudRefiner]) {
        refiners = newRefiners
    }

    func refine(text: String, task: String, vocabulary: String = "") async throws -> String {
        var failures: [String] = []
        for refiner in refiners {
            if let until = paused[refiner.name], until > clock() { continue }
            do {
                let output = try await refiner.refine(text: text, task: task, vocabulary: vocabulary)
                lastBackend = refiner.name
                errors = failures
                return output
            } catch {
                paused[refiner.name] = clock() + cooldown
                failures.append("\(refiner.name)：\(error.localizedDescription)")
            }
        }
        errors = failures
        throw RefineError(failures.isEmpty ? "所有 LLM 暫停中" : failures.joined(separator: "；"))
    }
}
