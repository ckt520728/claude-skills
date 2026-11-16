import SwiftUI
import UIKit

struct ContentView: View {
    @StateObject private var model = Transcriber()
    @State private var confirmDelete = false
    @Environment(\.horizontalSizeClass) private var horizontalSizeClass

    var body: some View {
        TabView {
            NavigationStack {
                VStack(alignment: .leading, spacing: 20) {
                    Text("自在說，本機寫。")
                        .font(.largeTitle.bold())
                    Text("繁體中文 / English · 無訂閱")
                        .foregroundStyle(.secondary)
                    Picker("語言模式", selection: $model.mode) {
                        ForEach(VoiceMode.allCases) { mode in Text(mode.rawValue).tag(mode) }
                    }
                    .pickerStyle(.menu)
                    .disabled(model.recording || model.processing || model.starting)
                    TextEditor(text: $model.text)
                        .font(.title3)
                        .padding(8)
                        .background(Color.secondary.opacity(0.06))
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                    Text(model.status).font(.footnote).foregroundStyle(.secondary)
                    HStack {
                        Button {
                            if model.recording { model.stop() }
                            else { Task { await model.start() } }
                        } label: {
                            Label(model.recording ? "停止" : "開始說話", systemImage: model.recording ? "stop.fill" : "mic.fill")
                                .padding(.vertical, 8)
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(!model.ready || model.loading || model.starting || (!model.recording && model.processing))
                        Spacer()
                        Button("複製") { UIPasteboard.general.string = model.text }
                        ShareLink(item: model.text) { Image(systemName: "square.and.arrow.up") }
                    }
                }
                // iPad（regular size class）限制主欄寬度並置中，避免全寬版面。
                .frame(maxWidth: horizontalSizeClass == .regular ? 760 : .infinity, alignment: .leading)
                .frame(maxWidth: .infinity)
                .padding()
                .navigationTitle("Voice2Txt")
                .navigationBarTitleDisplayMode(.inline)
            }
            .tabItem { Label("即時語音", systemImage: "waveform") }
            NavigationStack {
                List(model.history) { record in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(record.text).textSelection(.enabled)
                        if let source = record.source, !source.isEmpty {
                            Text("Whisper 原文：\(source)")
                                .font(.caption).foregroundStyle(.secondary).textSelection(.enabled)
                        }
                        Text("\(record.date.formatted()) · \(record.mode.rawValue)" + (record.backend.map { " · \($0)" } ?? ""))
                            .font(.caption).foregroundStyle(.secondary)
                        ShareLink(item: record.text) { Text("分享") }.font(.caption)
                    }
                }
                .navigationTitle("歷史紀錄")
                .toolbar { Button("全部刪除", role: .destructive) { confirmDelete = true } }
                .confirmationDialog("刪除所有本機歷史紀錄？", isPresented: $confirmDelete) {
                    Button("刪除所有紀錄", role: .destructive) { model.clearHistory() }
                }
            }
            .tabItem { Label("歷史", systemImage: "clock") }
            NavigationStack {
                Form {
                    Section("本機 Whisper") {
                        Picker("模型", selection: $model.modelName) {
                            Text("small：較佳品質").tag("small")
                            Text("base：較省資源").tag("base")
                        }.disabled(model.loading || model.recording || model.processing || model.starting)
                        Text("多語模型支援中文、英文與中翻英。首次下載需要網路與儲存空間；下載後使用手機運算。")
                        Button(model.loading ? "載入中…" : "下載 / 載入模型") {
                            Task { await model.loadModel() }
                        }
                        .disabled(model.loading || model.recording || model.processing || model.starting)
                        if model.loading { ProgressView() }
                    }
                    RefineSettingsSection(settings: model.refineSettings)
                    Section("使用方式") {
                        Text("保持 App 在前景錄音。切換背景、音訊中斷或變更裝置時會停止，並處理尾段。")
                        Text("可複製或分享至其他 App。此版本不提供系統鍵盤擴充。")
                        Text("停頓約半秒時送出一段；連續語音最長 8 秒。實際延遲與準確度取決於裝置、語音和背景噪音。")
                    }
                    Text(model.status).font(.footnote)
                }
                .navigationTitle("設定")
            }
            .tabItem { Label("設定", systemImage: "gearshape") }
        }
        .tint(.indigo)
    }
}

// LLM 整理（選用）設定：只送出 Whisper 轉錄文字，不送錄音。
struct RefineSettingsSection: View {
    @ObservedObject var settings: RefineSettings

    var body: some View {
        Section("LLM 整理（選用）") {
            Toggle("啟用 LLM 整理", isOn: $settings.enabled)
            Text("只送出 Whisper 轉錄文字，不送錄音；依用量計費，需自備 API key；無訂閱；關閉時完全離線。")
                .font(.footnote).foregroundStyle(.secondary)
            if settings.enabled {
                Text("依序嘗試 Anthropic → OpenAI → Gemini，全部失敗時中文／英文保留 Whisper 原文，中翻英改用 Whisper 內建翻譯。")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        if settings.enabled {
            ForEach(CloudProvider.allCases) { provider in
                ProviderSection(settings: settings, provider: provider)
            }
        }
    }
}

struct ProviderSection: View {
    @ObservedObject var settings: RefineSettings
    let provider: CloudProvider
    @State private var apiKey = ""
    @State private var keyNote = ""

    var body: some View {
        Section(provider.title) {
            Toggle("啟用 \(provider.title)", isOn: Binding(
                get: { settings.settings(for: provider).enabled },
                set: { value in settings.update(provider) { $0.enabled = value } }))
            TextField("模型", text: Binding(
                get: { settings.settings(for: provider).model },
                set: { value in settings.update(provider) { $0.model = value } }))
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            Picker("推理強度", selection: Binding(
                get: { settings.settings(for: provider).effort },
                set: { value in settings.update(provider) { $0.effort = value } })) {
                ForEach(RefineEffort.allCases) { effort in Text(effort.rawValue).tag(effort) }
            }
            SecureField("API key（按 Return 或「儲存」存入鑰匙圈）", text: $apiKey)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .onSubmit { saveKey() }
            Button("儲存") { saveKey() }
            if !keyNote.isEmpty { Text(keyNote).font(.footnote).foregroundStyle(.secondary) }
        }
        .onAppear { apiKey = KeychainStore.load(provider) }
    }

    private func saveKey() {
        keyNote = KeychainStore.save(apiKey, for: provider) ? "已儲存到鑰匙圈。" : "鑰匙圈儲存失敗。"
    }
}
