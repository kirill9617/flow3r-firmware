import bl00mbox
import math
from ui.pages.synth import *


class acid_osc(bl00mbox.Patch):
    name = "acid"

    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.oscs = [self._channel.new(bl00mbox.plugins.osc) for i in range(3)]
        self.plugins.ranges = [
            self._channel.new(bl00mbox.plugins.range_shifter) for i in range(3)
        ]
        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, 4)
        self.plugins.noise_burst = self._channel.new(bl00mbox.plugins.noise_burst)
        self.plugins.noise_burst.signals.length = 0
        self.plugins.noise_burst.signals.trigger = self.plugins.oscs[
            0
        ].signals.sync_output
        self.plugins.noise_burst.signals.output = self.plugins.mixer.signals.input[3]

        for i in range(3):
            self.plugins.oscs[i].signals.output = self.plugins.mixer.signals.input[i]
            self.plugins.oscs[i].signals.waveform = self.plugins.ranges[
                0
            ].signals.output
            self.plugins.oscs[i].signals.speed.switch.AUDIO = True
            self.plugins.mixer.signals.input_gain[i] = 15201
        for r in self.plugins.ranges:
            r.signals.speed.switch.SLOW = True

        max_detune_ct = 50
        min_detune_ct = 0.5

        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 3)
        self.plugins.ranges[1].signals.output_range[0] = 18367 + min_detune_ct * 2
        self.plugins.ranges[1].signals.output_range[1] = 18367 + max_detune_ct * 2
        self.plugins.ranges[2].signals.input_range[0] = 18367 + min_detune_ct * 2
        self.plugins.ranges[2].signals.input_range[1] = 18367 + max_detune_ct * 2
        self.plugins.ranges[2].signals.output_range[0] = 18367 - min_detune_ct * 2
        self.plugins.ranges[2].signals.output_range[1] = 18367 - max_detune_ct * 2
        self.plugins.ranges[2].signals.input = self.plugins.ranges[1].signals.output

        for i in range(3):
            self.plugins.mp.signals.output[i] = self.plugins.oscs[i].signals.pitch
            if i:
                self.plugins.mp.signals.shift[i] = self.plugins.ranges[i].signals.output

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.output = self.plugins.mixer.signals.output

    def make_page(self):
        page = ParameterPage(self.name, self)
        param = Parameter(
            self.plugins.ranges[1].signals.input,
            "detune",
            0.15,
            modulated=True,
        )
        param.default_env_mod = 1
        page.params += [param]
        param = Parameter(
            self.plugins.ranges[0].signals.input,
            "wave",
            0.98,
            modulated=True,
        )
        page.params += [param]
        param = Parameter(
            self.plugins.mixer.signals.gain,
            "dist",
            0.34,
            [367, 32767],
            modulated=True,
        )
        param.default_env_mod = 1
        param.default_lfo_mod = 0.4
        page.params += [param]
        param = Parameter(
            self.plugins.mixer.signals.input_gain[3],
            "noise",
            0,
            [0, 9001],
            modulated=True,
        )
        page.params += [param]
        return page
