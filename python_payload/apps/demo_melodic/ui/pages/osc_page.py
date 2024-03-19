from . import *


class SoundSavePage(SavePage):
    def draw_saveslot(self, ctx, slot, geometry):
        xsize, ysize, center, yoffset = geometry
        names = self._slot_content[slot]
        names = names[:1] + ["x"] + names[1:]
        ctx.save()
        ctx.font_size = 16
        for i, name in enumerate(names):
            ctx.move_to(center, yoffset + ysize / 4 + 14 * i - 15)
            ctx.text(name)
        ctx.restore()

    def load(self, app):
        app.load_sound_settings(self.slotpath())
        print("sound loaded from " + self.slotpath())

    def save(self, app):
        app.save_sound_settings(self.slotpath())
        print("sound saved to " + self.slotpath())

    def delete(self, app):
        app.delete_sound_settings(self.slotpath())
        print("sound deleted at " + self.slotpath())

    def load_files(self, app):
        for i in range(self.num_slots):
            settings = app.load_sound_settings_file(self.slotpath(i))
            if settings is None:
                self._slot_content[i] = None
            else:
                if "oscs" in settings.keys():
                    names = []
                    for x, osc in enumerate(settings["oscs"]):
                        names += [osc["type"]]
                    self._slot_content[i] = names
                else:
                    self._slot_content[i] = ["???"]
        self.full_redraw = True


class OscSetupPage(Page):
    def __init__(self, name, osc_list):
        super().__init__(name)
        self._osc_type = [0, 0]
        self.osc_list = osc_list

    def think(self, ins, delta_ms, app):
        for i in range(2):
            if app.osc_pages[i] is not None:
                if self.osc_list[self._osc_type[i]] != type(app.osc_pages[i].patch):
                    self._osc_type[i] = self.osc_list.index(
                        type(app.osc_pages[i].patch)
                    )
        for osc, petal, plusminus in [[0, 7, 1], [0, 9, -1], [1, 3, 1], [1, 1, -1]]:
            if app.input.captouch.petals[petal].whole.pressed:
                self._osc_type[osc] = (self._osc_type[osc] + plusminus) % len(
                    self.osc_list
                )
                app._build_osc(self.osc_list[self._osc_type[osc]], osc)

    def draw(self, ctx, app):
        ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
        app.draw_title(ctx, self.display_name)
        # app.draw_modulator_indicator(ctx, "save/load", col=app.cols.fg, arrow=True)
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"

        for k in range(2):
            ctx.save()
            x = (k * 2 - 1) * 65
            y = -5
            rot = (1 - k * 2) * 0.5 * math.tau / 60
            ctx.translate(x, y)
            ctx.rotate(rot)
            ctx.translate(-x, -y)
            for i in range(3):
                j = (self._osc_type[k] + i - 1) % len(self.osc_list)
                rot = (1 - k * 2) * (1 - i) * math.tau / 60
                x = (k * 2 - 1) * 67
                y = i * 40 - 52
                ctx.font_size = 20
                xsize = 80
                ysize = 30
                ctx.save()
                if i != 1:
                    ctx.font_size *= 0.8
                    xsize *= 0.8
                    ysize *= 0.8
                    x *= 0.67
                    ctx.global_alpha *= 0.8
                ctx.translate(x, y)
                ctx.rotate(rot)
                ctx.translate(-x, -y)
                ctx.line_width = 3
                ctx.rgb(*app.cols.fg)
                ctx.round_rectangle(
                    x - xsize / 2, y - 5 - ysize / 2, xsize, ysize, 5
                ).stroke()
                ctx.rgb(*app.cols.alt)
                ctx.move_to(x, y)
                ctx.text(self.osc_list[j].name)
                ctx.restore()
            ctx.restore()

        ctx.rgb(*app.cols.hi)

        # arrows
        for sign in [-1, 1]:
            ctx.move_to(100 * sign, 50)
            ctx.rel_line_to(-4, -6)
            ctx.rel_line_to(8, 0)
            ctx.rel_line_to(-4, 6)
            ctx.stroke()

            ctx.move_to(70 * sign, -93)
            ctx.rel_line_to(-4, 6)
            ctx.rel_line_to(8, 0)
            ctx.rel_line_to(-4, -6)
            ctx.stroke()
