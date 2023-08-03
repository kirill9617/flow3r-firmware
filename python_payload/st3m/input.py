from st3m.goose import List, Optional, Enum, Tuple
from st3m.ui.ctx import Ctx

import hardware
import captouch

import math


class InputState:
    """
    Current state of inputs from badge user. Passed via think() to every
    Responder.

    If you want to detect edges, use the stateful InputController.
    """

    def __init__(
        self,
        petal_pressed: List[bool],
        # petal_pads: List[List[int]],
        petal_pos: List[Tuple[int, int]],
        left_button: int,
        right_button: int,
    ) -> None:
        self.petal_pressed = petal_pressed
        # self.petal_pads = petal_pads
        self.petal_pos = petal_pos
        self.left_button = left_button
        self.right_button = right_button

    @classmethod
    def gather(cls) -> "InputState":
        """
        Build InputState from current hardware state. Should only be used by the
        Reactor.
        """
        cts = captouch.read()
        petal_pressed = [cts.petals[i].pressed for i in range(10)]
        # petal_pads = [
        #    [hardware.captouch_get_petal_pad(petal_ix, pad_ix) for pad_ix in range(3)]
        #    for petal_ix in range(10)
        # ]
        petal_pos = [cts.petals[petal_ix].position for petal_ix in range(10)]

        left_button = hardware.left_button_get()
        right_button = hardware.right_button_get()

        return InputState(petal_pressed, petal_pos, left_button, right_button)


class RepeatSettings:
    def __init__(self, first: float, subsequent: float) -> None:
        self.first = first
        self.subsequent = subsequent


class Pressable:
    """
    A pressable button or button-acting object (like captouch petal in button
    mode).

    Carries information about current and previous state of button, allowing to
    detect edges (pressed/released) and state (down/up). Additionally implements
    button repeating.
    """

    PRESSED = "pressed"
    REPEATED = "repeated"
    RELEASED = "released"
    DOWN = "down"
    UP = "up"

    def __init__(self, state: bool) -> None:
        self._state = state
        self._prev_state = state
        self._repeat = RepeatSettings(400, 200)

        self._pressed_at: Optional[float] = None
        self._repeating = False
        self._repeated = False

        self._ignoring = 0

    def _update(self, ts: int, state: bool) -> None:
        if self._ignoring > 0:
            self._ignoring -= 1

        self._prev_state = self._state
        self._state = state
        self._repeated = False

        if state == False:
            self._pressed_at = None
            self._repeating = False
        else:
            if self._pressed_at is None:
                self._pressed_at = ts

        repeat = self._repeat
        if state and repeat is not None and self._pressed_at is not None:
            if not self._repeating:
                if ts > self._pressed_at + repeat.first:
                    self._repeating = True
                    self._repeated = True
                    self._prev_state = False
                    self._pressed_at = ts
            else:
                if ts > self._pressed_at + repeat.subsequent:
                    self._prev_state = False
                    self._pressed_at = ts
                    self._repeated = True

    @property
    def state(self) -> str:
        """
        Returns one of Pressable.{UP,DOWN,PRESSED,RELEASED,REPEATED}.
        """
        prev = self._prev_state
        cur = self._state

        if self._ignoring > 0:
            return self.UP

        if self._repeated:
            return self.REPEATED

        if cur and not prev:
            return self.PRESSED
        if not cur and prev:
            return self.RELEASED
        if cur and prev:
            return self.DOWN
        return self.UP

    @property
    def pressed(self) -> bool:
        """
        True if the button has just been pressed.
        """
        return self.state == self.PRESSED

    @property
    def repeated(self) -> bool:
        """
        True if the button has been held long enough that a virtual 'repeat'
        press should be acted upon.
        """
        return self.state == self.REPEATED

    @property
    def released(self) -> bool:
        """
        True if the button has just been released.
        """
        return self.state == self.RELEASED

    @property
    def down(self) -> bool:
        """
        True if the button is held down, after first being pressed.
        """
        return self.state == self.DOWN

    @property
    def up(self) -> bool:
        """
        True if the button is currently not being held down.
        """
        return self.state == self.UP

    def _ignore_pressed(self) -> None:
        """
        Pretend the button isn't being pressed for the next two update
        iterations. Used to prevent spurious presses to be routed to apps that
        have just been foregrounded.
        """
        self._ignoring = 2
        self._repeating = False
        self._repeated = False

    def __repr__(self) -> str:
        return "<Pressable: " + self.state + ">"


class PetalState(Pressable):
    def __init__(self, ix: int) -> None:
        self.ix = ix
        super().__init__(False)


