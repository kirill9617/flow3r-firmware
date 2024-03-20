import bl00mbox
import math
from pages import *

class fltr(bl00mbox.Patch):
    name = "fltr"
    def __init__(self, chan):
        super().__init__(chan)
        self.plugins.filter = self._channel.new(bl00mbox.plugins.filter)
        self.signals.input = self.plugins.filter.signals.input
        self.signals.output = self.plugins.filter.signals.output

    @staticmethod
    def get_cutoff_string(signal):
        return str(int(signal.freq)) + "Hz"

    @staticmethod
    def get_reso_string(signal):
        val = signal.value / 4096
        return f"{val:.2f}Q"

    @staticmethod
    def get_mode_string(signal):
        val = signal.value
        val = ((val / 65534) * 8 + 5) // 2
        val = min(val, 4)
        return ["lp", "lp+bp", "bp", "bp+hp", "hp"][int(val)]

    def make_page(self):
        page = ParameterPage("fltr")
        param = Parameter(
            self.plugins.filter.signals.cutoff,
            "cutoff",
            0.8,
            [13000, 26000],
        )
        param.signal_get_string = self.get_cutoff_string
        param.modulated = True
        page.params += [param]
        param = Parameter(
            self.plugins.filter.signals.reso,
            "q",
            0.27,
            [2048, 4096 * 7.5],
        )
        param.signal_get_string = self.get_reso_string
        param.modulated = True
        page.params += [param]
        param = Parameter(self.plugins.filter.signals.mode, "mode", 0.45)
        param.signal_get_string = self.get_mode_string
        param.modulated = True
        page.params += [param]
        param = Parameter(self.plugins.filter.signals.mix, "mix", 1, [0, 32767])
        param.modulated = True
        page.params += [param]
        return page

