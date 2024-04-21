#include "flow3r_bsp_captouch.h"
#include <math.h>
#include "esp_err.h"
#include "esp_log.h"

static const char *TAG = "flow3r-bsp-captouch";

// no other drivers around for now...
#define FLOW3R_BSP_CAPTOUCH_AD7147

#ifdef FLOW3R_BSP_CAPTOUCH_AD7147
#include "flow3r_bsp_ad7147.h"
void flow3r_bsp_captouch_set_calibration_data(int32_t *data) {
    flow3r_bsp_ad7147_set_calibration_data(data);
}
void flow3r_bsp_captouch_get_calibration_data(int32_t *data) {
    flow3r_bsp_ad7147_get_calibration_data(data);
}
bool flow3r_bsp_captouch_calibrating() {
    return flow3r_bsp_ad7147_calibrating();
}
void flow3r_bsp_captouch_calibration_request() {
    flow3r_bsp_ad7147_calibrate();
}
void flow3r_bsp_captouch_get(flow3r_bsp_captouch_data_t *dest) {
    flow3r_bsp_ad7147_get(dest);
}
void flow3r_bsp_captouch_refresh_events() {
    flow3r_bsp_ad7147_refresh_events();
}
void flow3r_bsp_captouch_init() {
    esp_err_t ret = flow3r_bsp_ad7147_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Captouch init failed: %s", esp_err_to_name(ret));
    }
}
#endif

typedef struct {
    uint8_t len;
    uint8_t min_len;
    int32_t coeff[CAPTOUCH_POS_FILT_LEN];
} _ir_t;

static _ir_t filters[] = {
    {
        .len = 1,
        .min_len = 1,
        .coeff = { 256 },
    },
    {
        .len = 4,
        .min_len = 2,
        .coeff = { 135, 69, 35, 17 },
    },
    {
        .len = 5,
        .min_len = 2,
        .coeff = { 90, 89, 44, 22, 11 },
    },
    {
        .len = 6,
        .min_len = 3,
        .coeff = { 69, 57, 46, 36, 28, 20 },
    },
    {
        .len = 8,
        .min_len = 4,
        .coeff = { 32, 32, 32, 32, 32, 32, 32, 32 },
    },
};

static uint8_t num_filters = sizeof(filters) / sizeof(_ir_t);

#define ring_decr(X, Y) \
    ((X + CAPTOUCH_POS_RING_LEN - Y) % CAPTOUCH_POS_RING_LEN)

static float _get_pos(flow3r_bsp_captouch_petal_data_t *petal, uint8_t smooth,
                      uint8_t drop_first, uint8_t drop_last, int16_t *ring) {
    uint8_t start_ring = petal->last_ring;

    // drop_last
    // to drop the last n samples we must delay the signal by n samples.
    // we then simply return NAN as soon as the first !pressed appears.
    drop_last %= 4;
    for (uint8_t i = 0; i < drop_last; i++) {
        if (!petal->pressed[start_ring]) return NAN;
        start_ring = ring_decr(start_ring, 1);
    }

    // drop_first
    // we apply a tiny hack later in the filter:
    // normally, the filter would check if a sample that it's about to process
    // is (i.e. pressed). for convenience we hijack this and make it look ahead
    // by drop_first ringbuffer steps.
    // since this means we're not checking the first drop_first ringbuffer steps
    // at that time anymore we do it here in advance.
    drop_first %= 4;
    for (uint8_t i = 0, index = start_ring; i < drop_first; i++) {
        if (!petal->pressed[index]) return NAN;
        index = ring_decr(index, 1);
    }

    smooth = smooth > (num_filters - 1) ? (num_filters - 1) : smooth;
    _ir_t *filter = &(filters[smooth]);
    // apply filter
    int32_t acc = 0;
    for (uint8_t i = 0, index = start_ring; i < filter->len; i++) {
        if (!petal->pressed[ring_decr(index, drop_first)]) {
            // the filter may "overflow" to newer data for quicker startup
            // in exchange for slightly higher initial noise.
            // we're still going through all addition steps to make sure
            // it's unity gain.
            if (i < filter->min_len) return NAN;
            index = start_ring;
        }
        acc += ring[index] * filter->coeff[i];
        index = ring_decr(index, 1);
    }

    // formatting: convert to [-1..1] floats
    float ret = acc / 256;
    ret = (ret * 2 + 1) / 65535;  // ocd, sorry
    return ret > 1.0 ? 1.0 : (ret < -1.0 ? -1.0 : ret);
}

float flow3r_bsp_captouch_get_rad(flow3r_bsp_captouch_petal_data_t *petal,
                                  uint8_t smooth, uint8_t drop_first,
                                  uint8_t drop_last) {
    return _get_pos(petal, smooth, drop_first, drop_last, petal->rad_ring);
}
float flow3r_bsp_captouch_get_phi(flow3r_bsp_captouch_petal_data_t *petal,
                                  uint8_t smooth, uint8_t drop_first,
                                  uint8_t drop_last) {
    if (petal->index % 2) return NAN;
    return _get_pos(petal, smooth, drop_first, drop_last, petal->phi_ring);
}
