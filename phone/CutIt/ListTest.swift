import SwiftUI

/// A test of what TouchOSC can't do: a long list that scrolls, with typed search. The names are made up here.
struct ListTest: View {
    private static let all: [String] = {
        let a = ["Glass", "Iron", "Soft", "Hollow", "Bright", "Dark", "Slow", "Metal", "Wood", "Sour", "Round", "Thin"]
        let b = ["Bell", "Bass", "Keys", "Pad", "Pluck", "Lead", "Organ", "Brass", "Mallet", "Strings", "Choir", "Harp"]
        var out: [String] = []
        for n in 1...420 { for x in a.prefix(3) { for y in b.prefix(4) { out.append("\(x) \(y) \(n)") } } }
        for x in a { for y in b { out.append("\(x) \(y)") } }
        return out
    }()

    @State private var query = ""
    @State private var chosen: String?

    var body: some View {
        let q = query.lowercased()
        let shown = q.isEmpty ? Self.all : Self.all.filter { $0.lowercased().contains(q) }
        VStack(spacing: 6) {
            HStack {
                TextField("search", text: $query)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                Text("\(shown.count)").font(.system(size: 14, design: .monospaced)).foregroundStyle(Theme.dim)
            }
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(shown, id: \.self) { name in
                        Button { chosen = name } label: {
                            Text(name).frame(maxWidth: .infinity, minHeight: 36, alignment: .leading)
                                .padding(.horizontal, 10)
                                .foregroundStyle(chosen == name ? Color.black : Color.white)
                                .background(chosen == name ? Theme.teal : Color.clear)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }
}
