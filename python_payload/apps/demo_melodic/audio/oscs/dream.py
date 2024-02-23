import bl00mbox
import math
from ui.pages.synth import *


class dream_osc(bl00mbox.Patch):
    name = "dream"

    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.mixers = [
            self._channel.new(bl00mbox.plugins.mixer, 1) for _ in range(2)
        ]
        self.plugins.dists = [
            self._channel.new(bl00mbox.plugins.distortion) for _ in range(2)
        ]
        self.plugins.mix_ranges = [
            self._channel.new(bl00mbox.plugins.range_shifter) for _ in range(2)
        ]
        self.plugins.out_mixer = self._channel.new(bl00mbox.plugins.mixer, 2)
        self.plugins.osc.signals.waveform.switch.SINE = True

        for i in range(2):
            self.plugins.dists[i].signals.input = self.plugins.mixers[i].signals.output
            self.plugins.osc.signals.output = self.plugins.mixers[i].signals.input[0]
            self.plugins.dists[i].signals.output = self.plugins.out_mixer.signals.input[
                i
            ]
            self.plugins.mix_ranges[
                i
            ].signals.output = self.plugins.out_mixer.signals.input_gain[i]
            self.plugins.mix_ranges[i].signals.output_range[1] = 0
            self.plugins.mix_ranges[i].signals.output_range[0] = 8192

        self.plugins.dists[0].curve = [
            32767 * math.sin((math.tau * 5) * (0.1 + (x / 128) ** 2))
            for x in range(129)
        ]
        self.plugins.dists[1].curve = [
            32767 * math.sin((math.tau * 5) * (0.225 + (x / 128) ** 3))
            for x in range(129)
        ]
        self.plugins.mix_ranges[1].signals.input_range[0] = 0
        self.plugins.mix_ranges[1].signals.input_range[1] = 8192
        self.plugins.mix_ranges[1].signals.input = self.plugins.mix_ranges[
            0
        ].signals.output

        self.signals.pitch = self.plugins.osc.signals.pitch
        self.signals.output = self.plugins.out_mixer.signals.output

    def make_page(self):
        page = ParameterPage(self.name, self)
        param = Parameter(
            [self.plugins.mixers[0].signals.input_gain[0]],
            "shine",
            0.5,
            [4096 * 0.2, 4096],
            modulated=True,
        )
        page.params += [param]
        param = Parameter(
            [self.plugins.mix_ranges[0].signals.input],
            "mix",
            0.5,
            modulated=True,
        )
        page.params += [param]
        param = Parameter(
            [self.plugins.mixers[1].signals.input_gain[0]],
            "shimmer",
            0.5,
            [4096 * 0.2, 4096],
            modulated=True,
        )
        page.params += [param]
        return page
