// Written by phone/state-at.py from the Lua that sends each state: don't edit it.
// Where each field of a state begins in its list, 0 the first atom. A field of groups (a slot, a
// voice) has an enum of its own: where each part is within a group, and a group's width.

/// /cutit/drums, from c_steps.lua's R.PHONE_FIELDS.
enum DrumsAt {
    static let playing = 0
    static let last = 1
    static let track = 2
    static let pending = 3
    static let lasts = 4
    static let own = 20
    static let num = 36
    static let den = 37
    static let drunk = 38
    static let swing = 39
    static let vol = 40
    static let pitch = 56
    static let randomness = 72
    static let fxDrive = 88
    static let fxTone = 89
    static let fxDist = 90
    static let fxNote = 91
    static let fxFeel = 92
    static let fxFeedback = 93
    static let fxDelay = 94
    static let fxSend = 95
    static let fxChar = 96
    static let verbSize = 97
    static let verbDamping = 98
    static let mute = 99
    static let solo = 115
    static let verbType = 131
    static let rolled = 132
    static let count = 148
}

/// /cutit/melody, from c_melody.lua's R.PHONE_FIELDS.
enum MelodyAt {
    static let chords = 0
    static let chordLock = 1
    static let smooth = 2
    static let tension = 3
    static let home = 4
    static let span = 5
    static let sounding = 6
    static let onH = 7
    static let onM = 8
    static let key = 9
    static let mode = 10
    static let total = 11
    static let last = 12
    static let slot = 13
    enum Slot {
        static let name = 0
        static let spell = 1
        static let roman = 2
        static let start = 3
        static let width = 4
    }
    static let voiceH = 45
    static let voiceM = 46
    static let lock = 47
    static let fit = 48
    static let leap = 49
    static let notes = 50
    static let length = 51
    static let echo = 52
    static let loop = 53
    static let range = 54
    static let style = 55
    static let bass = 56
    static let arrive = 57
    static let octave = 58
    static let pin = 59
    static let count = 67
}

/// /cutit/notes, from c_melody.lua's R.NOTES_FIELDS.
enum NotesAt {
    static let loop = 0
    static let tonic = 1
    static let scale = 2
    static let note = 9
    static let code = 41
    static let count = 73
}

/// /cutit/perform, from u_perform.lua's R.PHONE_FIELDS.
enum PerformAt {
    static let armed = 0
    static let group = 1
    enum Group {
        static let knobLabel = 0
        static let knobRow = 1
        static let knobValue = 2
        static let knobHeld = 3
        static let faderLabel = 4
        static let faderRow = 5
        static let faderValue = 6
        static let faderHeld = 7
        static let topLabel = 8
        static let topRow = 9
        static let topOn = 10
        static let bottomLabel = 11
        static let bottomRow = 12
        static let bottomOn = 13
        static let width = 14
    }
    static let count = 113
}

/// /cutit/voices, from u_voices.lua's R.PHONE_FIELDS.
enum VoicesAt {
    static let page = 0
    static let kind = 1
    static let row = 2
    static let voice = 3
    enum Voice {
        static let name = 0
        static let behavior = 1
        static let instrument = 2
        static let width = 3
    }
    static let count = 27
}
