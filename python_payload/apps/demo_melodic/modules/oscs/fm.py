import bl00mbox
import math
from pages import *

class fm_osc(bl00mbox.Patch):
    name = "fm"

    def __init__(self, chan):
        super().__init__(chan)

        self.max_mult = 10
        self.pitches = [12 * math.log(1 + x, 2) for x in range(self.max_mult)]

        self.plugins.oscs = [self._channel.new(bl00mbox.plugins.osc) for x in range(3)]
        self.plugins.mixers = [
            self._channel.new(bl00mbox.plugins.mixer, 1) for x in range(2)
        ]
        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 4)

        self.plugins.mp.signals.thru = self.plugins.oscs[0].signals.pitch
        for x in range(2):
            self.plugins.mp.signals.output[x] = self.plugins.oscs[x + 1].signals.pitch
            # self.plugins.oscs[0].signals.sync_output = self.plugins.oscs[x + 1].signals.sync_input

        self.plugins.oscs[0].signals.fm = self.plugins.mixers[0].signals.output
        self.plugins.oscs[1].signals.fm = self.plugins.mixers[1].signals.output
        self.plugins.mixers[0].signals.input[0] = self.plugins.oscs[1].signals.output
        self.plugins.mixers[1].signals.input[0] = self.plugins.oscs[2].signals.output

        for x in range(2):
            self.plugins.oscs[x].signals.waveform.switch.TRI = True

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.output = self.plugins.oscs[0].signals.output

    def set_pitch_value(self, signal, val):
        val = round(val / 100)
        val = int(val - 1) % len(self.pitches)
        signal.tone = self.pitches[val]

    def get_pitch_value(self, signal):
        return round(2 ** (signal.tone / 12)) * 100 / self.max_mult

    @staticmethod
    def get_pitch_string(signal):
        return "x" + str(round(2 ** (signal.tone / 12)))

    def make_page(self):
        page = ParameterPage(self.name, self)
        dparams = []
        sparams = []
        for i in range(2):
            suffix = [" A", " B"][i]
            param = Parameter(
                self.plugins.mixers[i].signals.input_gain[0],
                "depth" + suffix,
                0.5,
                [0, 4096],
                modulated=True,
            )
            dparams += [param]
            param = Parameter(
                self.plugins.mp.signals.shift[i],
                "shift" + suffix,
                0.5,
                [100, self.max_mult * 100],
            )
            param.signal_get_value = self.get_pitch_value
            param.signal_get_string = self.get_pitch_string
            param.signal_set_value = self.set_pitch_value
            sparams += [param]
        page.params += [dparams[0]] + sparams + [dparams[1]]
        return page
