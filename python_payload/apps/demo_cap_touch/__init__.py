from st3m import logging
from st3m.application import Application, ApplicationContext
from st3m.goose import List, Optional
from st3m.input import InputState
from st3m.ui.view import ViewManager
from ctx import Context

log = logging.Log(__name__, level=logging.INFO)
log.info("import")

import cmath
import math
import time
import captouch


class Dot:
    def __init__(self):
        self.size = 0
        self.pos = 0.0j


class CapTouchDemo(Application):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        super().__init__(app_ctx)
        self.dots = [Dot() for x in range(10)]
        self.last_calib = None
        self.state = 0
        self.timer = 0
        self.button = None
        self.full_redraw = True
        self.tinymenu_position = 0
        self.tinymenu_state = 0
        self.smooth = 1
        self.hold = False
        self.shadow_index = 0
        self.shadow_list = [1, 0.35, 0.14, 0.06]

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        if self.button is not None:
            press_event = (self.button != ins.buttons.app) and ins.buttons.app
        else:
            press_event = False
        self.button = int(ins.buttons.app)
        if self.state == 0:
            if press_event:
                if self.button == ins.buttons.PRESSED_DOWN:
                    self.tinymenu_state += 1
                    self.tinymenu_state %= 3
                else:
                    lr_dir = int(self.button == ins.buttons.PRESSED_RIGHT)
                    lr_dir -= int(self.button == ins.buttons.PRESSED_LEFT)
                    if lr_dir:
                        if self.tinymenu_state == 1:
                            self.tinymenu_position += lr_dir
                            self.tinymenu_position %= 4
                        elif self.tinymenu_state == 2:
                            if self.tinymenu_position == 0:
                                self.smooth += lr_dir
                                self.smooth %= 5
                            elif self.tinymenu_position == 1:
                                self.hold = not self.hold
                            elif self.tinymenu_position == 2:
                                self.shadow_index += lr_dir
                                self.shadow_index %= len(self.shadow_list)
                            elif self.tinymenu_position == 3:
                                if lr_dir == 1:
                                    self.tinymenu_state = 0
                                    self.state = 1
            for i in range(10):
                top = not (i % 2)
                petal = ins.captouch.petals[i]
                rad = petal.get_rad(smooth=self.smooth)
                phi = petal.get_phi(smooth=self.smooth)
                if rad is None:
                    self.dots[i].size = 4
                    if not self.hold:
                        self.dots[i].pos = 0
                else:
                    self.dots[i].size = 8
                    if phi is None:
                        phi = 0
                    self.dots[i].pos = rad - phi * 1j
                    print(f"rad: {rad}, phi: {phi}")
        elif self.state == 1:
            if press_event:
                if self.button == ins.buttons.PRESSED_DOWN:
                    self.state = 2
                    self.timer = 2999
                else:
                    self.state = 0
        elif self.state == 2:
            self.timer -= delta_ms
            if self.timer < 0:
                self.state = 3
                captouch.calibration_request()
        elif self.state == 3:
            if not captouch.calibration_active():
                self.state = 0

    def draw_dot(self, i, ctx):
        s = self.dots[i].size

        x = 70 + 35 * self.dots[i].pos
        rot = cmath.exp(-2j * math.pi * i / 10)
        x = -x * rot

        if i % 2:
            ctx.rgb(0.0, 0.8, 0.8)
        else:
            ctx.rgb(1.0, 0.0, 1.0)
        ctx.arc(x.imag, x.real, s / 2, 0, math.tau, 1)
        ctx.fill()

    def draw_tinymenu(self, ctx):
        if not self.tinymenu_state:
            return
        xsize = 60
        ysize = 40
        ctx.rgb(0, 0, 0)
        ctx.rectangle(-xsize / 2, -ysize / 2, xsize, ysize).fill()
        ctx.rgb(1.0, 0.0, 1.0)
        ctx.round_rectangle(-xsize / 2, -ysize / 2, xsize, ysize, 5).stroke()
        ctx.text_align = ctx.CENTER
        ctx.font_size = 16
        descr = "???"
        value = "???"
        if self.tinymenu_position == 0:
            descr = "smooth"
            value = str(self.smooth)
        elif self.tinymenu_position == 1:
            descr = "hold"
            value = "on" if self.hold else "off"
        elif self.tinymenu_position == 2:
            descr = "shadow"
            value = str(self.shadow_index)
        elif self.tinymenu_position == 3:
            descr = "calib"
            value = "go ->"
        if self.tinymenu_state == 1:
            ctx.rgb(0, 0.8, 0.8)
            ctx.round_rectangle(-27, -17, 54, 16, 2).fill()
            ctx.move_to(0, 14)
            ctx.text(value)
            ctx.rgb(0, 0, 0)
            ctx.move_to(0, -4)
            ctx.text(descr)
        else:
            ctx.rgb(0, 0.8, 0.8)
            ctx.round_rectangle(-27, 1, 54, 16, 2).fill()
            ctx.move_to(0, -4)
            ctx.text(descr)
            ctx.rgb(0, 0, 0)
            ctx.move_to(0, 14)
            ctx.text(value)

    def draw_main(self, ctx):
        if self.full_redraw:
            alpha = 1
            self.full_redraw = False
        else:
            alpha = self.shadow_list[self.shadow_index]
        ctx.rgba(0, 0, 0, alpha).rectangle(-120, -120, 240, 240).fill()
        for i in range(10):
            self.draw_dot(i, ctx)
        self.draw_tinymenu(ctx)

    def draw_calib(self, ctx):
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(0.8, 0.8, 0.8)
        ctx.text_align = ctx.CENTER
        ctx.move_to(0, 0)
        ctx.font = ctx.get_font_name(0)
        ctx.font_size = 20
        pos = -55
        ctx.move_to(0, pos)
        ctx.text("calibration mode")
        pos += 30
        ctx.move_to(0, pos)
        ctx.text("do not touch the petals")
        pos += 20
        ctx.move_to(0, pos)
        ctx.text("from the front during")
        pos += 20
        ctx.move_to(0, pos)
        ctx.text("calibration")
        pos += 40
        ctx.move_to(0, pos)
        if self.state == 1:
            pos -= 10
            ctx.move_to(0, pos)
            ctx.text("down: start 3s countdown")
            pos += 20
            ctx.move_to(0, pos)
            ctx.text("left/right: cancel")
        elif self.state == 2:
            ctx.text("calibrating in " + str(1 + int(self.timer / 1000)))
        elif self.state == 3:
            ctx.rgb(1.0, 0.5, 0.2)
            ctx.text("calibrating...")

    def draw(self, ctx):
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240)
        if self.state == 0:
            self.draw_main(ctx)
        else:
            self.draw_calib(ctx)

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        super().on_enter(vm)
        self.button = None
        self.full_redraw = True
        self.tinymenu_state = 0
        self.state = 0


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(CapTouchDemo)
