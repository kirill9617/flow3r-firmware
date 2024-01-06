from st3m.goose import List, Optional
from st3m.input import InputState, InputController
from st3m.ui.view import ViewManager
from st3m.application import Application, ApplicationContext
from ctx import Context
import bl00mbox
import leds
import math
from st3m.ui import colours


class Page:
    def __init__(self, name):
        self.name = name
        self.params = []
        self.scope_param = None
        self.toggle = None
        self.subwindow = 0
        self.finalized = False

    def finalize(self, channel, lfo_signal, env_signals):
        for param in self.params:
            param.finalize(channel, lfo_signal, env_signals)
        self.finalized = True


class ToggleParameter:
    def __init__(self, name):
        self.name = name
        self.value = False


class FullRangeParameter:
    def __init__(
        self,
        signals,
        name,
        signal_range=[-32767, 32767],
        default_norm=None,
        modulated=False,
    ):
        def get_val(signal):
            return signal.value

        def set_val(signal, val):
            signal.value = val

        def get_str(signal):
            norm = (
                self.signal_get_value(signal) - self._string_signal_output_min
            ) / self._string_signal_output_spread
            return str(int(norm * 100 + 0.5)) + "%"

        self.signal_get_value = get_val
        self.signal_set_value = set_val
        self.signal_get_string = get_str
        self._signals = signals
        self._mod_mixers = []
        self.name = name
        self.modulated = modulated
        self.finalized = False
        self.default_env_mod = 0.5
        self.default_lfo_mod = 0.5

        self._output_min = signal_range[0]
        self._output_spread = signal_range[1] - signal_range[0]
        self.set_unit_signal(signals[0], signal_range)
        if default_norm is not None:
            self.norm = default_norm

    def set_unit_signal(self, signal, signal_range=[-32767, 32767]):
        self._signal_string_signal = signal
        self._string_signal_output_min = signal_range[0]
        self._string_signal_output_spread = signal_range[1] - signal_range[0]

    def _norm_from_signal(self, signal):
        return (self.signal_get_value(signal) - self._output_min) / self._output_spread

    def _norm_to_signal(self, val, signal=None):
        val = (val * self._output_spread) + self._output_min
        if signal is None:
            return val
        else:
            self.signal_set_value(signal, val)

    @property
    def norm(self):
        return self._norm_from_signal(self._signals[0])

    @norm.setter
    def norm(self, val):
        val = self._norm_to_signal(val)
        for signal in self._signals:
            self.signal_set_value(signal, val)

    @property
    def unit(self):
        return self.signal_get_string(self._signal_string_signal)

    def _create_modulator(self, channel, lfo_signal, env_signals):
        range_shift = True
        if self._output_min == -32767 and self._output_spread == 65534:
            range_shift = False
        for i, signal in enumerate(self._signals):
            val = signal.value
            mod_mixer = channel.new(bl00mbox.plugins.mixer, 3)
            mod_shifter = None
            if range_shift:
                val = (val - self._output_min) / self._output_spread
                val = (val * 64434) - 32767
                mod_shifter = channel.new(bl00mbox.plugins.range_shifter)
                mod_shifter.signals.input = mod_mixer.signals.output
                mod_shifter.signals.output_range[0] = self._output_min
                mod_shifter.signals.output_range[1] = (
                    self._output_min + self._output_spread
                )
                mod_shifter.signals.output = signal
                self._output_min = -32767
                self._output_spread = 65534
            else:
                mod_mixer.signals.output = signal
            mod_mixer.signals.gain.mult = 2
            mod_mixer.signals.input[0] = val
            self._signals[i] = mod_mixer.signals.input[0]
            mod_mixer.signals.input[1] = lfo_signal
            mod_mixer.signals.input[2] = env_signals[i]
            mod_mixer.signals.input_gain[0].mult = 0.5
            mod_mixer.signals.input_gain[1] = 0
            mod_mixer.signals.input_gain[2] = 0
            self._mod_mixers += [mod_mixer]
            self.lfo_norm = self.default_lfo_mod
            self.env_norm = self.default_env_mod

    def finalize(self, channel, lfo_signal, env_signals):
        if self.modulated:
            self._create_modulator(channel, lfo_signal, env_signals)
        self.finalized = True

    @property
    def mod_norms(self):
        ret = [(m.signals.output.value + 32767) / 65534 for m in self._mod_mixers]
        return ret

    @property
    def lfo_norm(self):
        if not self.modulated:
            return 0
        else:
            return (self._mod_mixers[0].signals.input_gain[1].value + 32767) / 65534

    @lfo_norm.setter
    def lfo_norm(self, val):
        if self.modulated:
            for m in self._mod_mixers:
                m.signals.input_gain[1].value = val * 65534 - 32767

    @property
    def env_norm(self):
        if not self.modulated:
            return 0
        else:
            return (self._mod_mixers[0].signals.input_gain[2].value + 32767) / 65534

    @env_norm.setter
    def env_norm(self, val):
        if self.modulated:
            for m in self._mod_mixers:
                m.signals.input_gain[2].value = val * 65534 - 32767


