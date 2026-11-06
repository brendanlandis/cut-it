import Foundation
import Observation

/// What the phone knows of Cut It: whatever the Organelle last said. Everything here is drawn, none of it decided.
@MainActor
@Observable
final class Cut {
    struct Chord: Identifiable {
        let id: Int          // its slot, 1 to 8
        var name = "-", spell = "-", roman = "-"
        var start = -1
        var pinned = false
    }

    var linked = false
    // The melody grid.
    var loop = 16
    var tonic = 0
    var scale: Set<Int> = [0, 2, 3, 5, 7, 8, 10]
    var notes = [Int](repeating: 0, count: 32)
    var codes = [Int](repeating: 0, count: 32)
    var every = 4
    var melodyStep = -1
    // The rhythm grid.
    var total = 32
    var last = 16
    var span = 2
    var gridStep = -1
    var chords = (1...8).map { Chord(id: $0) }
    var sounding = 0
    var onChords = false
    var onMelody = false

    private let link = Link()
    private var lastHeard = Date.distantPast

    func start() {
        link.onMessage = { [weak self] path, args in
            Task { @MainActor in self?.heard(path, args) }
        }
        // `-host <address>` on launch points it elsewhere, as the tests do.
        link.start(host: UserDefaults.standard.string(forKey: "host") ?? Link.host)
        // Linked while the heartbeat comes; nothing to connect, so a dropped network comes back by itself.
        Task { @MainActor [weak self] in
            while let self {
                self.linked = Date().timeIntervalSince(self.lastHeard) < 1.5
                try? await Task.sleep(for: .milliseconds(250))
            }
        }
    }

    func send(_ words: Any...) {
        link.send(words.map {
            if let s = $0 as? String { return .text(s) }
            if let i = $0 as? Int { return .number(Float(i)) }
            return .number(Float(($0 as? Double) ?? 0))
        })
    }

    private func heard(_ path: String, _ a: [OSCValue]) {
        switch path {
        case "/cutit/hb": lastHeard = Date()
        case "/cutit/here":
            guard a.count >= 2 else { return }
            gridStep = a[0].number
            melodyStep = a[1].number
        case "/cutit/notes":
            guard a.count >= 73, !holding else { return }
            loop = max(1, a[0].number)
            tonic = a[1].number
            scale = Set((2...8).map { a[$0].number % 12 })
            notes = (0..<32).map { a[9 + $0].number }
            codes = (0..<32).map { a[41 + $0].number }
        case "/cutit/melody":
            guard a.count >= 67 else { return }
            span = a[5].number
            sounding = a[6].number
            onChords = a[7].number == 1
            onMelody = a[8].number == 1
            total = max(1, a[11].number)
            last = max(1, a[12].number)
            if !holding {
                for i in 0..<8 {
                    let b = 13 + i * 4
                    chords[i].name = a[b].text
                    chords[i].spell = a[b + 1].text
                    chords[i].roman = a[b + 2].text
                    chords[i].start = a[b + 3].number
                    chords[i].pinned = a[59 + i].number == 1
                }
            }
        case "/cutit/drums":
            if a.count >= 37 { every = max(1, a[36].number) }
        default: break
        }
    }

    /// While a finger holds something, what the Organelle says doesn't move it.
    var holding = false
}
