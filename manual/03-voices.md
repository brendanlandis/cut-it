# Voices and their sound

## Starting a voice

Press an unused row's right button, or its + on the phone. The phone asks what the voice does, its **behavior**, and what
it plays on, its **instrument**: tap one of each, then **add voice**. Nothing is made until then, and what's dim can't be
chosen. The voice's setup page opens, where it can be named.
Voices are the section's: each section has its own, and a new section starts with a copy of the one it was made from.

| Behavior | Plays on | There can be |
|---|---|---|
| drums | The kit | One, for now |
| harmony | FM, strings, sine, saw or square | Two |
| melody | FM, strings, sine, saw or square | Two |
| keys | FM, strings, sine, saw or square | As many as you like |

A section with no drums voice plays no drums. Removing its drums voice, or giving it another behavior, clears the section's
drum pattern, so a drums voice added back starts from an empty one; revert brings the pattern back until you save.

A melody follows the chords of the harmony voice in the same place: the first melody the first harmony, the second the
second. Choosing a synth another voice has asks first, since it can only play one part.

## Patches

A patch is an instrument's saved sound.

- **Factory patches** are starting points, outside any song. Choosing one copies it into the song, which depends on nothing
  after that. They show in the patch dropdown with a +.
- **Song patches** live with the song.
- **Save to patch** makes what you hear what the patch holds. **Save as new** makes another.

A synth is only told what you've actually set, so a voice taking up the FM-1 keeps whatever sound it has until you change
something. Its own knobs still work, but Cut It can't see them, so they can't be saved.

## DX7 voices on the FM-1

An FM voice has two knobs past its effects, **dx7-bank** and **dx7-voice**: 32 banks of 32, the DX7's factory voices and
Yamaha's cartridges. Turn either and that voice is sent to the FM-1, whose screen shows its name. It lands in the FM-1's
voice 128, which Cut It keeps for this, so the other 127 stay as they are. A voice is its program or a DX7 voice, whichever
you chose last, and a patch saves whichever it is.

## Effects on a Pd voice

A sine, saw or square voice's patch can hold **distortion** (drive and its type), **echo** (level, time and feedback) and
**reverb** (level and room). Each is off until you turn it up. Distortion and echo cost almost nothing. A reverb costs about
6% of the Organelle's CPU for as long as its level is up, even while stopped. A hardware synth's effects are its own.

## The setup page

- **Phone:** name, behavior, instrument and patch along the top, and every parameter as a knob.
- **Launchpad:** the first eight parameters as columns to tap; below, the instrument's song patches; on the bottom row, eight
  notes to hear it with.

The kit's sound (each pad's volume, pitch and effects) is on the phone's drum page. Save to patch on a drum voice makes that
what it snaps back to.

{{instruments}}

{{factory}}
