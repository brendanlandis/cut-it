import SwiftUI

// MARK: - performance

/// The performance page: what each of the nanoKONTROL's first eight groups moves, for this section. Its
/// knob, its fader and its two buttons, named. Tap a name to take it out of play.
struct PerformView: View {
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 4) {
            HStack(spacing: 8) {
                Text(cut.songName.replacingOccurrences(of: "_", with: " ")).font(.system(size: 15, weight: .medium))
                if cut.sections.indices.contains(cut.sectionPlaying - 1) {
                    Text(cut.sections[cut.sectionPlaying - 1].name).font(.system(size: 15)).foregroundStyle(Theme.dim)
                }
                Spacer()
                Text(String(format: "%g", cut.tempo)).font(.system(size: 15, design: .monospaced))
                Pad(title: armText, on: cut.armed > 0, width: 150, color: Theme.red) { cut.press("perform", "arm") }
                    .frame(height: 32).scaleEffect(y: 0.8)
            }
            .frame(height: 34)
            HStack(spacing: 3) {
                ForEach(1...8, id: \.self) { lane in
                    StripView(lane: lane, strip: cut.strips[lane - 1])
                }
            }
        }
    }

    private var armText: String {
        switch cut.armed {
        case 1: return "move a control"
        case 2: return "move the nano"
        default: return "take into play"
        }
    }
}

struct StripView: View {
    let lane: Int
    let strip: Cut.Strip
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 3) {
            name(strip.knob, "knob")
            ZStack {
                Circle().trim(from: 0, to: 0.8).rotation(.degrees(126))
                    .stroke(Color.white.opacity(0.14), style: .init(lineWidth: 4, lineCap: .round))
                if strip.knob.inPlay {
                    Circle().trim(from: 0, to: 0.8 * max(0.001, strip.knob.value)).rotation(.degrees(126))
                        .stroke(Theme.blue.opacity(strip.knob.waiting ? 0.45 : 1), style: .init(lineWidth: 4, lineCap: .round))
                }
            }
            .frame(width: 34, height: 34)
            name(strip.fader, "slider")
            GeometryReader { geo in
                ZStack(alignment: .bottom) {
                    RoundedRectangle(cornerRadius: 4).fill(Color.white.opacity(0.07))
                    if strip.fader.inPlay {
                        RoundedRectangle(cornerRadius: 4)
                            .fill(LinearGradient(colors: [Theme.green, Theme.green, .yellow, .orange, Theme.red],
                                                 startPoint: .bottom, endPoint: .top))
                            .frame(height: geo.size.height)
                            .mask(alignment: .bottom) {
                                Rectangle().frame(height: geo.size.height * strip.fader.value)
                            }
                            .opacity(strip.fader.waiting ? 0.45 : 1)
                    }
                }
            }
            button(strip.top, "btn-a")
            button(strip.bottom, "btn-b")
        }
        .padding(3)
        .background(Color.white.opacity(0.03), in: .rect(cornerRadius: 6))
    }

    private func name(_ h: Cut.Held, _ what: String) -> some View {
        Button { if h.inPlay { cut.press("perform", "remove", "\(what)-\(lane)") } } label: {
            VStack(spacing: 0) {
                Text(voiceName(h)).font(.system(size: 10)).foregroundStyle(Theme.voice(h.row))
                Text(h.inPlay ? h.label : "").font(.system(size: 11))
            }
            .lineLimit(1).minimumScaleFactor(0.6).frame(maxWidth: .infinity, minHeight: 26)
        }
        .buttonStyle(.plain)
    }

    private func voiceName(_ h: Cut.Held) -> String {
        guard h.inPlay else { return "" }
        guard (1...8).contains(h.row), let v = cut.voices[h.row - 1] else { return " " }
        return v.shown
    }

    private func button(_ h: Cut.Held, _ what: String) -> some View {
        Button {
            if h.inPlay {
                Tick.down()
                cut.press("perform", "press", "\(what)-\(lane)")
            }
        } label: {
            Text(h.inPlay ? h.label : "").font(.system(size: 11)).lineLimit(1).minimumScaleFactor(0.6)
                .frame(maxWidth: .infinity, minHeight: 28)
                .foregroundStyle(h.inPlay && h.value >= 0.5 ? Color.black : Color.white)
                .background(!h.inPlay ? Color.white.opacity(0.05)
                            : Theme.voice(h.row).opacity(h.value >= 0.5 ? 1 : 0.25), in: .rect(cornerRadius: 4))
        }
        .buttonStyle(.plain)
        .simultaneousGesture(LongPressGesture(minimumDuration: 0.6).onEnded { _ in
            if h.inPlay { cut.press("perform", "remove", "\(what)-\(lane)") }
        })
    }
}

