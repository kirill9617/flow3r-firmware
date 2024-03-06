from . import *


def center_notch(val, deadzone=0.2):
    refval = (2 * val) - 1
    gain = 1 / (1 - deadzone)
    if refval < -deadzone:
        return val * gain
    if refval > deadzone:
        return 1 - (1 - val) * gain
    return 0.5


class ParameterPage(Page):
    def __init__(self, name, patch=None):
        super().__init__(name)
        self.patch = patch
        self.mod_source = 0
        self.num_mod_sources = 2

    def delete(self):
        self.patch.delete()
        for param in self.params:
            param.delete()

    def finalize(self, channel, lfo_signal, env_signals):
        self.params = self.params[:4]
        for param in self.params:
            param.finalize(channel, lfo_signal, env_signals)
        self.finalized = True

    def get_settings(self):
        settings = {}
        params = list(self.params)
        if self.toggle is not None:
            params += [self.toggle]
        for param in params:
            settings[param.name] = param.get_settings()
        return settings

    def set_settings(self, settings):
        params = list(self.params)
        if self.toggle is not None:
            params += [self.toggle]
        for param in params:
            if param.name in settings.keys():
                param.set_settings(settings[param.name])
            else:
                print(f"no setting found for {self.name}->{param.name}")

    def think(self, ins, delta_ms, app):
        modulated = False
        for i, param in enumerate(self.params):
            if param.modulated:
                modulated = True
            val = app.petal_val[app.petal_index[i]][0]
            if val is not None:
                if param.modulated:
                    if self.subwindow == 0:
                        param.norm = val
                    elif self.mod_source == 0:
                        param.env_norm = center_notch(val)
                    elif self.mod_source == 1:
                            param.lfo_norm = center_notch(val)
                else:
                    param.norm = val
        if self.toggle is not None:
            if self.subwindow > 0:
                self.subwindow = 0
                self.toggle.value = not self.toggle.value
        elif modulated:
            self.subwindow %= 2
        else:
            self.subwindow %= 1
        self.locked = bool(self.subwindow)
        if self.locked:
            lr_dir = app.input.buttons.app.right.pressed - app.input.buttons.app.left.pressed
            if lr_dir:
                self.full_redraw = True
                self.mod_source = (self.mod_source + lr_dir) % self.num_mod_sources

    def draw(self, ctx, app):
        # changed encoding a bit but didn't follow thru yet, will clean that up
        fakesubwindow = 0
        if self.subwindow:
            fakesubwindow = self.mod_source + 1

        if self.full_redraw:
            ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
            if not self.hide_header:
                app.draw_title(ctx, self.display_name)
        modulated = False
        for i, param in enumerate(self.params):
            if param.modulated:
                modulated = True
                plusminus = True
                redraw = 2
                if self.subwindow == 0:
                    val = param.norm
                    plusminus = False
                    if param.norm_changed:
                        param.norm_changed = False
                        redraw = 1
                elif self.mod_source == 0:
                    val = param.env_norm
                    if param.env_norm_changed:
                        param.env_norm_changed = False
                        redraw = 1
                elif self.mod_source == 1:
                    val = param.lfo_norm
                    if param.lfo_norm_changed:
                        param.lfo_norm_changed = False
                        redraw = 1
                if self.full_redraw:
                    redraw = 0
                app.draw_bar_graph(
                    ctx,
                    app.petal_index[i],
                    [val, param.mod_norms[0]],
                    param.display_name,
                    param.unit,
                    sub=fakesubwindow,
                    plusminus=plusminus,
                    skip_redraw=redraw,
                )
            else:
                if self.full_redraw:
                    redraw = 0
                elif param.norm_changed:
                    redraw = 1
                else:
                    redraw = 2
                if redraw != 2:
                    param.norm_changed = False
                    app.draw_bar_graph(
                        ctx,
                        app.petal_index[i],
                        param.norm,
                        param.display_name,
                        param.unit,
                        skip_redraw=redraw,
                    )
        if self.scope_param is not None:
            app.draw_scope(ctx, self.scope_param)
        if self.hide_footer:
            pass
        elif modulated:
            app.draw_modulator_indicator(ctx, sub=fakesubwindow)
        elif self.toggle is not None:
            if self.toggle.full_redraw or self.full_redraw:
                if self.toggle.value:
                    app.draw_modulator_indicator(
                        ctx, self.toggle.name + ": on", col=app.cols.alt
                    )
                else:
                    app.draw_modulator_indicator(
                        ctx, self.toggle.name + ": off", col=app.cols.fg
                    )
            self.toggle.full_redraw = False
        self.full_redraw = False


