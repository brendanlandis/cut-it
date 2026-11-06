import SwiftUI

@main
struct CutItApp: App {
    @State private var cut = Cut()
    @Environment(\.scenePhase) private var phase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(cut)
                .preferredColorScheme(.dark)
                .statusBarHidden()
                .persistentSystemOverlays(.hidden)
                .onAppear {
                    UIApplication.shared.isIdleTimerDisabled = true
                    cut.start()
                }
                .onChange(of: phase) { _, now in
                    if now == .active { cut.cameBack() }
                }
        }
    }
}

enum Theme {
    static let red = Color(red: 1, green: 0.12, blue: 0.25)
    static let teal = Color(red: 0.2, green: 0.78, blue: 0.75)
    static let amber = Color(red: 1, green: 0.66, blue: 0.12)
    static let blue = Color(red: 0.16, green: 0.35, blue: 1)
    static let green = Color(red: 0.18, green: 0.82, blue: 0.42)
    static let line = Color.white.opacity(0.09)
    static let barLine = Color.white.opacity(0.32)
    static let dim = Color.white.opacity(0.55)
    static let field = Color.white.opacity(0.08)

    /// A voice's color, by its row, the Launchpad's.
    static let voices: [Color] = [
        Color(red: 1, green: 0.16, blue: 0.57), Color(red: 0, green: 0.76, blue: 1),
        Color(red: 1, green: 0.44, blue: 0), Color(red: 0, green: 1, blue: 0.25),
        Color(red: 0.5, green: 0.16, blue: 1), Color(red: 1, green: 0.87, blue: 0),
        Color(red: 1, green: 0.19, blue: 0.06), Color(red: 0.75, green: 0.75, blue: 0.75),
    ]
    static func voice(_ row: Int) -> Color { (1...8).contains(row) ? voices[row - 1] : .white }
}

/// One haptic tick per cell a finger crosses.
@MainActor
enum Tick {
    private static let select = UISelectionFeedbackGenerator()
    private static let press = UIImpactFeedbackGenerator(style: .light)
    static func cell() { select.selectionChanged() }
    static func down() { press.impactOccurred() }
}

/// The Launchpad's two columns down each side, the page between them.
struct RootView: View {
    @Environment(Cut.self) private var cut

    var body: some View {
        HStack(spacing: 6) {
            Rail(side: .left)
            VStack(spacing: 4) {
                if !cut.linked {
                    Text("no link").font(.system(size: 14, weight: .semibold))
                        .frame(maxWidth: .infinity, minHeight: 22)
                        .background(Theme.red, in: .rect(cornerRadius: 4))
                }
                page.frame(maxWidth: .infinity, maxHeight: .infinity)
            }
            Rail(side: .right)
        }
        .padding(.vertical, 4)
        .background(Color.black)
    }

    @ViewBuilder private var page: some View {
        switch cut.pageName {
        case "drums": DrumsView()
        case "harmony": HarmonyView()
        case "melody": MelodyView()
        case "keys": KeysView()
        case "sound": SoundView()
        case "songs": SongsView()
        case "diag": DiagView()
        default: PerformView()
        }
    }
}

/// A column: eight buttons, in each voice's color; dark for a row with none.
struct Rail: View {
    enum Side { case left, right }
    let side: Side
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 3) {
            ForEach(1...8, id: \.self) { row in
                let v = cut.voices[row - 1]
                let lit = cut.pageRow == row && cut.pageKind == (side == .left ? "voice" : "setup")
                Button {
                    Tick.down()
                    cut.send("voices", side == .left ? "left" : "right", row)
                } label: {
                    Text(title(v, row))
                        .font(.system(size: 12, weight: lit ? .semibold : .regular))
                        .lineLimit(2).minimumScaleFactor(0.7).multilineTextAlignment(.center)
                        .frame(width: 58).frame(maxHeight: .infinity)
                        .foregroundStyle(lit ? Color.black : (v == nil ? Color.white.opacity(0.3) : Color.white))
                        .background(fill(v, row, lit), in: .rect(cornerRadius: 5))
                }
                .buttonStyle(.plain)
            }
        }
    }

    private func title(_ v: Cut.Voice?, _ row: Int) -> String {
        guard let v else { return side == .right ? "+" : "" }
        return side == .left ? v.shown : v.machine
    }

    private func fill(_ v: Cut.Voice?, _ row: Int, _ lit: Bool) -> Color {
        guard v != nil else { return Color.white.opacity(0.05) }
        return lit ? Theme.voice(row) : Theme.voice(row).opacity(0.24)
    }
}

/// A button lit from Cut It's state, or just a press.
struct Pad: View {
    let title: String
    var on = false
    var width: CGFloat = 96
    var color: Color = Theme.red
    let action: () -> Void

    var body: some View {
        Button(action: { Tick.down(); action() }) {
            Text(title).font(.system(size: 15, weight: .medium)).lineLimit(1).minimumScaleFactor(0.7)
                .frame(width: width, height: 40)
                .foregroundStyle(on ? Color.black : Color.white)
                .background(on ? color : color.opacity(0.26), in: .rect(cornerRadius: 6))
        }
        .buttonStyle(.plain)
    }
}

/// A knob, dragged up and down. Its value is what Cut It last said, 0 to 1, unless a finger is on it.
struct Knob: View {
    let label: String
    let value: Double
    var text: String? = nil
    var color: Color = Theme.teal
    var size: CGFloat = 44
    let send: (Double) -> Void

    @State private var held: Double?
    @State private var from = 0.0
    @State private var sent = -1.0

    var body: some View {
        let v = held ?? value
        VStack(spacing: 2) {
            ZStack {
                Circle().trim(from: 0, to: 0.8).rotation(.degrees(126))
                    .stroke(Color.white.opacity(0.14), style: .init(lineWidth: 4, lineCap: .round))
                Circle().trim(from: 0, to: 0.8 * max(0.001, min(1, v))).rotation(.degrees(126))
                    .stroke(color, style: .init(lineWidth: 4, lineCap: .round))
                Text(text ?? String(Int((v * 100).rounded()))).font(.system(size: 13, design: .monospaced))
            }
            .frame(width: size, height: size)
            Text(label).font(.system(size: 12)).foregroundStyle(Theme.dim).lineLimit(1).minimumScaleFactor(0.7)
        }
        .contentShape(.rect)
        .gesture(DragGesture(minimumDistance: 0)
            .onChanged { d in
                if held == nil { from = value; held = value; Tick.down() }
                let now = max(0, min(1, from - d.translation.height / 180))
                held = now
                if abs(now - sent) >= 0.004 { sent = now; send(now) }
            }
            .onEnded { _ in held = nil; sent = -1 })
    }
}

/// A short list of choices, on a menu.
struct Choice: View {
    let label: String
    let value: String
    let options: [String]
    var width: CGFloat = 110
    let pick: (Int, String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label).font(.system(size: 12)).foregroundStyle(Theme.dim)
            Menu {
                ForEach(Array(options.enumerated()), id: \.offset) { i, o in
                    Button(o) { pick(i, o) }
                }
            } label: {
                HStack {
                    Text(value).font(.system(size: 15)).lineLimit(1)
                    Spacer(minLength: 2)
                    Image(systemName: "chevron.down").font(.system(size: 10))
                }
                .padding(.horizontal, 8)
                .frame(width: width, height: 32)
                .foregroundStyle(.white)
                .background(Theme.field, in: .rect(cornerRadius: 5))
            }
        }
    }
}