// MARK: - harmony

struct HarmonyView: View {
    enum Tab: String, CaseIterable { case chords, rhythm }
    @State private var tab = Tab.chords
    @Environment(Cut.self) private var cut
    private static let keys = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    private static let modes = ["ionian", "dorian", "phrygian", "lydian", "mixolydian", "aeolian", "locrian",
                                "harm minor", "mel minor"]

    var body: some View {
        VStack(spacing: 6) {
            Tabs(tab: $tab)
            if tab == .rhythm {
                RhythmView()
            } else {
                chordsPage
            }
        }
    }

    private var chordsPage: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Pad(title: "on", on: cut.onChords, width: 60, color: Theme.voice(cut.pageRow)) { cut.press("melody", "on-h", 1) }
                Pad(title: "roll", width: 60) { cut.press("melody", "roll-chords", 1) }
                Choice(label: "key", value: Self.keys[max(0, min(11, cut.key - 1))], options: Self.keys, width: 66) { i, _ in
                    cut.press("melody", "set", "key", i + 1)
                }
                Choice(label: "mode", value: Self.modes[max(0, min(8, cut.mode - 1))], options: Self.modes, width: 112) { i, _ in
                    cut.press("melody", "set", "mode", i + 1)
                }
                Pad(title: cut.style == 2 ? "functional" : "modal", on: cut.style == 2, width: 84) { cut.press("melody", "style", 1) }
                Pad(title: "bass", on: cut.bass == 1, width: 54) { cut.press("melody", "bass", 1) }
                Spacer(minLength: 0)
            }
            HStack(spacing: 4) {
                ForEach(order, id: \.self) { slot in ChordBox(chord: cut.chords[slot - 1]) }
            }
            .frame(maxHeight: .infinity)
            HStack {
                knob("lock", "chord-lock", Double(cut.chordLock) / 100)
                knob("smooth", "smooth", Double(cut.smooth) / 100)
                knob("tension", "tension", Double(cut.tension) / 100)
                knob("home", "home", Double(cut.home) / 100)
                knob("chords", "chords", Double(cut.chordCount - 1) / 7, text: String(cut.chordCount))
            }
        }
    }

    private var order: [Int] {
        (1...max(1, min(8, cut.chordCount))).sorted { cut.chords[$0 - 1].start < cut.chords[$1 - 1].start }
    }

    private func knob(_ label: String, _ arg: String, _ v: Double, text: String? = nil) -> some View {
        Knob(label: label, value: v, text: text, color: Theme.voice(cut.pageRow)) { cut.control("melody", arg, $0) }
            .frame(maxWidth: .infinity)
    }
}

/// A chord's box: its name, its spelling and its role. Held, it sounds, and the nanoKEY writes it.
struct ChordBox: View {
    let chord: Cut.Chord
    @Environment(Cut.self) private var cut
    @GestureState private var down = false

