from . import *


class NotesSavePage(SavePage):
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

    def load_slot_content(self, app):
        for i in range(self.num_slots):
            settings = app.load_notes_settings_file(self.slotpath(i))
            if settings is None or "base scale" not in settings.keys():
                self._slot_content[i] = None
            else:
                self._slot_content[i] = list(settings["base scale"])


class ScaleSetupPage(Page):
    def think(self, ins, delta_ms, app):
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

    def draw(self, ctx, app):
        ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
        app.draw_title(ctx, self.display_name)
        if app._scale_setup_root_mode:
            app.draw_modulator_indicator(ctx, "root shift", col=app.cols.fg, arrow=True)
        else:
            app.draw_modulator_indicator(
                ctx, "note select", col=app.cols.fg, arrow=True
            )
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
