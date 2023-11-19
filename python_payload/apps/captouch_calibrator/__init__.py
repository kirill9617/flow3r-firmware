from st3m import logging
from st3m.application import Application, ApplicationContext
from st3m.goose import List
from st3m.input import InputState
from ctx import Context
from st3m.ui.elements.sun_menu import SunMenu


log = logging.Log(__name__, level=logging.INFO)
log.info("import")

import time
import captouch
import json


class CaptouchCalibrator(Application):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        super().__init__(app_ctx)
        self.last_calib = None
        self.state = 0
        self.timer = 0
        self.button = None
        self.path = "/flash/captouch_calib.json"

    def return_to_caller_ish(self):
        # wip
        if not self.vm._history:
            menu_main = SunMenu(self.sunmenu_bundles)
            self.vm.replace(menu_main)
        else:
            self.vm.pop()

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        if self.button is not None:
            press_event = (self.button != ins.buttons.app) and ins.buttons.app
        else:
            press_event = False
        self.button = int(ins.buttons.app)
        if self.state == 1:
            if press_event:
                if self.button == ins.buttons.PRESSED_DOWN:
                    self.state = 2
                    self.timer = 2999
                elif self.calib_optional:
                    self.return_to_caller_ish()

        elif self.state == 2:
            self.timer -= delta_ms
            if self.timer < 0:
                self.state = 3
                log.info("calibrating captouch")
                captouch.calibration_request()
        elif self.state == 3:
            if not captouch.calibration_active():
                try:
                    with open(self.path, "w") as f:
                        f.write(json.dumps(captouch.calibration_get_data()))
                        log.info(f"captouch calibration saved at {self.path}")
                except OSError:
                    log.warning(
                        f"captouch calibration could not be saved at {self.path}"
                    )
                self.return_to_caller_ish()

    def draw(self, ctx: Context) -> None:
        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.text_align = ctx.CENTER
        pos = -55
        ctx.move_to(0, pos)
        ctx.font_size = 30
        ctx.rgb(0, 1, 0.2)
        ctx.font = ctx.get_font_name(5)
        ctx.text("captouch calibration")
        ctx.font = ctx.get_font_name(8)
        ctx.font_size = 17
        ctx.rgb(0, 0.8, 0.8)
        pos += 30
        ctx.move_to(0, pos)
        ctx.text("please do not touch the")
        pos += 20
        ctx.move_to(0, pos)
        ctx.text("petals from the front")
        pos += 20
        ctx.move_to(0, pos)
        ctx.text("during calibration")
        pos += 40
        ctx.move_to(0, pos)
        if self.state == 1:
            pos -= 10
            ctx.move_to(0, pos)
            ctx.text("down: start 3s countdown")
            if self.calib_optional:
                pos += 20
                ctx.move_to(0, pos)
                ctx.text("left/right: cancel")
            else:
                pos += 24
                ctx.move_to(0, pos)
                ctx.font_size = 14
                ctx.text("(no calibration data")
                pos += 16
                ctx.move_to(0, pos)
                ctx.text("found, cannot skip)")
        elif self.state == 2:
            ctx.text("calibrating in " + str(1 + int(self.timer / 1000)))
        elif self.state == 3:
            ctx.rgb(1.0, 0.5, 0.2)
            ctx.text("calibrating...")

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        super().on_enter(vm)
        try:
            with open(self.path, "r") as f:
                calib_data = json.load(f)
                assert len(calib_data) == 52
                self.calib_optional = True
        except (OSError, AssertionError, ValueError):
            self.calib_optional = False
        self.button = None
        self.state = 1


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(CaptouchCalibrator)
