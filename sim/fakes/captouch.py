from typing import List


class CaptouchPetalState:
    def __init__(self, ix: int, pressed: bool):
        self._pressed = pressed
        self._ix = ix
        self.position = (0, 0)

    @property
    def pressed(self) -> bool:
        return self._pressed

    @property
    def top(self) -> bool:
        return self._ix % 2 == 0

    @property
    def bottom(self) -> bool:
        return not self.top


class CaptouchState:
    def __init__(self, petals: List[CaptouchPetalState]):
        self._petals = petals

    @property
    def petals(self) -> List[CaptouchPetalState]:
        return self._petals


def read() -> CaptouchState:
    import _sim

    _sim._sim.process_events()
    _sim._sim.render_gui_lazy()
    petals = _sim._sim.petals

    res = []
    for petal in range(10):
        top = petal % 2 == 0
        if top:
            ccw = petals.state_for_petal_pad(petal, 1)
            cw = petals.state_for_petal_pad(petal, 2)
            base = petals.state_for_petal_pad(petal, 3)
            pressed = cw or ccw or base
            res.append(CaptouchPetalState(petal, pressed))
        else:
            tip = petals.state_for_petal_pad(petal, 0)
            base = petals.state_for_petal_pad(petal, 3)
            pads = CaptouchPetalPadsState(tip, base, False, False)
            pressed = tip or base
            res.append(CaptouchPetalState(petal, pressed))
    return CaptouchState(res)


def calibration_active() -> bool:
    return False


def calibration_request() -> None:
    return


def refresh_events() -> None:
    return