class hard_sync_osc(bl00mbox._patches._Patch):
    def __init__(self, chan):
        super().__init__(chan)
        self.name = "overtoner"

        self.plugins.root_osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.mod_osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.main_osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.root_osc.signals.sync_output = (
            self.plugins.mod_osc.signals.sync_input
        )
        self.plugins.mod_osc.signals.sync_output = (
            self.plugins.main_osc.signals.sync_input
        )

        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 2)
        self.plugins.mp.signals.thru = self.plugins.root_osc.signals.pitch
        self.plugins.mp.signals.output[0] = self.plugins.mod_osc.signals.pitch
        self.plugins.mp.signals.output[1] = self.plugins.main_osc.signals.pitch

        self.plugins.main_osc.signals.waveform.switch.SINE = True

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.output = self.plugins.main_osc.signals.output

    def make_page(self):
        page = Page(self.name)
        param = FullRangeParameter(
            [self.plugins.mp.signals.shift[1]],
            "focus",
            [18367, 18367 + 2400 * 2],
            default_norm=0.2,
            modulated=True,
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.mp.signals.shift[0]],
            "disrupt",
            [18367, 18367 + 2400 * 2],
            default_norm=0,
            modulated=True,
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.main_osc.signals.waveform],
            "wave",
            default_norm=0.33,
            modulated=True,
        )
        page.params += [param]
        return page


class detune_osc(bl00mbox._patches._Patch):
    def __init__(self, chan):
        super().__init__(chan)
        self.name = "detuner"

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
        page = Page(self.name)
        param = FullRangeParameter(
            [self.plugins.ranges[1].signals.input],
            "detune",
            default_norm=0.15,
            modulated=True,
        )
        param.default_env_mod = 1
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.ranges[0].signals.input],
            "wave",
            default_norm=0.98,
            modulated=True,
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.mixer.signals.gain],
            "dist",
            [367, 32767],
            default_norm=0.34,
            modulated=True,
        )
        param.default_env_mod = 1
        param.default_lfo_mod = 0.4
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.mixer.signals.input_gain[3]],
            "noise",
            [0, 9001],
            default_norm=0,
            modulated=True,
        )
        page.params += [param]
        return page


