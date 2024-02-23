import bl00mbox
import math
from ui.pages.synth import *


class sines_osc(bl00mbox.Patch):
    name = "sines"

    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.oscs = [self._channel.new(bl00mbox.plugins.osc) for x in range(4)]
        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, 4)
        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 3)

        self.plugins.mp.signals.thru = self.plugins.oscs[0].signals.pitch
        for x in range(3):
            self.plugins.mp.signals.output[x] = self.plugins.oscs[x + 1].signals.pitch
            self.plugins.mp.signals.shift[x].tone = [12, 19.02, 27.863][x]
        for x in range(4):
            self.plugins.oscs[x].signals.waveform.switch.SINE = True
            self.plugins.oscs[x].signals.output = self.plugins.mixer.signals.input[x]
        self.plugins.mixer.gain = 4096 / 8 / 4

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.output = self.plugins.mixer.signals.output

    def make_page(self):
        page = ParameterPage(self.name, self)
        names = ["root", "oct", "fifth", "third"]
        for x in range(4):
            param = Parameter(
                [self.plugins.mixer.signals.input_gain[x]],
                names[x],
                0.5,
                [0, 32767],
                modulated=True,
            )
            page.params += [param]
        return page
