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
        self.hide_footer = False
        self.hide_header = False
        self.parent = None
        self._prev_child = None
        self._children = []
        self._child_index = None
        self.use_bottom_petals = True
        self.ghost = False
        self.loner = False
        self.dummy = False

    def think(self, ins, delta_ms, app):
        pass

    def draw(self, ctx, app):
        pass

    def get_settings(self):
        settings = {}
        for child in self.children:
            s = child.get_settings()
            if s:
                settings[child.name] = s
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

    def scroll_to_child(self, app, child_index=None):
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
        if self.loner:
            return
        index = self._child_index + distance
        index %= len(self.parent.children)
        while self.parent.children[index].loner:
            index += 1 if distance > 0 else -1
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


class PlayingPage(Page):
    def __init__(self, name="play"):
        super().__init__(name)
        self.use_bottom_petals = False

    def right_press_event(self, app):
        app.shift_playing_field_by_num_petals(4)
        self.full_redraw = True

    def left_press_event(self, app):
        app.shift_playing_field_by_num_petals(-4)
        self.full_redraw = True

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


class LonerPage(Page):
    """cannot be rotated to or from"""

    def __init__(self, name):
        super().__init__(name)
        self.loner = True


class GhostPage(LonerPage):
    def __init__(self, name):
        super().__init__(name)
        self.ghost = True

    """cannot be navigated to"""

    def draw(self, ctx, app):
        if not self.full_redraw:
            return
        ctx.rgb(*app.cols.bg)
        ctx.rectangle(-120, -120, 240, 240).fill()
        app.draw_title(ctx, self.name)
        ctx.font = "Arimo"
        ctx.font_size = 18
        ctx.rgb(*app.cols.alt)
        ctx.text_align = ctx.CENTER
        pos = -36
        ctx.move_to(0, pos)
        ctx.text("whoopsie!!")
        pos += 18
        ctx.move_to(0, pos)
        ctx.text("this shouldn't happen :3")
        pos += 18
        ctx.move_to(0, pos)
        ctx.text("page class:")
        pos += 18
        ctx.move_to(0, pos)
        ctx.text(self.__class__.__name__)


class DummyPage(GhostPage):
    def __init__(self, name):
        super().__init__(name)
        self.dummy = True


class PageGroup(GhostPage):
    pass


"""
class AudioModulePageGroup(PageGroup):
    def __init__(self, name, num_slots):
        super().__init__(name)
        self.slots = [None] * num_slots

    @property
    def selectpage(self):
        return self._selectpage

    @selectpage.setter
    def selectpage(self, val):
        self._savepage = val
        self._update_children()

    def _update_children(self):
        self.children = self._savepage

    def swap_module(self):
        pass

    def _build_osc(self, app, osc_target, slot):
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

        pages = [self.osc_selector_page] + [self.mixer_page] + [self.env_page]
        pages += [page for page in self.osc_pages if page is not None]
        self.oscs_page.children = pages
"""