class ToggleParameter:
    def __init__(self, name):
        self.name = name
        self.full_redraw = True
        self._value = False
        self.changed = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if self._value != val:
            self.changed = True
            self._value = val
            self.full_redraw = True

    def get_settings(self):
        return {"val": self.value}

    def set_settings(self, settings):
        self.value = settings["val"]


class Parameter:
    def __init__(
        self,
        signals,
        name,
        default_norm,
        signal_range=[-32767, 32767],
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
        self._mod_shifters = []
        self.name = name
        self.display_name = name
        self.modulated = modulated
        self.finalized = False
        self.default_env_mod = 0.5
        self.default_lfo_mod = 0.5
        self.default_norm = default_norm

        # seperate track keeping to avoid blm rounding errors
        self._thou = -1
        self._lfo_thou = -1
        self._env_thou = -1
        self.norm_changed = True
        self.lfo_norm_changed = True
        self.env_norm_changed = True

        self._output_min = signal_range[0]
        self._output_spread = signal_range[1] - signal_range[0]
        self.set_unit_signal(signals[0], signal_range)

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
        if self.default_norm is not None:
            return self._thou / 1000
        else:
            return self._norm_from_signal(self._signals[0])

    @norm.setter
    def norm(self, val):
        intval = int(val * 1000)
        if intval != self._thou:
            self.norm_changed = True
            self._thou = intval
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
                mod_shifter.always_render = True
                self._mod_shifters += [mod_shifter]
            else:
                mod_mixer.signals.output = signal
                mod_mixer.always_render = True
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
        if self.finalized:
            return
        self.norm = self.default_norm
        if self.modulated:
            self._create_modulator(channel, lfo_signal, env_signals)
        self.finalized = True

    def delete(self):
        for plugin in self._mod_shifters + self._mod_mixers:
            plugin.delete()

    @property
    def mod_norms(self):
        ret = [(m.signals.output.value + 32767) / 65534 for m in self._mod_mixers]
        return ret

    @property
    def lfo_norm(self):
        return self._lfo_thou / 1000

    @lfo_norm.setter
    def lfo_norm(self, val):
        if self.modulated:
            intval = int(val * 1000)
            if intval != self._lfo_thou:
                self.lfo_norm_changed = True
                self._lfo_thou = intval
            val = 2 * val - 1
            val = val * abs(val) * 32767
            for m in self._mod_mixers:
                m.signals.input_gain[1].value = val

    @property
    def env_norm(self):
        return self._env_thou / 1000

    @env_norm.setter
    def env_norm(self, val):
        if self.modulated:
            intval = int(val * 1000)
            if intval != self._env_thou:
                self.env_norm_changed = True
                self._env_thou = intval
            val = 2 * val - 1
            val = val * abs(val) * 32767
            for m in self._mod_mixers:
                m.signals.input_gain[2].value = val

    def get_settings(self):
        if not self.finalized:
            return
        settings = {}
        settings["val"] = self._thou
        if self.modulated:
            settings["lfo"] = self._lfo_thou
            settings["env"] = self._env_thou
        return settings

    def set_settings(self, settings):
        if not self.finalized:
            return
        self.norm = settings["val"] / 1000
        if self.modulated:
            if "lfo" in settings.keys():
                self.lfo_norm = settings["lfo"] / 1000
            else:
                self.lfo_norm = 0.5
            if "env" in settings.keys():
                self.env_norm = settings["env"] / 1000
            else:
                self.env_norm = 0.5
