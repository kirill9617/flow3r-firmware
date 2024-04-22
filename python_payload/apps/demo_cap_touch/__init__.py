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
        self.rad_ref = None
        self.phi_ref = None
        self.status = 0
        self.pos = 0j

class AutoParam:
    def __init__(self, app, max_value, auto_values):
        self.auto = True
        self._auto_values = auto_values
        self._max_value = max_value
        self._value = 0
        self._app = app

    @property
    def value(self):
        if self.auto:
            return self._auto_values[self._app.mode]
        else:
            return self._value

    def incr(self, amount):
        if self.auto:
            state = 0
        else:
            state = self._value + 1
        state += amount
        state %= self._max_value + 1
        self._value = state - 1
        self.auto = not state

    def print(self):
        if self.auto:
            return f"auto ({self.value})"
        else:
            return f"{self.value}"

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
        self.smooth = AutoParam(self, 5, [1,2,2])
        self.drop_first = AutoParam(self, 4, [0,0,1])
        self.drop_last = AutoParam(self, 4, [0,2,2])
        self.mode = 0
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
                            self.tinymenu_position %= 6
                        elif self.tinymenu_state == 2:
                            if self.tinymenu_position == 0:
                                self.mode += lr_dir
                                self.mode %= 3
                            elif self.tinymenu_position == 1:
                                self.smooth.incr(lr_dir)
                            elif self.tinymenu_position == 2:
                                self.drop_first.incr(lr_dir)
                            elif self.tinymenu_position == 3:
                                self.drop_last.incr(lr_dir)
                            elif self.tinymenu_position == 4:
                                self.shadow_index += lr_dir
                                self.shadow_index %= len(self.shadow_list)
                            elif self.tinymenu_position == 5:
                                if lr_dir == 1:
                                    self.tinymenu_state = 0
                                    self.state = 1
            for i in range(10):
                top = not (i % 2)
                petal = ins.captouch.petals[i]
                rad = petal.get_rad(
                    smooth=self.smooth.value,
                    drop_first=self.drop_first.value,
                    drop_last=self.drop_last.value,
                )
                phi = petal.get_phi(
                    smooth=self.smooth.value,
                    drop_first=self.drop_first.value,
                    drop_last=self.drop_last.value,
                )
                if (not petal.pressed) or rad is None:
                    self.dots[i].status = int(petal.pressed)
                    self.dots[i].rad_ref = None
                    self.dots[i].phi_ref = None
                    if self.mode == 0:
                        self.dots[i].pos = 0j
                else:
                    self.dots[i].status = 2
                    if not top:
                        phi = 0
                    if self.mode == 2:
                        if self.dots[i].rad_ref is None:
                            self.dots[i].rad_ref = rad - self.dots[i].pos.real
                            self.dots[i].phi_ref = phi + self.dots[i].pos.imag
                        rad -= self.dots[i].rad_ref
                        phi -= self.dots[i].phi_ref
                        if rad > 1:
                            rad = 1
                        elif rad < -1:
                            rad = -1
                        if phi > 1:
                            phi = 1
                        elif phi < -1:
                            phi = -1
                    self.dots[i].pos = rad - phi * 1j
                    # print(f"rad: {rad}, phi: {phi}")
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
        s = self.dots[i].status

        x = 70 + 35 * self.dots[i].pos
        rot = cmath.exp(-2j * math.pi * i / 10)
        x = -x * rot

        if i % 2:
            ctx.rgb(0.0, 0.8, 0.8)
        else:
            ctx.rgb(1.0, 0.0, 1.0)
        if s == 2:
            ctx.arc(x.imag, x.real, 4, 0, math.tau, 1).fill()
            """
        elif s == 1:
            ctx.arc(x.imag, x.real, 4, 0, math.tau, 1).fill()
            ctx.rgb(0.0, 0.0, 0.0)
            ctx.arc(x.imag, x.real, 2, 0, math.tau, 1).fill()
            """
        else:
            ctx.arc(x.imag, x.real, 2, 0, math.tau, 1).fill()

    def draw_tinymenu(self, ctx):
        if not self.tinymenu_state:
            return
        xsize = 60
        ysize = 42
        ctx.rgb(0, 0, 0)
        ctx.rectangle(-xsize / 2, -ysize / 2, xsize, ysize).fill()
        
        ctx.rgb(1.0, 0.0, 1.0)
        ctx.round_rectangle(-xsize / 2, -ysize / 2, xsize, ysize, 5).stroke()
        ctx.text_align = ctx.CENTER
        ctx.font_size = 15
        descr = "???"
        value = "???"
        xsize -= 6
        ysize -= 4
        if self.tinymenu_position == 0:
            descr = "mode"
            value = ["std", "hold", "drag"][self.mode]
        elif self.tinymenu_position == 1:
            descr = "smooth"
            value = self.smooth.print()
        elif self.tinymenu_position == 2:
            descr = "drop_fr"
            value = self.drop_first.print()
        elif self.tinymenu_position == 3:
            descr = "drop_ls"
            value = self.drop_last.print()
        elif self.tinymenu_position == 4:
            descr = "shadow"
            value = str(self.shadow_index)
        elif self.tinymenu_position == 5:
            descr = "calib"
            value = "go ->"
        if self.tinymenu_state == 1:
            ctx.rgb(0, 0.8, 0.8)
            ctx.round_rectangle(-xsize/2, -ysize/2 + 1, xsize, ysize/2 - 2, 2).fill()
            ctx.move_to(0, 14)
            ctx.text(value)
            ctx.rgb(0, 0, 0)
            ctx.move_to(0, -5)
            ctx.text(descr)
        else:
            ctx.rgb(0, 0.8, 0.8)
            ctx.round_rectangle(-xsize/2, 1, xsize, ysize/2 - 2, 2).fill()
            ctx.move_to(0, -5)
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
