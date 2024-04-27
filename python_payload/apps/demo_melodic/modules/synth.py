import bl00mbox
import math
from ..pages import *


class rand_lfo(bl00mbox.Patch):
    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.osc = self._channel.new(bl00mbox.plugins.osc)
        self.plugins.range = self._channel.new(bl00mbox.plugins.range_shifter)
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

        self.plugins.range.signals.speed.switch.SLOW = True
        self.plugins.range.always_render = True

        self.plugins.noise_shift.signals.input.freq = 1
        self.plugins.noise_vol.signals.input_gain[0] = 0
        # read only
        self.signals.modulation_output = self.plugins.range.signals.output

    @staticmethod
    def get_speed_string(signal):
        val = signal.freq
        return f"{val:.2f}Hz"

    def make_page(self, name="lfo"):
        page = ParameterPage(name, self)
        param = Parameter(self.plugins.osc.signals.waveform, "wave", 0.33)
        page.params += [param]
        param = Parameter(self.plugins.osc.signals.morph, "morph", 0.50)
        page.params += [param]
        param = Parameter(
            self.plugins.noise_vol.signals.input_gain[0],
            "rng",
            0.41,
            [0, 768],
        )
        page.params += [param]
        param = Parameter(
            self.plugins.noise_shift.signals.input,
            "speed",
            0.65,
            [-10000, 6000],
        )
        param.signal_get_string = rand_lfo.get_speed_string
        page.params += [param]
        page.scope_param = Parameter(
            self.signals.modulation_output, "", None, [-2048, 2048]
        )

        return page


class sensors(bl00mbox.Patch):
    def __init__(self, chan):
        super().__init__(chan)
        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, 3)
        self.plugins.mixer.signals.gain.dB = 0
        self.plugins.mixer.signals.input[2] = -2048
        self.plugins.mixer.always_render = True
        self.signals.modulation_output = self.plugins.mixer.signals.output

    def make_page(self, name="sensors"):
        page = ParameterPage(name, self)
        param = Parameter(
            self.plugins.mixer.signals.input_gain[0], "tilt", 0.5, [-4096, 4096]
        )
        page.params += [param]
        param = Parameter(
            self.plugins.mixer.signals.input_gain[1], "speed", 0.5, [-4096, 4096]
        )
        page.params += [param]
        page.scope_param = Parameter(
            self.signals.modulation_output, "", None, [-2048, 2048]
        )
        return page

    def update_data(self, ins, delta_ms):
        acc_vector = ins.imu.acc

        def inclination(vec):
            x, y, z = vec[0], vec[1], vec[2]
            if z > 0:
                return math.atan((((x**2) + (y**2)) ** 0.5) / z)
            elif z < 0:
                return math.tau / 2 + math.atan((((x**2) + (y**2)) ** 0.5) / z)
            return math.tau / 4

        def azimuth(vec):
            x, y, z = vec[0], vec[1], vec[2]
            if x > 0:
                return math.atan(y / x)
            elif x < 0:
                if y < 0:
                    return math.atan(y / x) - math.tau / 2
                else:
                    return math.atan(y / x) + math.tau / 2
            elif y < 0:
                return -math.tau / 4
            return math.tau / 4

        self.plugins.mixer.signals.input[0] = inclination(acc_vector) * 4096 * 2
        r = math.sqrt(sum([x * x for x in acc_vector]))
        self.plugins.mixer.signals.input[1] = (r - 9.81) * 256


