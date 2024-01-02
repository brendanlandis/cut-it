# Cut It

A cutup / harsh noise patch for the (older) Organelle. It's in the early design stages and mostly not built out yet.

The idea is, with a single audio input that might not have too much variation, this patch should be able to create stressful sounding, fast tempo music, ala [cut up harsh noise](https://trianglerecords.bandcamp.com/album/hard-panning-the-ultimate-contemporary-cut-up-harsh-noise-international-compilation).

It takes MIDI clock info via USB. There are multiple parts of the patch that can do their thing either by tempo divisions based on that MIDI clock (quarter notes, eighth notes, etc.), or by milliseconds. Different parts of the patch can use different time units independently if you want (e.g. 1/8th note sample shuffling and 30ms tremolo), making for some potentially pretty freaky shit.

The controls will take some practice and memorization in order to get fluent with them. The intention in designing and building this patch is that it should be something that rewards practice, as any instrument does.

In general it's a pretty idiosyncratic tool, but it can make some pretty exciting music too.


## ok, what does all this shit do then

Cut It turns the Organelle into a chain of four pedals, basically. (So, you'll want to have audio going into the device. It doesn't generate any sound on its own.) The buttons represent four groups of controls, one for each "pedal" (I'll call them "filters" from now on). These filters process the sound serially (from right to left), as a pedal chain would.

The filters and their controls are, from right to left:

- F5-B6 - chop
- C5-E5 - filter / pitch
- F4-B5 - tremolo
- C4-E4 - reverb / freeze

The knobs also control different stuff for each of the filters, and the display will give status of what's happening with whichever filter is "selected". You can select a filter by pressing the "on/off" or "shift" buttons for that filter (see diagrams below).


## nitty gritty controls

### chop
The first filter in the chain, and the right-most group of controls. There are a couple concepts behind this filter:

1. In its default state, Chop revolves around the recording and playback of a single sample at a time ("Sample Mode"). The knobs can be used to mangle the playback of the sample in some fun ways. Pressing D#4 engages sample mode, which acts as a kind of loop pedal, using whichever sample was played or recorded last. If there are no samples recorded, it will start recording one for the length specified by knob2 ("grain size"). Once the sample is recorded, Sample Mode will engage.
2. Chop is also equipped with Chop mode, which, when engaged, will start randomly shuffling between the live sound going into the Organelle, and up to four recorded samples. If no recorded samples are present, it'll start recording samples one at a time, for the length specified by knob2 ("Grain Size"). Once each sample is recorded, Chop Mode will engage.

#### buttons
        B5  - sample mode on/off
    A#5     - chop mode on/off
        A5  - reverse play direction of current sample
    G#5     - 
        G5  - record sample 3
    F#5     - record sample 4
        F5  - shift

and, with shift engaged:

        B5  - delete all samples
    A#5     - 
        A5  - 
    G#5     - 
        G5  - 
    F#5     - 
        F5  - shift

#### knobs

    - knob1: playhead start position
    - knob2: grain size (percentage of sample to play [while recording a sample, this knob specifies how long to record for - max 5 seconds])
    - knob3: playback speed
    - knob4: tempo of playhead movement in BPM (0 = playhead does not move, 100 = playhead skips around randomly at the rate of 256th notes)

and, with shift engaged:

    - shift + knob1:
    - shift + knob2:
    - shift + knob3: playback pitch
    - shift + knob4: tempo of playhead movement in MS (0 = no movement, 100 = idk hella fast)




# dev notes for me while I figure this shit out

https://www.critterandguitari.com/manual?m=Organelle_Manual#7-additional-info