    var body: some View {
        let lit = cut.sounding == chord.id
        VStack(spacing: 2) {
            Text(chord.name).font(.system(size: 16, weight: .semibold)).lineLimit(1).minimumScaleFactor(0.6)
            Text(chord.spell).font(.system(size: 11)).lineLimit(1).minimumScaleFactor(0.6)
            Text(chord.roman).font(.system(size: 13)).lineLimit(1).minimumScaleFactor(0.6)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .foregroundStyle(lit ? Color.black : Color.white)
        .background(Theme.voice(cut.pageRow).opacity(lit ? 1 : 0.22), in: .rect(cornerRadius: 6))
        .overlay {
            if chord.pinned { RoundedRectangle(cornerRadius: 6).stroke(.white, lineWidth: 1.5) }
        }
        .gesture(DragGesture(minimumDistance: 0)
            .updating($down) { _, on, _ in on = true })
        .onChange(of: down) { _, on in
            if on { Tick.down() }
            cut.press("melody", "audition", chord.id, on ? 1 : 0)
        }
    }
}

// MARK: - melody

struct MelodyView: View {
    enum Tab: String, CaseIterable { case notes, shape }
    @State private var tab = Tab.notes
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 6) {
            Tabs(tab: $tab)
            if tab == .notes {
                NotesView()
            } else {
                shape
            }
        }
    }

    private var shape: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Pad(title: "on", on: cut.onMelody, width: 60, color: Theme.voice(cut.pageRow)) { cut.press("melody", "on-m", 1) }
                Pad(title: "roll", width: 60) { cut.press("melody", "roll-melody", 1) }
                Pad(title: "clear pins", width: 90) { cut.press("melody", "pins-clear", 1) }
                Spacer()
            }
            Spacer(minLength: 0)
            row(["lock", "fit", "leap", "notes", "length"])
            row(["echo", "loop", "range", "arrive", "octave"])
            Spacer(minLength: 0)
        }
    }

    private func row(_ names: [String]) -> some View {
        HStack {
            ForEach(names, id: \.self) { n in
                let raw = cut.melodyValues[n] ?? 0
                Knob(label: n, value: normal(n, raw), text: String(raw), color: Theme.voice(cut.pageRow)) {
                    cut.control("melody", n, $0)
                }
                .frame(maxWidth: .infinity)
            }
        }
    }

    private func normal(_ n: String, _ raw: Int) -> Double {
        switch n {
        case "loop": return Double(raw - 1) / 31
        case "range": return Double(raw - 5) / 43
        default: return Double(raw) / 100
        }
    }
}

// MARK: - keys

struct KeysView: View {
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            HStack(spacing: 10) {
                Text(voiceName).font(.system(size: 22, weight: .medium)).foregroundStyle(Theme.voice(cut.pageRow))
                Text(machine).font(.system(size: 18)).foregroundStyle(Theme.dim)
            }
            Pad(title: "velocity", on: cut.velocityOn, width: 120) {
                cut.press("velocity", cut.velocityOn ? "off" : "on")
            }
            Spacer()
        }
    }

    private var voiceName: String {
        guard (1...8).contains(cut.pageRow), let v = cut.voices[cut.pageRow - 1] else { return "" }
        return v.shown
    }
    private var machine: String {
        guard (1...8).contains(cut.pageRow), let v = cut.voices[cut.pageRow - 1] else { return "" }
        return v.machine
    }
}

// MARK: - a voice's setup

struct SoundView: View {
    @Environment(Cut.self) private var cut
    @State private var name = ""
    @FocusState private var typing: Bool
    @State private var sure: String?
    private static let machines = ["fm", "strings", "sine", "saw", "square"]
    private static let methods = ["drums", "harmony", "melody", "keys"]

    var body: some View {
        VStack(spacing: 8) {
            HStack(alignment: .bottom, spacing: 8) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("name").font(.system(size: 12)).foregroundStyle(Theme.dim)
                    TextField("", text: $name)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                        .focused($typing).submitLabel(.done)
                        .padding(.horizontal, 8).frame(width: 130, height: 32)
                        .background(Theme.field, in: .rect(cornerRadius: 5))
                        .onSubmit { cut.press("voices", "name", cut.pageRow, name) }
                }
                Choice(label: "does", value: voice?.method ?? "-", options: Self.methods, width: 96) { _, m in
                    cut.press("voices", "method", cut.pageRow, m)
                }
                if voice?.method != "drums" {
                    Choice(label: "machine", value: voice?.machine ?? "-", options: Self.machines, width: 96) { _, m in
                        choose(m)
                    }
                }
                Choice(label: "patch", value: cut.patch, options: cut.patches + cut.factory.map { "+ \($0)" }, width: 130) { _, p in
                    if p.hasPrefix("+ ") {
                        cut.press("sound", "copy", String(p.dropFirst(2)))
                    } else {
                        cut.press("sound", "patch", p)
                    }
                }
                Spacer(minLength: 0)
            }
            if let sure {
                HStack(spacing: 8) {
                    Text("\(sure) is another voice's").font(.system(size: 14))
                    Pad(title: "use it", width: 80) { cut.press("voices", "machine", cut.pageRow, sure); self.sure = nil }
                    Pad(title: "cancel", width: 80, color: .gray) { self.sure = nil }
                    Spacer()
                }
            }
            params.frame(maxHeight: .infinity)
            HStack(spacing: 8) {
                Pad(title: "save to patch", width: 120) { cut.press("sound", "save") }
                Pad(title: "save as new", width: 110) { cut.press("sound", "saveas") }
                Pad(title: "perform", on: cut.armed > 0, width: 90) { cut.press("perform", "arm") }
                Spacer()
                Pad(title: "remove voice", width: 110, color: .gray) { cut.press("voices", "remove", cut.pageRow) }
            }
        }
        .onAppear { name = voice?.shown ?? "" }
        .onChange(of: cut.pageRow) { _, _ in name = voice?.shown ?? "" }
    }

    private var voice: Cut.Voice? {
        (1...8).contains(cut.pageRow) ? cut.voices[cut.pageRow - 1] : nil
    }

    private var params: some View {
        let cols = Array(repeating: GridItem(.flexible(), spacing: 6), count: 8)
        return ScrollView {
            LazyVGrid(columns: cols, spacing: 10) {
                ForEach(cut.params) { p in
                    Knob(label: p.name, value: p.value, color: Theme.voice(cut.pageRow)) {
                        cut.control("machine", p.name, $0)
                    }
                }
            }
            .padding(.vertical, 6)
        }
    }

    private func choose(_ m: String) {
        let taken = cut.voices.enumerated().contains { i, v in
            i + 1 != cut.pageRow && v?.machine == m
        }
        if taken && (m == "fm" || m == "strings") {
            sure = m
        } else {
            cut.press("voices", "machine", cut.pageRow, m)
        }
    }
}

