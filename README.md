# Cut It

A cutup / harsh noise patch for the (older) Organelle. It's in the early design stages and mostly not built out yet.

The idea is, with a single audio input that might not have too much variation, this patch should be able to create stressful sounding, fast tempo music, ala [cut up harsh noise](https://trianglerecords.bandcamp.com/album/hard-panning-the-ultimate-contemporary-cut-up-harsh-noise-international-compilation).

It takes MIDI clock info via USB. There are multiple parts of the patch that can do their thing either by tempo divisions based on that MIDI clock (quarter notes, eighth notes, etc.), or by milliseconds. Different parts of the patch can use different time units independently if you want (e.g. 1/8th note sample shuffling and 30ms tremolo), making for some potentially pretty freaky shit.

The controls will take some practice and memorization in order to get fluent with them. The intention in designing and building this patch is that it should be something that rewards practice, as any instrument does.

In general it's a pretty idiosyncratic tool, but it can make some pretty exciting music too.


## ok, what does all this shit do then

Cut It turns the Organelle into a chain of four pedals, basically. (So, you'll want to have audio going into the device. It doesn't generate any sound on its own.) To play the patch as intended, the physical device itself should be rotated 90° counter-clockwise, so that the keyboard buttons are arranged from C4 at the bottom to B6 at the top. From this perspective, the buttons represent four groups of controls, one for each "pedal" (Ugh, I'll call them "filters" from now on). These filters process the sound serially (from bottom to top), as a pedal chain would.

The filters and their controls are, from bottom to top:

- F5-B6 - reverb / freeze
- C5-E5 - tremolo
- F4-B5 - filter / pitch
- C4-E4 - chop

The knobs also control different stuff for each of the filters, and are selected by pressing the lower-left-most button of each group. (So for example, if you want to use the knobs to control stuff for the tremolo filter, you'll press C5 to switch them over to those controls. For filter / pitch, F#4.)

This lower-left-most button also functions as a "shift" button, allowing access to other controls for each filter. More on each filter below.


## nitty gritty controls

### chop
The first filter in the "pedal chain", and the bottom-most group of controls. There are a couple concepts behind this filter:

1. In its default state, Chop revolves around the recording and playback of a single sample at a time. The knobs can be used to mangle the playback of the sample in some fun ways. Pressing D#4 engages sample mode, which acts as a kind of loop pedal, using whichever sample was played or recorded last. If there are no samples recorded, it will start recording one for the length specified by knob2 ("grain size"). Once the sample is recorded, sample mode will engage.
2. Chop is also equipped with Chop mode, which, when engaged, will start randomly shuffling between the live sound going into the Organelle, and up to four recorded samples. If no recorded samples are present, it'll start recording samples one at a time, for the length specified by knob2 ("grain size"). Once each sample is recorded, chop mode will engage.

#### knobs

- knob1: playhead start position
    - knob1 + shift:
- knob2: grain size (percentage of sample to play [while recording a sample, this knob specifies how long to record for - max 5 seconds])
    - knob2 + shift:
- knob3: playback speed
    - knob3 + shift: playback pitch
- knob4: tempo of playhead movement in BPM (0 = playhead does not move, 100 = playhead skips around randomly at the rate of 256th notes)
    - knob4 + shift: tempo of playhead movement in BPM (0 = no movement, 100 = idk hella fast)

#### buttons
        E4  - engage sample mode
    D#4     - engage chop mode
        D4  - stop either sample mode or chop mode
    C#4     - shift / make knobs start controlling sample / chop stuff
        C4  - delete all samples

and, with shift engaged:

        E4  - record sample 2
    D#4     - record sample 1
        D4  - record sample 3
    C#4     - still shift, duh
        C4  - record sample 4





# dev notes for me while I figure this shit out

https://www.critterandguitari.com/manual?m=Organelle_Manual#7-additional-info
