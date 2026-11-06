import SwiftUI

/// The drum page's other half: what the Launchpad can't show. The sixteen pads, each what the show radio says,
/// dragged; each pad's mute and solo; and the selected track's effects.
struct DrumsView: View {
    enum Show: String, CaseIterable { case volume, pitch, last, random }
    enum Effect: String, CaseIterable { case distortion, delay, reverb }
    @State private var show = Show.volume
    @State private var effect = Effect.distortion
    @Environment(Cut.self) private var cut

    var body: some View {
        HStack(spacing: 8) {
            VStack(spacing: 6) {
                Tabs(tab: $show)
                // Counted from the bottom left, as the Launchpad's are.
                VStack(spacing: 3) {
                    ForEach([12, 8, 4, 0], id: \.self) { base in
                        HStack(spacing: 3) {
                            ForEach(1...4, id: \.self) { c in TrackPad(track: base + c, show: show) }
                        }
                    }
                }
                .frame(maxHeight: .infinity)
                HStack(spacing: 6) {
                    Pad(title: "sync", width: 70) { cut.press("drums", "sync") }
                    Pad(title: "snap", width: 70) { cut.press("drums", "snap") }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity)
            VStack(spacing: 6) {
                Tabs(tab: $effect)
                effects.frame(maxHeight: .infinity)
            }
            .frame(width: 236)
        }
    }

    private func fx(_ i: Int) -> Double { cut.drum(fxOffset + i) }
    private var fxOffset: Int { 4 + 32 + 4 + 48 }

    @ViewBuilder private var effects: some View {
        let t = cut.drumTrack
        switch effect {
        case .distortion:
            VStack(spacing: 10) {
                segments(["soft", "hard", "fold", "crush"], Int(fx(Fx.char)) - 1) { cut.press("drums", "char", t, $0 + 1) }
                HStack {
                    knob("drive", fx(Fx.drive)) { cut.control("drums", "drive-\(t)", Double($0) / 100) }
                    knob("tone", fx(Fx.tone)) { cut.control("drums", "tone-\(t)", Double($0) / 100) }
                    knob("mix", fx(Fx.dist)) { cut.control("drums", "dist-\(t)", Double($0) / 100) }
                }
                Spacer(minLength: 0)
            }
        case .delay:
            VStack(spacing: 10) {
                segments(["1/2", "1/4", "1/8", "1/16", "1/32"], Int(fx(Fx.delayNote)) - 1) { cut.press("drums", "delay-note", t, $0 + 1) }
                segments(["straight", "triplet", "dotted"], Int(fx(Fx.delayFeel)) - 1) { cut.press("drums", "delay-feel", t, $0 + 1) }
                HStack {
                    knob("feedback", fx(Fx.feedback)) { cut.control("drums", "feedback-\(t)", Double($0) / 100) }
                    knob("level", fx(Fx.delay)) { cut.control("drums", "delay-\(t)", Double($0) / 100) }
                }
                Spacer(minLength: 0)
            }
        case .reverb:
            VStack(spacing: 10) {
                segments(["plate", "giga", "free"], Int(cut.drum(verbTypeAt))) { cut.press("drums", "verb-type", $0) }
                HStack {
                    knob("send", fx(Fx.send)) { cut.control("drums", "send-\(t)", Double($0) / 100) }
                    knob("size", cut.drum(fxOffset + Fx.count)) { cut.control("drums", "kit-size", Double($0) / 100) }
                    knob("damping", cut.drum(fxOffset + Fx.count + 1)) { cut.control("drums", "kit-damping", Double($0) / 100) }
                }
                Spacer(minLength: 0)
            }
        }
    }

    private var verbTypeAt: Int { fxOffset + Fx.count + 2 + 32 }

    private func knob(_ label: String, _ v: Double, _ send: @escaping (Int) -> Void) -> some View {
        Knob(label: label, value: v / 100, text: String(Int(v)), color: Theme.voice(cut.pageRow)) { send(Int(($0 * 100).rounded())) }
            .frame(maxWidth: .infinity)
    }

    private func segments(_ names: [String], _ on: Int, _ pick: @escaping (Int) -> Void) -> some View {
        HStack(spacing: 2) {
            ForEach(Array(names.enumerated()), id: \.offset) { i, n in
                Button { pick(i) } label: {
                    Text(n).font(.system(size: 12)).lineLimit(1).minimumScaleFactor(0.7)
                        .frame(maxWidth: .infinity, minHeight: 30)
                        .foregroundStyle(i == on ? Color.black : Color.white)
                        .background(i == on ? Color.white : Theme.field, in: .rect(cornerRadius: 4))
                }
                .buttonStyle(.plain)
            }
        }
    }

    /// c_steps' R.FX order, from c_steps.lua.
    enum Fx {
        static let drive = 0, tone = 1, dist = 2, delayNote = 3, delayFeel = 4, feedback = 5, delay = 6, send = 7, char = 8
        static let count = 9
    }
}

/// A drum pad: tapped, it's the selected track; dragged, what the show radio says moves; M and S under it.
struct TrackPad: View {
    let track: Int
    let show: DrumsView.Show
    @Environment(Cut.self) private var cut
    @State private var from: Double?

