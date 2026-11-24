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
    /// Test mode, the Organelle's own, from the heartbeat: the line check stands in for the page while it's on.
    var testMode = false
    /// The synth the nanoKEY plays, c_synth's choice.
    var synth = "fm"
    /// The line check: the step on show, each step's verdict by its number, and how many verdicts the Organelle has
    /// answered, which flashes the button that gave the last.
    let lineCheck = LineCheck.bundled()
    var checkAt = 0
    var verdicts: [Int: String] = [:]
    var lastVerdict = ""
    var verdictsHeard = 0

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
    // Presses not yet heard. A start somewhere in the numbers a float holds exactly, so the app starting again
    // doesn't repeat one still remembered.
    private var seq = Int.random(in: 1...8_000_000)
    private var waiting: [Int: (message: [OSCValue], tries: Int)] = [:]
    private static let maxTries = 8

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
        Task { @MainActor [weak self] in
            while let self {
                self.resend()
                try? await Task.sleep(for: .milliseconds(120))
            }
        }
    }

    /// Coming back to the app: new sockets, and no finger is still down.
    func cameBack() {
        holding = false
        waiting = [:]
        link.restart()
    }

    private func values(_ words: [Any]) -> [OSCValue] {
        words.map {
            if let s = $0 as? String { return .text(s) }
            if let i = $0 as? Int { return .number(Float(i)) }
            return .number(Float(($0 as? Double) ?? 0))
        }
    }

    /// Something continuous, a knob or a drag: the next value will follow, so one lost doesn't matter.
    func send(_ words: Any...) {
        link.send(values(words))
    }

    /// A one-time press: sent until the Organelle says it heard. UDP can drop it, and a press lost on stage is a
    /// press that didn't happen. u_once lets each through only once, so one whose answer was lost isn't doubled.
    func press(_ words: Any...) {
        seq = seq >= 16_000_000 ? 1 : seq + 1
        let message: [OSCValue] = [.text("once"), .number(Float(seq))] + values(words)
        waiting[seq] = (message, 0)
        link.send(message)
    }

    private func resend() {
        for (id, entry) in waiting {
            if entry.tries >= Self.maxTries {
                waiting[id] = nil
            } else {
                waiting[id] = (entry.message, entry.tries + 1)
                link.send(entry.message)
            }
        }
    }

    /// A voice's control moved: through u_perform, so it can be taken into play.
    func control(_ dest: String, _ arg: String, _ value: Double) {
        send("perform", "ctl", pageRow, dest, arg, value)
    }

    /// A number of the drums' state, at a place StateAt.swift names; and a track's, 1 the first, of a field
    /// that holds one a track.
    func drum(_ at: Int) -> Double { at < drumRaw.count ? drumRaw[at] : 0 }
    func drum(_ at: Int, track: Int) -> Double {
        let i = at + track - 1
        return i < drumRaw.count ? drumRaw[i] : 0
    }

    private func heard(_ path: String, _ a: [OSCValue]) {
        switch path {
        case "/cutit/hb":
            lastHeard = Date()
            if a.count >= 2 { testMode = a[1].number == 1 }
        case "/cutit/synth":
            if let v = a.first?.text, !v.isEmpty { synth = v }
        case "/cutit/ack":
            if a.first?.text == "result" { verdictsHeard += 1 }
        case "/cutit/once":
            if let id = a.first?.number { waiting[id] = nil }
        case "/cutit/here":
            guard a.count >= 2 else { return }
            gridStep = a[0].number
            melodyStep = a[1].number
        case "/cutit/notes":
            guard a.count >= NotesAt.count, !holding else { return }
            loop = max(1, a[NotesAt.loop].number)
            tonic = a[NotesAt.tonic].number
            scale = Set((0..<7).map { a[NotesAt.scale + $0].number % 12 })
            notes = (0..<32).map { a[NotesAt.note + $0].number }
            codes = (0..<32).map { a[NotesAt.code + $0].number }
        case "/cutit/melody":
            guard a.count >= MelodyAt.count else { return }
            chordCount = a[MelodyAt.chords].number
            chordLock = a[MelodyAt.chordLock].number
            smooth = a[MelodyAt.smooth].number
            tension = a[MelodyAt.tension].number
            home = a[MelodyAt.home].number
            span = a[MelodyAt.span].number
            sounding = a[MelodyAt.sounding].number
            onChords = a[MelodyAt.onH].number == 1
            onMelody = a[MelodyAt.onM].number == 1
            key = a[MelodyAt.key].number
            mode = a[MelodyAt.mode].number
            total = max(1, a[MelodyAt.total].number)
            last = max(1, a[MelodyAt.last].number)
            melodyValues["lock"] = a[MelodyAt.lock].number
            melodyValues["fit"] = a[MelodyAt.fit].number
            melodyValues["leap"] = a[MelodyAt.leap].number
            melodyValues["notes"] = a[MelodyAt.notes].number
            melodyValues["length"] = a[MelodyAt.length].number
            melodyValues["echo"] = a[MelodyAt.echo].number
            melodyValues["loop"] = a[MelodyAt.loop].number
            melodyValues["range"] = a[MelodyAt.range].number
            style = a[MelodyAt.style].number
            bass = a[MelodyAt.bass].number
            melodyValues["arrive"] = a[MelodyAt.arrive].number
            melodyValues["octave"] = a[MelodyAt.octave].number
            if !holding {
                for i in 0..<8 {
                    let b = MelodyAt.slot + i * MelodyAt.Slot.width
                    chords[i].name = a[b + MelodyAt.Slot.name].text
                    chords[i].spell = a[b + MelodyAt.Slot.spell].text
                    chords[i].roman = a[b + MelodyAt.Slot.roman].text
                    chords[i].start = a[b + MelodyAt.Slot.start].number
                    chords[i].pinned = a[MelodyAt.pin + i].number == 1
                }
            }
        case "/cutit/drums":
            guard a.count > DrumsAt.num else { return }
            playing = a[DrumsAt.playing].number == 1
            drumTrack = a[DrumsAt.track].number
            every = max(1, a[DrumsAt.num].number)
            drumRaw = a.map(\.value)
        case "/cutit/tempo":
            if let v = a.first { tempo = v.value }
        case "/cutit/velocity":
            velocityOn = a.first?.text == "on"
        case "/cutit/voices":
            guard a.count >= VoicesAt.count else { return }
            pageName = a[VoicesAt.page].text
            pageKind = a[VoicesAt.kind].text
            pageRow = a[VoicesAt.row].number
            voices = (0..<8).map { r in
                let b = VoicesAt.voice + r * VoicesAt.Voice.width
                let name = a[b + VoicesAt.Voice.name].text
                return name == "-" ? nil : Voice(name: name, method: a[b + VoicesAt.Voice.method].text,
                                                 machine: a[b + VoicesAt.Voice.machine].text)
            }
        case "/cutit/perform":
            guard a.count >= PerformAt.count else { return }
            armed = a[PerformAt.armed].number
            strips = (0..<8).map { g in
                let b = PerformAt.group + g * PerformAt.Group.width
                return Strip(
                    knob: Held(label: a[b + PerformAt.Group.knobLabel].text, row: a[b + PerformAt.Group.knobRow].number,
                               value: a[b + PerformAt.Group.knobValue].value,
                               waiting: a[b + PerformAt.Group.knobHeld].number == 1),
                    fader: Held(label: a[b + PerformAt.Group.faderLabel].text, row: a[b + PerformAt.Group.faderRow].number,
                                value: a[b + PerformAt.Group.faderValue].value,
                                waiting: a[b + PerformAt.Group.faderHeld].number == 1),
                    top: Held(label: a[b + PerformAt.Group.topLabel].text, row: a[b + PerformAt.Group.topRow].number,
                              value: a[b + PerformAt.Group.topOn].value),
                    bottom: Held(label: a[b + PerformAt.Group.bottomLabel].text, row: a[b + PerformAt.Group.bottomRow].number,
                                 value: a[b + PerformAt.Group.bottomOn].value))
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

    /// A verdict on the line check's step on show: logged on the Organelle as `info phone linecheck-<n>-<verdict>`,
    /// then on to the next step.
    func verdict(_ v: String) {
        guard checkAt < lineCheck.steps.count else { return }
        let n = lineCheck.steps[checkAt].id
        press("result", "\(lineCheck.name)-\(n)-\(v)")
        verdicts[n] = v
        lastVerdict = v
        checkAt = min(checkAt + 1, lineCheck.steps.count - 1)
    }
}
