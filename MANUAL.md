# Cut It manual

<!-- Written by manual/build.py from manual/ and the instrument's own tables in Cut It/. Edit those, then run it. -->

- [The rig](#the-rig)
- [Songs and sections](#songs-and-sections)
- [Voices and their sound](#voices-and-their-sound)
- [Writing parts](#writing-parts)
- [In play](#in-play)
- [When something's wrong](#when-somethings-wrong)
- [Every control](#every-control)

## The rig

Five surfaces, each with one job. The same control does the same thing on every page, unless a page says otherwise.

| Surface | Its job |
|---|---|
| **Phone** | See and edit: lists, names, patches, detail. You need it to play a set. |
| **Launchpad** | Move and hit: color only, no words. |
| **nanoKONTROL** | What's in play in this section. The same on every page. |
| **Organelle** | The master: tempo, last step, track last step and rush on its knobs. Its keys load songs. Its screen says what just moved. An on/off foot pedal in its pedal jack is heard, but has no job yet. |
| **nanoKEY** | Notes, on whichever voice is on show. |

### A row is a voice

A song has up to eight voices, one a row, each with its own color on every surface.

- The button on the **right** is the voice's setup: what machine it plays, its name, and its sound.
- The button across from it on the **left** is what the voice does: a drum page, chords, a melody, or the nanoKEY.
- The phone has the same two columns down its sides. Pressing either device's button moves both.
- A dark row has no voice yet. Its right button starts one.
- Pressing the lit button again goes back to the performance page.

### The pages

| Page | How you get there |
|---|---|
| Performance | PLAY brings it up, or the lit button again |
| A voice's behavior | Its left button |
| A voice's setup | Its right button |
| Songs and sections | Aux, on the Organelle; aux again closes it |
| Diagnostics | Setup, on the Launchpad; Setup again closes it |

Save and revert are the rightmost buttons of the Launchpad's two bottom rows, on every page but the performance page.
They light when something's unsaved, and cover the whole song.

## Songs and sections

A song is any number of sections. A section holds its patterns, its tempo, and what's in play. The song holds its voices
and their sounds, which every section shares.

### Moving through a song

The Launchpad's top row is always the song's sections: back, forward, then six buttons that scroll with the one playing.

- Pressed while playing, a section starts when the pattern comes round. It blinks until then.
- Pressed while stopped, it starts at once.
- A section with a length hands over to the next by itself. One without loops until you move on.

### Moving on to the next song

On a song's last section, the forward arrow turns **blue**. Pressing it queues the setlist's next song for the next bar, and
the arrow blinks until it starts. Back takes it back.

- To blend, let the last section play and press blue when you're ready.
- To start from silence: STOP, press blue, which loads at once, then PLAY.

On the setlist's last song, or one that isn't in the setlist, the arrow is dark. The Organelle's keys do the same for any
song: key N is the Nth song of the setlist, next bar while playing and at once while stopped.

### The songs and sections page

Aux opens it, and its LED goes white while it's open. Three columns:

- **Songs:** the setlist's, numbered by Organelle key. The dropdown chooses another setlist, or all songs.
- **Sections:** the selected song's. Green is playing, amber is queued.
- **The section:** its length, tempo, last step, time signature, swing and drunkenness, and **tweaks**.

**Tweaks** is what happens to a sound you've tweaked when this section starts. Snap back returns every voice to what it
was saved as. Carry on leaves it as it stands.

**Save as new** makes what's playing a new section after the one it was, and the original goes back to how it was saved.
Play around with a section until you like it, then press this.

## Voices and their sound

### Starting a voice

Press an unused row's right button. On the phone, give it a name, say what it **does**, and choose its **machine**.

| Does | Plays on | There can be |
|---|---|---|
| drums | The kit | One, for now |
| harmony | FM, strings, sine, saw or square | Two |
| melody | FM, strings, sine, saw or square | Two |
| keys | FM, strings, sine, saw or square | As many as you like |

A melody follows the chords of the harmony voice in the same place: the first melody the first harmony, the second the
second. Choosing a synth another voice has asks first, since it can only play one part.

### Patches

A patch is a machine's saved sound.

- **Factory patches** are starting points, outside any song. Choosing one copies it into the song, which depends on nothing
  after that. They show in the patch dropdown with a +.
- **Song patches** live with the song.
- **Save to patch** makes what you hear what the patch holds. **Save as new** makes another.

A synth is only told what you've actually set, so a voice taking up the Volca keeps whatever sound it has until you change
something. Its own knobs still work, but Cut It can't see them, so they can't be saved.

### Effects on a Pd voice

A sine, saw or square voice's patch can hold **distortion** (drive and its type), **echo** (level, time and feedback) and
**reverb** (level and room). Each is off until you turn it up. Distortion and echo cost almost nothing. A reverb costs about
6% of the Organelle's CPU for as long as its level is up, even while stopped. A hardware synth's effects are its own.

### The setup page

- **Phone:** name, what it does, machine and patch along the top, and every parameter as a knob.
- **Launchpad:** the first eight parameters as columns to tap; below, the machine's song patches; on the bottom row, eight
  notes to hear it with.

The kit's sound (each pad's volume, pitch and effects) is on the phone's drum page. Save to patch on a drum voice makes that
what it snaps back to.

### Each machine's parameters

| Machine | Parameters |
|---|---|
| FM (Volca) | program, mod-attack, mod-decay, car-attack, car-decay, lfo-rate, lfo-depth, algorithm, chorus, chorus-width, chorus-speed |
| strings (Streichfett) | program, registration, octaves, release, crescendo, ensemble-type, ensemble, solo-tone, tremolo, split, solo-sustain, solo-attack, solo-decay, balance, fx-type, animate, phaser, reverb |
| sine | attack, release, bright, level, drive, echo, echo-time, reverb, echo-fb, room, drive-type |
| saw | attack, release, bright, level, drive, echo, echo-time, reverb, echo-fb, room, drive-type |
| square | attack, release, bright, level, drive, echo, echo-time, reverb, echo-fb, room, drive-type |

### Factory patches

| Machine | Patches |
|---|---|
| sine | soft, bell |
| saw | pluck, pad, brass |
| square | hollow, reed |
| strings (Streichfett) | wide, thin, solo |
| FM (Volca) | slow-bloom, short |

## Writing parts

### Drums

The Launchpad's drum page: steps above, velocity and pads below. Press a pad to select its track and hear it. The phone
adds what the Launchpad can't show: each pad's volume, pitch, last step and randomness, its mute and solo, and the selected
track's distortion, delay and reverb.

### Harmony

**Launchpad**

- **Top row:** the chords, in playing order. Hold one to hear it. While holding, play the nanoKEY to write it, or press roll
  to reroll just that one.
- **The seven rows below:** the rhythm, each chord lit where it starts. Hold a chord and tap a step to move it there. Longer
  rhythms show the part that's playing.
- **Upper bottom row:** on, roll chords, roll rhythm, bass only, modal or functional.

**Phone**

- **Chords tab:** key, mode, each chord's name, spelling and role, and the knobs. Lock is how much the chords stay put from
  one loop to the next. Smooth favors chords near the last. Tension reaches for sourer ones. Home pulls toward the tonic.
- **Rhythm tab:** the same grid to drag on, with how many times through the last step it spans.

### Melody

**Launchpad**

- **Top four rows:** 32 steps. Tap one to turn it on or off.
- **Bottom four rows:** the mode's notes, low to high, with the tonic marked. The pad for the note playing lights up.
- **To set a pitch:** hold a step and press a note.
- **Upper bottom row:** on, roll, clear pins.

**Phone**

- **Notes tab:** the melody on a grid, to drag notes around.
- **Shape tab:** the on, roll and clear pins buttons, and the knobs. Leap is how far it jumps. Arrive is how often phrases
  land on a tension. Octave is how often a note jumps an octave.

A note or chord you edit by hand is **pinned**: rolls and drift leave it alone until you clear it.

### Keys

The nanoKEY plays the voice on show. A voice that does keys has nothing else: choose its machine and play.

## In play

The performance page comes up when you press PLAY. It's where the nanoKONTROL lives. Its faders, knobs and buttons move
whatever this section has taken into play, on every page.

### Taking a control into play

1. Press **REC** on the nanoKONTROL, or **perform** on a voice's setup page.
2. Move the control you want, on the phone or the Launchpad.
3. Move the fader, knob or button that should move it.

That lasts for this section, and a new section copies the list. Tempo, rush, a drum track's volume, pitch and effects, and
any parameter on a voice's setup page work the same way. To take one back out, tap
its name on the phone's performance page. A button's name is on the button: hold it.

### What you see

**Launchpad:** each of the first eight columns is that group of the nanoKONTROL. It shows one control, a green-to-red bar
for its fader or a blue bar for its knob. With both in play, it shows whichever moved last.

**A control that's waiting** shows dimmer. When a section starts, each control holds the value it has, and ignores its
physical control until you've turned that to the value or through it. So nothing jumps.

Tapping a column sets its fader to that height, and the physical fader then has to catch up.

**The two bottom rows** are the nanoKONTROL's sixteen buttons, which can't light themselves: dim off, bright on, in their
voices' colors. Pressing one does the same as its button.

**Phone:** the same eight groups, each naming its knob, fader and two buttons, and whose they are.

The nanoKONTROL's ninth group isn't used.

### What can be taken into play

Besides these, every parameter of a voice's machine.

| Control | Part | Kind |
|---|---|---|
| tempo | master | value |
| rush | master | value |
| last-step | drums | value |
| track-last | drums | value |
| lock | harmony | value |
| smooth | harmony | value |
| tension | harmony | value |
| home | harmony | value |
| span | harmony | value |
| chords | harmony | value |
| on | harmony | toggle |
| bass | harmony | toggle |
| modal | harmony | toggle |
| roll | harmony | hit |
| rhythm | harmony | hit |
| lock | melody | value |
| fit | melody | value |
| leap | melody | value |
| notes | melody | value |
| length | melody | value |
| echo | melody | value |
| loop | melody | value |
| range | melody | value |
| arrive | melody | value |
| octave | melody | value |
| on | melody | toggle |
| roll | melody | hit |
| clear | melody | hit |
| room | drums | value |
| damping | drums | value |
| drunk | drums | value |
| swing | drums | value |
| vol | drums | value |
| pitch | drums | value |
| random | drums | value |
| drive | drums | value |
| tone | drums | value |
| dist | drums | value |
| feedback | drums | value |
| delay | drums | value |
| send | drums | value |

## When something's wrong

- **Launchpad's top-left corner button** is recover: a press stops everything. Pressed again quickly, it restarts Pd.
- **Setup, on the Launchpad,** opens the diagnostics: its top-left pad shows the diagnostic screen on the Organelle, and the
  one beside it turns test mode on.
- **A press on the phone** is sent again until the Organelle answers, so a dropped WiFi packet doesn't lose it, and it's
  only acted on once.
- **The phone says "no link"** when the Organelle's heartbeat stops. The instrument keeps playing without it. Coming back to
  the app reconnects it.
- **The aux LED** is green while running and blue while stopped, so a stopped patch can't look like a dead one, and white
  while the songs page is open.
- **A warning or failure** draws on the Organelle's screen, on every page.

### Trying a whole voice on the Volca

The diagnostics page has two amber pads, and the phone has two buttons, that each send the Volca a whole DX7 voice: a glassy
bell and a growling bass. Play the nanoKEY on an FM voice after each. If the sound changes, and the Volca's stored patches
are as they were, Volca patches can be DX7 voices held in Cut It.

## Every control

Generated from the tables the instrument reads, so nothing can go unlisted.

### On every page

| Control | Does |
|---|---|
| Organelle knob 1 | tempo |
| Organelle knob 2 | the global last step |
| Organelle knob 3 | the selected track's last step |
| Organelle knob 4 | rush |
| nanoKONTROL PLAY | PLAY |
| nanoKONTROL STOP | STOP |
| nanoKONTROL LOOP | tap tempo |
| nanoKONTROL REC | arm: take a control into play |
| Launchpad top-left corner | recover |
| Launchpad Setup | the diagnostics page |
| Organelle aux | the songs and sections page |
| Launchpad top row 1 | back a section |
| Launchpad top row 2 | forward a section, or the next song |
| Launchpad top row 3 to Launchpad top row 8 | the section it shows |
| Launchpad upper bottom row 8 | save |
| Launchpad lower bottom row 8 | revert |
| Organelle key 1 to Organelle key 25 | that song of the setlist |
| Launchpad left column, row 1 to Launchpad left column, row 8 | that row's behavior |
| Launchpad right column, row 1 to Launchpad right column, row 8 | that row's setup |
| nanoKONTROL fader 1 to nanoKONTROL lower button 8 | whatever this section has in play |

### On the performance page

| Control | Does |
|---|---|
| Launchpad's pads | tap a column to set its fader |
| Launchpad upper bottom row 1 to Launchpad lower bottom row 8 | whatever this section has in play |

### On the drum page

| Control | Does |
|---|---|
| Launchpad pad, row 8, column 1 to Launchpad pad, row 1, column 8 | the drum page |

### On the harmony page

| Control | Does |
|---|---|
| Launchpad's pads | chords on the top row, the rhythm below |
| Launchpad upper bottom row 1 | on |
| Launchpad upper bottom row 2 | roll chords |
| Launchpad upper bottom row 3 | roll the rhythm |
| Launchpad upper bottom row 4 | bass only |
| Launchpad upper bottom row 5 | modal or functional |

### On the melody page

| Control | Does |
|---|---|
| Launchpad's pads | 32 steps above, the mode's notes below |
| Launchpad upper bottom row 1 | on |
| Launchpad upper bottom row 2 | roll the melody |
| Launchpad upper bottom row 3 | clear pins |

### On a voice's setup page

| Control | Does |
|---|---|
| Launchpad's pads | parameters above, patches on row 2, notes on row 1 |

### On the diagnostics page

| Control | Does |
|---|---|
| Launchpad pad, row 8, column 1 | the diagnostic screen |
| Launchpad pad, row 8, column 2 | test mode |
| Launchpad pad, row 8, column 3 | machine vox1 |
| Launchpad pad, row 8, column 4 | machine vox2 |
