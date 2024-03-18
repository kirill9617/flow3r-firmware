import math
import bl00mbox


class Page:
    def __init__(self, name):
        # TODO: clean up this mess
        self.name = name
        self.display_name = name
        self.params = []
        self.scope_param = None
        self.toggle = None
        self.subwindow = 0
        self.finalized = False
        self.full_redraw = True
        self.locked = False
        self.reset_on_enter = True
        self.hide_footer = False
        self.hide_header = False
        self.parent = None
        self._prev_child = None
        self._children = []
        self._child_index = None
        self.use_bottom_petals = True
        self.ghost = False

    def think(self, ins, delta_ms, app):
        pass

    def draw(self, ctx, app):
        pass

    def get_settings(self):
        settings = {}
        for child in self.children:
            settings[child.name] = child.get_settings()
        return settings

    def set_settings(self, settings):
        for child in self.children:
            if child.name in settings.keys():
                child.set_settings(settings[child.name])

    def finalize(self, channel, modulators):
        for child in self.children:
            child.finalize(channel, modulators)

    @property
    def children(self):
        return self._children
    
    @children.setter
    def children(self, vals):
        for x, child in enumerate(vals):
            child.parent = self
            child._child_index = x
        self._children = vals

    @property
    def prev_child(self):
        if self._prev_child is not None:
            return self._prev_child
        elif len(self.children):
            return self.children[0]
        else:
            return None
    
    @prev_child.setter
    def prev_child(self, val):
        self._prev_child = val


    def scroll_to_child(self, app, child_index = None):
        scrolled = False
        if child_index is not None and child_index < len(self.children):
            candidate = self.children[child_index]
        else:
            candidate = self.prev_child
        inspected = []
        while candidate is not None or candidate in inspected:
            inspected += [candidate]
            if not candidate.ghost:
                app.fg_page = candidate
                scrolled = True
                break
            candidate = candidate.prev_child
        return scrolled

    def scroll_to_parent(self, app):
        scrolled = False
        prev_child = self
        candidate = self.parent
        inspected = []
        while candidate is not None or candidate in inspected:
            candidate.prev_child = prev_child
            inspected += [candidate]
            if not candidate.ghost:
                app.fg_page = candidate
                scrolled = True
                break
            prev_child = candidate
            candidate = candidate.parent
        return scrolled

    def scroll_siblings(self, app, distance):
        index = self._child_index + distance
        index %= len(self.parent.children)
        app.fg_page = self.parent.children[index]

    def lr_press_event(self, app, lr):
        # feel free to override if there's no siblings
        self.scroll_siblings(app, lr)

    def right_press_event(self, app):
        self.lr_press_event(app, 1)

    def left_press_event(self, app):
        self.lr_press_event(app, -1)

    def down_press_event(self, app):
        # do not override pls~
        if not self.scroll_to_parent(app):
            self.scroll_to_child(app)

    def petal_5_press_event(self, app):
        self.subwindow += 1
        self.full_redraw = True

