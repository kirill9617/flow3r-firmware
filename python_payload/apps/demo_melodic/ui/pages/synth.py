from . import *


class Modulator:
    def __init__(self, name, patch, signal_range=[-2048, 2048], feed_hook=None):
        self.name = name
        self.patch = patch
        self.signal = patch.signals.modulation_output
        self.output = 0
        self.signal_range = signal_range
        self.feed_hook = feed_hook

    def feed(self, ins, delta_ms):
        if self.feed_hook is not None:
            self.feed_hook(ins, delta_ms)

    def update(self):
        self.output = (self.signal.value - self.signal_range[0]) / (
            self.signal_range[1] - self.signal_range[0]
        )


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
        self.modulated = False

    def delete(self):
        self.patch.delete()
        for param in self.params:
            param.delete()

    def finalize(self, channel, modulators):
        self.params = self.params[:4]
        for param in self.params:
            param.finalize(channel, modulators)
            if param.modulated:
                self.modulated = True
        self.num_mod_sources = len(modulators)
        self.mod_source = 0
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
        if app.input.captouch.petals[5].whole.pressed:
            if self.toggle is not None:
                self.toggle.value = not self.toggle.value
                self.full_redraw = True
            elif self.modulated:
                self.subwindow += 1
                self.subwindow %= 2
                self.full_redraw = True

        for i, param in enumerate(self.params):
            val = app.petal_val[app.petal_index[i]][0]
            if val is not None:
                if param.modulated and self.subwindow:
                    param.set_modulator_norm(self.mod_source, center_notch(val))
                else:
                    param.norm = val

    def petal_5_press_event(self, app):
        pass

    def lr_press_event(self, app, lr):
        if self.subwindow == 0:
            super().lr_press_event(app, lr)
        else:
            self.full_redraw = True
            self.mod_source = (self.mod_source + lr) % self.num_mod_sources
    
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
                else:
                    val = param.get_modulator_norm(self.mod_source)
                    if param.mod_norm_changed[self.mod_source]:
                        param.mod_norm_changed[self.mod_source] = False
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
        signal,
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
        self._signal = signal
        self._mod_mixers = []
        self._mod_shifters = []
        self.name = name
        self.display_name = name
        self.modulated = modulated
        self.finalized = False
        self.default_norm = default_norm

        # seperate track keeping to avoid blm rounding errors
        self._thou = -1
        self.norm_changed = True

        self._output_min = signal_range[0]
        self._output_spread = signal_range[1] - signal_range[0]
        self.set_unit_signal(self._signal, signal_range)

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
            return self._norm_from_signal(self._signal)

    @norm.setter
    def norm(self, val):
        intval = int(val * 1000)
        if intval != self._thou:
            self.norm_changed = True
            self._thou = intval
        val = self._norm_to_signal(val)
        self.signal_set_value(self._signal, val)

    @property
    def unit(self):
        return self.signal_get_string(self._signal_string_signal)

    def _create_modulator(self, channel, modulators):
        self._mod_thou = [-1] * len(modulators)
        self.mod_norm_changed = [True] * len(modulators)
        range_shift = True
        if self._output_min == -32767 and self._output_spread == 65534:
            range_shift = False
        val = self._signal.value
        mod_mixer = channel.new(bl00mbox.plugins.mixer, len(modulators) + 1)
        mod_shifter = None
        if range_shift:
            val = (val - self._output_min) / self._output_spread
            val = (val * 64434) - 32767
            mod_shifter = channel.new(bl00mbox.plugins.range_shifter)
            mod_shifter.signals.input = mod_mixer.signals.output
            mod_shifter.signals.output_range[0] = self._output_min
            mod_shifter.signals.output_range[1] = self._output_min + self._output_spread
            mod_shifter.signals.output = self._signal
            self._output_min = -32767
            self._output_spread = 65534
            mod_shifter.always_render = True
            self._mod_shifters += [mod_shifter]
        else:
            mod_mixer.signals.output = self._signal
            mod_mixer.always_render = True
        mod_mixer.signals.gain.mult = 2
        mod_mixer.signals.input[0] = val
        self._signal = mod_mixer.signals.input[0]
        for x in range(len(modulators)):
            mod_mixer.signals.input[x + 1] = modulators[x].signal
            mod_mixer.signals.input_gain[x + 1] = 0
            self.set_modulator_norm(x, 0.5)
        mod_mixer.signals.input_gain[0].mult = 0.5
        self._mod_mixers += [mod_mixer]

    def finalize(self, channel, modulators):
        if self.finalized:
            return
        self.norm = self.default_norm
        if self.modulated:
            self._modulators = modulators
            self._create_modulator(channel, modulators)
        self.finalized = True

    def delete(self):
        for plugin in self._mod_shifters + self._mod_mixers:
            plugin.delete()

    @property
    def mod_norms(self):
        ret = [(m.signals.output.value + 32767) / 65534 for m in self._mod_mixers]
        return ret

    def get_modulator_norm(self, modulator_index):
        return self._mod_thou[modulator_index] / 1000

    def set_modulator_norm(self, modulator_index, val):
        if self.modulated:
            intval = int(val * 1000)
            if intval != self._mod_thou[modulator_index]:
                self.mod_norm_changed[modulator_index] = True
                self._mod_thou[modulator_index] = intval
            val = 2 * val - 1
            val = val * abs(val) * 32767
            for m in self._mod_mixers:
                m.signals.input_gain[1 + modulator_index].value = val

    def get_settings(self):
        if not self.finalized:
            return
        settings = {}
        settings["val"] = self._thou
        if self.modulated:
            for x, mod in enumerate(self._modulators):
                settings[mod.name] = self._mod_thou[x]
        return settings

    def set_settings(self, settings):
        if not self.finalized:
            return
        self.norm = settings["val"] / 1000
        if self.modulated:
            for x, mod in enumerate(self._modulators):
                if mod.name in settings.keys():
                    self.set_modulator_norm(x, settings[mod.name] / 1000)
                else:
                    self.set_modulator_norm(x, 0.5)