    var body: some View {
        let sel = cut.drumTrack == track
        VStack(spacing: 1) {
            Text(text).font(.system(size: 12, design: .monospaced)).lineLimit(1).minimumScaleFactor(0.6)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .foregroundStyle(sel ? Color.black : Color.white)
                .background(sel ? Theme.red : Theme.voice(1).opacity(0.3), in: .rect(cornerRadius: 4))
                .gesture(DragGesture(minimumDistance: 0)
                    .onChanged { d in
                        if from == nil {
                            from = value
                            if !sel { cut.press("drums", "select", track) }
                        }
                        drag(d.translation.height)
                    }
                    .onEnded { _ in from = nil })
            HStack(spacing: 1) {
                flag("M", muteOn) { cut.press("drums", "mute", track, muteOn ? 0 : 1) }
                flag("S", soloOn) { cut.press("drums", "solo", track, soloOn ? 0 : 1) }
            }
        }
    }

    private func flag(_ t: String, _ on: Bool, _ a: @escaping () -> Void) -> some View {
        Button(action: a) {
            Text(t).font(.system(size: 10)).frame(maxWidth: .infinity, minHeight: 16)
                .foregroundStyle(on ? Color.black : Color.white)
                .background(on ? Theme.amber : Theme.field, in: .rect(cornerRadius: 2))
        }
        .buttonStyle(.plain)
    }

    private var i: Int { track - 1 }
    private var base: Int { 4 + 32 + 4 }
    private var value: Double {
        switch show {
        case .volume: return cut.drum(base + i)
        case .pitch: return cut.drum(base + 16 + i)
        case .random: return cut.drum(base + 32 + i)
        case .last: return cut.drum(4 + i)
        }
    }
    private var text: String {
        let v = value
        switch show {
        case .volume: return String(format: "%+.0f", v)
        case .pitch: return String(format: "%+.0f", v)
        default: return String(Int(v))
        }
    }
    private var after: Int { base + 48 + DrumsView.Fx.count + 2 }
    private var muteOn: Bool { cut.drum(after + i) == 1 }
    private var soloOn: Bool { cut.drum(after + 16 + i) == 1 }

    private func drag(_ dy: Double) {
        guard let from else { return }
        switch show {
        case .volume:
            cut.control("drums", "vol-\(track)", (max(-30, min(6, (from - dy / 5).rounded())) + 30) / 36)
        case .pitch:
            cut.control("drums", "pitch-\(track)", (max(-12, min(12, (from - dy / 8).rounded())) + 12) / 24)
        case .last:
            cut.send("drums", "set-track-last", track, Int(max(1, min(32, (from - dy / 6).rounded()))))
        case .random:
            cut.control("drums", "randomness-\(track)", max(0, min(100, ((from - dy) / 5).rounded() * 5)) / 100)
        }
    }
}