// MARK: - songs and sections

/// Three columns: a setlist's songs, the song's sections, the section's settings.
struct SongsView: View {
    @Environment(Cut.self) private var cut
    @State private var showAll = false
    @State private var naming: Naming?
    @State private var typed = ""
    enum Naming { case song, section, set }

    var body: some View {
        HStack(spacing: 8) {
            songs.frame(width: 204)
            sections.frame(width: 214)
            detail.frame(maxWidth: .infinity)
        }
        .alert(title, isPresented: Binding(get: { naming != nil }, set: { if !$0 { naming = nil } })) {
            TextField("", text: $typed)
                .textInputAutocapitalization(.never).autocorrectionDisabled()
            Button("Done") { name() }
            Button("Cancel", role: .cancel) { }
        }
    }

    private var title: String {
        switch naming {
        case .song: return "song's name"
        case .section: return "section's name"
        case .set: return "setlist's name"
        default: return ""
        }
    }

    private func name() {
        switch naming {
        case .song: cut.press("songs", "name", typed)
        case .section: cut.press("sections", "name", typed)
        case .set: cut.press("songs", "set-name", typed)
        default: break
        }
        naming = nil
    }

    private func ask(_ n: Naming, _ now: String) {
        typed = now
        naming = n
    }

    private var songs: some View {
        VStack(spacing: 4) {
            Menu {
                ForEach(Array(cut.sets.enumerated()), id: \.offset) { i, s in
                    Button(s) { showAll = false; cut.press("songs", "choose", i + 1) }
                }
                Button("all songs") { showAll = true }
                Button("new setlist") { cut.press("songs", "new-set") }
                Button("name this setlist") { ask(.set, setName) }
            } label: {
                HStack {
                    Text(showAll ? "all songs" : setName).font(.system(size: 15, weight: .medium)).lineLimit(1)
                    Spacer()
                    Image(systemName: "chevron.down").font(.system(size: 10))
                }
                .padding(.horizontal, 8).frame(height: 34)
                .foregroundStyle(.white)
                .background(Theme.field, in: .rect(cornerRadius: 5))
            }
            ScrollView {
                VStack(spacing: 3) {
                    if showAll {
                        ForEach(cut.allSongs) { s in
                            ListRow(number: nil, name: s.name, words: s.words, selected: s.id == cut.songSelected,
                                    playing: s.words.contains("loaded"), queued: s.words.contains("next")) {
                                cut.press("songs", "select", s.id)
                            }
                        }
                    } else {
                        ForEach(cut.setEntries) { e in
                            ListRow(number: e.id, name: e.name, words: e.words, selected: e.id == cut.entrySelected,
                                    playing: e.words.contains("loaded"), queued: e.words.contains("next")) {
                                cut.press("songs", "entry", e.id)
                            }
                        }
                    }
                }
            }
            HStack(spacing: 4) {
                small("load") { cut.press("songs", "load") }
                small("new") { cut.press("songs", "new") }
                Menu {
                    Button("name") { ask(.song, cut.allSongs.first { $0.id == cut.songSelected }?.name ?? "") }
                    Button("add to setlist") { cut.press("songs", "add") }
                    Button("take off setlist") { cut.press("songs", "remove") }
                    Button("move up") { cut.press("songs", "up") }
                    Button("move down") { cut.press("songs", "down") }
                    Button("delete song", role: .destructive) { cut.press("songs", "delete"); cut.press("songs", "delete") }
                } label: {
                    Image(systemName: "ellipsis").frame(maxWidth: .infinity, minHeight: 36)
                        .foregroundStyle(.white).background(Theme.field, in: .rect(cornerRadius: 6))
                }
            }
        }
    }

