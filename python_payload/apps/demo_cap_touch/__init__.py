from st3m.application import Application, ApplicationContext
from st3m.goose import List
from st3m.input import InputState
from st3m.ui.view import BaseView
from ctx import Context

import cmath
import math
import time
import captouch


class Dot:
    def __init__(self, size: float, imag: float, real: float) -> None:
        self.size = size
        self.imag = imag
        self.real = real

    def draw(self, i: int, ctx: Context) -> None:
        imag = self.imag
        real = self.real
        size = self.size

        col = (1.0, 0.0, 1.0)
        if i % 2:
            col = (0.0, 0.8, 0.8)
        ctx.rgb(*col).rectangle(
            -int(imag - (size / 2)), -int(real - (size / 2)), size, size
        ).fill()


class Calibration(BaseView):
    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.timer = 0

    def draw(self, ctx: Context) -> None:
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(0, 0.8, 0.8)
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
        if not self.started:
            pos -= 10
            ctx.move_to(0, pos)
            ctx.text("down: start 3s countdown")
            pos += 20
            ctx.move_to(0, pos)
            ctx.text("left/right: cancel")
        elif self.timer > 0:
            ctx.text("calibrating in " + str(1 + int(self.timer / 1000)))
        else:
            ctx.rgb(1.0, 0.5, 0.2)
            ctx.text("calibrating...")

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        if not self.started:
            if self.input.buttons.app.middle.pressed:
                self.started = True
                self.timer = 2999
        elif self.timer > 0:
            self.timer -= delta_ms
            if self.timer <= 0:
                captouch.calibration_request()
        else:
            if not captouch.calibration_active():
                self.vm.pop()
            return

        if self.input.buttons.app.left.pressed or self.input.buttons.app.right.pressed:
            self.vm.pop()


class CapTouchDemo(Application):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        super().__init__(app_ctx)
        self.dots: List[Dot] = []

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)

        if (
            self.input.buttons.app.middle.pressed
            or self.input.buttons.app.left.pressed
            or self.input.buttons.app.right.pressed
        ):
            self.vm.push(Calibration())

        self.dots = []
        for i in range(10):
            petal = ins.captouch.petals[i]
            (rad, phi) = petal.position
            size = 4
            if petal.pressed:
                size += 4
            x = 70 + (rad / 1000) + 0j
            x += ((-phi) / 600) * 1j
            rot = cmath.exp(-2j * math.pi * i / 10)
            x = x * rot
            self.dots.append(Dot(size, x.imag, x.real))

    def draw(self, ctx: Context) -> None:
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        for i, dot in enumerate(self.dots):
            dot.draw(i, ctx)


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(CapTouchDemo)
