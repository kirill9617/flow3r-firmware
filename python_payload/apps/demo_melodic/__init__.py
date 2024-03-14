from st3m.application import Application
from st3m.ui import colours
import bl00mbox
import leds
import math, os, json, errno

from .ui import colorthemes
from .ui.pages.osc_page import OscPage
from .ui.pages.scale_page import ScalePage
from .ui.pages.synth import ToggleParameter, Modulator
from .audio.synth import *
from .helpers import *
from .audio import oscs


class MelodicApp(Application):
    def __init__(self, app_ctx) -> None:
        super().__init__(app_ctx)

        self.cols = colorthemes["standard"]

        self.savefile_dir = "/sd/mono_synth"

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

        self.enter_done = False

        self._scale_setup_highlight = 0
        self._scale_setup_root = 0
        self._scale_setup_root_mode = False

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
        if not self.enter_done and not self.mode_main:
            self.pages[self.active_page].full_redraw = True
        for mod in self.modulators:
            mod.update()
        if self.mode_main:
            self.draw_main(ctx)
            return
        self.pages[self.active_page].draw(ctx, self)

    def draw_title(self, ctx, name):
        ctx.save()
        ctx.font = "Arimo Bold"
        ctx.text_align = ctx.CENTER
        ctx.font_size = 22
        ctx.rgb(*self.cols.fg)
        ctx.arc(0, -180, 95, 0, math.tau, 1).fill()
        ctx.move_to(0, -97)
        ctx.rgb(*self.cols.bg)
        ctx.text(name)
        ctx.restore()

    def draw_modulator_indicator(self, ctx, text=None, arrow=False, col=None, sub=0):
        ctx.save()
        ctx.font = "Arimo Bold"
        ctx.rgb(*self.cols.fg)
        ctx.arc(0, 150, 100, 0, math.tau, 1).fill()
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
                ctx.rgb(*self.cols.fg)
        else:
            ctx.rgb(*col)
        if sub:
            rad = 40 + self.modulators[sub - 1].output * 10
        ctx.arc(0, 150, rad, 0, math.tau, 1).fill()
        ctx.rgb(*self.cols.bg)
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

    def draw_main(self, ctx):
        ctx.rgb(*self.cols.bg).rectangle(-120, -120, 240, 240).fill()
        ctx.text_align = ctx.CENTER

        pos = [x * 0.87 + 85 for x in self.scale]
        start = [math.tau * (0.75 - 0.04 + i / 10) for i in range(10)]
        stop = [math.tau * (0.75 + 0.04 + i / 10) for i in range(10)]

        ctx.rgb(*self.cols.fg)
        ctx.line_width = 35
        for i in range(10):
            ctx.arc(0, 0, pos[i], start[i], stop[i], 0).stroke()
        ctx.line_width = 4
        ctx.rgb(*[x * 0.75 for x in self.cols.fg])
        for i in range(10):
            ctx.arc(0, 0, pos[i] - 26, start[i], stop[i], 0).stroke()
        ctx.rgb(*[x * 0.5 for x in self.cols.fg])
        for i in range(10):
            ctx.arc(0, 0, pos[i] - 36, start[i], stop[i], 0).stroke()

        ctx.rotate(-math.tau / 4)
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"
        ctx.font_size = 20
        ctx.rgb(*self.cols.bg)
        for i in range(10):
            ctx.rgb(*self.cols.bg)
            ctx.move_to(pos[i], 6)
            note = bl00mbox.helpers.sct_to_note_name(self.scale[i] * 200 + 18367)
            ctx.text(note[:-1])
            ctx.rotate(math.tau / 10)

        ctx.rotate(math.tau * (self.mid_point_petal + 4.5) / 10)
        ctx.rgb(*self.cols.bg)
        ctx.line_width = 8
        ctx.move_to(0, 0)
        ctx.line_to(120, 0).stroke()
        ctx.rgb(*self.cols.hi)
        ctx.line_width = 1
        ctx.move_to(3, 0)
        ctx.line_to(120, 0).stroke()

    def _build_osc(self, osc_target, slot):
        if self.blm is None:
            return
        if slot > len(self.osc_pages):
            return

        if osc_target is None:
            if self.osc_pages[slot] is not None:
                self.osc_pages[slot].delete()
            self.osc_pages[slot] = None
            self.mixer_page.params[slot].name = "/"
        else:
            if self.osc_pages[slot] is None:
                pass
            elif isinstance(self.osc_pages[slot], osc_target):
                return
            else:
                self.osc_pages[slot].delete()
            osc = self.blm.new(osc_target)
            osc.signals.pitch = self.synth.signals.osc_pitch[slot]
            osc.signals.output = self.synth.signals.osc_input[slot]
            self.mixer_page.params[slot * 3].display_name = osc.name
            page = osc.make_page()
            page.finalize(self.blm, self.modulators)
            self.osc_pages[slot] = page

        pages = []
        pages += [self.scale_page] + [self.osc_page] + [self.mixer_page]
        pages += [page for page in self.osc_pages if page is not None]
        pages += self.synth_pages
        self.pages = pages
        print(self.blm)

    def _build_synth(self):
        if self.blm is None:
            self.blm = bl00mbox.Channel("mono synth")
            self.blm.volume = 13000
            self.poly_squeeze = self.blm.new(bl00mbox.plugins.poly_squeeze, 1, 10)

            self.synth = self.blm.new(mix_env_filt)
            self.synth.signals.output = self.blm.mixer
            self.synth.signals.trigger = self.poly_squeeze.signals.trigger_out[0]
            self.synth.signals.pitch = self.poly_squeeze.signals.pitch_out[0]

            mod_envs = [self.blm.new(env) for x in range(2)]
            for mod_env in mod_envs:
                mod_env.always_render = True
                mod_env.signals.trigger = self.poly_squeeze.signals.trigger_out[0]

            self.mixer_page = self.synth.make_mixer_page()

            self.synth_pages = []
            self.synth_pages += [self.synth.make_filter_page()]
            self.synth_pages += [self.synth.make_env_page(toggle=self.drone_toggle)]

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
            self.synth_pages += [MultiPage("mods", mod_pages)]

            self.osc_pages = [None, None]

            for page in self.synth_pages + [self.mixer_page]:
                page.finalize(self.blm, self.modulators)

        self.scale_page = ScalePage()
        self.osc_page = OscPage(oscs.osc_list)

    def update_leds(self, init=False):
        norm = self.env_value / 2 + 0.5
        env = [x * norm for x in self.cols.alt]
        norm = self.lfo_value / 2 + 0.5
        lfo = [x * norm for x in self.cols.hi]
        for i in range(0, 40, 8):
            for k in [2]:
                leds.set_rgb((i + k) % 40, *lfo)
            for k in [-2]:
                leds.set_rgb((i + k) % 40, *env)
        if init:
            for i in range(0, 40, 8):
                for k in [3, -3, 4]:
                    leds.set_rgb((i + k) % 40, *self.cols.fg)
                for k in [0, 1, -1]:
                    leds.set_rgb((i + k) % 40, 0, 0, 0)
        leds.update()

    def on_enter(self, vm):
        self.pages = []
        super().on_enter(vm)
        oscs.update_oscs("/flash/sys/apps/demo_melodic")
        if self.blm is None:
            self._build_synth()
        self.blm.foreground = True
        self.make_scale()
        self.update_leds(init=True)
        self.enter_done = False
        if not self.mode_main:
            self.pages[self.active_page].full_redraw = True
        self.load_sound_settings("autosave.json")
        self.load_notes_settings("autosave.json")
        if self.osc_pages[0] is None:
            self._build_osc(oscs.get_osc_by_name("acid"), 0)
        if self.osc_pages[1] is None:
            self._build_osc(oscs.get_osc_by_name("dream"), 1)

    def on_enter_done(self):
        self.enter_done = True

    def on_exit(self):
        if self.blm is not None:
            self.blm.volume = 0
        self.save_sound_settings("autosave.json")
        self.save_notes_settings("autosave.json")
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

    def think(self, ins, delta_ms):
        super().think(ins, delta_ms)

        if self.blm is None:
            return

        for mod in self.modulators:
            mod.feed(ins, delta_ms)

        if self.mode_main:
            playable_petals = range(10)
        else:
            playable_petals = range(0, 10, 2)

        """
        petals = []
        for i in playable_petals:
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
        """

        for i in playable_petals:
            if self.input.captouch.petals[i].whole.pressed:
                self.poly_squeeze.signals.pitch_in[i].tone = self.scale[i]
                self.poly_squeeze.signals.trigger_in[i].start()
            elif (
                self.input.captouch.petals[i].whole.released
                and not self.drone_toggle.value
            ):
                self.poly_squeeze.signals.trigger_in[i].stop()

        self.update_leds()

        if self.input.buttons.app.middle.pressed:
            self.mode_main = not self.mode_main
            if not self.mode_main:
                self.pages[self.active_page].full_redraw = True
                if not self.drone_toggle.value:
                    for i in range(1, 10, 2):
                        self.poly_squeeze.signals.trigger_in[i].stop()

        if self.drone_toggle.changed and not self.drone_toggle.value:
            for i in range(10):
                if not ins.captouch.petals[i].pressed:
                    self.poly_squeeze.signals.trigger_in[i].stop()
            self.drone_toggle.changed = False

        lr_dir = (
            self.input.buttons.app.right.pressed - self.input.buttons.app.left.pressed
        )
        if lr_dir:
            if self.mode_main:
                self.shift_playing_field_by_num_petals(4 * lr_dir)
            else:
                if not self.pages[self.active_page].locked:
                    self.active_page = (self.active_page + lr_dir) % len(self.pages)
                    self.pages[self.active_page].full_redraw = True
                    if self.pages[self.active_page].reset_on_enter:
                        self.pages[self.active_page].subwindow = 0

        if self.mode_main:
            return

        for petal in [7, 9, 1, 3]:
            petal_len = len(self.petal_val[petal])
            if ins.captouch.petals[petal].pressed:
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
                for i in range(petal_len):
                    self.petal_val[petal][i] = None

        tmp = ins.captouch.petals[5].pressed
        if tmp != self.petal_val[5]:
            if self.petal_val[5] == False:
                self.pages[self.active_page].subwindow += 1
                self.pages[self.active_page].full_redraw = True
            self.petal_val[5] = tmp

        self.pages[self.active_page].think(ins, delta_ms, self)

    def get_sound_settings(self):
        sound_settings = {}
        for page in self.synth_pages + [self.mixer_page]:
            sound_settings[page.name] = page.get_settings()
        osc_settings = []
        for page in self.osc_pages:
            if page is not None:
                settings = {}
                settings["params"] = page.get_settings()
                settings["type"] = page.patch.name
                osc_settings += [settings]
        sound_settings["oscs"] = osc_settings
        return sound_settings

    def get_notes_settings(self):
        notes_settings = {
            "base scale": self.base_scale,
            "mid point": self.mid_point,
            "mid point petal": self.mid_point_petal,
        }
        return notes_settings

    def set_sound_settings(self, settings):
        for page in self.synth_pages + [self.mixer_page]:
            if page.name in settings.keys():
                page.set_settings(settings[page.name])
            else:
                print(f"no setting found for {page.name}")

        if "oscs" in settings.keys():
            for x, osc in enumerate(settings["oscs"]):
                name = osc["type"]
                osc_type = oscs.get_osc_by_name(name)
                if osc_type is not None:
                    self._build_osc(osc_type, x)
                    self.osc_pages[x].set_settings(osc["params"])
                else:
                    print(f"couldn't find osc type {name}")
        else:
            print("no setting found for oscs")

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
            if dict_contains_dict(old_settings, settings):
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
            if dict_contains_dict(old_settings, settings):
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
