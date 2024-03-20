import math
import bl00mbox
import os
import sys

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


class AudioModulePageGroup(PageGroup):
    def __init__(self, name, app, selectpage, collection):
        super().__init__(name)
        self._fixedpages = []
        self._slotpages = [None, None]
        self._selectpage = selectpage(name, app, collection)
        self._app = app
        self._update_children()

    def get_settings(self):
        settings = {}
        for child in self._fixedpages:
            s = child.get_settings()
            if s:
                settings[child.name] = s
        for slot, slotlabel in [[0,"slot A"], [1, "slot B"]]:
            if self._slotpages[slot] is not None:
                s = {}
                s["type"] = self._slotpages[slot].name
                s["params"] = self._slotpages[slot].get_settings()
                settings[slotlabel] = s
        return settings

    def set_settings(self, settings):
        for child in self.fixedpages:
            if child.name in settings.keys():
                child.set_settings(settings[child.name])
        for slot, slotlabel in [[0,"slot A"], [1, "slot B"]]:
            sp = self._selectpage
            if slotlabel in settings.keys():
                module_type = self._slotpages[slot].name
                params = self._slotpages[slot].get_settings()
                sp.swap_module(self._app, self.get_module_by_name(module_type), slot)
            else:
                sp.swap_module(self._app, None, slot)

    def get_module_by_name(self, name):
        return None

    @property
    def selectpage(self):
        return self._selectpage

    @selectpage.setter
    def selectpage(self, val):
        self._selectpage = val
        self._update_children()

    @property
    def slotpages(self):
        return self._slotpages

    @slotpages.setter
    def slotpages(self, val):
        self._slotpages = val
        self._update_children()

    @property
    def fixedpages(self):
        return self._fixedpages

    @fixedpages.setter
    def fixedpages(self, val):
        self._fixedpages = val
        self._update_children()

    def _update_children(self):
        pages = [self.selectpage] + self.slotpages + self.fixedpages
        self.children = [page for page in pages if page is not None]


class AudioModuleSelectPage(Page):
    def __init__(self, name, app, collection):
        super().__init__(name)
        collection.update()
        self.collection = collection
        self.module_list = collection.module_list
        self._module_type = [len(self.module_list)] * 2
        self.slot_pages = [None, None]
        self._app = app

    def _update_parent(self):
        self.parent.slotpages = self.slot_pages

    def swap_module(self, app, module, slot):
        pass

    def draw(self, ctx, app):
        ctx.rgb(*app.cols.bg).rectangle(-120, -120, 240, 240).fill()
        app.draw_title(ctx, self.display_name)
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
                j = (self._module_type[k] + i - 1) % (len(self.module_list) + 1)
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
                if j == len(self.module_list):
                    ctx.text("(none)")
                else:
                    ctx.text(self.module_list[j].name)
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

    def _update_module_type(self):
        for i in range(2):
            if self.slot_pages[i] is not None:
                if self.module_list[self._module_type[i]] != type(self.slot_pages[i].patch):
                    print(self.slot_pages[i].patch)
                    print(self.module_list)
                    self._module_type[i] = self.module_list.index(
                        type(self.slot_pages[i].patch)
                    )
            else:
                self._module_type[i] = len(self.module_list)

    def think(self, ins, delta_ms, app):
        for slot, petal, plusminus in [[0, 7, 1], [0, 9, -1], [1, 3, 1], [1, 1, -1]]:
            if app.input.captouch.petals[petal].whole.pressed:
                self._module_type[slot] += plusminus
                self._module_type[slot] %= len(self.module_list) + 1
                if self._module_type[slot] == len(self.module_list):
                    self.swap_module(app, None, slot)
                else:
                    self.swap_module(app, self.module_list[self._module_type[slot]], slot)
                self._update_parent()
                self._update_module_type()


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

    def load_slot_content(self, app):
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
        self._load_slot_content_request = True

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
                    self._load_slot_content_request = True
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
                self._load_slot_content_request = True

        if self._load_slot_content_request:
            self.load_slot_content(app)
            self.full_redraw = True
            self._load_slot_content_request = False

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

class SoundSavePage(SavePage):
    def draw_saveslot(self, ctx, slot, geometry):
        xsize, ysize, center, yoffset = geometry
        names = self._slot_content[slot]
        ctx.font_size = 16
        if not names:
            ctx.font_size = 14
            names = ["(nothing)"]
        names = names[:3]
        ctx.save()
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

    def load_slot_content(self, app):
        for i in range(self.num_slots):
            settings = app.load_sound_settings_file(self.slotpath(i))
            if settings is None:
                self._slot_content[i] = None
            else:
                names = []
                for y in ["oscs", "fx"]:
                    for x in ["slot A", "slot B"]:
                        if y in settings.keys():
                            if x in settings[y].keys():
                                names += [settings[y][x]["type"]]
                self._slot_content[i] = names


