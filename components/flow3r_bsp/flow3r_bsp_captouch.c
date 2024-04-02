#include "flow3r_bsp_captouch.h"
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
