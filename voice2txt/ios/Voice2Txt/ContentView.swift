import SwiftUI
import UIKit

struct ContentView: View {
    @StateObject private var model = Transcriber()
    @State private var confirmDelete = false

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
                .padding()
                .navigationTitle("Voice2Txt")
                .navigationBarTitleDisplayMode(.inline)
            }
            .tabItem { Label("即時語音", systemImage: "waveform") }
            NavigationStack {
                List(model.history) { record in
                    VStack(alignment: .leading, spacing: 8) {
                        Text(record.text).textSelection(.enabled)
                        Text("\(record.date.formatted()) · \(record.mode.rawValue)")
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
