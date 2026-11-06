import SwiftUI

/// Where the chords fall: a row per time through the pattern's last step, a cell per step. A chord rings until
/// the next one starts. Touched, it sounds; dragged, it moves; dropped on another, the two swap.
struct RhythmView: View {
    @Environment(Cut.self) private var cut
    @State private var drag: (slot: Int, at: Int)?
    @GestureState private var touching = false

    var body: some View {
        VStack(spacing: 6) {
            GeometryReader { geo in
                let size = geo.size
                Canvas { ctx, _ in draw(&ctx, size) }
                    .contentShape(.rect)
                    .gesture(DragGesture(minimumDistance: 0)
                        .updating($touching) { _, on, _ in on = true }
                        .onChanged { touch($0.location, size) }
                        .onEnded { _ in release() })
            }
            HStack(spacing: 8) {
                Pad(title: "on", on: cut.onChords) { cut.send("melody", "on-h", 1) }
                Pad(title: "roll rhythm", width: 110) { cut.send("melody", "roll-rhythm", 1) }
                Pad(title: "\u{2212}", width: 44) { cut.send("melody", "set", "span", max(1, cut.span - 1)) }
                Text("\u{00d7} last \(cut.span)").font(.system(size: 15, design: .monospaced)).frame(width: 90)
                Pad(title: "+", width: 44) { cut.send("melody", "set", "span", min(8, cut.span + 1)) }
                Spacer()
            }
        }
        .onChange(of: touching) { _, on in if !on { cancel() } }
    }

    /// A touch iOS took away, as when switching apps: the chord goes back, and nothing changes.
    private func cancel() {
        guard let d = drag else { return }
        drag = nil
        cut.holding = false
        cut.send("melody", "audition", d.slot, 0)
    }

    private var rowCount: Int { max(1, cut.total / max(1, cut.last)) }

    private func cell(_ t: Int, _ size: CGSize) -> CGRect {
        let w = size.width / CGFloat(cut.last), h = size.height / CGFloat(rowCount)
        return CGRect(x: CGFloat(t % cut.last) * w, y: CGFloat(t / cut.last) * h, width: w, height: h)
    }

    private func step(at p: CGPoint, _ size: CGSize) -> Int {
        let w = size.width / CGFloat(cut.last), h = size.height / CGFloat(rowCount)
        let col = min(cut.last - 1, max(0, Int(p.x / w)))
        let row = min(rowCount - 1, max(0, Int(p.y / h)))
        return row * cut.last + col
    }

    private func draw(_ ctx: inout GraphicsContext, _ size: CGSize) {
        let w = size.width / CGFloat(cut.last), h = size.height / CGFloat(rowCount)
        ctx.fill(Path(CGRect(origin: .zero, size: size)), with: .color(.white.opacity(0.04)))
        for col in stride(from: 0, to: cut.last, by: max(1, cut.every)) {
            ctx.fill(Path(CGRect(x: CGFloat(col) * w, y: 0, width: w, height: size.height)),
                     with: .color(Theme.blue.opacity(0.22)))
        }
        var lines = Path()
        for c in 0...cut.last {
            lines.move(to: CGPoint(x: CGFloat(c) * w, y: 0)); lines.addLine(to: CGPoint(x: CGFloat(c) * w, y: size.height))
        }
        ctx.stroke(lines, with: .color(Theme.line), lineWidth: 0.5)
        var bars = Path()
        for r in 0...rowCount {
            bars.move(to: CGPoint(x: 0, y: CGFloat(r) * h)); bars.addLine(to: CGPoint(x: size.width, y: CGFloat(r) * h))
        }
        ctx.stroke(bars, with: .color(Theme.barLine), lineWidth: 1)
        if cut.gridStep >= 0 { ctx.fill(Path(cell(cut.gridStep, size)), with: .color(.white.opacity(0.3))) }
        for c in cut.chords where c.start >= 0 {
            let at = drag?.slot == c.id ? drag!.at : c.start
            let r = cell(at, size).insetBy(dx: 0.75, dy: 0.75)
            let now = c.id == cut.sounding || drag?.slot == c.id
            let shape = Path(roundedRect: r, cornerRadius: 3)
            ctx.fill(shape, with: .color(Theme.teal.opacity(now ? 1 : 0.28)))
            ctx.stroke(shape, with: .color(c.pinned ? Theme.amber : Theme.teal), lineWidth: c.pinned ? 2 : 1)
            let label = Text(c.roman).font(.system(size: min(13, max(9, w * 0.3)), weight: .medium))
                .foregroundStyle(now ? Color.black : (c.pinned ? Theme.amber : Color.white))
            ctx.draw(label, at: CGPoint(x: r.midX, y: r.midY))
        }
    }

    private func touch(_ p: CGPoint, _ size: CGSize) {
        let t = step(at: p, size)
        guard let d = drag else {
            let col = t % cut.last, row = t / cut.last
            let near = cut.chords.filter { $0.start >= 0 }.map { c -> (Int, Int) in
                (c.id, max(abs(c.start % cut.last - col), abs(c.start / cut.last - row)))
            }.min { $0.1 < $1.1 }
            guard let near, near.1 <= 1 else { return }
            drag = (near.0, cut.chords[near.0 - 1].start)
            cut.holding = true
            cut.send("melody", "audition", near.0, 1)
            Tick.down()
            return
        }
        if t != d.at {
            drag = (d.slot, t)
            Tick.cell()
        }
    }

    private func release() {
        guard let d = drag else { return }
        drag = nil
        cut.holding = false
        cut.send("melody", "audition", d.slot, 0)
        let was = cut.chords[d.slot - 1].start
        guard d.at != was else { return }
        cut.send("melody", "move", d.slot, d.at)
        for i in cut.chords.indices where cut.chords[i].start == d.at { cut.chords[i].start = was }
        cut.chords[d.slot - 1].start = d.at
    }
}
