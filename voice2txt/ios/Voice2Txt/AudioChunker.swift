import Foundation

/// 以 20 ms 音量窗找停頓，最短 1 秒、最長 8 秒；所有樣本僅輸出一次。
final class AudioChunker {
    private var pending: [Float] = []
    private let maximum = 16000 * 8
    private let minimum = 16000
    private let silence = 8000
    private let frameSize = 320

    func feed(_ samples: [Float]) -> [[Float]] {
        pending.append(contentsOf: samples)
        var chunks: [[Float]] = []
        while !pending.isEmpty {
            var cut: Int?
            if pending.count >= minimum {
                var quietCount = 0
                let frames = min(pending.count, maximum) / frameSize
                for frame in 0..<frames {
                    let start = frame * frameSize
                    let end = start + frameSize
                    let energy = pending[start..<end].reduce(Float(0)) { $0 + $1 * $1 } / Float(frameSize)
                    quietCount = energy < 0.006 * 0.006 ? quietCount + frameSize : 0
                    if quietCount >= silence && end >= minimum {
                        cut = end
                        break
                    }
                }
            }
            if cut == nil && pending.count >= maximum { cut = maximum }
            guard let cut else { break }
            chunks.append(Array(pending.prefix(cut)))
            pending.removeFirst(cut)
        }
        return chunks
    }

    func flush() -> [[Float]] {
        let result = pending.isEmpty ? [] : [pending]
        pending = []
        return result
    }
}
