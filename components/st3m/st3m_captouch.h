#pragma once

// GENERAL INFORMATION
//
// Geometry:
//
// The badge has 10 petals, 5 top petals (on the top PCB) and 5 bottom petals
// (on the bottom PCB). Each petal is made up of pads. Top petals have 3 pads,
// bottom petals have 2 pads.
//
// Every pad on a petal has a kind. The kind infidicates the relative position
// of the pad within the petal.
//
//   tip: pad closest to the outside of the badge
//   base: pad closest to the inside of the badge
//   cw: pad going clockwise around the badge
//   ccw: pad going counter-clockwise around the badge
//
// Top petals have base, cw, ccw pads. Bottom petals have tip, base pads.
//
// NOTE: if you have a 'proto3' badge, it has a slightly different top petal
// layout (tip, cw, ccw). This API pretends base == tip in this case.
//
// Petals are numbered. 0 is the top petal above the USB-C jack, increases
// clockwise so that bottom petals are uneven and top petals even.
//
// Processing:
//
// Every time new capacitive touch data is available, a 'raw' value is extracted
// for each pad. This value is then used to calcualte the following information:
//
//  1. Per-pad touch: if the raw value exceeds some threshold, the pad is
//     considered to be touched.
//  2. Per-petal touch: if any of a pad's petals is considered to be touched,
//     the petal is also considered to be touched.
//  3. Per-petal position: petals allow for estimting a polar coordinate of
//     touch. Top petals have two degrees of freedom, bottom petals have a
//     single degree of freedom (distance from center).

// NOTE: keep the enum definitions below in-sync with flow3r_bsp_captouch.h, as
// they are converted by numerical value internally.

#include <stdbool.h>
#include "flow3r_bsp_captouch.h"

void st3m_captouch_init(void);
bool st3m_captouch_calibrating(void);
void st3m_captouch_calibration_request(void);
void st3m_captouch_get(flow3r_bsp_captouch_data_t *dest);
void st3m_captouch_refresh_events();
