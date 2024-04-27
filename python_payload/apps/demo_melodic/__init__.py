from st3m.application import Application
from st3m.ui import colours
import bl00mbox
import leds
import math, os, json, errno

from .pages import *
from .modules.synth import *
from .helpers import *
from .colors import colorthemes


class MelodicApp(Application):
    def __init__(self, app_ctx) -> None:
        super().__init__(app_ctx)

        self.cols = colorthemes["mellow laserz"]

        self.savefile_dir = "/sd/mono_synth"

        self.base_scale = [0, 2, 3, 5, 7, 8, 10]
        self.mid_point_petal = 0

        self.min_note = -45
        self.max_note = +15
        self.mid_point = -15

        self.auto_color = (1, 0.5, 1)
        self.min_hue = 0
        self.max_hue = 0
        self.petal_val = [[None] * 3 for x in range(10)]
        self.petal_index = [7, 9, 1, 3]
        self.petal_block = [True for x in range(10)]

        self._scale = [0] * 10
        self.blm = None

        self.drone_toggle = ToggleParameter("drone")

        self.env_value = 0
        self.lfo_value = 0

        self.enter_done = False

        self._fg_page = None
        # put these in their own class someday
        self._scale_setup_highlight = 0
        self._scale_setup_root = 0
        self._scale_setup_root_mode = False
        self._shift_steps = 4
        self._scale_steps = 1

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, vals):
        new_vals = []
        for val in vals:
            # last resort limiters, these should never trigger
            while val > self.max_note:
                val -= 12
            while val < self.min_note:
                val += 12
            new_vals += [val]
        self._scale = new_vals

    @property
    def fg_page(self):
        return self._fg_page

    @fg_page.setter
    def fg_page(self, new_page):
        if new_page is self._fg_page:
            return
        new_page.full_redraw = True
        if new_page.use_bottom_petals and not self._fg_page.use_bottom_petals:
            if not self.drone_toggle.value:
                for i in range(1, 10, 2):
                    self.poly_squeeze.signals.trigger_in[i].stop()
        self.petal_block = [True for _ in self.petal_block]
        self._fg_page = new_page

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

    def _make_scale(self):
        new_scale = [None] * 10
        i = self.base_scale_get_mod_index_from_val(self.mid_point)
        for j in range(-5, 5):
            tone = self.base_scale_get_val_from_mod_index(i + j * self._scale_steps)
            new_scale[(self.mid_point_petal + j) % 10] = tone
        return new_scale
        
    def make_scale(self):
        self.scale = self._make_scale()

    def _shift_playing_field_by_num_steps(self, num):
        i = self.base_scale_get_mod_index_from_val(self.mid_point)
        self.mid_point = self.base_scale_get_val_from_mod_index(i + num)
        if self._scale_steps < 0:
            num = -num
        self.mid_point_petal += num
        self.mid_point_petal = self.mid_point_petal % 10
        return self._make_scale()

    def shift_playing_field_by_num_steps(self, num):
        new_scale = self._shift_playing_field_by_num_steps(num)
        while min(new_scale) < self.min_note:
            new_scale = self._shift_playing_field_by_num_steps(1)
        while max(new_scale) > self.max_note:
            new_scale = self._shift_playing_field_by_num_steps(-1)
        self.scale = new_scale

    def _shift_playing_field_by_oct(self, num):
        self.mid_point += num * 12
        return self._make_scale()

    def shift_playing_field_by_oct(self, num):
        new_scale = self._shift_playing_field_by_oct(num)
        while min(new_scale) < self.min_note:
            new_scale = self._shift_playing_field_by_oct(1)
        while max(new_scale) > self.max_note:
            new_scale = self._shift_playing_field_by_oct(-1)
        self.scale = new_scale

    def draw(self, ctx):
        if not self.enter_done or self.blm is None:
            self.fg_page.full_redraw = True
            return
        for mod in self.modulators:
            mod.update()
        self.fg_page.draw(ctx, self)

    def draw_title(self, ctx, name):
        ctx.save()
        ctx.font = "Arimo Bold"
        ctx.text_align = ctx.CENTER
        ctx.font_size = 22
        ctx.rgb(*self.cols.alt)
        ctx.line_width = 2
        ctx.arc(0, -180, 95, 0, math.tau, 1).stroke()
        ctx.move_to(0, -97)
        ctx.rgb(*self.cols.fg)
        ctx.text(name)
        ctx.restore()

    def draw_modulator_indicator(self, ctx, text=None, arrow=False, col=None, sub=0):
        ctx.save()
        ctx.font = "Arimo Bold"
        ctx.line_width = 2
        ctx.rgb(*self.cols.bg)
        ctx.arc(0, 150, 100, 0, math.tau, 1).fill()
        ctx.rgb(*self.cols.alt)
        ctx.arc(0, 150, 100, 0, math.tau, 1).stroke()
        rad = 50
        pos = 83
        lr_arrows = False
        if text is None:
            arrow = not sub
            if sub:
                text = self.modulators[sub - 1].name
            else:
                text = "mods"
            lr_arrows = not arrow
        if arrow:
            rad = 45
        if col is None:
            if sub:
                ctx.rgb(*self.cols.hi)
            else:
                ctx.rgb(*self.cols.bg)
        else:
            ctx.rgb(*col)
        if sub:
            rad = 40 + self.modulators[sub - 1].output * 10
        ctx.arc(0, 150, rad, 0, math.tau, 1).fill()
        ctx.rgb(*self.cols.fg)
        ctx.text_align = ctx.CENTER
        ctx.font_size = 19
        if arrow:
            ctx.move_to(-10, pos + 9)
            ctx.rel_line_to(10, 5)
            ctx.rel_line_to(10, -5)
            ctx.stroke()
        if lr_arrows:
            for i in [-1, 1]:
                ctx.move_to(63 * i, 86)
                ctx.rel_line_to(5 * i, 4)
                ctx.rel_line_to(-5 * i, 3)
                ctx.stroke()
        ctx.move_to(0, pos)
        ctx.text(text)
        ctx.restore()

    def draw_bar_graph(
        self, ctx, petal, norms, label, unit=None, sub=0, plusminus=False, skip_redraw=0
    ):
        if petal not in [1, 3, 7, 9]:
            return
        if not type(norms) == list:
            norms = [norms]
        norms = [max(0, min(1, norm)) for norm in norms]
        if unit is None:
            unit = str(norms[0]) + "%"
        if len(norms) == 1 and skip_redraw > 1:
            return

        labelcol = self.cols.alt
        if sub:
            handlecol = self.cols.fg
            barcol = self.cols.alt
            subbarcol = self.cols.alt
            unitcol = self.cols.alt
            framecol = self.cols.hi
        else:
            handlecol = self.cols.alt
            barcol = self.cols.fg
            subbarcol = self.cols.hi
            unitcol = self.cols.hi
            framecol = self.cols.fg

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

        if skip_redraw == 0:
            ctx.move_to(labelstart * sign, -15)
            ctx.text_align = labelalign
            ctx.font_size = labelsize
            ctx.rgb(*labelcol)
            ctx.text(label)

        ctx.move_to(unitend * sign, 10 + unitsize)
        if skip_redraw:
            ctx.rgb(*self.cols.bg)
            ctx.rectangle((unitend - 1) * sign, 13, 80 * sign, 17).fill()

        ctx.rgb(*unitcol)
        ctx.text_align = unitalign
        ctx.font_size = unitsize
        ctx.text(unit)

        if skip_redraw == 0:
            ctx.rgb(*framecol)
            ctx.rectangle(barstart * sign, -10, barlen * sign, 20).stroke()
        elif skip_redraw == 1:
            ctx.rgb(*self.cols.bg)
            ctx.rectangle((barstart + 4) * sign, -6, (barlen - 8) * sign, 12).fill()
        elif skip_redraw == 2:
            ctx.rgb(*self.cols.bg)
            ctx.rectangle((barstart + 4) * sign, 2, (barlen - 8) * sign, 4).fill()

        ctx.rgb(*barcol)

        if len(norms) == 1:
            if plusminus:
                a = 0
                b = 0
                if norms[0] > 0.50001:
                    a = -5
                    b = 10
                elif norms[0] < 0.49999:
                    a = 5
                    b = 10
                ctx.rectangle(
                    (barstart + barlen / 2 - a) * sign,
                    -5,
                    (barlen - 10 - b) * sign * (norms[0] - 0.5),
                    10,
                ).fill()
                ctx.rgb(*handlecol)
                ctx.arc((barstart + barlen / 2) * sign, 0, 4, 0, math.tau, 1).fill()
            else:
                ctx.rectangle(
                    (barstart + 5) * sign, -5, (barlen - 10) * sign * norms[0], 10
                ).fill()
        if len(norms) == 2:
            if skip_redraw != 2:
                if plusminus:
                    width = 5
                    a = 0
                    b = 0
                    if norms[0] > 0.50001:
                        a = -width
                        b = width * 2
                    elif norms[0] < 0.49999:
                        a = width
                        b = width * 2
                    ctx.rectangle(
                        (barstart + barlen / 2 - a) * sign,
                        -5,
                        (barlen - 10 - b) * sign * (norms[0] - 0.5),
                        7,
                    ).fill()
                    ctx.rgb(*handlecol)
                    ctx.arc(
                        (barstart + barlen / 2) * sign, -1.5, 3.5, 0, math.tau, 0
                    ).fill()
                else:
                    ctx.rectangle(
                        (barstart + 5) * sign, -5, (barlen - 10) * sign * norms[0], 7
                    ).fill()
            ctx.rgb(*subbarcol)
            ctx.rectangle(
                (barstart + 5) * sign, 3, (barlen - 10) * sign * norms[1], 2
            ).fill()

        ctx.restore()

    def draw_scope(self, ctx, param):
        ctx.save()
        ctx.rgb(*self.cols.hi)
        ctx.arc(0, 0, 18, 0, math.tau, 1).fill()
        ctx.rgb(*self.cols.bg)
        ctx.rectangle(-18, -18, 36, 36 - param.norm * 36).fill()
        ctx.line_width = 4
        ctx.rgb(*self.cols.fg)
        ctx.arc(0, 0, 25, 0, math.tau, 1).stroke()
        ctx.restore()

    def destroy_synth(self):
        if self.blm is not None:
            self.blm.volume = 0
            self.blm.clear()
            self.blm.free = True
            self.blm = None

    def build_synth(self):
        self.destroy_synth

        self.blm = bl00mbox.Channel("mono synth")
        self.blm.volume = 13000
        self.poly_squeeze = self.blm.new(bl00mbox.plugins.poly_squeeze, 1, 10)

        self.synth = self.blm.new(mix_env)
        self.synth.signals.output = self.blm.mixer
        self.synth.signals.trigger = self.poly_squeeze.signals.trigger_out[0]
        self.synth.signals.pitch = self.poly_squeeze.signals.pitch_out[0]

        mod_envs = [self.blm.new(env) for x in range(2)]
        for mod_env in mod_envs:
            mod_env.always_render = True
            mod_env.signals.trigger = self.poly_squeeze.signals.trigger_out[0]

        self.mixer_page = self.synth.make_mixer_page()

        self.env_page = self.synth.make_env_page(toggle=self.drone_toggle)

        self.modulators = [
            Modulator("lfo 1", self.blm.new(rand_lfo), signal_range=[-2048, 2048]),
            Modulator("lfo 2", self.blm.new(rand_lfo), signal_range=[-2048, 2048]),
            Modulator("env 1", mod_envs[0], signal_range=[0, 4096]),
            Modulator("env 2", mod_envs[1], signal_range=[0, 4096]),
        ]

        sens = self.blm.new(sensors)

        self.modulators += [
            Modulator(
                "sensors", sens, signal_range=[0, 4096], feed_hook=sens.update_data
            ),
        ]

        mod_pages = [mod.patch.make_page(mod.name) for mod in self.modulators]

        self.osc_pages = [None, None]

        for page in [self.mixer_page, self.env_page] + mod_pages:
            page.finalize(self.blm, self.modulators)

        self.scale_page = ScaleSetupPage("scale")
        self.steps_page = StepsPage("steps")

        self.notes_page = SubMenuPage("notes")
        self.sound_page = SubMenuPage("sounds")
        self.config_page = SubMenuPage("config")
        self._abs_path_ = "/flash/sys/apps/demo_melodic"

        oscs = AudioModuleCollection(
            "oscs", self._abs_path_, defaults=["acid", "dream"]
        )
        self.oscs_page = AudioModulePageGroup("oscs", self, OscSelectPage, oscs)
        fx = AudioModuleCollection("fx", self._abs_path_, defaults=["fltr", None])
        self.fx_page = AudioModulePageGroup("fx", self, FxSelectPage, fx)

        self.dyna_page = PageGroup("dyna")
        self.mods_page = PageGroup("mods")
        self.play_page = PlayingPage()

        self.mods_page.children = mod_pages
        self.dyna_page.children = [self.mixer_page] + [self.env_page]
        self.sound_page.menupages = [
            self.oscs_page,
            self.fx_page,
            self.mods_page,
            self.dyna_page,
        ]
        self.sound_page.savepage = SoundSavePage("sound", 5)
        self.notes_page.menupages = [
            self.scale_page,
            DummyPage("arp"),
            DummyPage("bend"),
            DummyPage("steps"),
            #self.steps_page,
        ]
        self.notes_page.savepage = NotesSavePage("notes", 5)
        self.config_page.menupages = [
            DummyPage("ui"),
            DummyPage("conn"),
            DummyPage("idk"),
            DummyPage("???"),
        ]

        self.play_page.children = [self.notes_page, self.sound_page]
        self._fg_page = self.play_page

    def update_leds(self, full_redraw=False):
        norm = self.env_value / 2 + 0.5
        env = [x * norm for x in self.cols.alt]
        norm = self.lfo_value / 2 + 0.5
        lfo = [x * norm for x in self.cols.hi]
        for i in range(0, 40, 8):
            for k in [2]:
                leds.set_rgb((i + k) % 40, *lfo)
            for k in [-2]:
                leds.set_rgb((i + k) % 40, *env)
        if full_redraw:
            for i in range(0, 40, 8):
                for k in [3, -3, 4]:
                    leds.set_rgb((i + k) % 40, *self.cols.fg)
                for k in [0, 1, -1]:
                    leds.set_rgb((i + k) % 40, 0, 0, 0)
        leds.update()

    def on_enter(self, vm):
        super().on_enter(vm)
        self.enter_done = False
        self.build_synth()

        # self.load_sound_settings("autosave.json")
        # self.load_notes_settings("autosave.json")

        self.update_leds(full_redraw=True)
        self.make_scale()

    def on_enter_done(self):
        self.enter_done = True

    def on_exit(self):
        self.save_sound_settings("autosave.json")
        self.save_notes_settings("autosave.json")
        self.destroy_synth()

    def think(self, ins, delta_ms):
        super().think(ins, delta_ms)
        if not self.enter_done:
            return

        if self.input.buttons.app.right.pressed:
            self.fg_page.right_press_event(self)
        if self.input.buttons.app.left.pressed:
            self.fg_page.left_press_event(self)
        if self.input.buttons.app.middle.pressed:
            self.fg_page.down_press_event(self)

        for mod in self.modulators:
            mod.feed(ins, delta_ms)
        self.update_leds()

        for i in range(0, 10, 2 if self.fg_page.use_bottom_petals else 1):
            if self.input.captouch.petals[i].whole.pressed:
                self.poly_squeeze.signals.pitch_in[i].tone = self.scale[i]
                self.poly_squeeze.signals.trigger_in[i].start()
            elif (
                self.input.captouch.petals[i].whole.released
                and not self.drone_toggle.value
            ):
                self.poly_squeeze.signals.trigger_in[i].stop()

        if self.drone_toggle.changed and not self.drone_toggle.value:
            for i in range(10):
                if not ins.captouch.petals[i].pressed:
                    self.poly_squeeze.signals.trigger_in[i].stop()
            self.drone_toggle.changed = False

        if self.fg_page.use_bottom_petals:
            for petal in [7, 9, 1, 3]:
                petal_len = len(self.petal_val[petal])
                pressed = ins.captouch.petals[petal].pressed
                if pressed and not self.petal_block[petal]:
                    val = (ins.captouch.petals[petal].position[0] + 15000) / 34000
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
                    if not pressed:
                        self.petal_block[petal] = False
                    for i in range(petal_len):
                        self.petal_val[petal][i] = None

        self.fg_page.think(ins, delta_ms, self)

    def get_sound_settings(self):
        return self.sound_page.get_settings()

    def set_sound_settings(self, settings):
        self.sound_page.set_settings(settings)

    def get_notes_settings(self):
        notes_settings = {
            "base scale": self.base_scale,
            "mid point": self.mid_point,
            "mid point petal": self.mid_point_petal,
        }
        return notes_settings

    def set_notes_settings(self, settings):
        self.base_scale = settings["base scale"]
        self.mid_point = settings["mid point"]
        self.mid_point_petal = settings["mid point petal"]
        self.make_scale()

    def load_sound_settings_file(self, filename):
        path = self.savefile_dir + "/sounds/" + filename
        settings = None
        try:
            with open(path, "r") as f:
                return json.load(f)
        except OSError as e:
            return

    def load_sound_settings(self, filename):
        settings = self.load_sound_settings_file(filename)
        if settings is not None:
            self.set_sound_settings(settings)
        else:
            print("could not load sound settings")

    def save_sound_settings(self, filename):
        settings = self.get_sound_settings()
        old_settings = self.load_sound_settings_file(filename)
        if old_settings is not None:
            if dicts_match_recursive(old_settings, settings):
                return
        path = self.savefile_dir + "/sounds"
        try:
            fakemakedirs(path, exist_ok=True)
            path += "/" + filename
            with open(path, "w+") as f:
                f.write(json.dumps(settings))
                f.close()
        except OSError as e:
            print("could not save sound settings")

    def delete_sound_settings(self, filename):
        path = self.savefile_dir + "/sounds/" + filename
        try:
            os.remove(path)
            return True
        except OSError:
            return False

    def load_notes_settings_file(self, filename):
        path = self.savefile_dir + "/notes/" + filename
        try:
            with open(path, "r") as f:
                return json.load(f)
        except OSError as e:
            return

    def load_notes_settings(self, filename):
        settings = self.load_notes_settings_file(filename)
        if settings is not None:
            self.set_notes_settings(settings)
        else:
            print("could not load notes settings")

    def save_notes_settings(self, filename):
        settings = self.get_notes_settings()
        old_settings = self.load_notes_settings_file(filename)
        if old_settings is not None:
            if dicts_match_recursive(old_settings, settings):
                return
        path = self.savefile_dir + "/notes"
        try:
            fakemakedirs(path, exist_ok=True)
            path += "/" + filename
            with open(path, "w+") as f:
                f.write(json.dumps(settings))
                f.close()
        except OSError as e:
            print("could not save notes settings")

    def delete_notes_settings(self, filename):
        path = self.savefile_dir + "/notes/" + filename
        try:
            os.remove(path)
            return True
        except OSError:
            return False


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(MelodicApp)
