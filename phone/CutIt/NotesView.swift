import SwiftUI

/// The melody on a grid: a column per step, a row per note of the mode across what the loop uses.
struct NotesView: View {
    @Environment(Cut.self) private var cut
    @State private var rows: [Int] = []
    @State private var drag: Drag?
    private let gutter: CGFloat = 34

    private struct Drag {
        let from: Int
        var step: Int, row: Int, pitch: Int
        let made: Bool
        var moved = false
    }

    var body: some View {
        VStack(spacing: 6) {
            GeometryReader { geo in
                let size = geo.size
                Canvas { ctx, _ in draw(&ctx, size) }
                    .contentShape(.rect)
                    .gesture(DragGesture(minimumDistance: 0)
                        .onChanged { touch($0.location, size) }
                        .onEnded { _ in release() })
            }
            HStack(spacing: 8) {
                Pad(title: "on", on: cut.onMelody) { cut.send("melody", "on-m", 1) }
                Pad(title: "roll") { cut.send("melody", "roll-melody", 1) }
                Pad(title: "clear pins", width: 110) { cut.send("melody", "pins-clear", 1) }
                Spacer()
            }
        }
        .onChange(of: cut.notes) { if drag == nil { rows = makeRows() } }
        .onChange(of: cut.scale) { if drag == nil { rows = makeRows() } }
        .onAppear { rows = makeRows() }
    }

    private func makeRows() -> [Int] {
        let sounding = cut.notes.prefix(cut.loop).filter { $0 > 0 }
        var lo = (sounding.min() ?? 60) - 3, hi = (sounding.max() ?? 76) + 3
        while hi - lo < 24 { lo -= 1; hi += 1 }
        return (lo...hi).filter { cut.scale.contains(($0 % 12 + 12) % 12) }
    }

    private func rowOf(_ note: Int) -> Int {
        rows.enumerated().min { abs($0.element - note) < abs($1.element - note) }?.offset ?? 0
    }

    private func cellSize(_ size: CGSize) -> CGSize {
        CGSize(width: (size.width - gutter) / CGFloat(cut.loop), height: size.height / CGFloat(max(1, rows.count)))
    }

    private func rect(step: Int, row: Int, _ size: CGSize) -> CGRect {
        let c = cellSize(size)
        return CGRect(x: gutter + CGFloat(step - 1) * c.width,
                      y: size.height - CGFloat(row + 1) * c.height, width: c.width, height: c.height)
    }

    private func draw(_ ctx: inout GraphicsContext, _ size: CGSize) {
        guard !rows.isEmpty else { return }
        let c = cellSize(size)
        let grid = CGRect(x: gutter, y: 0, width: size.width - gutter, height: size.height)
        ctx.fill(Path(grid), with: .color(.white.opacity(0.04)))
        // Every Nth step blue, and the tonic's rows.
        for step in stride(from: 0, to: cut.loop, by: max(1, cut.every)) {
            ctx.fill(Path(CGRect(x: gutter + CGFloat(step) * c.width, y: 0, width: c.width, height: size.height)),
                     with: .color(Theme.blue.opacity(0.22)))
        }
        for (r, p) in rows.enumerated() where (p % 12 + 12) % 12 == cut.tonic {
            ctx.fill(Path(rect(step: 1, row: r, size).applying(.identity).with(width: size.width - gutter)),
                     with: .color(Theme.teal.opacity(0.16)))
        }
        // The grid's own lines, as thin as the screen can draw.
        var lines = Path()
        for s in 0...cut.loop {
            let x = gutter + CGFloat(s) * c.width
            lines.move(to: CGPoint(x: x, y: 0)); lines.addLine(to: CGPoint(x: x, y: size.height))
        }
        for r in 0...rows.count {
            let y = CGFloat(r) * c.height
            lines.move(to: CGPoint(x: gutter, y: y)); lines.addLine(to: CGPoint(x: size.width, y: y))
        }
        ctx.stroke(lines, with: .color(Theme.line), lineWidth: 0.5)
        // Where the loop is.
        if cut.melodyStep >= 1, cut.melodyStep <= cut.loop {
            ctx.fill(Path(CGRect(x: gutter + CGFloat(cut.melodyStep - 1) * c.width, y: 0, width: c.width,
                                 height: size.height)), with: .color(.white.opacity(0.16)))
        }
        // Pitch names up the side.
        let names = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
        for (r, p) in rows.enumerated() {
            let pc = (p % 12 + 12) % 12
            guard c.height >= 11 || pc == cut.tonic else { continue }
            let label = Text(names[pc] + String(p / 12 - 1))
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(pc == cut.tonic ? Color.white : Theme.dim)
            ctx.draw(label, at: CGPoint(x: gutter - 3, y: size.height - (CGFloat(r) + 0.5) * c.height), anchor: .trailing)
        }
        // The notes: dim as rolled, bright once edited, arrivals amber.
        for i in 1...cut.loop where i != drag?.from {
            let n = cut.notes[i - 1]
            guard n > 0 else { continue }
            cell(&ctx, rect(step: i, row: rowOf(n), size), code: cut.codes[i - 1], now: i == cut.melodyStep)
        }
        if let d = drag {
            cell(&ctx, rect(step: d.step, row: d.row, size).insetBy(dx: -1, dy: -1), code: 4, now: true)
        }
    }

