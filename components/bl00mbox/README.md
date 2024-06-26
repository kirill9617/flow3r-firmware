bl00mbox is a modular synthesizer engine designed for 32bit microcontrollers. At this point in time it is running exclusively on the ccc2023 badge "flow3r", but we intend to branch out to other devices soon.

At this moment the only recommended API is written in micropython, there are C bindings but they are a pain, we will probably add a C++ API when we get around to it. It is not quite ready yet to run on other hardware in general though due to limitations in sample rate and buffer size.

# stability

This software is generally in a very early stage, API-breaking changes and deprecations are still happening regularily, but since it is already running on at least 1 user-facing device we try to keep it at a minimum. Due to this incentive to change things ideally only once a bunch of this software is not where we'd like it to be.

Any API not documented in here is unstable. One noteworthy case is the `.table` member of plugins; accessing it directly used to be commonplace, now we always wrap access in helper functions. If you explore the members of objects in the REPL there are plenty non-hidden ones that are not intended for direct use, but we can't quite delete them yet due to backwards compatibility - we'll figure something out there.

# table of contents

1. [usage](#usage)
    1. [basic concepts](#basic_concepts)
    2. [creating channels and plugins](#creating_channels_and_plugins)
    3. [setting a signal to a static value](#static_value)
    4. [signal types](#signal_types)
    5. [connecting signals](#connecting_signals)
    6. [channel management](#channel_management)
    7. [dead ends and circular connections](#dead_circ)
    8. [working in the repl](#work_repl)
2. [plugins](#plugins)
    1. [tone generators](#tone_generators)
        1. [noise](#noise)
        2. [noise\_burst](#noise_burst)
        3. [osc](#osc)
        4. [sampler](#sampler)
    2. [signal processors](#signal_processors)
        1. [env\_adsr](#env_adsr)
        2. [mixer](#mixer)
        3. [filter](#filter)
        4. [distortion](#distortion)
        5. [delay\_static](#delay_static)
        6. [flanger](#flanger)
    3. [control signal utilities](#ctrl_utils)
        1. [range\_shifter](#range_shifter)
        2. [multipitch](#multipitch)
    4. [trigger handlers](#trigger_handlers)
        1. [sequencer](#sequencer)
        2. [poly\_squeeze](#poly_squeeze)
    5. [deprecated plugins](#deprecated_plugins)
        1. [osc\_fm](#osc_fm)
        2. [ampliverter](#ampliverter)
        3. [lowpass](#lowpass)
        4. [slew\_rate\_limiter](#slew_rate_limiter)
        5. [delay](#delay)
3. [patches](#patches)
4. [examples](#examples)

# usage <a name="usage"></a>

## basic concepts <a name="basic_concepts"></a>

bl00mbox uses plugins as atomic sound generators/processors. These plugins provide signals which can be used to stream audio or control data from one plugin to another. Arbitrary signals may then be routed to the global sound output.

Plugins are grouped into channels so that operating systems can quickly switch between presets and/or mix different sound generators/processors together. Channels are a limited resource, so care must be taken to free them once they are no longer needed.

Audio signals and control signals are in principle intercompatible, but for performance reasons the bandwidth of some signal sinks and sources is limited to a sample rate of about 750Hz (@ 64 samples/buffer).

## creating channels and plugins <a name="creating_channels_and_plugins"></a>

A plugin can be generated as such:

```python
import bl00mbox

# request a new channel named "demo"
blm = bl00mbox.Channel("demo")

# create an instance of the "osc" plugin
osc = blm.new(bl00mbox.plugins.osc)

# connect the output signal of the plugin to the channel mixer
osc.signals.output = blm.mixer
# disconnect it
osc.signals.output = None
```
Here we used the `=` operator to connect signals, more on that later.

Some plugins require additional initialization variables, the mixer for example needs a number of input channels:
```python
mixer = blm.new(bl00mbox.plugins.mixer, 5)
```

## setting a signal to a static value <a name="static_value"></a>


All signals are encoded as integer values from `-32767..32767`. You can assign a fixed value directly to any *[input]* type signal, but to read it you need to use the `.value` member:

```python
# assign a fixed value to a signal and disconnect all sources
osc.signals.morph = -12000
# read the current value
print(osc.signals.morph.value)
```

If the signal is streaming data from an output signal the stream is severed.

*Note: The `signals` member of a plugin is what makes this syntax happen. If signals are accessed by references in other locations, functionality will break.*

```python
# bad code, don't create references of recursive `signals` members
a = osc.signals.wave
# does not work since `__setattr__` of `signals` is bypassed
a = 15
```

## signal types <a name="signal_types"></a>

The mapping between signal value and how it modulates whatever property it affects is basically arbitrary, and you'll find a detailed list below in the plugins section. However, there are a few standardized types that come with special members:

**pitch:** Encoding for musical pitch. A440 is at a value of 18367, a semitone is represented by an increment of 200. Several setters/getters exist:

- `.tone`: Setter/getter for musical pitch as semitone distance from A440.
- `.freq`: Setter/getter for frequency in Hertz.

**gain:** Encoding for volume. A value of 4096 represents a multiplier of 1.

- `.dB`: Setter/getter for volume in dB
- `.mult`: Setter/getter for volume in expressed as a multiplier.

**trigger:** This signal type processes events.

Normally you'd only connect trigger signals to other signal triggers or use them directly, but for completion's sake here is the encoding: A change from 0 to any other value is a *start event* with abs(value) as a velocity parameter, a change from a nonzero value to a nonzero value of opposite sign is a *restart event*, and a change from a nonzero value to 0 is a *stop event*. This means a 0-biased square wave will continuously generate restart events.

- `.start(velocity = 32767)`: Generate a (re-) start event. Velocity is optional and must be within 1..32767.
- `.stop()`: Generate a stop event.

For example, to set the pitch of one oscillator to the pitch of another plus an octave:

```python
osc1.signals.pitch.tone = osc2.signals.pitch.tone + 12
```

**switched/semi-switched:** This signal type has discrete named value markers stored in the `switch` member. Switched signals typically interpret their value as rounded to the nearest marker while semi-switched signals allow for values in-between. The markers are subclassing `int` and return their value when accessed, but a special setter allows them to be applied to the signal directly by setting them to `True`.

```python
# selecting the square wave
osc.signals.wave.switch.SQUARE = True
# using the integer values to interpolate between neighbors
mixed = (osc.signals.wave.switch.TRI + osc.signals.wave.switch.SINE)/2
osc.signals.wave = mixed
```

*Note: In case of a binary switch you might be tempted to assume that setting one marker to `False` activates the other. This is NOT the case.*

**list-type signal:** Some signals come as lists. Unlike other signals we denote them by adding `[]` to their name without whitespace in this guide. They are used like any other signal with the addition of requiring an index parameter:

```python
# connect and assign values as usual
mixer.signals.input[0] = env_adsr0.signals.output
mixer.signals.input_gain[0].dB = -3
mixer.signals.input[1] = env_adsr1.signals.output
mixer.signals.input_gain[1].dB = -3

# better: put envelope generators in list and iterate
for x in range(5):
    mixer.signals.input[x] = env_adsr[x].signals.output
    mixer.signals.input_gain[x].dB = -3
```

As a final note: What if you need the value that a certain conversion, `.freq` for example, would generate? We wanted to bring helper functions for that into this release but we plain forgot. `bl00mbox.helpers` exists but we don't even know what's in there right now. Best of luck, cya at the next update :3!

## connecting signals <a name="connecting_signals"></a>

A connection can only be made between an input and an output type signal:

```python
# connecting an input to an output...
env_adsr.signals.input = osc.signals.output
# ...or an output to an input!
env_adsr.signals.env_output = osc.signals.morph
# the channel mixer is an input type signal:
env_adsr.signals.output = blm.mixer
# listen :D
env_adsr.signals.trigger.start()
```

An output signal can fan out to arbitrary many inputs, but an input may only receive data from a single source, attempting to assign a different source or static value to it will result in the exiting connection being severed. A signal may also be disconnected by setting it to `None`, in which case an input signal will fall back to its last static value.

An exception to the rule is the channel mixer; you can connect as many signals as you want to it, but you can only disconnect them source-side. *We're not quite sure if we're gonna keep the mixer around in its current form anyways, so we'll just keep it inconsistent for now until we've figured out what we want.*

```python
# connects normally
env_adsr1.signals.output = blm.mixer
# exception to the rule: both are connected and summed
env_adsr2.signals.output = blm.mixer
# does not work
blm.mixer = None
# works, but also disconnects all other sinks from the signal
env_adsr2.signals.output = None
# there's really no clean way to do this atm :/
```

## channel management <a name="channel_management"></a>


Channels are a limited resource. Also they are not garbage collected and happily live on in the backend no matter the state of the frontend. These are intentional design decisions which bring some advantages but also require discipline from the user to free resources when they're done with them:

```python
# create a new channel and a plugin
blm = bl00mbox.Channel("demo")
osc = blm.new(bl00mbox.plugins.osc)

# set channel volume (1..32767)
blm.volume = 2000

# clear all plugins from the channel
blm.clear()

# osc is now a stale reference and the following will fail:
osc.signals.output = blm.mixer

# mark the channel as free so that it can be passed to the
# next caller of bl00mbox.Channel()
blm.free = True

# best to not use that reference anymore to not interfere
# with other applications that now might use it
blm = None
```

bl00mbox does some basic automatic channel management under the hood. Most importantly, there is no more than one channel which is *foregrounded*. By default, only the foreground channel is rendered, all others are waiting in memory until their foreground time has come. By default, the engine foregrounds whichever channel was *last interacted with*; this prevents people from forgetting foregrounding and waiting in silence. In the future we'll add a config option for fully manual switching too.

Backgrounded channels may render as well using the `background_mute_override` option, so that a simple setup could look like this:

```python
drums = bl00mbox.Channel("drums")
# [skipped: build some auto-drum patch, beat is now playing]

lead = bl00mbox.Channel("lead")
# "drums" is now paused since "lead" took the foreground

lead.foreground = False
# "drums" is still silent, nothing is in foreground

drums.background_mute_override = True
# "drums" starts playing in background

# "drums" is in foreground again
drums.foreground = True
drums.background_mute_override = False
```

## dead ends and circular connections <a name="dead_circ"></a>

bl00mbox does not render all plugins in an active channel at all times. A plugin is rendered exactly when another plugin uses it as a source. For example:

```python
# assume these are instances of plugins of the same name in vanilla state:
bl00mbox_line_in.signals.mid = sampler.signals.record_input
sampler.signals.record.trigger.start()
# this will never record anything as nobody requests data from the sampler.
```

This behavior is intended as it can be used to efficiently shut down a whole network of plugins from a single plugin that is set to mute for example, however as shown above it sometimes can have unintended side effects. A simple solution could be:

```python
mixer.signals.input[0] = sampler.signals.playback_output
mixer.signals.input_gain[0].mult = 0 # mute
mixer.signals.output = blm.mixer
```

This is far from elegant and we'll come up with something better in the future :D.

As a redeeming quality the rendering engine has a trick up its sleeve:

```python
osc.signals.output = range_shifter.signals.input
range_shifter.signals.output_range[0] = -10
range_shifter.signals.output_range[1] = 10
osc.signals.fm = range_shifter.signals.output
```

Circular dependencies are generally allowed, but they do come with a grain of salt: If the rendering engine finds itself at the situation where during the render of a plugin data from the same plugin is being requested, it simply uses data from the last render cycle! This of course means that there is suddenly a buffer-length delay (i.e., 4/3 ms) in the feedback loop which means the feedback-fm topology above has a pitch-dependent waveform, but it's better than not having the feature at all so we just went for it :P. *Tip: use feedback loops in conjunction with filters and distortion to create sounds that are truly "out there".*

## working in the repl <a name="work_repl"></a>


bl00mbox has a few features that make repl work nice and easy, albeit there being some or the other quirk. First and foremost the `__repr__` of plugins, patches and channels shows generally useful information. Try:

```python
blm = bl00mbox.Channel("demo")
osc = blm.new(bl00mbox.plugins.osc)
# just hit enter to show `__repr__`
blm
osc
```

Ever wondered why we give those channel names? Channel management is still very underwhelming, but here's a useful trick: Since all data lives in the backend, you can run a python script that spawns a channel, then Ctrl-C out of it, summon the abandoned channel and start playing with the debris!

```python
# retrieve a channel by ID number
blm = bl00mbox.Channel(1) # NEVER EVER DO THIS IN AN APPLICATION WE'LL haunt YOU
# check repr if it's the channel u wanted
blm
# if no, get next
blm = bl00mbox.Channel(2) # SRSLY DON'T
blm
# if yes: check plugins!
[print(x) for x in blm.plugins]

# note: the plugin number that is given by the plugin repr does not 
# represent the index in the blm.plugins list! we'll upgrade this someday.
# it's not really a production code feature yet, but rather a tiny backdoor
# to figure out what's down with the up.

# you can now mess with plugins as usual. ideally do give them names tho :P
blm.plugins[0].signals.gain = blm.plugins[1].signals.pitch_out
```

# plugins <a name="plugins"></a>

## tone generators <a name="tone_generators"></a>

### noise <a name="noise"></a>

provides flat-ish pseudorandom data from a xoroshiro generator.

###### signals

- `output [output]`: full range random data signal.
- `speed [input/switched]` *(default: AUDIO)*: **LFO** (-32767): `output` provides constant buffers; **AUDIO** (32767): `output` provides random data for each individual sample.

---

### noise\_burst <a name="noise_burst"></a>


similar to **noise**, but stops after a specified amount of time. low-cpu alternative to hooking up a full **env_adsr**. *might add a lightweight filter here at some point depending on how the yet-unfinished 1st order mode of* **filter** *performs, there's a good amount of common use cases.*

###### signals

- `output [output]`: full range random data signal.
- `trigger [input/trigger]`: upon receiving a start signal: plays flat-ish noise at max sample rate until a stop signal is received or the time given by `length` has passed.
- `length [input]` *(unit: ms, default: 100ms)*: specifies length of noise burst. the value is only read when `trigger` receives a start signal, but sends render request to source regardless. values above 0 result in resetting `output` to 0 when the burst is over, else the last random `output` value is being held until `trigger` receives the next start signal. At a value of 0 a single random datapoint is produced.

---

### osc <a name="osc"></a>


basic oscillator building block with modulation options.

###### signals

- `output [output]`: continuously outputs a full range wave. *note: thru-zero fm and hard sync may result in outputs that do not cover the full value range in some cases*
- `pitch [input/pitch]` *(default: 440Hz)*: sets the basic pitch of the oscillator.
- `waveform [input/semi-switched]` *(default: TRI)*: linearily blends between different waveforms. available waveforms: SINE (-32767), TRI (-10922), SQUARE (10922), SAW (32767).
- `morph [input]` *(default: 0)*: stretches/compresses the waveform in each "half" so that the midpoint is shifted relative to the signal value.For the square wave is equivalent to PWM, for example a value of -32767/2 is equivalent to 25% pulse width. at this point in time the signal is clamped to a value that rises with `pitch` to avoid aliasing issues. this is not the ideal solution (and can be bypassed with `fm`), we will probably reconsider this at some point.
- `fm [input]` *(default: 0)*: allows thru-zero linear frequency modulation. the frequency multiplier is ((*signal value*)/8192) + 1 so that the full range represents a multiplication range of ]-3..5[.
- `sync_input [input/trigger]`: used for hard syncing: upon receiving a start signal the oscillator phase is reset to whichever value is provided by `sync_input_phase`. at this point in time there is no anti-aliasing, but we intend to change this in the next major upgrade. stop signals are ignored.
- `sync_input_phase [input]` *(default: 0)*: phase used by `sync_input`. ignored if no triggers are received, but always sends a render request to its source. A phase of 0 is equivalent to the "middle point" of a sawtooth. *note: the other waveforms are generally aligned so that the fundamental is in phase.*
- `sync_output [output/trigger]`: sends a trigger signal each time the oscillator passes the equivalent of the sawtooth midpoint. can be used to hard sync other oscillators or periodically trigger other events. at this point in time always outputs a max volume trigger, but we intend to encode the subsample phase for antialiasing purposes in the last few bits at some point in the future so there will be hopefully inaudible volume variations. keep this in mind when using this signal for more numerical purposes.
- `speed [input/switched]` *(default: AUTO)*: **LFO** (-32767): the oscillator generates a constant sample for each buffer. useful for CPU-efficient modulators or bass sounds, ideally with subsequent low pass filtering. **AUTO** (0): switches between LFO and AUDIO based on `pitch`. the switching point is around 20Hz-ish. **AUDIO** (32767): generates samples at the full audio sample rate.

###### members

- `.wave`: read-only 64-tuple of total waveshape (`morph` + `waveform` + antialiasing), kinda. currently rigged as a lightweight debug output: during each buffer, a single sample is written to this output, so that the tuple not only takes some time to catch up with the actual waveshape, but also in some conditions (harmonic relationship between buffer rate and osc period, hardsync, thru-zero fm) some parts of the tuple **may never be updated** and contain garbage data. when modulating the waveform very fast you'll see a lot of noise. we could replicate the waveform generator in python, but that's not ideal and we're not gonna go for it. at some point radspa will provide some sort of variadic function interface to micropython which will solve this very elegantly, so we rather focus on getting there instead even though it'll take some time.

---

### sampler <a name="sampler"></a>


*note: unlike the old sampler patch this one does not have flow3r-specifc paths built in, you need to pass the full path for every file operation. also we renamed the signals to be more consistent*

a simple fixed buffer size sampler that can load and save int16 *.wav* files. can be initialized either with a sample buffer length in milliseconds at 48kHz sample rate or a filename, in which case the sample buffer length is automatically is set to just so fit the file:

```python
sampler_empty_3seconds = blm.new(bl00mbox.plugins.sampler, 3000)
sampler_preloaded = blm.new(bl00mbox.plugins.sampler, "/flash/sys/samples/kick.wav")
```

the sample buffer size does **not** change size dynamically. when loading a file into an already initialized sample buffer it will be cropped if it doesn't fit. when recording time exceeds the sample buffer length it keeps the most recent data only.

###### signals

- `playback_output [output]`: outputs the sample buffer contents if playback is active, else 0. provides constant buffers if idle or the sample rate is below 1kHz, else buffers are never constant.
- `playback_trigger [input/trigger]`: replay trigger, handles start, stop and restart events as expected and honors volume of trigger event.
- `playback_speed [input/pitch]` *(default: 0 semitones): replay speed of playback. `.tone = 0` is original pitch. does not affect recording. requests source render only if playback is active.
- `record_input [input]` *(default: 0)*: requests source render only when recording.
- `record_trigger [input/trigger]`: handles start, stop and restart events as expected but ignores volume of trigger event. there's one caveat to be aware of: as input processing is part of rendering, the sampler cannot record if no other plugin or the channel mixer requests rendering. in practice, this means you should connect `output` to the channel mixer in some "uninterruptable" way (like, no **env_adsr** or the likes that can choose to not render their sources when idle). the sampler idles with fairly low load, so this is typically fine. this will be nicer somewhere down the line, please bear with it for a little while.

###### members

- `.load(filename: str)`: attempts to load a mono or stereo int16 *.wav* file from the absolute path and sets the appropriate `.sample_rate`. it supports up/downsampling, but audio quality is best if the file has the native sample rate. if the buffer can't contain it completely the end is cropped. raises a `Bl00mboxError` if the file format can be handled by the wave library but can't be processed by the plugin.
- `.save(filename: str)`: attempts to save the contents of its buffer as delimited by the start/end flags to an int16 *.wav* file at the absolute path.
- `.sample_rate: int` *(unit: Hz, default: 48000)*: read/write sample rate that the plugin uses to interpret its buffer contents during playback and recording. All signals switch into constant buffer mode if the sample rate is below 100Hz so that the sampler can be used to efficiently store and replay modulation data. Gets clamped below 1.
- `.sample_length: int`: length of last recorded/loaded sample buffer contents, read-only.
- `.buffer_length: int`: length of sample buffer, read-only.
- `.playback_progress: None/float`: read-only. `None` if sampler is not playing, else position of read head relative to `sample_length`, range [0..1[
- `.playback_loop: bool` *(default: False)*: read/write. if false playback automatically stops after reaching the end of the sample, else it loops the sample forever.
- `.record_progress: None/float`: read-only. `None` if sampler is not recording, else position of write head relative to `sample_length`, range [0..1[
- `.record_overflow: bool` *(default: True)*: read/write. if false recording automatically stops when the sample buffer is full, else the oldest data is overwritten.

## signal processors <a name="signal_processors"></a>


### env\_adsr <a name="env_adsr"></a>

generates a linear ADSR envelope and optionally applies a version with "squared" slopes to a signal.

###### signals

- `output [output]`: provides a version of `input` with `env_output` applied, however the transition phases are modified with a square function to achieve a CPU-cheap log-ish behavior. lerps between `env_output` cornerpoints to minimize zipper noise. constant buffer if `input` is a constant buffer or if the envelope is idling.
- `input [input]`: signal to be sent to `output` with `env_output` applied. source render is only requested if envelope is not idling and `gain` is not 0.
- `env_output [output/lazy/gain]`: provides a constant buffer with the current gain value of the envelope scaled by last event volume received by `trigger` as well as `gain`.
- `trigger [input/lazy/trigger]`: processes start, stop and restart events as expected and honors event volume.
- `attack [input/lazy]` *(unit: ms, default: 100)*: linear attack time of the envelope. sign is dropped.
- `decay [input/lazy]` *(unit: ms, default: 250)*: linear decay time of the envelope. sign is dropped.
- `sustain [input/lazy]` *(unit: x1/32768, default: 16000)*: sustain target of the envelope. sign is dropped. nonzero sustain means a note keeps ringing forever until receiving a stop event, zero sustain means it mutes after the attack and decay phases.
- `release [input/lazy]` *(unit: ms, default: 50)*: linear release time of the envelope. sign is dropped.
- `gain [input/lazy]` *(default: 0dB)*: overall gain of the envelope.

---

### mixer <a name="mixer"></a>

mixes several input signals together. initialize with `num_channels` as addtional argument (defaults to 4 if not provided, allowed range [1..127]):

```python
mixer = blm.new(bl00mbox.plugins.mixer, 2)
```

###### signals

- `output [output]`: mix of all inputs with corresponding gain applied.
- `gain [input/gain]` *(default: x1/num\_channels)*: global gain of mixer.
- `block_dc [input/switched]` *(default: OFF)*: **ON** (32767): block dc below audio frequencies (10Hz-ish, we forgot); **OFF** (-32767): don't apply any filtering.
- `input[num_channels] [input]` *(default: 0)*: signals to be mixed together.
- `input_gain[num_channels] [input/gain]` *(default: 0dB)*: gains of individual input signals.

---

### filter <a name="filter"></a>


a collection of second-order filters.

*note: if you're unfamiliar with filters, here's a visualization aid: https://www.earlevel.com/main/2021/09/02/biquad-calculator-v3/*

###### signals

- `output [output]`: outputs a mix of the filtered and unfiltered `input` signal.
- `input [input]` *(default: 0)*: input for signal to be filtered.
- `cutoff [input/pitch]` *(default: 440Hz)*: sets cutoff frequency of the filter type. see `mode` for details.
- `reso [input]` *(unit: 4096\*Q, default: 1Q)*: resonance of the filter. low values (<0.7Q) result in a soft attenuation knee, medium values (<3Q) result in a boost around cutoff and a sharper transition into the attenuation zone, high values may cause self-oscillation. at negative values the filter switches into allpass mode. *note: absolute values below 684 are clamped at this point in time. we are considering using this region for first order filters in the future, so please avoid actively using this clamp if reasonably possible.*
- `gain [input/gain]` *(default: 0dB)*: gain of both wet and dry output of the filter. loud signals in combination with high Q can lead to clipping which can be solved by reducing this value.
- `mix [input]` *(default: 32767)*: blends between the original "dry" input signal (fully dry at 0) and the filtered "wet" signal (fully wet at 32767). for negative values the wet signal is inverted while the dry signal isn't, allowing for phase cancellation experiments.
- `mode [input/semi-switched]` *(default: LOWPASS)*: selects between different filter types. **LOWPASS** (-32767) barely affects frequencies far below the cutoff and progressively attenuates above the resonant peak, **HIGHPASS** (32767) does the same with higher/lower frequencies flipped. **BANDPASS** (0) only allows signals around the cutoff to pass. A bandblock can be achieved by setting `mix` to -16384. If `reso` is negative the transformation *wet = dry - 2\*wet* is applied to create an equivalent allpass. In-between values interpolate between filter types.

---

### distortion <a name="distortion"></a>

Wavetable distortion with fixed length 129 entry list. At this point there is no antialiasing but we'll add an antiderivative approximation soon.

It was quite common to use the generic `.table` property directly with this plugin, however direct access to this member is being deprecated across all plugins and we'd ask you to use `.curve` instead. In return you get a cute repr.

###### signals

- `output [output]`: output of linearily interpolated wavetable.
- `input [input]` *(default: 0)*: represents fractional index of wavetable when scaled to 0..128

###### members

- `.curve: list[int]`: The wavetable of the distortion. Always returns the full 129 entry list, but has a special setter that takes lists of arbitrary length and interpolates to generate a reasonably equivalent 129 entry list.
- `.curve_set_power(power: float = 2, volume: int = 32767, gate: int = 0)`: fills the wavetable with two power functions smoothly stitched together at the origin. `power > 1` yields compressing distortion, `0 < power < 1` yields expanding distortion. `volume` sets the maximum value. `gate > 0` results in the wavetable filled with zeros so that input values roughly up to the `gate` value result are suppressed (the math is a bit janky in the current release, rushed that one a little bit, will be more precise soon).

---

### delay_static <a name="delay_static"></a>


simple delay. is currently also available as `delay`, but since we want to switch it to use proper gain-type signals in the next update the `delay` plugin will be overwritten while the `delay_static` will remain stable for a few more versions for a smoother transition, so don't use the `delay` plugin for now. the suffix is chosen as it currently the time setting is very coarse and doesn't allow for smooth modulation. this will be fixed in the upcoming `delay` plugin as well.

initialize with the maximum desired delay time in ms (range: 1-10000, default: 500):

###### signals

- `output [output]`: provides a mix of a delayed "wet" and the original "dry" version of `input`. never a constant buffer at this point in time, but will be in the future.
- `input [input]` *(default: 0)*: input to be delayed.
- `time [input]` *(unit: ms, default: 200)*: delay time.
- `feedback [input]` *(unit: 1/32768, default: 16000)*: how much of the delayed signal is mixed back into the delay generator's input. sadly not a gain-type signal so the unit is weird.
- `level [input]` *(unit: 1/32768, default: 16000)*: output volume applied to the wet signal. weird unit again.
- `dry_vol [input]` *(unit: 1/32768, default: 32767)*: output volume applied to the dry signal. actually *ampliverter* uses the same bad unit.
- `rec_vol [input]` *(unit: 1/32768, default: 32767)*: volume applied to the dry signal before it is mixed with the feedbacked wet signal and fed to the delay generator. we were under a lot of time pressure back then, if this doesn't have unity gain it's because neither did we personally when we wrote it.

---

### flanger <a name="flanger"></a>

basic flanger with subsample interpolation and karplus-strong resonator support. not ideal for chorus due to a lack of time-linear modulators, but might add one in the future (or make a new one to get rid of the silly `resonance` unit).

###### signals

- `output [output]`: provides a mix of a resonant comb filtered "wet" and the original "dry" version of `input`. never a constant buffer at this point in time, but will be in the future.
- `input [input]` *(default: 0)*: input to be filtered.
- `manual [input/lazy/pitch]` *(default: 440Hz)*: sets delay time of flanger to match one period of the desired frequency.
- `resonance [input/lazy]` *(unit: x1/32768, default: 2048)*: base feedback applied to flanger, may be modulated by `manual` via `decay`. stops just before self-oscillation. was tagged as a gain signal but doesn't act as one, our bad. gonna stick with it for now tho.
- `decay [input/lazy]` *(unit: ms/6dB, default: 0)*: if `resonance` is set to 0 this adjusts resonance depending on `manual` to result in a roughly constant pulse decay. negative values do not result in volume growth but instead flip the sign of feedback applied, results may vary. may be used in conjuction with `resonance` to create custom tapers.
- `level [input/lazy/gain]` *(default: 0dB)*: overall gain of the flanger.
- `mix [input/lazy]` *(default: 16384)*: blends between dry and wet. at 0 the signal is fully dry, negative values flip the phase of the wet signal but not of the dry signal.

## control signal utilities <a name="ctrl_utils"></a>

### range\_shifter <a name="range_shifter"></a>


takes an arbitrary non-trigger `input` and applies a linear transformation so that the `input_range[0,1]` points are mapped to their respective and `output_range[0,1]` counterparts.

###### signals

- `input [input]` *(default: 0)*: input to which the linear transformation is applied.
- `input_range[2] [input]` *(default: [0] = -32767, [1] = 32767)*: defines 2 points that are mapped to their `output_range[]` counterparts. if both values are identical `output` is the average of `output_range[]`.
- `output [output]`: linear transformation of input. not clamped to `output_range[]`. is a constant buffer if all other signals are constant buffers or treated as such (see `speed`).
- `output_range[2] [input]` *(default: [0] = -32767, [1] = 32767)*: defines 2 points that are mapped to their `input_range[]` counterparts. if both values are identical `output` is always this value.
- `speed [input/switched]` *(default: FAST)*: may force `output` to provide a constant buffer. **FAST** (32767): treat all other signals as they are. **SLOW_RANGE** (0): treat `input_range[]` and `output_range[]` as constant buffers and `input` as it is. **SLOW** (-32767): treat all other signals as constant buffers.

---

### multipitch <a name="multipitch"></a>


generates pitch-shifted and -limited copies of a pitch input. all outputs are constant buffers. initialize with `num_channels` as a positional argument (defaults to 0 if not provided, allowed range [0..127]):

###### signals

- `input [input/pitch]` *(default: 440Hz)*: input pitch which is processed and forwarded to `thru` and `output[]`.
- `thru [output/pitch]`: copy of `input`, but reduced to a constant buffer and octave-shifted to fit in the range given by `max_pitch` and `min_pitch`.
- `trigger_in [input/trigger]`: gets forwarded to `trigger thru` and reduced to a constant buffer
- `trigger_thru [output/trigger]`: copy of `trigger in` and reduced to a constant buffer if
- `mod_in [input]` *(default: 0)*: pitch modulation input that first gets reduced to a constant buffer and scaled according to `mod_sens` and then applied to `output` and `thru`.
- `mod_sens [input]` *(unit: +-1oct/fullswing/4096 default: +-1oct/fullswing)*: sensitivity of `mod_in`.
- `max_pitch [input/pitch]` *(default: 7040Hz, 4 octaves above A440)*: maximum pitch for `thru` and `output[]`. doesn't clamp but only shifts by octaves. if smaller than `min_pitch` they get flipped in the entire calculation.
- `min_pitch [input/pitch]` *(default: 27.5Hz, 4 octaves below A440)*: minimum pitch for `thru` and `output[]`. if less than an octave below `max_pitch` the limit does not apply so that pitch limiting always results in octave shifts.
- `output[num_channels] [output/pitch]`: outputs a copy of `input` shifted by the pitch indicated by `shift[]` of the same index and octave-shifted to fit in the range `max_pitch and `min_pitch`.
- `shift[num_channels]` [input/pitch]` *(default: 0 semitones)*: determines the amount of pitch shifting applied to the respective output.

## trigger handlers <a name="trigger_handlers"></a>


### sequencer <a name="sequencer"></a>

TODO (no changes from old version tho)

---

### poly\_squeeze <a name="poly_squeeze"></a>


Multiplexes a number of trigger and pitch inputs into a lesser number of trigger pitch output pairs. In the typical use case all outputs are connected to identical signal generators.

Initialize with `num_outputs` (range: [1..16], default: 3) and `num_inputs` (range: [`num_outputs`..32], default 10) as positional arguments:

###### signals

- `pitch_in[num_inputs] [input/pitch]` *(default: A440)*: pitch of the respective input. if the input is internally connected to an output the pitch data is constantly streamed, allowing for modulation.
- `trigger_in[num_inputs] [input/trigger]`: the latest triggered inputs are internally connected to a disconnected output, or, if none exists, to the output with the oldest internal connection. if such an input receives a stop trigger and another input is in triggered state but not internally connected it will be internally connected to that output and the output is triggered. *note: if more signals are triggered during a single buffer than are available as outputs the ones with the lowest indices will be dropped. in a future version this will mitigated to only occur when it's during a single sample instead.*
- `pitch_out[num_outputs] [output/pitch]`: pitch of a respective output. if the output is not connected the last connected pitch will be held. Always constant buffer.
- `trigger_out[num_outputs] [output/trigger]`: sends out a start event if the output is internally being connected to a new source or a stop event if it is being disconnected. Always constant buffer.

## deprecated plugins <a name="deprecated_plugins"></a>


all of these will be removed with the flow3r 2.0 firmware release.

### osc\_fm <a name="osc_fm"></a>


deprecation reason: was created before switched signals were a thing, some application examples have used a "shorthand" of using say -1 and 0 to switch between triangle and square, can't be unified with wave blending approach. also the whole fm\_thru thing was kinda weird.

### ampliverter <a name="ampliverter"></a>


deprecation reason: was created before the `gain` signal type existed, its gain signal is not a `gain` signal, can't change it without breaking everything that uses it. replacement: `range_shifter` (more for control signal kinda stuff), `mixer` (more for audio signal kinda stuff, can be used as volume control with a single channel).

### lowpass <a name="lowpass"></a>


deprecation reason: didn't use `pitch` input signal type for cutoff, and also a more universal filter plugin made more sense and the name just doesn't work for that. replacement: `filter`.

### slew\_rate\_limiter <a name="slew_rate_limiter"></a>


deprecation reason: early hack for very low cpu load filtering, used only a few times but didn't bother do delete it, not very well made, aliasing issues and sample rate dependent slew rate signal. no replacement yet, but nobody uses it anyways. will probably make a nonlinear filter that can do the same trick some day, but not sure yet what's a good feature set. **filter** should have you covered to get close enough.

### delay <a name="delay"></a>

still exists as `delay_static` for now but has issues as described there.

# patches <a name="patches"></a>

confession time: when this was very young software but a release was necessary we did not have the infrastructure to attach arbitrary functions to individual plugins, so we misappropriated patches for this. the situation has been fixed, but many existing patches are deprecated now for this reason, specifically `fuzz`, `sampler` and `sequencer`.

furthermore we made the mistake of not specifying stable/unstable surfaces so that we find ourselves in the sad situation where we would be able to improve patches but find ourselves unable to do so since users may have hooked up signals to the internal structure.

with this in mind, you could say that from a general point of view **all existing patches are deprecated**. the only exceptions at this point are `tinysynth` and `tinysynth_fm`, but their internal structure will be modified in the next major update - if your application accesses anything in the `.plugins` attribute, please create a local copy of the patch in your application, else it's destined to break.

# examples <a name="examples"></a>

Feedbacked filter (needs kickstart for self-oscillation):

```python
import bl00mbox
blm = bl00mbox.Channel()
f = blm.new(bl00mbox.plugins.filter)
m = blm.new(bl00mbox.plugins.mixer, 2)
f.signals.output = m.signals.input[0]
f.signals.output = blm.mixer
f.signals.input = m.signals.output

f.signals.gain.dB = 18
f.signals.mode.switch.BANDPASS = True
f.signals.cutoff.tone = -1
f.signals.reso = -12000
f.signals.mix = -18000
m.signals.input_gain[0].dB = 18
m.signals.gain.dB = 18

# kickstart
m.signals.input[1] = 32767
```