    private var setName: String {
        (1...max(1, cut.sets.count)).contains(cut.setChosen) && !cut.sets.isEmpty ? cut.sets[cut.setChosen - 1] : "-"
    }

    private var sections: some View {
        VStack(spacing: 4) {
            HStack {
                Text(cut.songName).font(.system(size: 15, weight: .medium)).lineLimit(1)
                Spacer()
                if cut.unsaved { Text("unsaved").font(.system(size: 12)).foregroundStyle(Theme.amber) }
            }
            .frame(height: 34)
            ScrollView {
                VStack(spacing: 3) {
                    ForEach(cut.sections) { s in
                        ListRow(number: s.id, name: s.name, words: s.words, selected: s.id == cut.sectionSelected,
                                playing: s.id == cut.sectionPlaying, queued: s.id == cut.sectionQueued) {
                            cut.press("sections", "select", s.id)
                        }
                    }
                }
            }
            HStack(spacing: 4) {
                small("new") { cut.press("sections", "new") }
                small("save as new") { cut.press("sections", "saveas") }
                Menu {
                    Button("name") { ask(.section, selected?.name ?? "") }
                    Button("move up") { cut.press("sections", "up") }
                    Button("move down") { cut.press("sections", "down") }
                    Button("delete section", role: .destructive) { cut.press("sections", "delete") }
                } label: {
                    Image(systemName: "ellipsis").frame(width: 44, height: 36)
                        .foregroundStyle(.white).background(Theme.field, in: .rect(cornerRadius: 6))
                }
            }
        }
    }

    private var selected: Cut.Row? {
        cut.sections.first { $0.id == cut.sectionSelected }
    }

    private var detail: some View {
        VStack(spacing: 2) {
            HStack {
                Text(selected?.name ?? "-").font(.system(size: 15, weight: .medium)).lineLimit(1)
                Spacer()
            }
            .frame(height: 34)
            stepper("length", selected?.words ?? "loop",
                    { cut.press("sections", "length", max(0, length - 1)) },
                    { cut.press("sections", "length", min(64, length + 1)) })
            stepper("tempo", String(format: "%g", cut.tempo),
                    { cut.press("tempo", (cut.tempo - 1).rounded()) },
                    { cut.press("tempo", (cut.tempo + 1).rounded()) })
            stepper("last step", String(Int(cut.drum(1))),
                    { cut.press("drums", "set-last", Int(cut.drum(1)) - 1) },
                    { cut.press("drums", "set-last", Int(cut.drum(1)) + 1) })
            stepper("time", "\(Int(cut.drum(36)))/\(Int(cut.drum(37)))",
                    { cut.press("drums", "num", -1) }, { cut.press("drums", "num", 1) })
            stepper("swing", String(Int(cut.drum(39))),
                    { cut.press("drums", "set-swing", max(50, Int(cut.drum(39)) - 1)) },
                    { cut.press("drums", "set-swing", min(75, Int(cut.drum(39)) + 1)) })
            stepper("drunk", String(Int(cut.drum(38))),
                    { cut.press("drums", "drunk", max(0, Int(cut.drum(38)) - 5)) },
                    { cut.press("drums", "drunk", min(100, Int(cut.drum(38)) + 5)) })
            HStack {
                Text("tweaks").font(.system(size: 13)).foregroundStyle(Theme.dim)
                Spacer()
                HStack(spacing: 0) {
                    seg("snap back", cut.keepTweaks == 0) { cut.press("sections", "tweaks", 0) }
                    seg("carry on", cut.keepTweaks == 1) { cut.press("sections", "tweaks", 1) }
                }
            }
            .frame(height: 36)
            Spacer(minLength: 0)
        }
    }

