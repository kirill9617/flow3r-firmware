from st4m.goose import Optional, List, ABCBase, abstractmethod
from st4m.ui.view import ViewManager
from st4m.ui.elements.visuals import Sun, GroupRing, FlowerIcon
from st4m.ui.menu import MenuController, MenuItem

from st4m import Ctx, InputState

from st4m.utils import lerp
import math
from st4m.vector import tau


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


class SunMenu(MenuController):
    """
    A circular menu with a rotating sun.
    """

    __slots__ = (
        "_ts",
        "_sun",
    )

    def __init__(self, items: List[MenuItem], vm: ViewManager) -> None:
        self._ts = 0
        self._sun = Sun()
        super().__init__(items, vm)

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        self._sun.think(ins, delta_ms)
        self._ts += delta_ms

    def _draw_text_angled(
        self, ctx: Ctx, text: str, angle: float, activity: float
    ) -> None:
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
            self._draw_text_angled(ctx, item.label(), rot, 1 - abs(rot))


class FlowerMenu(MenuController):
    """
    A circular menu with flowers.
    """

    __slots__ = (
        "_ts",
        "_sun",
    )

    def __init__(self, items: List[MenuItem], vm: ViewManager, name="flow3r") -> None:
        self._ts = 0
        self.name = name
        self.ui = GroupRing(r=80)
        for item in items:
            self.ui.items_ring.append(FlowerIcon(label=item.label()))
        super().__init__(items, vm)
        self._scroll_controller.wrap = True

        self.icon = FlowerIcon(label=self.name)
        self.icon.rotation_time = -5000
        self.ui.item_center = self.icon

        self.angle = 0
        self.angle_step = 0.2

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        self.ui.think(ins, delta_ms)
        self._ts += delta_ms

    def draw(self, ctx: Ctx) -> None:
        ctx.gray(0)
        ctx.rectangle(-120, -120, 240, 240).fill()
        for item in self.ui.items_ring:
            item.highlighted = False
            item.rotation_time = 10000
        current = self._scroll_controller.current_position()
        self.ui.items_ring[int(current)].highlighted = True
        self.ui.items_ring[int(current)].rotation_time = 3000
        self.ui.angle_offset = math.pi - (tau * current / len(self.ui.items_ring))

        self.ui.draw(ctx)
