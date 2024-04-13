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

typedef struct {
    bool pressed;
    bool press_event;
    uint16_t raw_coverage;
    // legacy
    int32_t pos_distance;
    int32_t pos_angle;
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