    private var length: Int {
        let i = cut.sectionSelected - 1
        return cut.sectionLengths.indices.contains(i) ? cut.sectionLengths[i] : 0
    }

    private func seg(_ t: String, _ on: Bool, _ a: @escaping () -> Void) -> some View {
        Button(action: a) {
            Text(t).font(.system(size: 12)).padding(.horizontal, 7).frame(height: 28)
                .foregroundStyle(on ? Color.black : Color.white)
                .background(on ? Color.white : Theme.field)
        }
        .buttonStyle(.plain)
    }

    private func stepper(_ label: String, _ value: String, _ down: @escaping () -> Void, _ up: @escaping () -> Void) -> some View {
        HStack(spacing: 4) {
            Text(label).font(.system(size: 13)).foregroundStyle(Theme.dim)
            Spacer(minLength: 2)
            arrow("minus", down)
            Text(value).font(.system(size: 14, design: .monospaced)).frame(minWidth: 40)
            arrow("plus", up)
        }
        .frame(height: 38)
    }

    private func arrow(_ icon: String, _ a: @escaping () -> Void) -> some View {
        Button { Tick.down(); a() } label: {
            Image(systemName: icon).font(.system(size: 11)).frame(width: 32, height: 32)
                .foregroundStyle(.white).background(Theme.field, in: .rect(cornerRadius: 5))
        }
        .buttonStyle(.plain)
    }

    private func small(_ t: String, _ a: @escaping () -> Void) -> some View {
        Button { Tick.down(); a() } label: {
            Text(t).font(.system(size: 13)).lineLimit(1).minimumScaleFactor(0.7)
                .frame(maxWidth: .infinity, minHeight: 36)
                .foregroundStyle(.white).background(Theme.field, in: .rect(cornerRadius: 6))
        }
        .buttonStyle(.plain)
    }
}

struct ListRow: View {
    let number: Int?
    let name: String
    let words: String
    let selected: Bool
    let playing: Bool
    let queued: Bool
    let tap: () -> Void

    var body: some View {
        Button { tap() } label: {
            HStack(spacing: 6) {
                if let number {
                    Text(String(number)).font(.system(size: 12)).foregroundStyle(Theme.dim).frame(width: 18, alignment: .trailing)
                }
                Text(name).font(.system(size: 15)).lineLimit(1)
                    .foregroundStyle(playing ? Theme.green : Color.white)
                Spacer(minLength: 2)
                Text(shownWords).font(.system(size: 12)).foregroundStyle(Theme.dim).lineLimit(1)
            }
            .padding(.horizontal, 8).frame(height: 38)
            .background(selected ? Color.white.opacity(0.18) : Color.white.opacity(0.04), in: .rect(cornerRadius: 5))
            .overlay(alignment: .leading) {
                if playing || queued {
                    Rectangle().fill(queued ? Theme.amber : Theme.green).frame(width: 3)
                }
            }
        }
        .buttonStyle(.plain)
    }

    private var shownWords: String {
        words == "-" || words == "loaded" ? "" : words
    }
}

// MARK: - diagnostics

struct DiagView: View {
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 12) {
            Spacer()
            HStack(spacing: 12) {
                Pad(title: "diagnostics", width: 130, color: Theme.green) { cut.press("perform", "ctl", 0, "diag", 0, 1) }
                Pad(title: "test mode", width: 130, color: Theme.blue) { cut.press("perform", "ctl", 0, "test-mode", 0, 1) }
            }
            HStack(spacing: 12) {
                Pad(title: "Volca voice 1", width: 130) { cut.press("sound", "vox", 1) }
                Pad(title: "Volca voice 2", width: 130) { cut.press("sound", "vox", 2) }
            }
            Spacer()
        }
    }
}

/// A row of tabs inside a page.
struct Tabs<T: Hashable & RawRepresentable & CaseIterable>: View where T.RawValue == String, T.AllCases: RandomAccessCollection {
    @Binding var tab: T

    var body: some View {
        HStack(spacing: 4) {
            ForEach(T.allCases, id: \.self) { t in
                Button { tab = t } label: {
                    Text(t.rawValue).font(.system(size: 14, weight: .medium))
                        .frame(maxWidth: .infinity, minHeight: 28)
                        .foregroundStyle(tab == t ? Color.black : Color.white)
                        .background(tab == t ? Color.white : Theme.field, in: .rect(cornerRadius: 5))
                }
                .buttonStyle(.plain)
            }
        }
    }
}
