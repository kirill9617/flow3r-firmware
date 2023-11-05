import os
import machine

import sys_display
import leds
from ctx import Context

from st3m.goose import Optional, List, Set
from st3m.ui.view import ViewManager, ViewTransitionDirection
from st3m.ui.elements.visuals import Sun
from st3m import InputState
from st3m import settings_menu as settings
from st3m.utils import lerp
import st3m.wifi
from st3m.ui import led_patterns
from st3m.ui.menu import (
    MenuController,
    MenuItem,
    MenuItemBack,
    MenuItemForeground,
    MenuItemAction,
    MenuItemLaunchPersistentView,
)
from st3m.application import (
    BundleManager,
    BundleMetadata,
    MenuItemAppLaunch,
)
from st3m.about import About
from st3m.ui.elements.menus import SimpleMenu


class ApplicationMenu(SimpleMenu):
    def _restore_sys_defaults(self) -> None:
        if (
            not self.vm
            or not self.is_active()
            or self.vm.direction != ViewTransitionDirection.BACKWARD
        ):
            return
        # fall back to system defaults on app exit
        st3m.wifi._onoff_wifi_update()
        # set the default graphics mode, this is a no-op if
        # it is already set
        sys_display.set_mode(0)
        sys_display.fbconfig(240, 240, 0, 0)
        leds.set_slew_rate(100)
        leds.set_gamma(1.0, 1.0, 1.0)
        leds.set_auto_update(False)
        leds.set_brightness(settings.num_leds_brightness.value)
        sys_display.set_backlight(settings.num_display_brightness.value)
        led_patterns.set_menu_colors()
        # media.stop()

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        super().on_enter(vm)
        self._restore_sys_defaults()

    def on_enter_done(self):
        # set the defaults again in case the app continued
        # doing stuff during the transition
        self._restore_sys_defaults()
        leds.update()


def _get_bundle_menu_kinds(mgr: BundleManager) -> Set[str]:
    kinds: Set[str] = set()
    for bundle in mgr.bundles.values():
        kinds.update(bundle.menu_kinds())
    return kinds


def _get_bundle_menu_entries(mgr: BundleManager, kind: str) -> List[MenuItem]:
    entries: List[MenuItem] = []
    ids = sorted(mgr.bundles.keys(), key=str.lower)
    for id in ids:
        bundle = mgr.bundles[id]
        entries += bundle.menu_entries(kind)
        if bundle.menu_entries(kind):
            print(id, kind)
    return entries


def _yeet_local_changes() -> None:
    os.remove("/flash/sys/.sys-installed")
    machine.reset()


class SunMenu(MenuController):
    """
    A circular menu with a rotating sun.
    """

    __slots__ = (
        "_ts",
        "_sun",
    )

    def __init__(self, bundles: Optional[list] = None) -> None:
        self._ts = 0
        self._sun = Sun()
        if bundles:
            self._bundles = bundles
        else:
            self._bundles = BundleManager()

        self.reload_menu()

    def reload_menu(self) -> None:
        self._bundles.bundles = {}
        self._bundles.update()
        self.rebuild_menu()
        super().__init__(self._items)

    def rebuild_menu(self) -> None:
        menu_settings = settings.build_menu()
        menu_system = ApplicationMenu(
            [
                MenuItemBack(),
                MenuItemLaunchPersistentView("About", About),
                MenuItemForeground("Settings", menu_settings),
                MenuItemAppLaunch(BundleMetadata("/flash/sys/apps/gr33nhouse")),
                MenuItemAppLaunch(BundleMetadata("/flash/sys/apps/updat3r")),
                MenuItemAction("Disk Mode (Flash)", machine.disk_mode_flash),
                MenuItemAction("Disk Mode (SD)", machine.disk_mode_sd),
                MenuItemAction("Yeet Local Changes", _yeet_local_changes),
                MenuItemAction("Refresh App List", self.reload_menu),
                MenuItemAction("Reboot", machine.reset),
            ],
        )

        app_kinds = _get_bundle_menu_kinds(self._bundles)
        menu_categories = ["Badge", "Music", "Media", "Apps", "Games"]
        for kind in app_kinds:
            if kind not in ["Hidden", "System"] and kind not in menu_categories:
                menu_categories.append(kind)

        categories = [
            MenuItemForeground(kind, ApplicationMenu([MenuItemBack()] + entries))
            for kind in menu_categories
            if (entries := _get_bundle_menu_entries(self._bundles, kind))
        ]
        categories.append(MenuItemForeground("System", menu_system))

        self._items = categories
        # # self._scroll_controller = ScrollController()
        # self._scroll_controller.set_item_count(len(categories))

    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        self._sun.think(ins, delta_ms)
        self._ts += delta_ms

    def _draw_item_angled(
        self, ctx: Context, item: MenuItem, angle: float, activity: float
    ) -> None:
        size = lerp(20, 40, activity)
        color = lerp(0, 1, activity)
        if color < 0.01:
            return

        ctx.save()
        ctx.translate(-120, 0).rotate(angle).translate(140, 0)
        ctx.font_size = size
        ctx.rgba(1.0, 1.0, 1.0, color).move_to(0, 0)
        item.draw(ctx)
        ctx.restore()

    def draw(self, ctx: Context) -> None:
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
            self._draw_item_angled(ctx, item, rot, 1 - abs(rot))