# class Touchable(Pressable):
#    """
#    An object that can receive touch gestures (captouch petal)
#    """
#
#    BEGIN = "begin"
#    RESTING = "resting"
#    MOVED = "moved"
#    ENDED = "ended"
#
#    def __init__(self, pos: tuple[int,int] = (0, 0)) -> None:
#        super().__init__(False)
#        self._pos = pos
#        self._prev_pos = pos
#        self._polar = self._prev_polar = (0, 0)
#        self._dx = 0.0
#        self._dy = 0.0
#        self._dphi = 0.0
#        self._dr = 0.0
#
#    def _update(self, ts, state, pos) -> None:
#        self._prev_pos = self._pos
#        self._pos = pos
#
#        self._prev_polar = self._polar
#
#        self._dx = self._pos[0] - self._prev_pos[0]
#        self._dy = self._pos[1] - self._prev_pos[1]
#
#        x0 = -pos[0] / 500
#        x1 = pos[1] / 500
#
#        phi = math.atan2(x0, x1) - math.pi / 2
#        r = math.sqrt(x0 * x0 + x1 * x1)
#        self._polar = (r, phi)
#
#        self._dr = self._polar[0] - self._prev_polar[0]
#
#        v = self._polar[1] - self._prev_polar[1]
#
#        for sign in [1, -1]:
#            t = v + sign * 2 * math.pi
#            if abs(t) < abs(v):
#                v = t
#
#        self._dphi = v
#
#        super()._update(ts, state)
#        if self.state != self.DOWN:
#            self._dx = self._dy = self._dphi = self._dr = 0
#        else:
#            pass
#            # print(r, phi, self._dr, self._dphi)
#
#    def phase(self) -> str:
#        if self.state == self.UP:
#            return self.UP
#        if self.state == self.RELEASED:
#            return self.ENDED
#        if self.state == self.PRESSED:
#            return self.BEGIN
#        if self.state == self.DOWN or self.state == self.REPEATED:
#            if abs(self._dr) > 1 or abs(self._dphi) > 0.01:
#                return self.MOVED
#            else:
#                return self.RESTING
#        return "HUHUHU"


# class PetalGestureState(Touchable):
#    def __init__(self, ix: int) -> None:
#        self.ix = ix
#        super().__init__()
#
#    def _update(self, ts: int, hr: InputState) -> None:
#        super()._update(ts, hr.petal_pressed[self.ix], hr.petal_pos[self.ix])


class CaptouchState:
    """
    State of capacitive touch petals.

    The petals are indexed from 0 to 9 (inclusive). Petal 0 is above the USB-C
    socket, then the numbering continues counter-clockwise.
    """

    __slots__ = "petals"

    def __init__(self) -> None:
        self.petals = [PetalState(i) for i in range(10)]

    def _update(self, ts: int, hr: InputState) -> None:
        for i, petal in enumerate(self.petals):
            petal._update(ts, hr.petal_pressed[i])

    def _ignore_pressed(self) -> None:
        for petal in self.petals:
            petal._ignore_pressed()


class TriSwitchHandedness(Enum):
    """
    Left or right shoulder button.
    """

    left = "left"
    right = "right"


class TriSwitchState:
    """
    State of a tri-stat shoulder button
    """

    __slots__ = ("left", "middle", "right", "handedness")

    def __init__(self, h: TriSwitchHandedness) -> None:
        self.handedness = h

        self.left = Pressable(False)
        self.middle = Pressable(False)
        self.right = Pressable(False)

    def _update(self, ts: int, hr: InputState) -> None:
        st = (
            hr.left_button
            if self.handedness == TriSwitchHandedness.left
            else hr.right_button
        )
        self.left._update(ts, st == -1)
        self.middle._update(ts, st == 2)
        self.right._update(ts, st == 1)

    def _ignore_pressed(self) -> None:
        self.left._ignore_pressed()
        self.middle._ignore_pressed()
        self.right._ignore_pressed()


class InputController:
    """
    A stateful input controller. It accepts InputState updates from the Reactor
    and allows a Responder to detect input events, like a button having just
    been pressed.

    To use, instantiate within a Responder and call think() from your
    responder's think().

    Then, access the captouch/left_shoulder/right_shoulder fields.
    """

    __slots__ = (
        "captouch",
        "left_shoulder",
        "right_shoulder",
        "_ts",
    )

    def __init__(self) -> None:
        self.captouch = CaptouchState()
        self.left_shoulder = TriSwitchState(TriSwitchHandedness.left)
        self.right_shoulder = TriSwitchState(TriSwitchHandedness.right)
        self._ts = 0

    def think(self, hr: InputState, delta_ms: int) -> None:
        self._ts += delta_ms
        self.captouch._update(self._ts, hr)
        self.left_shoulder._update(self._ts, hr)
        self.right_shoulder._update(self._ts, hr)

    def _ignore_pressed(self) -> None:
        """
        Pretend input buttons aren't being pressed for the next two update
        iterations. Used to prevent spurious presses to be routed to apps that
        have just been foregrounded.
        """
        self.captouch._ignore_pressed()
        self.left_shoulder._ignore_pressed()
        self.right_shoulder._ignore_pressed()


# class PetalController:
#    def __init__(self, ix):
#        self._ts = 0
#        self._input = PetalGestureState(ix)
#
#    def think(self, hr: InputState, delta_ms: int) -> None:
#        self._ts += delta_ms
#        self._input._update(self._ts, hr)
#
#    def _ignore_pressed(self) -> None:
#        self._input._ignore_pressed()
#