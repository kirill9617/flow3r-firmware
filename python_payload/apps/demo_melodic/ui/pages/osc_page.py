from . import *


class SoundSavePage(SavePage):
    def draw_saveslot(self, ctx, slot, geometry):
        xsize, ysize, center, yoffset = geometry
        names = self._slot_content[slot]
        if not names:
            names = ["???"]
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
                names = []
                for y in ["oscs", "fx"]:
                    for x in ["slot A", "slot B"]:
                        if y in settings.keys():
                            if x in settings[y].keys():
                                names += [settings[y][x]["type"]]
                self._slot_content[i] = names
        self.full_redraw = True


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