class SubMenuPage(Page):
    def __init__(self, name):
        super().__init__(name)
        self._savepage = None
        self._menupages = []

    def _update_children(self):
        self.children = self.menupages + (
            [self.savepage] if self.savepage is not None else []
        )

    @property
    def savepage(self):
        return self._savepage

    @savepage.setter
    def savepage(self, val):
        self._savepage = val
        self._update_children()

    @property
    def menupages(self):
        return self._menupages

    @menupages.setter
    def menupages(self, val):
        self._menupages = val
        self._update_children()

    def think(self, ins, delta_ms, app):
        for x in range(len(self.menupages)):
            if app.input.captouch.petals[app.petal_index[x]].whole.pressed:
                self.scroll_to_child(app, x)
        if self.savepage is not None and app.input.captouch.petals[5].whole.pressed:
            self.scroll_to_child(app, len(self.menupages))

    def draw_grouplabel(self, ctx, app, petal, name):
        labelsize = 18
        barlen = 70
        barstart = 40
        rot = 0.75 + petal / 10
        labelalign = ctx.LEFT
        translate_center = 40 + 70 / 2
        sign = 1
        top = True
        outshift = 10
        trans_rot = 0
        downshift = 0

        if petal in [3, 7]:
            trans_rot = -0.02
            top = False
        else:
            trans_rot = 0.07
            outshift += 10
            # downshift = 5

        if petal in [7, 9]:
            labelalign = ctx.RIGHT
            rot += 0.5
            sign = -1

        ctx.save()
        ctx.translate(outshift * sign, downshift)
        ctx.line_width = 3

        ctx.rotate(math.tau * rot)

        ctx.translate(translate_center * sign, 0)
        ctx.rotate(math.tau * trans_rot * sign)
        ctx.translate(-translate_center * sign, 0)

        ctx.move_to(55 * sign, 0)
        ctx.text_align = labelalign
        ctx.font_size = labelsize
        ctx.rgb(*app.cols.alt)
        ctx.text(name)

        def cool_triangle(xpos, ypos, length, width, backtilt, crop=0):
            xpos = xpos + crop
            lenght = xpos - crop
            width
            ctx.move_to(xpos * sign, ypos)
            ctx.rel_line_to(-backtilt * sign, width)
            ctx.rel_line_to((length + backtilt) * sign, -width)
            ctx.rel_line_to(-length * sign, 0)
            cool_draw()

        ctx.line_width = 3
        ctx.rgb(*app.cols.hi)
        cool_draw = ctx.fill
        s = 0
        # cool_triangle(45 + s, 5, 65 - s, 17*(65-s)/65, 9*(65-s)/65)
        ctx.rgb(*app.cols.bg)
        s = 6
        # cool_triangle(45 + s, 5, 65 - s, 17*(65-s)/65, 9*(65-s)/65)
        ctx.rgb(*app.cols.alt)
        # cool_triangle(50, -labelsize + 3, 45, -12, 5)
        s = 12
        # cool_triangle(45 + s, 5, 65*0.7 - s, 17*(65-s)/65, 9*(65-s)/65)
        ctx.rgb(*app.cols.alt)
        cool_draw = ctx.fill
        cool_triangle(60, 11, 65 * 0.7, 17 * 0.7, 9 * 0.7)
        cool_triangle(54, -labelsize - 2, 45 * 0.8, -12 * 0.8, 5 * 0.8)
        ctx.rgb(*app.cols.fg)
        cool_draw = ctx.stroke
        cool_triangle(45, 5, 65, 17, 9)
        cool_triangle(50, -labelsize + 3, 45, -12, 5)
        ctx.restore()

    def draw(self, ctx, app):
        if not self.full_redraw:
            return
        ctx.rgb(*app.cols.bg)
        ctx.rectangle(-120, -120, 240, 240).fill()
        app.draw_title(ctx, self.name)
        if self.savepage is not None:
            app.draw_modulator_indicator(ctx, "save/load", col=app.cols.fg, arrow=True)
        ctx.save()
        ctx.font = "Arimo Bold"
        for x, page in enumerate(self.menupages):
            if page.dummy:
                ctx.global_alpha = 0.5
            self.draw_grouplabel(ctx, app, app.petal_index[x], page.name)
            ctx.global_alpha = 1
        ctx.restore()
        self.full_redraw = False


class SavePage(LonerPage):
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

    def lr_press_event(self, app, lr):
        self._slot = (self._slot + lr) % self.num_slots
        self.full_redraw = True
        pass

    def __init__(self, name, slots):
        super().__init__(name)
        self.num_slots = slots
        self.lr_dir = 0
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
            ctx.rgb(*app.cols.bg)
            ctx.rectangle(-120, -120, 240, 240).fill()
            app.draw_title(ctx, self.name)
            # app.draw_modulator_indicator(ctx, "save/load", col=app.cols.hi)
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