class rand_lfo(bl00mbox._patches._Patch):
    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.range = self._channel.new(bl00mbox.plugins.range_shifter)
        self.plugins.dummy = self._channel.new(bl00mbox.plugins.range_shifter)
        self.plugins.noise = self._channel.new(bl00mbox.plugins.noise_burst)
        self.plugins.noise_vol = self._channel.new(bl00mbox.plugins.mixer, 2)
        self.plugins.noise_shift = self._channel.new(bl00mbox.plugins.multipitch, 1)

        self.plugins.noise.signals.trigger = self.plugins.osc.signals.sync_output
        self.plugins.noise.signals.length = 0
        self.plugins.noise_vol.signals.input[0] = self.plugins.noise.signals.output
        self.plugins.noise_vol.signals.input[1] = 18367
        self.plugins.noise_vol.signals.output = self.plugins.noise_shift.signals.shift[
            0
        ]
        self.plugins.noise_shift.signals.min_pitch = -32767
        self.plugins.noise_shift.signals.max_pitch = 32767
        self.plugins.noise_vol.signals.gain.mult = 1

        self.plugins.noise_shift.signals.output[0] = self.plugins.osc.signals.pitch
        self.plugins.osc.signals.speed.switch.AUDIO = True
        self.plugins.range.signals.input = self.plugins.osc.signals.output
        self.plugins.range.signals.output_range[0] = -2048
        self.plugins.range.signals.output_range[1] = 2048

        self.plugins.dummy.signals.output_range[0] = 0
        self.plugins.dummy.signals.output_range[1] = 0
        self.plugins.dummy.signals.input = self.plugins.range.signals.output

        self.plugins.noise_shift.signals.input.freq = 1
        self.plugins.noise_vol.signals.input_gain[0] = 0
        # read only
        self.signals.output = self.plugins.range.signals.output
        self.signals.dummy = self.plugins.dummy.signals.output

    @staticmethod
    def get_speed_string(signal):
        val = signal.freq
        return f"{val:.2f}Hz"

    def make_page(self):
        page = Page("lfo")
        param = FullRangeParameter(
            [self.plugins.osc.signals.waveform], "wave", default_norm=0.33
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.osc.signals.morph], "morph", default_norm=0.50
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.noise_vol.signals.input_gain[0]],
            "rng",
            [0, 768],
            default_norm=0.41,
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.noise_shift.signals.input],
            "speed",
            [-10000, 6000],
            default_norm=0.65,
        )
        param.signal_get_string = rand_lfo.get_speed_string
        page.params += [param]
        page.scope_param = FullRangeParameter([self.signals.output], "", [-2048, 2048])
        return page


class mix_env_filt(bl00mbox._patches._Patch):
    def __init__(self, chan, mixer_inputs=4):
        super().__init__(chan)
        self._mixer_inputs = mixer_inputs

        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 4)

        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, mixer_inputs)

        for i in range(mixer_inputs):
            self.plugins.mixer.signals.input_gain[i].dB = -6

        self.plugins.env = self._channel.new(bl00mbox.plugins.env_adsr)
        self.plugins.env.signals.input = self.plugins.mixer.signals.output
        self.plugins.env.signals.release = 100
        self.plugins.env.signals.decay = 500
        self.plugins.env.signals.attack = 100
        self.plugins.env.signals.sustain = 16000

        self.plugins.filter = self._channel.new(bl00mbox.plugins.filter)
        self.plugins.filter.signals.cutoff = 22000
        self.plugins.filter.signals.reso = 4096
        self.plugins.filter.signals.gain.dB -= 6

        self.plugins.filter.signals.input = self.plugins.env.signals.output

        self.signals.osc_input = self.plugins.mixer.signals.input
        self.signals.osc_pitch = self.plugins.mp.signals.output
        self.signals.osc_shift = self.plugins.mp.signals.shift

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.trigger = self.plugins.env.signals.trigger
        self.signals.output = self.plugins.filter.signals.output

        self.signals.envelope_data = self.plugins.env.signals.env_output

    @staticmethod
    def set_dB_value(signal, val):
        if val >= -30:
            signal.dB = val
        else:
            signal.mult = 0

    @staticmethod
    def get_dB_value(signal):
        ret = signal.dB
        if ret >= -30:
            return ret
        else:
            return -33

    @staticmethod
    def get_dB_string(signal):
        ret = int(signal.dB)
        if ret >= -30:
            return str(ret) + "dB"
        else:
            return "mute"

    def make_mixer_page(self):
        page = Page("mixer")
        for i in range(self._mixer_inputs):
            param = FullRangeParameter(
                [self.plugins.mixer.signals.input_gain[i]],
                "chan " + str(i + 1),
                [-33, 0],
            )
            param.signal_get_value = self.get_dB_value
            param.signal_set_value = self.set_dB_value
            param.signal_get_string = self.get_dB_string
            page.params += [param]
        return page

    @staticmethod
    def get_ms_string(signal):
        return str(int(signal.value)) + "ms"

    def make_env_page(self, toggle=None):
        page = Page("env")
        if toggle is not None:
            page.toggle = toggle
        param = FullRangeParameter(
            [self.plugins.env.signals.attack], "attack", [0, 1000], default_norm=0.091
        )
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.env.signals.decay], "decay", [0, 1000], default_norm=0.247
        )
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.env.signals.sustain], "sustain", [0, 32767], default_norm=0.2
        )
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.env.signals.release], "release", [0, 1000], default_norm=0.236
        )
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        page.scope_param = FullRangeParameter(
            [self.plugins.env.signals.env_output], "", [0, 4096]
        )
        return page

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

    def make_filter_page(self):
        page = Page("filter")
        param = FullRangeParameter(
            [self.plugins.filter.signals.cutoff],
            "cutoff",
            [13000, 26000],
            default_norm=0.8,
        )
        param.signal_get_string = self.get_cutoff_string
        param.default_env_mod = 0.1
        param.default_lfo_mod = 0.45
        param.modulated = True
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.filter.signals.reso],
            "reso",
            [2048, 4096 * 7.5],
            default_norm=0.27,
        )
        param.signal_get_string = self.get_reso_string
        param.modulated = True
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.filter.signals.mode], "mode", default_norm=0.45
        )
        param.signal_get_string = self.get_mode_string
        param.modulated = True
        page.params += [param]
        param = FullRangeParameter(
            [self.plugins.filter.signals.mix], "mix", [0, 32767], default_norm=1
        )
        param.modulated = True
        page.params += [param]
        return page


