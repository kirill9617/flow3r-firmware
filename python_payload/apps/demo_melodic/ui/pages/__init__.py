import math
import bl00mbox


class Page:
    def __init__(self, name):
        self.name = name
        self.display_name = name
        self.params = []
        self.scope_param = None
        self.toggle = None
        self.subwindow = 0
        self.finalized = False
        self.full_redraw = True

    def think(self, ins, delta_ms, app):
        pass

    def draw(self, ctx, app):
        pass

    def get_settings(self):
        return None

    def set_settings(self):
        pass


class SavePage(Page):
    def load(self, app):
        pass

    def save(self, app):
        pass

    def delete(self, app):
        pass

    def draw_saveslot(self, ctx, slot, geometry):
        pass

    def load_files(self, app):
        pass

    def __init__(self, name, slots):
        super().__init__(name)
        self.num_slots = slots
        self.hold_time = 1500
        self._slot_content = [None] * self.num_slots

        self._slot = 0
        self._slot_notes = [None] * self.num_slots
        self._save_timer = 0
        self._load_timer = 0
        self._load_files_request = True

    def slotpath(self, num=None):
        if num is None:
            num = self._slot
        return "slot" + str(num + 1) + ".json"

    def think(self, ins, delta_ms, app):
        if app.input.captouch.petals[7].whole.pressed:
            self._slot = (self._slot - 1) % self.num_slots
            self.full_redraw = True
        if app.input.captouch.petals[3].whole.pressed:
            self._slot = (self._slot + 1) % self.num_slots
            self.full_redraw = True

        if ins.captouch.petals[1].pressed:
            if self._save_timer < self.hold_time:
                self._save_timer += delta_ms
                if self._save_timer >= self.hold_time and not self._load_timer:
                    self.save(app)
                    self._load_files_request = True
        else:
            self._save_timer = 0

        if ins.captouch.petals[9].pressed:
            if self._load_timer < self.hold_time:
                self._load_timer += delta_ms
                if self._load_timer >= self.hold_time and not self._save_timer:
                    if self._slot_content[self._slot] is not None:
                        self.load(app)
        else:
            self._load_timer = 0

        if (self._load_timer + self._save_timer) >= (2 * self.hold_time):
            if self._load_timer < 33333 and (
                self._slot_content[self._slot] is not None
            ):
                self.delete(app)
                self._load_timer = 33333
                self._load_files_request = True

        if self._load_files_request:
            self.load_files(app)
            self._load_files_request = False

    def draw(self, ctx, app):
        if self.full_redraw:
            app.draw_modulator_indicator(ctx, "save/load", col=app.cols.hi)
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
                self.draw_saveslot(ctx, j, [xsize, ysize, center, yoffset])

            if highlight:
                ctx.global_alpha = 1
                xs = center - xsize / 2
                yw = ysize / 2
                if self._save_timer and self._load_timer:
                    if load_possible:
                        ctx.rgb(*app.cols.bg)
                        ybar = self._save_timer + self._load_timer
                        ybar = 2 * self.hold_time
                        ybar = min(ybar, 1) * ysize / 2
                        ctx.rectangle(xs, yoffset - yw, xsize, ybar).fill()
                        ctx.rectangle(xs, yoffset - ybar + yw, xsize, ybar).fill()
                        ctx.rgb(*app.cols.alt)
                        ctx.line_width = 2
                        ctx.move_to(xs, yoffset + ybar - yw)
                        ctx.rel_line_to(xsize, 0).stroke()
                        ctx.move_to(xs, yoffset - ybar + yw)
                        ctx.rel_line_to(xsize, 0).stroke()
                elif self._save_timer:
                    ctx.rgb(*app.cols.alt)
                    ybar = ysize * min(self._save_timer / self.hold_time, 1)
                    ctx.rectangle(xs, yoffset - ybar + yw, xsize, ybar).fill()
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