class env(bl00mbox.Patch):
    def __init__(self, chan):
        super().__init__(chan)
        self.plugins.env = self._channel.new(bl00mbox.plugins.env_adsr)
        self.plugins.env.always_render = True
        self.signals.trigger = self.plugins.env.signals.trigger
        self.signals.input = self.plugins.env.signals.input
        self.signals.output = self.plugins.env.signals.output
        self.signals.modulation_output = self.plugins.env.signals.env_output

    @staticmethod
    def get_ms_string(signal):
        return str(int(signal.value)) + "ms"

    def make_page(self, name="env", toggle=None):
        page = ParameterPage(name)
        if toggle is not None:
            page.toggle = toggle
        param = Parameter(self.plugins.env.signals.attack, "attack", 0.091, [0, 1000])
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        param = Parameter(self.plugins.env.signals.decay, "decay", 0.247, [0, 1000])
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        param = Parameter(self.plugins.env.signals.sustain, "sustain", 0.2, [0, 32767])
        page.params += [param]
        param = Parameter(self.plugins.env.signals.release, "release", 0.236, [0, 1000])
        param.signal_get_string = self.get_ms_string
        page.params += [param]
        page.scope_param = Parameter(
            self.signals.modulation_output, "", None, [0, 4096]
        )
        return page


class mix_env(bl00mbox.Patch):
    def __init__(self, chan):
        super().__init__(chan)

        self.plugins.mp = self._channel.new(bl00mbox.plugins.multipitch, 2)

        self.plugins.mixer = self._channel.new(bl00mbox.plugins.mixer, 2)
        self.plugins.thru = self._channel.new(bl00mbox.plugins.range_shifter)
        self.plugins.thru.always_render = True
        self.plugins.mixer.signals.gain.mult = 1 / 16
        self.plugins.gain_curves = [
            self._channel.new(bl00mbox.plugins.distortion) for x in range(2)
        ]
        for x in range(2):
            self.plugins.gain_curves[x].always_render = True
            self.plugins.gain_curves[x].curve_set_power(0.25)
            self.plugins.gain_curves[
                x
            ].signals.output = self.plugins.mixer.signals.input_gain[x]

        self.plugins.env = self._channel.new(env)
        self.plugins.env.signals.input = self.plugins.mixer.signals.output

        self.plugins.filter = self._channel.new(bl00mbox.plugins.filter)

        self.plugins.dist = self._channel.new(bl00mbox.plugins.distortion)
        self.plugins.dist.curve_set_power(3)

        self.plugins.tone = self._channel.new(bl00mbox.plugins.filter)
        self.plugins.tone.signals.input = self.plugins.dist.signals.output

        self.signals.osc_input = self.plugins.mixer.signals.input
        self.signals.osc_pitch = self.plugins.mp.signals.output
        self.signals.osc_shift = self.plugins.mp.signals.shift

        self.signals.pitch = self.plugins.mp.signals.input
        self.signals.trigger = self.plugins.env.signals.trigger
        self.signals.fx_send = self.plugins.env.signals.output
        self.signals.fx_return = self.plugins.dist.signals.input
        self.signals.fx_send = self.signals.fx_return

        self.signals.output = self.plugins.tone.signals.output
        self.signals.envelope_data = self.plugins.env.signals.modulation_output

    def make_env_page(self, name="env", toggle=None):
        return self.plugins.env.make_page(name, toggle)

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
        if signal.value == 0:
            return "mute"
        return str(int(signal.dB)) + "dB"

    @staticmethod
    def get_cutoff_string(signal):
        return str(int(signal.freq)) + "Hz"

    def make_mixer_page(self):
        page = ParameterPage("mixer")
        mix_params = []
        for x in range(2):
            param = Parameter(
                self.plugins.gain_curves[x].signals.input,
                "osc" + str(x),
                0.5,
                [0, 32767],
                modulated=True,
            )
            param.signal_get_string = self.get_dB_string
            param.set_unit_signal(self.plugins.mixer.signals.input_gain[x])
            mix_params += [param]
        page.params += [mix_params[0]]
        param = Parameter(
            self.plugins.tone.signals.cutoff, "hicut", 0.5, [23000, 29000]
        )
        param.signal_get_string = self.get_cutoff_string
        page.params += [param]
        param = Parameter(self.plugins.thru.signals.input, "bend", 0.1)
        page.params += [param]
        page.params += [mix_params[1]]
        return page