class MelodicApp(Application):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        super().__init__(app_ctx)
        self.PUR = (1, 0, 1)
        self.YEL = (1, 1, 0)
        self.CYA = (0, 1, 1)
        self.BLA = (0, 0, 0)
        self.synths = []
        self.base_scale = [0, 2, 3, 5, 7, 8, 10]
        self.mid_point_petal = 0
        self.mid_point_lock = True
        self.mid_point_petal_hyst = 3

        self.min_note = -45
        self.max_note = +15
        self.mid_point = -15

        self.at_min_note = False
        self.at_max_note = False

        self.auto_color = (1, 0.5, 1)
        self.min_hue = 0
        self.max_hue = 0
        self.petal_val = [[None] * 3 for x in range(10)]
        self.petal_index = [7, 9, 1, 3]

        self.scale = [0] * 10
        self.blm = None
        self.mode_main = True
        self.active_page = 0
        self.drone_toggle = ToggleParameter("drone")

        self.env_value = 0
        self.lfo_value = 0

        self.init_print_pending = True

    def get_col(self, index):
        index = index % 3
        if index == 0:
            return self.PUR
        if index == 1:
            return self.YEL
        if index == 2:
            return self.CYA

    def base_scale_get_val_from_mod_index(self, index):
        o = index // len(self.base_scale)
        i = index % len(self.base_scale)
        return 12 * o + self.base_scale[i]

    def base_scale_get_mod_index_from_val(self, val):
        val = int(val)
        index = val
        while True:
            try:
                i = self.base_scale.index(index % 12)
                break
            except:
                index -= 1
        o = val // 12
        return i + len(self.base_scale) * o

    def make_scale(self):
        i = self.base_scale_get_mod_index_from_val(self.mid_point)
        for j in range(-5, 5):
            tone = self.base_scale_get_val_from_mod_index(i + j)
            self.scale[(self.mid_point_petal + j) % 10] = tone

    def draw(self, ctx):
        if self.blm is None:
            return
        self.env_value = self._signal_env.value / 4096
        self.lfo_value = self._signal_lfo.value / 4096 + 0.5
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        if self.mode_main:
            self.draw_main(ctx)
        else:
            self.draw_page(ctx, self.pages[self.active_page])

    def draw_title(self, ctx, name):
        ctx.save()
        ctx.get_font_name(4)
        ctx.text_align = ctx.CENTER
        ctx.font_size = 22
        ctx.rgb(1, 0, 1)
        ctx.arc(0, -180, 95, 0, math.tau, 1).fill()
        ctx.move_to(0, -97)
        ctx.rgb(0, 0, 0)
        ctx.text(name)
        ctx.restore()

    def draw_modulator_indicator(self, ctx, text=None, subtext=None, col=None):
        sub = self.pages[self.active_page].subwindow
        ctx.save()
        ctx.rgb(*self.PUR)
        ctx.arc(0, 150, 100, 0, math.tau, 1).fill()
        rad = 50
        if col is None:
            ctx.rgb(*self.get_col(sub))
        else:
            ctx.rgb(*col)
        if sub == 1:
            rad = 40 + self.env_value * 10
        if sub == 2:
            rad = 40 + self.lfo_value * 10
        ctx.arc(0, 150, rad, 0, math.tau, 1).fill()
        if text is None:
            text = ["base", "env mod", "lfo mod"][sub]
        ctx.get_font_name(4)
        ctx.rgb(*self.BLA)
        ctx.text_align = ctx.CENTER
        ctx.font_size = 22
        ctx.move_to(0, 90)
        ctx.text(text)
        ctx.restore()

    def draw_bar_graph(
        self, ctx, petal, norms, label, unit=None, sub=0, plusminus=False
    ):
        if petal not in [1, 3, 7, 9]:
            return
        if not type(norms) == list:
            norms = [norms]
        norms = [max(0, min(1, norm)) for norm in norms]
        if unit is None:
            unit = str(norms[0]) + "%"

        labelsize = 18
        unitsize = 16
        barlen = 70
        barstart = 40
        labelstart = 105
        unitend = 45
        rot = 0.75 + petal / 10
        labelalign = ctx.RIGHT
        unitalign = ctx.LEFT
        translate_center = barstart + barlen / 2
        sign = 1

        if petal in [3, 7]:
            trans_rot = -0.02
            downshift = 0
            outshift = 0
        else:
            trans_rot = 0.07
            outshift = 10
            downshift = 10

        if petal in [7, 9]:
            labelalign = ctx.LEFT
            unitalign = ctx.RIGHT
            rot += 0.5
            sign = -1

        ctx.save()
        ctx.translate(outshift * sign, downshift)
        ctx.line_width = 3
        ctx.get_font_name(4)

        ctx.rotate(math.tau * rot)

        ctx.translate(translate_center * sign, 0)
        ctx.rotate(math.tau * trans_rot * sign)
        ctx.translate(-translate_center * sign, 0)

        ctx.move_to(labelstart * sign, -15)
        ctx.text_align = labelalign
        ctx.font_size = labelsize

        ctx.rgb(*self.CYA)
        ctx.text(label)

        ctx.rgb(*self.YEL)
        ctx.move_to(unitend * sign, 10 + unitsize)
        ctx.text_align = unitalign
        ctx.font_size = unitsize
        ctx.text(unit)

        ctx.rgb(*self.get_col(sub))

        ctx.rectangle(barstart * sign, -10, barlen * sign, 20).stroke()
        ctx.rgb(*self.PUR)
        if len(norms) == 1:
            if plusminus:
                ctx.rectangle(
                    (barstart + barlen / 2) * sign,
                    -5,
                    (barlen - 10) * sign * (norms[0] - 0.5),
                    10,
                ).fill()
            else:
                ctx.rectangle(
                    (barstart + 5) * sign, -5, (barlen - 10) * sign * norms[0], 10
                ).fill()
        if len(norms) == 2:
            if plusminus:
                ctx.rectangle(
                    (barstart + barlen / 2) * sign,
                    -5,
                    (barlen - 10) * sign * (norms[0] - 0.5),
                    10,
                ).fill()
            else:
                ctx.rectangle(
                    (barstart + 5) * sign, -5, (barlen - 10) * sign * norms[0], 7
                ).fill()
            ctx.rgb(*self.YEL)
            ctx.rectangle(
                (barstart + 5) * sign, 3, (barlen - 10) * sign * norms[1], 2
            ).fill()

        ctx.restore()

    def draw_page(self, ctx, page):
        self.draw_title(ctx, page.name)
        modulated = False
        for i, param in enumerate(page.params):
            if i >= 4:
                continue
            if param.modulated:
                modulated = True
                plusminus = True
                if page.subwindow == 0:
                    val = param.norm
                    plusminus = False
                elif page.subwindow == 1:
                    val = param.env_norm
                elif page.subwindow == 2:
                    val = param.lfo_norm
                self.draw_bar_graph(
                    ctx,
                    self.petal_index[i],
                    [val, param.mod_norms[0]],
                    param.name,
                    param.unit,
                    sub=page.subwindow,
                    plusminus=plusminus,
                )
            else:
                self.draw_bar_graph(
                    ctx, self.petal_index[i], param.norm, param.name, param.unit
                )
        if page.scope_param is not None:
            self.draw_scope(ctx, page.scope_param)
        if modulated:
            self.draw_modulator_indicator(ctx)
        elif page.toggle is not None:
            if page.toggle.value:
                self.draw_modulator_indicator(
                    ctx, page.toggle.name + ": on", col=self.CYA
                )
            else:
                self.draw_modulator_indicator(
                    ctx, page.toggle.name + ": off", col=self.PUR
                )

    def draw_scope(self, ctx, param):
        ctx.save()
        ctx.rgb(1, 1, 0)
        ctx.arc(0, 0, 18, 0, math.tau, 1).fill()
        ctx.rgb(0, 0, 0)
        ctx.rectangle(-18, -18, 36, 36 - param.norm * 36).fill()
        ctx.line_width = 4
        ctx.rgb(1, 0, 1)
        ctx.arc(0, 0, 25, 0, math.tau, 1).stroke()
        ctx.restore()

    def draw_main(self, ctx):
        ctx.text_align = ctx.CENTER

        pos_of_petal = [x * 0.87 + 85 for x in self.scale]

        ctx.rgb(*self.PUR)
        ctx.line_width = 35
        for i in range(10):
            ctx.arc(
                0,
                0,
                pos_of_petal[i],
                math.tau * (0.75 - 0.04 + i / 10),
                math.tau * (0.75 + 0.04 + i / 10),
                0,
            ).stroke()
        ctx.line_width = 4
        ctx.rgb(*[x * 0.75 for x in self.PUR])
        for i in range(10):
            ctx.arc(
                0,
                0,
                pos_of_petal[i] - 26,
                math.tau * (0.75 - 0.04 + i / 10),
                math.tau * (0.75 + 0.04 + i / 10),
                0,
            ).stroke()
        ctx.rgb(*[x * 0.5 for x in self.PUR])
        for i in range(10):
            ctx.arc(
                0,
                0,
                pos_of_petal[i] - 36,
                math.tau * (0.75 - 0.04 + i / 10),
                math.tau * (0.75 + 0.04 + i / 10),
                0,
            ).stroke()

        ctx.rotate(-math.tau / 4)
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"
        ctx.font_size = 20
        ctx.rgb(*self.BLA)
        for i in range(10):
            ctx.rgb(*self.BLA)
            ctx.move_to(pos_of_petal[i], 6)
            note = bl00mbox.helpers.sct_to_note_name(self.scale[i] * 200 + 18367)
            ctx.text(note[:-1])
            ctx.rotate(math.tau / 10)

        ctx.rotate(math.tau * (self.mid_point_petal + 4.5) / 10)
        ctx.rgb(*self.BLA)
        ctx.line_width = 8
        ctx.move_to(0, 0)
        ctx.line_to(120, 0).stroke()
        ctx.rgb(*self.YEL)
        ctx.line_width = 1
        ctx.move_to(3, 0)
        ctx.line_to(120, 0).stroke()

    def _build_synth(self):
        # doesn't work for other values atm
        self.polyphony = 1
        # max length 4, rest gets cropped
        self.osc_targets = [detune_osc]

        if self.blm is None:
            self.blm = bl00mbox.Channel("mono synth")

        self.mixer = self.blm.new(bl00mbox.plugins.mixer, self.polyphony)
        self.filter = self.blm.new(bl00mbox.plugins.filter)
        self.mixer.signals.output = self.filter.signals.input
        self.filter.signals.cutoff.freq = 5000
        self.filter.signals.output = self.blm.mixer
        self.poly_squeeze = self.blm.new(
            bl00mbox.plugins.poly_squeeze, self.polyphony, 10
        )

        self.synths = []
        self.oscs = [[]] * self.polyphony
        self.pages = []

        self.osc_targets = self.osc_targets[:4]
        num_oscs = len(self.osc_targets)
        for i in range(self.polyphony):
            synth = self.blm.new(mix_env_filt, num_oscs)
            synth.signals.output = self.mixer.signals.input[i]
            synth.signals.trigger = self.poly_squeeze.signals.trigger_out[i]
            synth.signals.pitch = self.poly_squeeze.signals.pitch_out[i]
            self.synths += [synth]

        mixer_page = self.synths[0].make_mixer_page()
        mixer_page.params = mixer_page.params[:4]
        draw_mixer = num_oscs > 1
        if draw_mixer:
            self.pages += [mixer_page]

        self.lfo = self.blm.new(rand_lfo)
        self.lfo.signals.dummy = self.blm.mixer

        for i in range(self.polyphony):
            for j, osc_target in enumerate(self.osc_targets):
                osc = self.blm.new(osc_target)
                osc.signals.pitch = self.synths[i].signals.osc_pitch[j]
                osc.signals.output = self.synths[i].signals.osc_input[j]
                mixer_page.params[j].name = osc.name
                if not draw_mixer:
                    mixer_page.params[j].name = "osc"
                make_page = getattr(osc, "make_page", None)
                if make_page is not None:
                    page = make_page()
                    if not draw_mixer:
                        page.name = "osc"
                    self.pages += [page]
                self.oscs[i] += [osc]

        self.pages += [self.synths[0].make_filter_page()]
        self.pages += [self.synths[0].make_env_page(toggle=self.drone_toggle)]
        self.pages += [self.lfo.make_page()]

        for page in self.pages:
            page.finalize(
                self.blm,
                self.lfo.signals.output,
                [self.synths[0].plugins.env.signals.env_output],
            )

        self._signal_env = self.synths[0].plugins.env.signals.env_output
        self._signal_lfo = self.lfo.signals.output

    def update_leds(self, init=False):
        norm = self.env_value / 2 + 0.5
        yel = [x * norm for x in self.YEL]
        norm = self.lfo_value / 2 + 0.5
        cya = [x * norm for x in self.CYA]
        for i in range(0, 40, 8):
            for k in [2]:
                leds.set_rgb((i + k) % 40, *cya)
            for k in [-2]:
                leds.set_rgb((i + k) % 40, *yel)
        if init:
            for i in range(0, 40, 8):
                for k in [3, -3, 4]:
                    leds.set_rgb((i + k) % 40, *self.PUR)
                for k in [0, 1, -1]:
                    leds.set_rgb((i + k) % 40, 0, 0, 0)
        leds.update()

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        self.pages = []
        super().on_enter(vm)
        if self.blm is None:
            self._build_synth()
        self.blm.foreground = True
        self.make_scale()
        self.update_leds(init=True)

    def on_exit(self):
        if self.blm is not None:
            self.blm.clear()
            self.blm.free = True
        self.pages = []
        self.blm = None

    def shift_playing_field_by_num_petals(self, num):
        num_positive = True
        if num < 0:
            num_positive = False
            self.at_max_note = False
        elif num > 0:
            self.at_min_note = False
        num = abs(num)
        while num != 0:
            if num > 3:
                num_part = 3
                num -= 3
            else:
                num_part = num
                num = 0
            if num_positive:
                self.mid_point_petal += num_part
                self.mid_point_petal = self.mid_point_petal % 10
            else:
                self.mid_point_petal -= num_part
                self.mid_point_petal = self.mid_point_petal % 10
            self.mid_point = self.scale[self.mid_point_petal]
            self.make_scale()

        # make sure things stay in bounds
        while max(self.scale) > self.max_note:
            self.mid_point_petal -= 1
            self.mid_point_petal = self.mid_point_petal % 10
            self.mid_point = self.scale[self.mid_point_petal]
            self.make_scale()
            self.at_max_note = True
        while min(self.scale) < self.min_note:
            self.mid_point_petal += 1
            self.mid_point_petal = self.mid_point_petal % 10
            self.mid_point = self.scale[self.mid_point_petal]
            self.make_scale()
            self.at_min_note = True

        self.make_scale()

        if max(self.scale) == self.max_note:
            self.at_max_note = True
        if min(self.scale) == self.min_note:
            self.at_min_note = True

    def think(self, ins: InputState, delta_ms: int) -> None:
        if self.blm is None:
            return
        super().think(ins, delta_ms)

        if self.input.buttons.app.middle.pressed:
            self.mode_main = not self.mode_main
            if not self.mode_main:
                for i in range(1, 10, 2):
                    self.poly_squeeze.signals.trigger_in[i].stop()
        elif self.input.buttons.app.right.pressed:
            if self.mode_main:
                self.shift_playing_field_by_num_petals(4)
            else:
                self.active_page = (self.active_page + 1) % len(self.pages)
        elif self.input.buttons.app.left.pressed:
            if self.mode_main:
                self.shift_playing_field_by_num_petals(-4)
            else:
                self.active_page = (self.active_page - 1) % len(self.pages)

        # TODO: fix this
        petals = []
        for i in range(0, 10, 1 if self.mode_main else 2):
            if ins.captouch.petals[i].pressed:
                petals += [i]
        if (len(petals) == 1) and (not self.mid_point_lock):
            delta = petals[0] - self.mid_point_petal
            if delta > 4:
                delta -= 10
            if delta < -5:
                delta += 10
            if delta > 2:
                self.shift_playing_field_by_num_petals(delta - 2)
            if delta < -3:
                self.shift_playing_field_by_num_petals(delta + 3)

        for i in range(0, 10, 1 if self.mode_main else 2):
            if self.input.captouch.petals[i].whole.pressed:
                self.poly_squeeze.signals.pitch_in[i].tone = self.scale[i]
                self.poly_squeeze.signals.trigger_in[i].start()
            elif (
                self.input.captouch.petals[i].whole.released
                and not self.drone_toggle.value
            ):
                self.poly_squeeze.signals.trigger_in[i].stop()

        # TODO: what's this even doing, bleh
        self.update_leds()

        if self.mode_main:
            return

        for petal in [7, 9, 1, 3]:
            petal_len = len(self.petal_val[petal])
            if ins.captouch.petals[petal].pressed:
                val = (ins.captouch.petals[petal].position[0] + 12000) / 34000
                val = max(0, min(1, val))
                if self.petal_val[petal][0] is None:
                    for i in range(petal_len):
                        self.petal_val[petal][i] = val
                else:
                    for i in range(petal_len - 1):
                        self.petal_val[petal][i] = self.petal_val[petal][i + 1]
                    self.petal_val[petal][petal_len - 1] += (
                        val - self.petal_val[petal][petal_len - 1]
                    ) * 0.2
            else:
                for i in range(petal_len):
                    self.petal_val[petal][i] = None

        tmp = ins.captouch.petals[5].pressed
        if tmp != self.petal_val[5]:
            if self.petal_val[5] == False:
                self.pages[self.active_page].subwindow += 1
            self.petal_val[5] = tmp

        self.think_page(self.pages[self.active_page])

    @staticmethod
    def center_notch(val, deadzone=0.1):
        refval = (2 * val) - 1
        gain = 1 / (1 - deadzone)
        if refval < -deadzone:
            return val * gain
        if refval > deadzone:
            return 1 - (1 - val) * gain
        return 0.5

    def think_page(self, page):
        modulated = False
        for i, param in enumerate(page.params):
            if param.modulated:
                modulated = True
            val = self.petal_val[self.petal_index[i]][0]
            if val is not None:
                if param.modulated:
                    if page.subwindow == 0:
                        param.norm = val
                    if page.subwindow == 1:
                        param.env_norm = self.center_notch(val)
                    if page.subwindow == 2:
                        param.lfo_norm = self.center_notch(val)
                else:
                    param.norm = val
        if page.toggle is not None:
            if page.subwindow > 0:
                page.subwindow = 0
                page.toggle.value = not page.toggle.value
        elif modulated:
            page.subwindow %= 3
        else:
            page.subwindow %= 1


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(MelodicApp)