class PlayingPage(Page):
    def __init__(self, name = "play"):
        super().__init__(name)
        self.use_bottom_petals = False

    def right_press_event(self, app):
        app.shift_playing_field_by_num_petals(4)
        self.full_redraw = True

    def left_press_event(self, app):
        app.shift_playing_field_by_num_petals(-4)
        self.full_redraw = True

    def petal_5_press_event(self, app):
        pass

    def draw(self, ctx, app):
        if not self.full_redraw:
            return
        self.full_redraw = False
        ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
        ctx.text_align = ctx.CENTER

        pos = [x * 0.87 + 85 for x in app.scale]
        start = [math.tau * (0.75 - 0.04 + i / 10) for i in range(10)]
        stop = [math.tau * (0.75 + 0.04 + i / 10) for i in range(10)]

        ctx.rgb(*app.cols.fg)
        ctx.line_width = 35
        for i in range(10):
            ctx.arc(0, 0, pos[i], start[i], stop[i], 0).stroke()
        ctx.line_width = 4
        ctx.rgb(*[x * 0.75 for x in app.cols.fg])
        for i in range(10):
            ctx.arc(0, 0, pos[i] - 26, start[i], stop[i], 0).stroke()
        ctx.rgb(*[x * 0.5 for x in app.cols.fg])
        for i in range(10):
            ctx.arc(0, 0, pos[i] - 36, start[i], stop[i], 0).stroke()

        ctx.rotate(-math.tau / 4)
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"
        ctx.font_size = 20
        ctx.rgb(*app.cols.bg)
        for i in range(10):
            ctx.rgb(*app.cols.bg)
            ctx.move_to(pos[i], 6)
            note = bl00mbox.helpers.sct_to_note_name(app.scale[i] * 200 + 18367)
            ctx.text(note[:-1])
            ctx.rotate(math.tau / 10)

        ctx.rotate(math.tau * (app.mid_point_petal + 4.5) / 10)
        ctx.rgb(*app.cols.bg)
        ctx.line_width = 8
        ctx.move_to(0, 0)
        ctx.line_to(120, 0).stroke()
        ctx.rgb(*app.cols.hi)
        ctx.line_width = 1
        ctx.move_to(3, 0)
        ctx.line_to(120, 0).stroke()



class MultiPage(Page):
    def __init__(self, name, subpages):
        super().__init__(name)
        self.subpages = subpages
        for subpage in self.subpages:
            subpage.hide_footer = True
            subpage.hide_header = True

    def finalize(self, channel, modulators):
        for subpage in self.subpages:
            subpage.finalize(channel, modulators)

    def get_settings(self):
        settings = {}
        for subpage in self.subpages:
            settings[subpage.name] = subpage.get_settings()
        return settings

    def set_settings(self, settings):
        for subpage in self.subpages:
            if subpage.name in settings.keys():
                subpage.set_settings(settings[subpage.name])
            else:
                print(f"no settings found for {subpage.name}")

    def think(self, ins, delta_ms, app):
        self.subwindow %= len(self.subpages)
        self.subpages[self.subwindow].think(ins, delta_ms, app)

    def draw(self, ctx, app):
        self.subwindow %= len(self.subpages)
        if self.full_redraw:
            for subpage in self.subpages:
                subpage.full_redraw = True
            self.full_redraw = False
        self.subpages[self.subwindow].draw(ctx, app)
        app.draw_title(ctx, self.name)
        app.draw_modulator_indicator(
            ctx, self.subpages[self.subwindow].name, col=app.cols.alt
        )

class PageGroup(Page):
    def __init__(self, name):
        super().__init__(name)
        self.ghost = True

class SubMenuPage(Page):
    def __init__(self, name):
        super().__init__(name)
        self.savepage = None

    def petal_5_press_event(self, app):
        pass

    def think(self, ins, delta_ms, app):
        for x in range(len(self.children)):
            if app.input.captouch.petals[app.petal_index[x]].whole.pressed:
                self.scroll_to_child(app, x)

    def draw(self, ctx, app):
        ctx.rgb(*app.cols.bg)
        ctx.rectangle(-120,-120,240,240).fill()
        app.draw_title(ctx, self.name)
        if self.savepage is not None:
            app.draw_modulator_indicator(ctx, "save/load", col=app.cols.fg, arrow=True)
        ctx.save()
        ctx.text_align = ctx.CENTER
        ctx.font = "Arimo Bold"
        ctx.font_size = 20
        ctx.rgb(*app.cols.alt)
        for x, s in enumerate(self.children):
            phi = -math.tau*(x+1)/5
            ctx.move_to(90 * math.sin(phi), 90 * math.cos(phi))
            ctx.text(s.name)
        ctx.restore()


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
        lr_dir = (
            app.input.captouch.petals[3].whole.pressed
            - app.input.captouch.petals[7].whole.pressed
        )
        if self.locked:
            lr_dir += (
                app.input.buttons.app.right.pressed - app.input.buttons.app.left.pressed
            )
        if lr_dir:
            self._slot = (self._slot + lr_dir) % self.num_slots
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
