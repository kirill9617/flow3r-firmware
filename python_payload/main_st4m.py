"""
Experimental/Research UI/UX framework (st4m).

To run, rename this file to main.py.

See st4m/README.md for more information.
"""


import st4m

from st4m.goose import Optional, List, ABCBase, abstractmethod
from st4m.ui.view import View, ViewManager, ViewTransitionBlend
from st4m.ui.menu import MenuItem, MenuController, MenuItemBack, MenuItemForeground, MenuItemNoop
from st4m import Responder, InputState, Ctx

import math


vm = ViewManager(ViewTransitionBlend())


def lerp(a: float, b: float, v: float) -> float:
    if v <= 0:
        return a
    if v >= 1.0:
        return b
    return a + (b - a) * v


class Sun(Responder):
    """
    A rotating sun widget.
    """
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.size = 50.0
        self.ts = 1.0

    def think(self, ins: InputState, delta_ms: int) -> None:
        self.ts += delta_ms
        pass

    def draw(self, ctx: Ctx) -> None:

        nrays = 10
        angle_per_ray = 6.28 / nrays
        for i in range(nrays):
            angle = i * angle_per_ray + self.ts / 4000
            angle %= 3.14159*2

            if angle > 2 and angle < 4:
                continue

            ctx.save()
            ctx.rgb(0.5, 0.5, 0)
            ctx.line_width = 30
            ctx.translate(-120, 0).rotate(angle)
            ctx.move_to(20, 0)
            ctx.line_to(260, 0)
            ctx.stroke()
            ctx.restore()

        ctx.save()
        ctx.rgb(0.92, 0.89, 0)
        ctx.translate(-120, 0)

        ctx.arc(self.x, self.y, self.size, 0, 6.29, 0)
        ctx.fill()
        ctx.restore()


class MainMenu(MenuController):
    """
    A circular menu with a rotating sun.
    """

    __slots__ = (
        '_ts',
        '_sun',
    )

    def __init__(self, items: List[MenuItem], vm: ViewManager) -> None:
        self._ts = 0
        self._sun = Sun()
        super().__init__(items, vm)

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        self._sun.think(ins, delta_ms)
        self._ts += delta_ms

    def _draw_text_angled(self, ctx: Ctx, text: str, angle: float, activity: float) -> None:
        size = lerp(20, 40, activity)
        color = lerp(0, 1, activity)
        if color < 0.01:
            return

        ctx.save()
        ctx.translate(-120, 0).rotate(angle).translate(140, 0)
        ctx.font_size = size
        ctx.rgba(1.0, 1.0, 1.0, color).move_to(0, 0).text(text)
        ctx.restore()

    def draw(self, ctx: Ctx) -> None:
        ctx.gray(0)
        ctx.rectangle(-120, -120, 240, 240).fill()
        
        self._sun.draw(ctx)

        ctx.font_size = 40
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        angle_per_item = 0.4

        current = self._scroll_controller.current_position()

        for ix, item in enumerate(self._items):
            rot = (ix - current) * angle_per_item
            self._draw_text_angled(ctx, item.label(), rot, 1-abs(rot))
    

class SimpleMenu(MenuController):
    """
    A simple line-by-line menu.
    """
    def draw(self, ctx: Ctx) -> None:
        ctx.gray(0)
        ctx.rectangle(-120, -120, 240, 240).fill()

        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        current = self._scroll_controller.current_position()

        ctx.gray(1)
        for ix, item in enumerate(self._items):
            offs = (ix - current) * 30
            size = lerp(30, 20, abs(offs / 20))
            ctx.font_size = size
            ctx.move_to(0, offs).text(item.label())


menu_music = SimpleMenu([
    MenuItemBack(),
    MenuItemNoop("Harmonic"),
    MenuItemNoop("Melodic"),
    MenuItemNoop("TinySynth"),
    MenuItemNoop("CrazySynth"),
    MenuItemNoop("Sequencer"),
], vm)

menu_apps = SimpleMenu([
    MenuItemBack(),
    MenuItemNoop("captouch"),
    MenuItemNoop("worms"),
], vm)

menu_main = MainMenu([
    MenuItemForeground("Music", menu_music),
    MenuItemForeground("Apps", menu_apps),
    MenuItemNoop("Settings"),
], vm)

vm.push(menu_main)

reactor = st4m.Reactor()
reactor.set_top(vm)
reactor.run()