class OscSelectPage(AudioModuleSelectPage):
    def swap_module(self, app, module_target, slot):
        if app.blm is None:
            return
        if slot > len(self.slot_pages):
            return

        if module_target is None:
            if self.slot_pages[slot] is not None:
                self.slot_pages[slot].delete()
                self.slot_pages[slot] = None
        else:
            if isinstance(self.slot_pages[slot], module_target):
                return 
            if self.slot_pages[slot] is not None:
                self.slot_pages[slot].delete()
            module = app.blm.new(module_target)
            module.signals.pitch = app.synth.signals.osc_pitch[slot]
            module.signals.output = app.synth.signals.osc_input[slot]
            page = module.make_page()
            page.finalize(app.blm, app.modulators)
            self.slot_pages[slot] = page

        if self.slot_pages[slot] is not None:
            app.mixer_page.params[slot * 3].display_name = self.slot_pages[slot].name
        else:
            app.mixer_page.params[slot * 3].display_name = "(none)"

class FxSelectPage(AudioModuleSelectPage):
    def swap_module(self, app, module_target, slot):
        if app.blm is None:
            return
        if slot > len(self.slot_pages):
            return
        if type(module_target) == str:
            module_target = self.collection.get_module_by_name(module_target)

        if module_target is None:
            if self.slot_pages[slot] is not None:
                self.slot_pages[slot].delete()
                self.slot_pages[slot] = None
        else:
            if isinstance(self.slot_pages[slot], module_target):
                return 
            if self.slot_pages[slot] is not None:
                self.slot_pages[slot].delete()
            module = app.blm.new(module_target)
            module.signals.pitch = app.synth.signals.fx_send
            module.signals.output = app.synth.signals.fx_return
            page = module.make_page()
            page.finalize(app.blm, app.modulators)
            page.patch = module
            self.slot_pages[slot] = page
        # serial connection only for now
        if self.slot_pages[0] is not None and self.slot_pages[1] is not None:
            app.synth.signals.fx_send = self.slot_pages[0].patch.signals.input
            self.slot_pages[0].patch.signals.output = self.slot_pages[1].patch.signals.input
            app.synth.signals.fx_return = self.slot_pages[1].patch.signals.output
        elif self.slot_pages[0] is not None:
            app.synth.signals.fx_send = self.slot_pages[0].patch.signals.input
            app.synth.signals.fx_return = self.slot_pages[0].patch.signals.output
        elif self.slot_pages[1] is not None:
            app.synth.signals.fx_send = self.slot_pages[1].patch.signals.input
            app.synth.signals.fx_return = self.slot_pages[1].patch.signals.output
        else:
            app.synth.signals.fx_send = app.synth.signals.fx_return


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
        return self.value

    def set_settings(self, settings):
        if type(settings) == dict:
            self.value = settings["val"]
        else:
            self.value = settings


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

    def set_modulator_norm(self, modulator_index, val, thou=False):
        if self.modulated:
            if thou:
                intval = int(val)
                val /= 1000
            else:
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
        modulated = False
        if self.modulated:
            for x, mod in enumerate(self._modulators):
                a = self._mod_thou[x]
                if a != 500:
                    settings[mod.name] = a
                    modulated = True
        if modulated:
            return settings
        return self._thou

    def set_settings(self, settings):
        if not self.finalized:
            return
        if type(settings) == dict:
            self.norm = settings["val"] / 1000
            if self.modulated:
                for x, mod in enumerate(self._modulators):
                    if mod.name in settings.keys():
                        self.set_modulator_norm(x, settings[mod.name], thou=True)
                    else:
                        self.set_modulator_norm(x, 500, thou=True)
        elif type(settings) == int or type(settings) == float:
            self.norm = settings / 1000

class AudioModuleCollection:
    def __init__(self, name, app_path, sub_paths = None):
        self.module_list = []
        if sub_paths is None:
            sub_paths = f"/modules/{name}/"
        if type(sub_paths) == str:
            sub_paths = [sub_paths]
        self.name = name
        self.sub_paths = sub_paths
        self.app_path = app_path

    def update(self):
        modules = []
        module_paths = ["/".join([self.app_path, s]) for s in self.sub_paths]
        path = list(sys.path)

        for module_path in module_paths:
            # relative imports don't work so we have to jump hoops
            sys.path.append(self.app_path)
            sys.path.append(module_path)
            module_files = os.listdir(module_path)
            module_files = [
                x[:-3] for x in module_files if x.endswith(".py") and not x.startswith("_")
            ]
            for module_file in module_files:
                try:
                    mod = __import__(module_file)
                    for attrname in dir(mod):
                        if attrname.startswith("_") or attrname in [
                            "bl00mbox",
                            "center_notch",
                        ]:
                            continue
                        attr = getattr(mod, attrname, None)
                        if isinstance(attr, type) and issubclass(attr, bl00mbox.Patch) and attr not in modules:
                            print(f"module collection {self.name}: discovered {attrname} in {module_file}.py")
                            modules += [attr]
                except:
                    print("failed to import " + module_file + ".py")

            # can't write directly
            sys.path.clear()
            for p in path:
                sys.path.append(p)

        self.module_list = list(set(modules))

    def _get_module_data_by_name(self, name):
        module_index = None
        module_type = None
        for x, module_t in enumerate(self.module_list):
            if module_t.name == name:
                module_type = module_t
                module_index = x
                break
        return module_index, module_type

    def get_module_index_by_name(self, name):
        ret, _ = self._get_module_data_by_name(name)
        return ret

    def get_module_by_name(self, name):
        _, ret = self._get_module_data_by_name(name)
        return ret
