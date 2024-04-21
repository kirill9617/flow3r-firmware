#pragma once

// Highest-level driver for captouch on the flow3r badge. Uses 2x AD7147.

// The flow3r has 10 touch petals. 5 petals on the top layer, 5 petals on the
// bottom layer.
//
// Top petals have three capacitive pads. Bottom petals have two capacitive
// pads.
//
// The petals are numbered from 0 to 9 (inclusive). Petal 0 is next to the USB
// port, and is a top petal. Petal 1 is a bottom petal to its right. Petal 2 is
// a top petal to its right, and the rest continue clockwise accordingly.

#include <stdbool.h>
#include <stdint.h>

#define CAPTOUCH_POS_FILT_LEN 8
#define CAPTOUCH_POS_EXTRA_LEN 6
#define CAPTOUCH_POS_RING_LEN \
    ((CAPTOUCH_POS_FILT_LEN) + (CAPTOUCH_POS_EXTRA_LEN))

typedef struct {
    uint8_t index;
    bool press_event;
    // ringbuffers with historical positional data
    bool pressed[CAPTOUCH_POS_RING_LEN];
    int16_t rad_ring[CAPTOUCH_POS_RING_LEN];
    int16_t phi_ring[CAPTOUCH_POS_RING_LEN];
    // index for latest data in ringbuffers above, smaller
    // indices (wrapped around) are further in the past
    uint8_t last_ring;
    // move elsewhere someday, not external api
    uint16_t raw[4];
    // used to be called pressure but it's not a good proxy.
    // apply grains of salt generously.
    uint16_t raw_coverage;
} flow3r_bsp_captouch_petal_data_t;

typedef struct {
    flow3r_bsp_captouch_petal_data_t petals[10];
} flow3r_bsp_captouch_data_t;

void flow3r_bsp_captouch_get(flow3r_bsp_captouch_data_t *dest);
void flow3r_bsp_captouch_refresh_events();

// Initialize captouch subsystem.
void flow3r_bsp_captouch_init();

// Request captouch calibration.
void flow3r_bsp_captouch_calibration_request();

// Returns true if captouch is currently calibrating.
bool flow3r_bsp_captouch_calibrating();

// Set/get calibration data. data[] should be at least 52 entries long.
void flow3r_bsp_captouch_get_calibration_data(int32_t *data);
void flow3r_bsp_captouch_set_calibration_data(int32_t *data);
float flow3r_bsp_captouch_get_rad(flow3r_bsp_captouch_petal_data_t *petal,
                                  uint8_t smooth, uint8_t drop_first,
                                  uint8_t drop_last);
float flow3r_bsp_captouch_get_phi(flow3r_bsp_captouch_petal_data_t *petal,
                                  uint8_t smooth, uint8_t drop_first,
                                  uint8_t drop_last);
