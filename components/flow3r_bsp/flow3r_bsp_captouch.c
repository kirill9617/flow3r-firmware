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
    int32_t coeff[CAPTOUCH_POSITIONAL_RINGBUFFER_LENGTH];
} _ir_t;

static _ir_t filters[] = {
    {
        .len = 1,
        .coeff = { 256 },
    },
    {
        .len = 4,
        .coeff = { 135, 69, 35, 17 },
    },
    {
        .len = 5,
        .coeff = { 90, 89, 44, 22, 11 },
    },
    {
        .len = 6,
        .coeff = { 69, 57, 46, 36, 28, 20 },
    },
    {
        .len = 8,
        .coeff = { 32, 32, 32, 32, 32, 32, 32, 32 },
    },
};

static uint8_t num_filters = sizeof(filters) / sizeof(_ir_t);

static float _get_pos(flow3r_bsp_captouch_petal_data_t *petal, uint8_t smooth,
                      uint8_t drop_first, uint8_t drop_last, int16_t *ring) {
    if (!petal->press_event) return NAN;
    uint8_t len = CAPTOUCH_POSITIONAL_RINGBUFFER_LENGTH;
    smooth = smooth > (num_filters - 1) ? (num_filters - 1) : smooth;
    _ir_t *filter = &(filters[smooth]);

    int32_t acc = 0;
    for (uint8_t i = 0; i < filter->len; i++) {
        uint8_t index = petal->last_ring - i;
        index = (index + len) % len;
        acc += ring[index] * filter->coeff[i];
    }
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
