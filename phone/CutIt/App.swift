import SwiftUI

@main
struct CutItApp: App {
    @State private var cut = Cut()

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
        }
    }
}

enum Theme {
    static let red = Color(red: 1, green: 0.12, blue: 0.25)
    static let teal = Color(red: 0.2, green: 0.78, blue: 0.75)
    static let amber = Color(red: 1, green: 0.66, blue: 0.12)
    static let blue = Color(red: 0.16, green: 0.35, blue: 1)
    static let line = Color.white.opacity(0.09)
    static let barLine = Color.white.opacity(0.32)
    static let dim = Color.white.opacity(0.55)
}

/// One haptic tick per cell a finger crosses.
@MainActor
enum Tick {
    private static let select = UISelectionFeedbackGenerator()
    private static let press = UIImpactFeedbackGenerator(style: .light)
    static func cell() { select.selectionChanged() }
    static func down() { press.impactOccurred() }
}

struct RootView: View {
    enum Tab: String, CaseIterable { case notes, rhythm, list }
    @State private var tab = Tab.notes
    @Environment(Cut.self) private var cut

    var body: some View {
        VStack(spacing: 6) {
            HStack(spacing: 6) {
                ForEach(Tab.allCases, id: \.self) { t in
                    Button { tab = t } label: {
                        Text(t.rawValue).font(.system(size: 15, weight: .medium))
                            .frame(maxWidth: .infinity, minHeight: 32)
                            .foregroundStyle(tab == t ? Color.black : Color.white)
                            .background(tab == t ? Theme.red : Color.white.opacity(0.1), in: .rect(cornerRadius: 6))
                    }
                    .buttonStyle(.plain)
                }
                Circle().fill(cut.linked ? Theme.teal : Theme.red).frame(width: 10, height: 10).padding(.horizontal, 6)
                    .accessibilityLabel(cut.linked ? "link" : "no link")
            }
            switch tab {
            case .notes: NotesView()
            case .rhythm: RhythmView()
            case .list: ListTest()
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(Color.black)
    }
}

/// A button lit from Cut It's state, or just a press.
struct Pad: View {
    let title: String
    var on = false
    var width: CGFloat = 96
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title).font(.system(size: 15, weight: .medium))
                .frame(width: width, height: 40)
                .foregroundStyle(on ? Color.black : Color.white)
                .background(on ? Theme.red : Theme.red.opacity(0.26), in: .rect(cornerRadius: 6))
        }
        .buttonStyle(.plain)
    }
}
