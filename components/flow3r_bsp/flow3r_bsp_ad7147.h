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

// It has 13 input channels, and can perform arbitrarily sequenced reads from
// these channels (then report the results of that sequence at once), but the
// maximum sequence length is 12 stages.

// One of the two chips only reads 12 channels so all is well, however the other
// must get data for all of its 13 channels. This means the chip needs to be
// dynamically reconfigured during operation. There is however the oddity that
// everytime a channel is reconfigured the first reading has a small likelyhood
// to be glitchy. This could be a locking issue that grabs stale data but we
// couldn't find anything the like and ran some experiments with very barebones
// code so we accept it as fact for now.

// To account for this we therefore need to throw away data. The most optimal
// sequence therefore only reconfigures one stage. As we can only reset the
// sequencer to stage 0 we use stage 0 for dynamic operations. This gives us
// an effective 15-step sequence (13 usable, 2 for throwing away after reconf).
// There's some overhead so we're running a bit slower than that.

#include <stdbool.h>
#include "esp_err.h"
#include "flow3r_bsp_ad7147_hw.h"
#include "flow3r_bsp_captouch.h"

#define _AD7147_CALIB_CYCLES 16

// State of an AD7147 channel. Each AD7147 has 13 channels, but can only access
// 12 of them at once in a single sequence.
typedef struct {
    // Positive AFE offset currently programmed. [0,126].
    volatile int8_t afe_offset;
    // Last measurement.
    uint16_t cdc;

    // Ambient value used for offset when checking for touch presence. Written
    // by calibration, and attempts to reach a preset calibration setpoint.
    volatile uint16_t amb;
    // Calibration samples gathered during the calibraiton process.
    uint16_t amb_meas[_AD7147_CALIB_CYCLES];
} ad7147_channel_t;

// State and configuration of an AD7147 chip. Wraps the low-level structure in
// everything required to manage multiple sequences and perform calibration.
typedef struct {
    // Opaque name used to prefix log messages.
    const char *name;
    // True for bottom chip, false for top
    bool is_bot;

    // [0, n_channels) are the expected connected channels to the inputs of the
    // chip.
    size_t nchannels;
    ad7147_channel_t channels[13];

    // Sequence to be handled by this chip as a -1 right-padded
    // list of channel numbers that the chip will read
    int8_t sequence[13];

    ad7147_hw_t dev;
    bool failed;

    // Request applying external calibration
    volatile bool calibration_pending;
    // True if calibration is running or pending
    volatile bool calibration_active;
    // Set true if external calibration is to be written to hw
    volatile bool calibration_external;
    int8_t calibration_cycles;
} ad7147_chip_t;

// One of the four possible touch points (pads) on a petal. Top petals have
// base/cw/ccw. Bottom petals have base/tip.
typedef enum {
    // Pad away from centre of badge.
    petal_pad_tip = 0,
    // Pad going counter-clockwise around the badge.
    petal_pad_ccw = 1,
    // Pad going clockwise around the badge.
    petal_pad_cw = 2,
    // Pad going towards the centre of the badge.
    petal_pad_base = 3,
} petal_pad_kind_t;

// Each petal can be either top or bottom.
typedef enum {
    // Petal on the top layer. Has base, cw, ccw pads.
    petal_top = 0,
    // petal on the bottom layer. Has base and tip fields.
    petal_bottom = 1,
} petal_kind_t;

// State of a petal's pad.
typedef struct {
    // Is it a top or bottom petal?
    petal_pad_kind_t kind;
    // Raw value, compensated for ambient value.
    uint16_t raw;
    // Configured threshold for touch detection.
    uint16_t threshold;
} flow3r_bsp_ad7147_petal_pad_state_t;

// State of a petal. Only the fields relevant to the petal kind (tip/base or
// base/cw/ccw) are present.
typedef struct {
    petal_kind_t kind;
    flow3r_bsp_ad7147_petal_pad_state_t tip;
    flow3r_bsp_ad7147_petal_pad_state_t ccw;
    flow3r_bsp_ad7147_petal_pad_state_t cw;
    flow3r_bsp_ad7147_petal_pad_state_t base;
} flow3r_bsp_ad7147_petal_state_t;

// State of all petals of the badge.
typedef struct {
    flow3r_bsp_ad7147_petal_state_t petals[10];
} flow3r_bsp_ad7147_state_t;

// Get a given petal's pad data for a given petal kind.
const flow3r_bsp_ad7147_petal_pad_state_t *
flow3r_bsp_ad7147_pad_for_petal_const(
    const flow3r_bsp_ad7147_petal_state_t *petal, petal_pad_kind_t kind);
flow3r_bsp_ad7147_petal_pad_state_t *flow3r_bsp_ad7147_pad_for_petal(
    flow3r_bsp_ad7147_petal_state_t *petal, petal_pad_kind_t kind);

// Request captouch calibration.
void flow3r_bsp_ad7147_calibrate();

// Returns true if captouch is currently calibrating.
bool flow3r_bsp_ad7147_calibrating();

// Set/get calibration data. data[] should be at least 50 entries long.
void flow3r_bsp_ad7147_get_calibration_data(int32_t *data);
void flow3r_bsp_ad7147_set_calibration_data(int32_t *data);
#pragma once

void flow3r_bsp_ad7147_get(flow3r_bsp_captouch_data_t *dest);
void flow3r_bsp_ad7147_refresh_events();
esp_err_t flow3r_bsp_ad7147_init();
