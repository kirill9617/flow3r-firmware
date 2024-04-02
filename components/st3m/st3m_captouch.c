#include "st3m_captouch.h"

// super thin shim

void st3m_captouch_init() { flow3r_bsp_captouch_init(); }

bool st3m_captouch_calibrating() { return flow3r_bsp_captouch_calibrating(); }

void st3m_captouch_calibration_request() {
    flow3r_bsp_captouch_calibration_request();
}

void st3m_captouch_get(flow3r_bsp_captouch_data_t *dest) {
    flow3r_bsp_captouch_get(dest);
}

void st3m_captouch_refresh_events() { flow3r_bsp_captouch_refresh_events(); }
