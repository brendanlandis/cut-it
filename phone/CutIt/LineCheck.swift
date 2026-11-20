import SwiftUI

/// The line check, test/checklists/linecheck.md, which the app carries as it is (project.yml): an edit to it is a
/// rebuild. Each step's title and its Need, Do, Check and Pass if; the Notes stay in the file.
struct LineCheck {
    struct Step: Identifiable, Equatable {
        let id: Int
        let title: String
        let fields: [Field]
    }

    struct Field: Equatable {
        let name: String, text: String
    }

    static let shown = ["Need", "Do", "Check", "Pass if"]

    let name: String
    let steps: [Step]

    static func bundled() -> LineCheck {
        let url = Bundle.main.url(forResource: "linecheck", withExtension: "md")
        let md = url.flatMap { try? String(contentsOf: $0, encoding: .utf8) } ?? ""
        return LineCheck(name: "linecheck", steps: parse(md))
    }

    /// `- [ ] **<n>. <title>**`, then `  - **<field>:** <text>` lines, as the checklists' README sets them out.
    static func parse(_ md: String) -> [Step] {
        md.components(separatedBy: "\n- [ ] ").dropFirst().compactMap { block in
            let lines = block.components(separatedBy: "\n")
            guard let head = lines.first?.firstMatch(of: /^\*\*(\d+)\. (.+?)\*\*/), let n = Int(head.1) else {
                return nil
            }
            let fields: [Field] = lines.dropFirst().compactMap { line in
                guard let m = line.firstMatch(of: /^\s+- \*\*([\w ]+):\*\* (.*)$/), shown.contains(String(m.1)) else {
                    return nil
                }
                return Field(name: String(m.1), text: plain(String(m.2)))
            }
            return Step(id: n, title: plain(String(head.2)), fields: fields)
        }
    }

    /// Markdown to the words on the screen: a link's text without its target, no bold, no code marks.
    static func plain(_ text: String) -> String {
        text.replacing(/\[([^\]]+)\]\([^)]*\)/) { String($0.1) }
            .replacingOccurrences(of: "**", with: "")
            .replacingOccurrences(of: "`", with: "")
    }
}

/// The line check a step at a time, in place of the page while test mode is on (ref/device/phone.md): on the left
/// where it is, the step's title and its words; on the right test mode, the synth the nanoKEY plays, Pass and Fail,
/// Back and Next. Pass and Fail log the verdict on the Organelle and go on to the next step; Back and Next log
/// nothing.
struct LineCheckView: View {
    @Environment(Cut.self) private var cut
    @State private var flash = ""

    var body: some View {
        let steps = cut.lineCheck.steps
        HStack(alignment: .top, spacing: 14) {
            if steps.isEmpty {
                Text("no line check in this build").font(.system(size: 15)).foregroundStyle(Theme.dim)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                let at = min(cut.checkAt, steps.count - 1)
                step(steps[at], of: steps.count)
            }
            controls
        }
        .padding(.horizontal, 4)
        .onChange(of: cut.verdictsHeard) {
            flash = cut.lastVerdict
            Task { @MainActor in
                try? await Task.sleep(for: .milliseconds(250))
                flash = ""
            }
        }
    }

    private func step(_ s: LineCheck.Step, of count: Int) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 14) {
                Text("\(s.id) of \(count)")
                if let v = cut.verdicts[s.id] {
                    Text(v == "pass" ? "passed" : "failed").foregroundStyle(v == "pass" ? Theme.teal : Theme.red)
                }
            }
            .font(.system(size: 14)).foregroundStyle(Theme.dim)
            Text(s.title).font(.system(size: 21, weight: .semibold)).lineLimit(2).minimumScaleFactor(0.8)
            ScrollView {
                VStack(alignment: .leading, spacing: 9) {
                    ForEach(s.fields, id: \.name) { f in
                        (Text(f.name + "  ").foregroundStyle(Theme.dim) + Text(f.text))
                            .font(.system(size: 15))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
            }
            .id(s.id)
            .scrollIndicators(.automatic)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var controls: some View {
        VStack(spacing: 10) {
            HStack(spacing: 8) {
                Circle().fill(Theme.teal).frame(width: 12, height: 12)
                Text("test mode on").font(.system(size: 14))
                Spacer(minLength: 0)
            }
            .frame(width: 2 * 104 + 8, height: 22)
            HStack(spacing: 8) {
                Pad(title: "FM", on: cut.synth == "fm", width: 104) { cut.press("synth", "fm") }
                Pad(title: "STRINGS", on: cut.synth == "strings", width: 104) { cut.press("synth", "strings") }
            }
            Spacer(minLength: 0)
            HStack(spacing: 8) {
                verdict("Pass", "pass", Theme.teal)
                verdict("Fail", "fail", Theme.red)
            }
            HStack(spacing: 8) {
                move("Back") { cut.checkAt = max(0, cut.checkAt - 1) }
                move("Next") { cut.checkAt = min(cut.lineCheck.steps.count - 1, cut.checkAt + 1) }
            }
        }
        .frame(width: 2 * 104 + 8)
    }

    private func verdict(_ title: String, _ v: String, _ color: Color) -> some View {
        Button {
            Tick.down()
            cut.verdict(v)
        } label: {
            Text(title).font(.system(size: 20, weight: .semibold))
                .frame(width: 104, height: 92)
                .foregroundStyle(flash == v ? Color.black : Color.white)
                .background(flash == v ? color : color.opacity(0.32), in: .rect(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }

    private func move(_ title: String, _ action: @escaping () -> Void) -> some View {
        Button {
            Tick.down()
            action()
        } label: {
            Text(title).font(.system(size: 17, weight: .medium))
                .frame(width: 104, height: 56)
                .foregroundStyle(.white)
                .background(Color.white.opacity(0.14), in: .rect(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }
}
