import bl00mbox
import math
from ui.pages.synth import *


class beep_osc(bl00mbox.Patch):
    name = "beep"

    def __init__(self, chan):
        super().__init__(chan)

        voices = 3

        self.plugins.detune_osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.detune_osc.signals.waveform.switch.SAW = True

        self.plugins.oscs = [
            self._channel.new(bl00mbox.plugins.osc) for i in range(voices)
        ]
        self.plugins.sync_osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.mps = [
            self._channel.new(bl00mbox.plugins.multipitch, 1) for i in range(voices)
        ]
        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, voices)
        self.plugins.shift_range = self._channel.new(bl00mbox.plugins.range_shifter)

        self.plugins.sync_osc.signals.pitch = self.plugins.mps[0].signals.thru

        for i in range(voices):
            self.plugins.oscs[
                i
            ].signals.sync_input_phase = self.plugins.detune_osc.signals.output
            self.plugins.oscs[i].signals.waveform.switch.SQUARE = True
            self.plugins.oscs[i].signals.pitch = self.plugins.mps[i].signals.output[0]
            self.plugins.oscs[
                i
            ].signals.sync_input = self.plugins.sync_osc.signals.sync_output
            self.plugins.oscs[i].signals.output = self.plugins.mixer.signals.input[i]
            self.plugins.shift_range.signals.output = self.plugins.mps[i].signals.shift[
                0
            ]
            if i:
                self.plugins.mps[i].signals.input = self.plugins.mps[
                    i - 1
                ].signals.output[0]

        self.plugins.shift_range.signals.output_range[0] = 18367 + (666 / voices)
        self.plugins.shift_range.signals.output_range[1] = 18367 + (6666 / voices)

        self.signals.pitch = self.plugins.mps[0].signals.input
        self.signals.output = self.plugins.mixer.signals.output

    def make_page(self):
        page = ParameterPage(self.name, self)
        voices = len(self.plugins.oscs)
        param = Parameter(
            [self.plugins.shift_range.signals.input],
            "shift",
            0.2,
            modulated=True,
        )
        page.params += [param]
        param = Parameter(
            [self.plugins.mixer.signals.gain],
            "dist",
            0,
            [4096 / voices, 4096],
            modulated=True,
        )
        page.params += [param]
        param = Parameter(
            [self.plugins.detune_osc.signals.pitch],
            "detune",
            0.2,
            [-9000, 0],
            modulated=True,
        )
        page.params += [param]
        return page