    private func cell(_ ctx: inout GraphicsContext, _ r: CGRect, code: Int, now: Bool) {
        let hue = code % 4 == 1 ? Theme.amber : Theme.teal
        let pinned = code >= 4
        let shape = Path(roundedRect: r.insetBy(dx: 0.75, dy: 0.75), cornerRadius: 2)
        ctx.fill(shape, with: .color(hue.opacity(pinned || now ? 1 : 0.5)))
        ctx.stroke(shape, with: .color(hue), lineWidth: 1)
    }

    private func where_(_ p: CGPoint, _ size: CGSize) -> (step: Int, row: Int) {
        let c = cellSize(size)
        let step = min(cut.loop, max(1, Int((p.x - gutter) / c.width) + 1))
        let row = min(rows.count - 1, max(0, Int((size.height - p.y) / c.height)))
        return (step, row)
    }

    private func touch(_ p: CGPoint, _ size: CGSize) {
        guard !rows.isEmpty else { return }
        let (step, row) = where_(p, size)
        guard var d = drag else {
            let n = cut.notes[step - 1]
            let on = n > 0 && abs(rowOf(n) - row) <= 1
            let pitch = on ? n : rows[row]
            drag = Drag(from: step, step: step, row: on ? rowOf(n) : row, pitch: pitch, made: !on)
            cut.holding = true
            cut.send("melody", "note-hear", pitch, 1)
            Tick.down()
            return
        }
        guard step != d.step || row != d.row else { return }
        d.moved = true
        if row != d.row {
            cut.send("melody", "note-hear", d.pitch, 0)
            d.pitch = rows[row]
            cut.send("melody", "note-hear", d.pitch, 1)
        }
        d.step = step
        d.row = row
        drag = d
        Tick.cell()
    }

    private func release() {
        guard let d = drag else { return }
        drag = nil
        cut.holding = false
        cut.send("melody", "note-hear", d.pitch, 0)
        if d.moved && d.step != d.from || (d.moved && !d.made) {
            cut.send("melody", "note-move", d.from, d.step, d.pitch)
            cut.notes[d.from - 1] = 0
            cut.notes[d.step - 1] = d.pitch
            cut.codes[d.step - 1] = 4
        } else if d.made {
            cut.send("melody", "note-set", d.step, d.pitch)
            cut.notes[d.step - 1] = d.pitch
            cut.codes[d.step - 1] = 4
        } else {
            cut.send("melody", "note-rest", d.from)
            cut.notes[d.from - 1] = 0
        }
    }
}

private extension CGRect {
    func with(width: CGFloat) -> CGRect { CGRect(x: minX, y: minY, width: width, height: height) }
}
