from typing import Protocol, List, Tuple

class CaptouchPetalState(Protocol):
    @property
    def pressed(self) -> bool:
        """
        True if the petal is being touched.
        """
        ...
    @property
    def top(self) -> bool:
        """
        True if this is a top petal.
        """
        ...
    @property
    def bottom(self) -> bool:
        """
        True if this is a bottom petal.
        """
        ...
    @property
    def position(self) -> Tuple[int, int]:
        """
        Polar coordinates of touch on petal in the form of a (distance, angle)
        tuple.

        The units are arbitrary, but centered around (0, 0).

        An increase in distance means the touch is further away from the centre
        of the badge.

        An increase in angle means the touch is more clockwise.
        """
        ...

class CaptouchState(Protocol):
    """
    State of captouch sensors, captured at some time.
    """

    @property
    def petals(self) -> List[CaptouchPetalState]:
        """
        State of individual petals.

        Contains 10 elements, with the zeroth element being the petal closest to
        the USB port. Then, every other petal in a clockwise direction.

        Petals 0, 2, 4, 6, 8 are Top petals.

        Petals 1, 3, 5, 7, 9 are Bottom petals.
        """
        ...

def read() -> CaptouchState:
    """
    Reads current captouch state from hardware and returns a snapshot in time.
    """
    ...

def calibration_active() -> bool:
    """
    Returns true if the captouch system is current recalibrating.
    """
    ...

def calibration_request() -> None:
    """
    Attempts to start calibration of captouch controllers. No-op if a
    calibration is already active.
    """
    ...
