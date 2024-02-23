from . import *


class ScalePage(SavePage):
    def __init__(self):
        super().__init__("notes", 5)

    def draw_saveslot(self, ctx, slot, geometry):
        xsize, ysize, center, yoffset = geometry
        notes = list(self._slot_content[slot])
        for k in range(12):
            dotsize = 9
            dotspace = 13
            doty = ((k // 4) * dotspace) - 11
            dotx = ((k % 4) - 1.5) * dotspace
            if k in notes:
                ctx.round_rectangle(
                    center + dotx - dotsize / 2,
                    doty - dotsize / 2,
                    dotsize,
                    dotsize,
                    2,
                ).fill()

    def load(self, app):
        app.load_notes_settings(self.slotpath())
        print("notes loaded from " + self.slotpath())

    def save(self, app):
        app.save_notes_settings(self.slotpath())
        print("notes saved to " + self.slotpath())

    def delete(self, app):
        app.delete_notes_settings(self.slotpath())
        print("notes deleted at " + self.slotpath())

    def think(self, ins, delta_ms, app):
        self.subwindow %= 2
        if self.subwindow == 0:
            self.think_scale_setup(ins, delta_ms, app)
        elif self.subwindow == 1:
            super().think(ins, delta_ms, app)

    def draw(self, ctx, app):
        if self.full_redraw:
            ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
            app.draw_title(ctx, self.display_name)
        if self.subwindow == 0:
            self.draw_scale_setup(ctx, app)
        elif self.subwindow == 1:
            super().draw(ctx, app)

    def think_scale_setup(self, ins, delta_ms, app):
        root_shift = 0
        if app.input.captouch.petals[7].whole.pressed:
            app._scale_setup_highlight = (app._scale_setup_highlight - 1) % 12
            if app._scale_setup_root_mode:
                app._scale_setup_root = (app._scale_setup_root - 1) % 12
                root_shift = -1
        if app.input.captouch.petals[3].whole.pressed:
            app._scale_setup_highlight = (app._scale_setup_highlight + 1) % 12
            if app._scale_setup_root_mode:
                app._scale_setup_root = (app._scale_setup_root + 1) % 12
                root_shift = 1

        if app.input.captouch.petals[9].whole.pressed:
            app._scale_setup_root_mode = True

        if root_shift != 0:
            new_scale = [(x + root_shift) % 12 for x in app.base_scale]
            new_scale.sort()
            app.base_scale = new_scale
            app.make_scale()

        if app.input.captouch.petals[1].whole.pressed:
            if app._scale_setup_root_mode:
                app._scale_setup_root_mode = False
            else:
                index = app._scale_setup_highlight
                new_scale = list(app.base_scale)
                if index in new_scale:
                    new_scale.remove(index)
                else:
                    new_scale += [index]
                new_scale.sort()
                app.base_scale = new_scale
                app.make_scale()

    def draw_scale_setup(self, ctx, app):
        app.draw_modulator_indicator(ctx, "save/load", col=app.cols.fg, arrow=True)
        ctx.rgb(*app.cols.hi)
        if app._scale_setup_root_mode:
            # note
            ctx.arc(68, -84, 2, 0, math.tau, 0)
            ctx.move_to(68 + 2, -84)
            ctx.rel_line_to(0, -7)
            ctx.rel_line_to(3, 2)
            ctx.stroke()
        else:
            # bars
            ctx.rectangle(68 - 2, -85, 3, 3).stroke()
            ctx.rectangle(68 + 2, -85, 3, -6).stroke()
        # root
        ctx.move_to(-68 + 3, -91)
        ctx.rel_line_to(-6, 0)
        ctx.rel_line_to(-3, 9)
        ctx.rel_line_to(-2, -6)
        ctx.stroke()
        # arrows
        for sign in [-1, 1]:
            ctx.move_to(100 * sign, 50)

            ctx.rel_line_to(-6 * sign, -4)
            ctx.rel_line_to(0, 8)
            ctx.rel_line_to(6 * sign, -4)
            ctx.stroke()

        ctx.text_align = ctx.LEFT
        radius = 500
        ctx.translate(0, radius - 25)
        ctx.rotate(0.25 * math.tau)
        step = 0.033
        oversize = 1.2
        if app._scale_setup_root_mode:
            oversize = 1
        ctx.rotate((-4.5 - oversize) * step)
        ctx.font_size = 16
        ctx.font = "Arimo Bold"
        for tone in range(12):
            tone = (tone + app._scale_setup_root) % 12
            note = bl00mbox.helpers.sct_to_note_name(tone * 200 + 18367)
            active = tone in app.base_scale
            size = 1
            if tone == app._scale_setup_highlight and not app._scale_setup_root_mode:
                size = oversize
            if size > 1:
                size = 1.5
                ctx.rotate((oversize - 1) * step)
                ctx.rgb(*app.cols.alt)
                if active:
                    ctx.rectangle(-radius - 5, -5 * size, -20 * size, 10 * size).fill()
                ctx.rectangle(-radius - 5, -5 * size, -20 * size, 10 * size).stroke()
                ctx.rgb(*app.cols.fg)
                if not active:
                    ctx.rectangle(-radius, -5 * size, 10 * size, 10 * size).fill()
                ctx.rectangle(-radius, -5 * size, 10 * size, 10 * size).stroke()
            else:
                if active:
                    ctx.rgb(*app.cols.alt)
                    ctx.rectangle(-radius - 5, -5, -20, 10)
                else:
                    ctx.rgb(*app.cols.fg)
                    ctx.rectangle(-radius, -5, 10, 10)
                if not app._scale_setup_root_mode:
                    ctx.fill()
                else:
                    ctx.rgb(*app.cols.fg)
                    ctx.stroke()

            if app._scale_setup_root_mode:
                ctx.rgb(*app.cols.alt)
            else:
                ctx.rgb(*app.cols.fg)
            ctx.move_to(22 - radius, 5)
            ctx.text(note[:-1])
            ctx.rotate(step)
            if size > 1:
                ctx.rotate((oversize - 1) * step)

    def load_files(self, app):
        for i in range(self.num_slots):
            settings = app.load_notes_settings_file(self.slotpath(i))
            if settings is None:
                self._slot_content[i] = None
            else:
                self._slot_content[i] = list(settings["base scale"])
        self.full_redraw = True

    def draw_scale_saveload(self, ctx, app):
        if self.full_redraw:
            app.draw_modulator_indicator(ctx, "return", col=app.cols.hi)
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"
        ctx.save()
        load_possible = False
        for i in range(3):
            ctx.line_width = 3
            j = i
            if self._slot > (self.num_slots - 2):
                j += self._slot - 2
            elif self._slot > 1:
                j += self._slot - 1
            highlight = self._slot == j
            if (not highlight) and (not self.full_redraw):
                continue

            xsize = 60
            ysize = 80
            center = (i - 1) * 70
            yoffset = -10
            ctx.rgb(*app.cols.bg)
            ctx.rectangle(
                center - 3 - xsize / 2, yoffset - 3 - ysize / 2, xsize + 6, ysize + 6
            ).fill()

            ctx.global_alpha = 0.5
            ctx.font_size = 20
            ctx.rgb(*app.cols.fg)

            if highlight:
                if self._slot_content[j] is not None:
                    load_possible = True
                ctx.global_alpha = 1
                if self._save_timer:
                    pass
                elif self._load_timer and load_possible:
                    ybar = ysize * min(self._load_timer / self.hold_time, 1)
                    ctx.rectangle(
                        center - xsize / 2, yoffset - ybar + ysize / 2, xsize, ybar
                    ).fill()

            ctx.rgb(*app.cols.alt)
            if self._slot_content[j] is None:
                ctx.move_to(center, yoffset + 5)
                ctx.text(self.slotpath(j).split(".")[0])
            else:
                ctx.move_to(center, yoffset - ysize / 4 + 5)
                ctx.text(self.slotpath(j).split(".")[0])
                notes = list(self._slot_content[j])
                for k in range(12):
                    dotsize = 9
                    dotspace = 13
                    doty = ((k // 4) * dotspace) - 11
                    dotx = ((k % 4) - 1.5) * dotspace
                    if k in notes:
                        ctx.round_rectangle(
                            center + dotx - dotsize / 2,
                            doty - dotsize / 2,
                            dotsize,
                            dotsize,
                            2,
                        ).fill()

            if highlight:
                ctx.global_alpha = 1
                if self._save_timer and self._load_timer:
                    if load_possible:
                        ctx.rgb(*app.cols.bg)
                        ybar = (
                            ysize
                            * min(
                                (self._save_timer + self._load_timer)
                                / (2 * self.hold_time),
                                1,
                            )
                            / 2
                        )
                        ctx.rectangle(
                            center - xsize / 2, yoffset - ysize / 2, xsize, ybar
                        ).fill()
                        ctx.rectangle(
                            center - xsize / 2, yoffset - ybar + ysize / 2, xsize, ybar
                        ).fill()
                        ctx.rgb(*app.cols.alt)
                        ctx.line_width = 2
                        ctx.move_to(
                            center - xsize / 2, yoffset + ybar - ysize / 2
                        ).rel_line_to(xsize, 0).stroke()
                        ctx.move_to(
                            center - xsize / 2, yoffset - ybar + ysize / 2
                        ).rel_line_to(xsize, 0).stroke()
                elif self._save_timer:
                    ctx.rgb(*app.cols.alt)
                    ybar = ysize * min(self._save_timer / self.hold_time, 1)
                    ctx.rectangle(
                        center - xsize / 2, yoffset - ybar + ysize / 2, xsize, ybar
                    ).fill()
            ctx.line_width = 3
            ctx.rgb(*app.cols.fg)
            ctx.round_rectangle(
                center - 1 - xsize / 2, yoffset - 1 - ysize / 2, xsize + 2, ysize + 2, 5
            ).stroke()

        ctx.restore()

        if self.full_redraw:
            ctx.rgb(*app.cols.bg)
            ctx.rectangle(-21, -66 - 16, 42, 18).fill()
            ctx.rectangle(-21 - 63, -74 - 18, 42, 20).fill()

            ctx.rgb(*app.cols.hi)

            if load_possible:
                ctx.global_alpha = 1
            else:
                ctx.global_alpha = 0.5
            ctx.font_size = 14
            ctx.move_to(0, -66)
            ctx.text("delete")
            ctx.font_size = 16
            ctx.move_to(-63, -74)
            ctx.text("load")

            start_deg = 1.1 / 40
            stop_deg = 1.65 / 40
            ctx.arc(
                0,
                -130 - 100,
                60 + 100,
                math.tau * (0.25 + start_deg),
                math.tau * (0.25 + stop_deg),
                0,
            ).stroke()
            ctx.arc(
                0,
                -130 - 100,
                60 + 100,
                math.tau * (0.25 - stop_deg),
                math.tau * (0.25 - start_deg),
                0,
            ).stroke()

            ctx.global_alpha = 1

            ctx.move_to(63, -74)
            ctx.text("save")

            # arrows
            for sign in [-1, 1]:
                ctx.move_to(100 * sign, 50)
                ctx.rel_line_to(-6 * sign, -4)
                ctx.rel_line_to(0, 8)
                ctx.rel_line_to(6 * sign, -4)
                ctx.stroke()

            self.full_redraw = False
