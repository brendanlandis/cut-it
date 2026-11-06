import Foundation
import Network

/// OSC over UDP, the phone's side of u_net: messages to the Organelle's port, and whatever comes in on ours.
/// UDP has no connection to lose, but iOS closes an app's sockets while it is away, so coming back makes new ones
/// (restart). After that, state flows again by itself.
final class Link: @unchecked Sendable {
    static let host = "192.168.1.15"
    static let sendPort: NWEndpoint.Port = 9001
    /// TouchOSC holds 8000 on the phone, so u_net sends this app a copy on its own port, and both can run.
    static let listenPort: NWEndpoint.Port = 8001

    private let queue = DispatchQueue(label: "cutit.link")
    private var out: NWConnection?
    private var listener: NWListener?
    private var incoming: [NWConnection] = []
    private var host = Link.host
    var onMessage: (@Sendable (String, [OSCValue]) -> Void)?

    func start(host: String = Link.host) {
        self.host = host
        restart()
    }

    /// New sockets both ways, dropping whatever iOS left of the old ones.
    func restart() {
        queue.async { [self] in
            out?.cancel()
            listener?.stateUpdateHandler = nil
            listener?.cancel()
            incoming.forEach { $0.cancel() }
            incoming = []
            let o = NWConnection(host: NWEndpoint.Host(host), port: Link.sendPort, using: .udp)
            o.start(queue: queue)
            out = o
            listen()
        }
    }

    private func listen() {
        let params = NWParameters.udp
        params.allowLocalEndpointReuse = true
        // The old listener's port can take a moment to come free.
        guard let l = try? NWListener(using: params, on: Link.listenPort) else {
            queue.asyncAfter(deadline: .now() + 1) { [weak self] in self?.restart() }
            return
        }
        l.newConnectionHandler = { [weak self] c in
            guard let self else { return }
            self.incoming.append(c)
            c.start(queue: self.queue)
            self.receive(c)
        }
        l.stateUpdateHandler = { [weak self] state in
            // A failed listener, after the network moves or the app comes back, starts again.
            if case .failed = state {
                self?.queue.asyncAfter(deadline: .now() + 1) { self?.restart() }
            }
        }
        l.start(queue: queue)
        listener = l
    }

    private func receive(_ c: NWConnection) {
        c.receiveMessage { [weak self] data, _, _, error in
            if let data, let (path, args) = OSC.decode(data) { self?.onMessage?(path, args) }
            if error == nil { self?.receive(c) }
        }
    }

    func send(_ args: [OSCValue]) {
        out?.send(content: OSC.encode("/cutit", args), completion: .idempotent)
    }
}

enum OSCValue: Sendable {
    case number(Float)
    case text(String)

    var number: Int { if case .number(let f) = self { return Int(f.rounded()) }; return 0 }
    var text: String {
        switch self {
        case .text(let s): return s
        case .number(let f): return f == f.rounded() ? String(Int(f)) : String(f)
        }
    }
}

enum OSC {
    private static func pad(_ s: String) -> Data {
        var d = Data(s.utf8)
        d.append(contentsOf: [UInt8](repeating: 0, count: 4 - d.count % 4))
        return d
    }

    static func encode(_ path: String, _ args: [OSCValue]) -> Data {
        var d = pad(path)
        var tags = ","
        var body = Data()
        for a in args {
            switch a {
            case .number(let f):
                tags += "f"
                withUnsafeBytes(of: f.bitPattern.bigEndian) { body.append(contentsOf: $0) }
            case .text(let s):
                tags += "s"
                body.append(pad(s))
            }
        }
        d.append(pad(tags))
        d.append(body)
        return d
    }

    private static func string(_ bytes: [UInt8], _ at: inout Int) -> String? {
        guard let end = bytes[at...].firstIndex(of: 0) else { return nil }
        let s = String(decoding: bytes[at..<end], as: UTF8.self)
        at = (end / 4 + 1) * 4
        return s
    }

    static func decode(_ data: Data) -> (String, [OSCValue])? {
        let b = [UInt8](data)
        var at = 0
        guard let path = string(b, &at), let tags = string(b, &at), tags.first == "," else { return nil }
        var args: [OSCValue] = []
        for t in tags.dropFirst() {
            switch t {
            case "f", "i":
                guard at + 4 <= b.count else { return nil }
                let raw = UInt32(b[at]) << 24 | UInt32(b[at + 1]) << 16 | UInt32(b[at + 2]) << 8 | UInt32(b[at + 3])
                args.append(.number(t == "f" ? Float(bitPattern: raw) : Float(Int32(bitPattern: raw))))
                at += 4
            case "s":
                guard let s = string(b, &at) else { return nil }
                args.append(.text(s))
            default:
                return nil
            }
        }
        return (path, args)
    }
}
