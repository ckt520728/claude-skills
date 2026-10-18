import AVFoundation
import Combine
import Foundation
import UIKit
import WhisperKit

enum VoiceMode: String, CaseIterable, Identifiable, Codable {
    case chinese = "繁體中文"
    case english = "English"
    case translate = "中文 → English"
    var id: String { rawValue }
}

struct Record: Identifiable, Codable {
    let id: UUID
    let date: Date
    let mode: VoiceMode
    let text: String
}

// 音訊 callback 與 UI 分離，停止時仍能取得最後一段音訊。
final class SampleBuffer {
    private let lock = NSLock()
    private var samples: [Float] = []
    private var overflow = false

    func append(_ values: [Float]) {
        lock.lock()
        defer { lock.unlock() }
        if samples.count + values.count > 16000 * 30 {
            overflow = true
            return
        }
        samples.append(contentsOf: values)
    }

    func take() -> ([Float], Bool) {
        lock.lock()
        defer { lock.unlock() }
        let result = (samples, overflow)
        samples = []
        overflow = false
        return result
    }
}

@MainActor
final class Transcriber: ObservableObject {
    @Published var mode: VoiceMode = .chinese
    @Published var modelName = "small"
    @Published var text = ""
    @Published var status = "首次使用請下載模型，完成後可離線轉錄。"
    @Published var recording = false
    @Published private(set) var starting = false
    @Published var loading = false
    @Published var processing = false
    @Published var ready = false
    @Published var history: [Record] = []
    private var pipe: WhisperKit?
    private var engine: AVAudioEngine?
    private let buffer = SampleBuffer()
    private var chunker = AudioChunker()
    private var timer: Timer?
    private var pending: [[Float]] = []
    private var sessionMode: VoiceMode = .chinese
    private var sessionError: String?
    private var worker: Task<Void, Never>?
    private var notificationTokens: [NSObjectProtocol] = []
    private let historyURL = URL.documentsDirectory.appending(path: "history.json")

