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

    struct Voice: Equatable {
        var name: String, method: String, machine: String
        var shown: String { name.replacingOccurrences(of: "_", with: " ") }
    }

    /// A control in play, on the performance page.
    struct Held: Equatable {
        var label = "-", row = 0
        var value = 0.0
        var waiting = false
        var inPlay: Bool { label != "-" }
    }

    struct Strip: Equatable {
        var knob = Held(), fader = Held(), top = Held(), bottom = Held()
    }

    struct Row: Identifiable, Equatable {
        let id: Int
        var name: String
        var words = ""
    }

    var linked = false

    // The page and the voices.
    var pageName = "perform"
    var pageKind = "perform"
    var pageRow = 0
    var voices = [Voice?](repeating: nil, count: 8)

    // The controls in play.
    var armed = 0
    var strips = [Strip](repeating: Strip(), count: 8)

    // The melody grid.
    var loop = 16
    var tonic = 0
    var scale: Set<Int> = [0, 2, 3, 5, 7, 8, 10]
    var notes = [Int](repeating: 0, count: 32)
    var codes = [Int](repeating: 0, count: 32)
    var every = 4
    var melodyStep = -1
    // The rhythm grid, and the chords' controls.
    var total = 32
    var last = 16
    var span = 2
    var gridStep = -1
    var chords = (1...8).map { Chord(id: $0) }
    var sounding = 0
    var onChords = false
    var onMelody = false
    var chordCount = 4
    var chordLock = 0
    var smooth = 0
    var tension = 0
    var home = 0
    var key = 1
    var mode = 6
    var style = 1
    var bass = 0
    var melodyValues: [String: Int] = [:]

    // The drums.
    var drumTrack = 1
    var playing = false
    var drumRaw = [Double](repeating: 0, count: 148)
    var tempo = 120.0

    // The songs and sections page.
    var sets: [String] = []
    var setChosen = 1
    var setEntries: [Row] = []
    var entrySelected = 0
    var allSongs: [Row] = []
    var songSelected = 0
    var songName = "-"
    var unsaved = false
    var sections: [Row] = []
    var sectionPlaying = 0
    var sectionQueued = 0
    var sectionSelected = 0
    var sectionLengths: [Int] = []
    var keepTweaks = 0
    // The keys.
    var velocityOn = true

    // A machine's parameters, and a voice's patches.
    var params: [Param] = []
    var patches: [String] = []
    var patch = "-"
    var factory: [String] = []

    struct Param: Identifiable, Equatable {
        var id: String { name }
        var name: String, value: Double
    }

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

    /// Coming back to the app: new sockets, and no finger is still down.
    func cameBack() {
        holding = false
        link.restart()
    }

    func send(_ words: Any...) {
        link.send(words.map {
            if let s = $0 as? String { return .text(s) }
            if let i = $0 as? Int { return .number(Float(i)) }
            return .number(Float(($0 as? Double) ?? 0))
        })
    }

    /// A voice's control moved: through u_perform, so it can be taken into play.
    func control(_ dest: String, _ arg: String, _ value: Double) {
        send("perform", "ctl", pageRow, dest, arg, value)
    }

    func drum(_ i: Int) -> Double { i < drumRaw.count ? drumRaw[i] : 0 }

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
            chordCount = a[0].number
            chordLock = a[1].number
            smooth = a[2].number
            tension = a[3].number
            home = a[4].number
            span = a[5].number
            sounding = a[6].number
            onChords = a[7].number == 1
            onMelody = a[8].number == 1
            key = a[9].number
            mode = a[10].number
            total = max(1, a[11].number)
            last = max(1, a[12].number)
            for (i, name) in ["lock", "fit", "leap", "notes", "length", "echo", "loop", "range"].enumerated() {
                melodyValues[name] = a[47 + i].number
            }
            style = a[55].number
            bass = a[56].number
            melodyValues["arrive"] = a[57].number
            melodyValues["octave"] = a[58].number
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
            guard a.count >= 37 else { return }
            playing = a[0].number == 1
            drumTrack = a[2].number
            every = max(1, a[36].number)
            drumRaw = a.map(\.value)
        case "/cutit/tempo":
            if let v = a.first { tempo = v.value }
        case "/cutit/velocity":
            velocityOn = a.first?.text == "on"
        case "/cutit/voices":
            guard a.count >= 27 else { return }
            pageName = a[0].text
            pageKind = a[1].text
            pageRow = a[2].number
            voices = (0..<8).map { r in
                let b = 3 + r * 3
                return a[b].text == "-" ? nil : Voice(name: a[b].text, method: a[b + 1].text, machine: a[b + 2].text)
            }
        case "/cutit/perform":
            guard a.count >= 113 else { return }
            armed = a[0].number
            var at = 1
            func held() -> Held {
                defer { at += 4 }
                return Held(label: a[at].text, row: a[at + 1].number, value: a[at + 2].value, waiting: a[at + 3].number == 1)
            }
            func button() -> Held {
                defer { at += 3 }
                return Held(label: a[at].text, row: a[at + 1].number, value: a[at + 2].value)
            }
            strips = (0..<8).map { _ in
                let k = held(), f = held(), t = button(), b = button()
                return Strip(knob: k, fader: f, top: t, bottom: b)
            }
        case "/cutit/lists":
            lists(a)
        case "/cutit/sound":
            sound(a)
        default: break
        }
    }

    /// u_song's whole lists: the setlists, the one chosen's entries, every song, and the song loaded's sections.
    private func lists(_ a: [OSCValue]) {
        var at = 0
        func next() -> OSCValue { defer { at += 1 }; return at < a.count ? a[at] : .number(0) }
        setChosen = next().number
        let nsets = next().number
        sets = (0..<max(0, nsets)).map { _ in next().text }
        entrySelected = next().number
        let nent = next().number
        setEntries = (0..<max(0, nent)).map { i in
            Row(id: i + 1, name: next().text, words: next().text)
        }
        songSelected = next().number
        let nsongs = next().number
        allSongs = (0..<max(0, nsongs)).map { i in
            Row(id: i + 1, name: next().text, words: next().text)
        }
        songName = next().text
        unsaved = next().number == 1
        sectionPlaying = next().number
        sectionQueued = next().number
        sectionSelected = next().number
        keepTweaks = next().number
        let nsec = next().number
        var lengths: [Int] = []
        sections = (0..<max(0, nsec)).map { i in
            let name = next().text
            let len = next().number
            lengths.append(len)
            return Row(id: i + 1, name: name, words: len == 0 ? "loop" : String(len))
        }
        sectionLengths = lengths
    }

    /// The voice on show's patch and its machine's parameters.
    private func sound(_ a: [OSCValue]) {
        var at = 0
        func next() -> OSCValue { defer { at += 1 }; return at < a.count ? a[at] : .number(0) }
        patch = next().text
        patches = (0..<max(0, next().number)).map { _ in next().text }
        factory = (0..<max(0, next().number)).map { _ in next().text }
        let n = next().number
        params = (0..<max(0, n)).map { _ in
            let name = next().text
            return Param(name: name, value: next().value)
        }
    }

    /// While a finger holds something, what the Organelle says doesn't move it.
    var holding = false
}
