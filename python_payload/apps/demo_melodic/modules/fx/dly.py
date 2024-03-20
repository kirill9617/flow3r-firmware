import bl00mbox
import math
from ui.pages.synth import *

class dly(bl00mbox.Patch):
    name = "dly"
    def __init__(self, chan):
        super().__init__(chan)
        self.plugins.delay = self._channel.new(bl00mbox.plugins.delay_static, 1000)
        self.signals.input = self.plugins.delay.signals.input
        self.signals.output = self.plugins.delay.signals.output

    def make_page(self):
        page = ParameterPage("dly")
        param = Parameter(
            self.plugins.delay.signals.time,
            "time",
            0.3,
            [0, 1000],
        )
        param.modulated = True
        page.params += [param]
        param = Parameter(
            self.plugins.delay.signals.feedback,
            "fdbk",
            0.3,
            [0, 32767],
        )
        param.modulated = True
        page.params += [param]
        param = Parameter(self.plugins.delay.signals.level, "wet", 0.5, [0,32767])
        param.modulated = True
        page.params += [param]
        param = Parameter(self.plugins.delay.signals.dry_vol, "dry", 1, [0, 32767])
        param.modulated = True
        page.params += [param]
        return page