    init() {
        do {
            if FileManager.default.fileExists(atPath: historyURL.path) {
                history = try JSONDecoder().decode([Record].self, from: Data(contentsOf: historyURL))
            }
        } catch { status = "歷史紀錄讀取失敗：\(error.localizedDescription)" }
        for name in [AVAudioSession.interruptionNotification, UIApplication.didEnterBackgroundNotification,
                     AVAudioSession.routeChangeNotification] {
            notificationTokens.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.recording else { return }
                    self.stop()
                    self.status = "錄音因背景切換、音訊中斷或裝置變更而停止。"
                }
            })
        }
    }

    func loadModel() async {
        guard !loading, !recording, !processing, !starting else { return }
        loading = true
        status = "下載 / 載入 \(modelName) 多語模型中…請保持 App 開啟。"
        defer { loading = false }
        do {
            pipe = try await WhisperKit(WhisperKitConfig(model: modelName, verbose: false))
            ready = true
            status = "模型就緒，可開始說話。後續轉錄與翻譯均在手機執行。"
        } catch { status = "模型載入失敗：\(error.localizedDescription)" }
    }

    func start() async {
        guard ready, !recording, !processing, !starting, !loading else { return }
        starting = true
        defer { starting = false }
        let allowed = await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { continuation.resume(returning: $0) }
        }
        guard allowed else {
            status = "請到 iPhone 設定允許 Voice2Txt 使用麥克風。"
            return
        }
        guard UIApplication.shared.applicationState == .active else {
            status = "請回到 App 前景後再開始錄音。"
            return
        }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .measurement)
            try session.setActive(true)
            let engine = AVAudioEngine()
            let input = engine.inputNode
            let source = input.outputFormat(forBus: 0)
            guard let output = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16000, channels: 1, interleaved: false),
                  let converter = AVAudioConverter(from: source, to: output) else {
                throw NSError(domain: "Voice2Txt", code: 1, userInfo: [NSLocalizedDescriptionKey: "無法轉換麥克風音訊格式"])
            }
            _ = buffer.take()
            chunker = AudioChunker()
            let buffer = self.buffer
            input.installTap(onBus: 0, bufferSize: 4096, format: source) { data, _ in
                let capacity = AVAudioFrameCount(Double(data.frameLength) * 16000 / source.sampleRate) + 32
                guard let converted = AVAudioPCMBuffer(pcmFormat: output, frameCapacity: capacity) else { return }
                var supplied = false
                var conversionError: NSError?
                converter.convert(to: converted, error: &conversionError) { _, state in
                    if supplied { state.pointee = .noDataNow; return nil }
                    supplied = true
                    state.pointee = .haveData
                    return data
                }
                guard conversionError == nil, let channel = converted.floatChannelData?[0] else { return }
                buffer.append(Array(UnsafeBufferPointer(start: channel, count: Int(converted.frameLength))))
            }
            self.engine = engine
            sessionMode = mode
            sessionError = nil
            try engine.start()
            recording = true
            status = "錄音中，停頓時送出，連續語音最長 8 秒一段…"
            timer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { [weak self] _ in
                Task { @MainActor in self?.collect() }
            }
        } catch {
            engine?.inputNode.removeTap(onBus: 0)
            engine?.stop()
            engine = nil
            try? AVAudioSession.sharedInstance().setActive(false)
            status = "無法錄音：\(error.localizedDescription)"
        }
    }

    func stop() {
        guard recording else { return }
        recording = false
        timer?.invalidate()
        timer = nil
        engine?.stop()
        engine?.inputNode.removeTap(onBus: 0)
        engine = nil
        try? AVAudioSession.sharedInstance().setActive(false)
        collect(final: true)
        status = processing ? "處理剩餘音訊中…" : "已停止錄音。"
    }

    private func collect(final: Bool = false) {
        let (samples, overflow) = buffer.take()
        pending.append(contentsOf: chunker.feed(samples))
        if final { pending.append(contentsOf: chunker.flush()) }
        if overflow || pending.count > 6 {
            if recording { stop() }
            status = "處理速度不足，已停止錄音並處理保留音訊。"
            sessionError = status
        }
        guard worker == nil, !pending.isEmpty else { return }
        processing = true
        worker = Task {
            while !pending.isEmpty {
                let audio = pending.removeFirst()
                guard audio.count >= 3200 else { continue }
                let rms = sqrt(audio.reduce(Float(0)) { $0 + $1 * $1 } / Float(audio.count))
                guard rms >= 0.002, let pipe else { continue }
                do {
                    let options = DecodingOptions(task: sessionMode == .translate ? .translate : .transcribe,
                                                  language: sessionMode == .english ? "en" : "zh",
                                                  skipSpecialTokens: true, withoutTimestamps: true,
                                                  concurrentWorkerCount: 1)
                    let results: [TranscriptionResult] = try await pipe.transcribe(audioArray: audio, decodeOptions: options)
                    var result = results.map(\.text).joined(separator: " ").trimmingCharacters(in: .whitespacesAndNewlines)
                    if sessionMode == .chinese {
                        result = result.applyingTransform(StringTransform("Hans-Hant"), reverse: false) ?? result
                    }
                    if !result.isEmpty {
                        text += result + "\n"
                        history.insert(Record(id: UUID(), date: Date(), mode: sessionMode, text: result), at: 0)
                        saveHistory()
                    }
                } catch {
                    if recording { stop() }
                    sessionError = "辨識失敗：\(error.localizedDescription)"
                    status = sessionError ?? "辨識失敗"
                }
            }
            processing = false
            worker = nil
            if !recording { status = sessionError ?? "已完成，紀錄保存在此 iPhone。" }
        }
    }

    func clearHistory() {
        history = []
        saveHistory()
    }

    private func saveHistory() {
        do { try JSONEncoder().encode(history).write(to: historyURL, options: [.atomic, .completeFileProtection]) }
        catch {
            sessionError = "歷史紀錄儲存失敗：\(error.localizedDescription)"
            status = sessionError ?? "儲存失敗"
        }
    }
}
