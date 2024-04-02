#include "flow3r_bsp_ad7147_hw.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "esp_err.h"
#include "esp_log.h"

#include <string.h>

#define TIMEOUT_MS 1000

#define CIN_CDC_NONE 0
#define CIN_CDC_NEG 1
#define CIN_CDC_POS 2
#define CIN_BIAS 3

#define AD7147_REG_PWR_CONTROL 0x00
#define AD7147_REG_STAGE_CAL_EN 0x01
#define AD7147_REG_AMB_COMP_CTRL0 0x02
#define AD7147_REG_STAGE_HIGH_INT_ENABLE 0x06
#define AD7147_REG_STAGE_COMPLETE_INT_ENABLE 0x07
#define AD7147_REG_STAGE_COMPLETE_INT_STATUS 0x0A
#define AD7147_REG_CDC_RESULT_S0 0x0B
#define AD7147_REG_DEVICE_ID 0x17
#define AD7147_REG_STAGE0_CONNECTION 0x80

static const char *TAG = "flow3r-bsp-ad7147-hw";

// Write single register at `reg`.
static esp_err_t _i2c_write(const ad7147_hw_t *dev, uint16_t reg,
                            uint16_t data) {
    const uint8_t tx[] = { reg >> 8, reg & 0xFF, data >> 8, data & 0xFF };
    return flow3r_bsp_i2c_write_to_device(dev->addr, tx, sizeof(tx),
                                          TIMEOUT_MS / portTICK_PERIOD_MS);
}

// Write continuous `len`-long register range starting at `reg`.
static esp_err_t _i2c_write_multiple(const ad7147_hw_t *dev, uint16_t reg,
                                     const uint16_t *data, size_t len) {
    uint8_t tx[len * 2 + 2];
    tx[0] = reg >> 8;
    tx[1] = reg & 0xff;
    for (size_t i = 0; i < len; i++) {
        tx[2 + i * 2] = data[i] >> 8;
        tx[2 + i * 2 + 1] = data[i] & 0xff;
    }
    esp_err_t ret = flow3r_bsp_i2c_write_to_device(
        dev->addr, tx, len * 2 + 2, TIMEOUT_MS / portTICK_PERIOD_MS);
    return ret;
}

// Read continuous `len`-long register range starting at `reg`.
static esp_err_t _i2c_read(const ad7147_hw_t *dev, const uint16_t reg,
                           uint16_t *data, const size_t len) {
    const uint8_t tx[] = { reg >> 8, reg & 0xFF };
    uint8_t rx[len * 2];
    esp_err_t ret = flow3r_bsp_i2c_write_read_device(
        dev->addr, tx, sizeof(tx), rx, sizeof(rx),
        TIMEOUT_MS / portTICK_PERIOD_MS);
    for (int i = 0; i < len; i++) {
        data[i] = (rx[i * 2] << 8) | rx[i * 2 + 1];
    }
    return ret;
}

// Configure device's PWR_CONTROL register based on dev_config.
static esp_err_t _configure_pwr_control(const ad7147_hw_t *dev) {
    const ad7147_device_config_t *config = &dev->dev_config;
    const uint16_t val =
        (config->cdc_bias << 14) | (config->ext_source << 12) |
        (config->int_pol << 11) | (config->sw_reset << 10) |
        (config->decimation << 8) | (config->sequence_stage_num << 4) |
        (config->lp_conv_delay << 2) | (config->power_mode << 0);
    return _i2c_write(dev, AD7147_REG_PWR_CONTROL, val);
}

// Configure device's STAGE_CAL_EN register based on dev_config.
static esp_err_t _configure_stage_cal_en(const ad7147_hw_t *dev) {
    const ad7147_device_config_t *config = &dev->dev_config;
    const uint16_t val =
        (config->avg_lp_skip << 14) | (config->avg_fp_skip << 12) |
        (config->stage11_cal_en << 11) | (config->stage10_cal_en << 10) |
        (config->stage9_cal_en << 9) | (config->stage8_cal_en << 8) |
        (config->stage7_cal_en << 7) | (config->stage6_cal_en << 6) |
        (config->stage5_cal_en << 5) | (config->stage4_cal_en << 4) |
        (config->stage3_cal_en << 3) | (config->stage2_cal_en << 2) |
        (config->stage1_cal_en << 1) | (config->stage0_cal_en << 0);

    return _i2c_write(dev, AD7147_REG_STAGE_CAL_EN, val);
}

// Configure device's STAGE_HIGH_INT_ENANBLE register based on dev_config.
static esp_err_t _configure_high_int_en(const ad7147_hw_t *dev) {
    const ad7147_device_config_t *config = &dev->dev_config;
    const uint16_t val = (config->stage11_high_int_enable << 11) |
                         (config->stage10_high_int_enable << 10) |
                         (config->stage9_high_int_enable << 9) |
                         (config->stage8_high_int_enable << 8) |
                         (config->stage7_high_int_enable << 7) |
                         (config->stage6_high_int_enable << 6) |
                         (config->stage5_high_int_enable << 5) |
                         (config->stage4_high_int_enable << 4) |
                         (config->stage3_high_int_enable << 3) |
                         (config->stage2_high_int_enable << 2) |
                         (config->stage1_high_int_enable << 1) |
                         (config->stage0_high_int_enable << 0);

    return _i2c_write(dev, AD7147_REG_STAGE_HIGH_INT_ENABLE, val);
}

// Configure device's STAGE_COMPLETE_INT_ENABLE register based on dev_config.
static esp_err_t _configure_complete_int_en(const ad7147_hw_t *dev) {
    const ad7147_device_config_t *config = &dev->dev_config;
    const uint16_t val =
        ((config->stageX_complete_int_enable[11] ? 1 : 0) << 11) |
        ((config->stageX_complete_int_enable[10] ? 1 : 0) << 10) |
        ((config->stageX_complete_int_enable[9] ? 1 : 0) << 9) |
        ((config->stageX_complete_int_enable[8] ? 1 : 0) << 8) |
        ((config->stageX_complete_int_enable[7] ? 1 : 0) << 7) |
        ((config->stageX_complete_int_enable[6] ? 1 : 0) << 6) |
        ((config->stageX_complete_int_enable[5] ? 1 : 0) << 5) |
        ((config->stageX_complete_int_enable[4] ? 1 : 0) << 4) |
        ((config->stageX_complete_int_enable[3] ? 1 : 0) << 3) |
        ((config->stageX_complete_int_enable[2] ? 1 : 0) << 2) |
        ((config->stageX_complete_int_enable[1] ? 1 : 0) << 1) |
        ((config->stageX_complete_int_enable[0] ? 1 : 0) << 0);

    // ESP_LOGE(TAG, "int val config: %u", val);
    return _i2c_write(dev, AD7147_REG_STAGE_COMPLETE_INT_ENABLE, val);
}

// Configure stage per stage_config.
static esp_err_t _configure_stage(const ad7147_hw_t *dev, uint8_t stage) {
    const ad7147_stage_config_t *config = &dev->stage_config[stage];
    const uint16_t connection_6_0 = (config->cinX_connection_setup[6] << 12) |
                                    (config->cinX_connection_setup[5] << 10) |
                                    (config->cinX_connection_setup[4] << 8) |
                                    (config->cinX_connection_setup[3] << 6) |
                                    (config->cinX_connection_setup[2] << 4) |
                                    (config->cinX_connection_setup[1] << 2) |
                                    (config->cinX_connection_setup[0] << 0);
    const uint16_t connection_12_7 = (config->pos_afe_offset_disable << 15) |
                                     (config->neg_afe_offset_disable << 14) |
                                     (config->se_connection_setup << 12) |
                                     (config->cinX_connection_setup[12] << 10) |
                                     (config->cinX_connection_setup[11] << 8) |
                                     (config->cinX_connection_setup[10] << 6) |
                                     (config->cinX_connection_setup[9] << 4) |
                                     (config->cinX_connection_setup[8] << 2) |
                                     (config->cinX_connection_setup[7] << 0);
    const uint16_t afe_offset =
        (config->pos_afe_offset_swap << 15) | (config->pos_afe_offset << 8) |
        (config->neg_afe_offset_swap << 7) | (config->neg_afe_offset << 0);
    const uint16_t sensitivity = (config->pos_peak_detect << 12) |
                                 (config->pos_threshold_sensitivity << 8) |
                                 (config->neg_peak_detect << 4) |
                                 (config->neg_threshold_sensitivity << 0);

    const uint8_t reg = AD7147_REG_STAGE0_CONNECTION + stage * 8;
    uint16_t tx[4] = {
        connection_6_0,
        connection_12_7,
        afe_offset,
        sensitivity,
    };
    esp_err_t ret = _i2c_write_multiple(dev, reg, tx, 4);
#if 0
    printf("stage %u config: %u %u %u %u\n", stage, tx[0], tx[1], tx[2], tx[3]);
    //uint16_t rx[4];
    //_i2c_read(dev, reg, rx, 4);
    //printf("read stage config:  %u %u %u %u\n", rx[0], rx[1], rx[2], rx[3]);
#endif
    return ret;
}

// Configure entire device per stage_config and dev_config.
static esp_err_t _configure_full(const ad7147_hw_t *dev) {
    esp_err_t ret;
    if ((ret = _configure_pwr_control(dev)) != ESP_OK) {
        return ret;
    }
    if ((ret = _configure_stage_cal_en(dev)) != ESP_OK) {
        return ret;
    }
    if ((ret = _configure_high_int_en(dev)) != ESP_OK) {
        return ret;
    }
    if ((ret = _configure_complete_int_en(dev)) != ESP_OK) {
        return ret;
    }
    for (uint8_t i = 0; i < 12; i++) {
        if ((ret = _configure_stage(dev, i)) != ESP_OK) {
            return ret;
        }
    }
    return ESP_OK;
}

// Force stage sequencer to reset.
static esp_err_t _reset_sequencer(const ad7147_hw_t *dev) {
    uint16_t val = (0x0 << 0) |   // FF_SKIP_CNT
                   (0xf << 4) |   // FP_PROXIMITY_CNT
                   (0xf << 8) |   // LP_PROXIMITY_CNT
                   (0x0 << 12) |  // PWR_DOWN_TIMEOUT
                   (0x0 << 14) |  // FORCED_CAL
                   (0x1 << 15);   // CONV_RESET
    return _i2c_write(dev, AD7147_REG_AMB_COMP_CTRL0, val);
}

esp_err_t ad7147_hw_init(ad7147_hw_t *device) {
    // ;w; y tho
    // memset(device, 0, sizeof(ad7147_hw_t));
    for (size_t i = 0; i < 12; i++) {
        for (size_t j = 0; j < 13; j++) {
            device->stage_config[i].cinX_connection_setup[j] = CIN_BIAS;
        }
        device->stage_config[i].se_connection_setup = 0b01;
    }
    return _configure_full(device);
}

static inline uint8_t afe_limit(int8_t offset) {
    return offset < 0 ? 0 : (offset > 63 ? 63 : offset);
}

esp_err_t ad7147_hw_configure_stages(ad7147_hw_t *device,
                                     const ad7147_sequence_t *seq) {
    // Reset all stage/channel configuration.
    for (size_t i = 0; i < 12; i++) {
        uint8_t idle_con =
            seq->stages[i].idle_to_bias ? CIN_BIAS : CIN_CDC_NONE;
        for (int8_t j = 0; j < 13; j++) {
            device->stage_config[i].cinX_connection_setup[j] = idle_con;
        }
        device->dev_config.stageX_complete_int_enable[i] = false;
    }

    // Configure stages as requested.
    for (size_t i = 0; i < seq->len; i++) {
        uint16_t channel_mask = seq->stages[i].channel_mask;
        for (uint8_t j = 0; j < 13; j++) {
            if (channel_mask & (1 << j)) {
                device->stage_config[i].cinX_connection_setup[j] = CIN_CDC_POS;
            }
        }
        device->stage_config[i].pos_afe_offset =
            afe_limit(seq->stages[i].pos_afe_offset);
        device->stage_config[i].neg_afe_offset =
            afe_limit(seq->stages[i].neg_afe_offset);
        device->stage_config[i].neg_afe_offset_swap = true;
        device->stage_config[i].pos_afe_offset_swap = false;
    }
    device->dev_config.sequence_stage_num = seq->len - 1;
    device->dev_config.stageX_complete_int_enable[0] = true;

    // For our own record (more precisely, for the interrupt handler).
    device->num_stages = seq->len;

    esp_err_t ret;
    // Submit changes over I2C.
    if ((ret = _configure_pwr_control(device)) != ESP_OK) {
        return ret;
    }
    for (uint8_t i = 0; i < 12; i++) {
        if ((ret = _configure_stage(device, i)) != ESP_OK) {
            return ret;
        }
    }
    if ((ret = _reset_sequencer(device)) != ESP_OK) {
        return ret;
    }
    if ((ret = _configure_complete_int_en(device)) != ESP_OK) {
        return ret;
    }
    uint16_t st;  // throwaway
    if ((ret = _i2c_read(device, AD7147_REG_STAGE_COMPLETE_INT_STATUS, &st,
                         1)) != ESP_OK) {
        return ret;
    }
    return ESP_OK;
}

bool ad7147_hw_get_and_clear_completed(ad7147_hw_t *device, uint16_t *st) {
    esp_err_t res =
        _i2c_read(device, AD7147_REG_STAGE_COMPLETE_INT_STATUS, st, 1);
    if (res != ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }
    return true;
}

bool ad7147_hw_get_cdc_data(ad7147_hw_t *device, uint16_t *data,
                            uint8_t stages) {
    esp_err_t res = _i2c_read(device, AD7147_REG_CDC_RESULT_S0, data, stages);
    if (res != ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }
    return true;
}

bool ad7147_hw_reset_sequencer(ad7147_hw_t *device) {
    esp_err_t res = _reset_sequencer(device);
    if (res != ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }
    return true;
}

// suuuuper duper flow3r specific stuff. shouldn't actually be here but putting
// it in _ad7147.c would require exposing a bunch of stuff to global
// namespace/duplicating/whatevs and we feel like putting it here is the better
// of two bad options. anyways:

// Configure stage. Defaults to stage_config if config is NULL.
static esp_err_t _i2c_golf_override_stage(ad7147_hw_t *dev, uint8_t stage,
                                          ad7147_stage_config_t *config) {
    if (config == NULL) {
        config = &dev->stage_config[stage];
    }
    const uint16_t connection_12_7 = (config->pos_afe_offset_disable << 15) |
                                     (config->neg_afe_offset_disable << 14) |
                                     (config->se_connection_setup << 12) |
                                     (config->cinX_connection_setup[12] << 10) |
                                     (config->cinX_connection_setup[11] << 8) |
                                     (config->cinX_connection_setup[10] << 6) |
                                     (config->cinX_connection_setup[9] << 4) |
                                     (config->cinX_connection_setup[8] << 2) |
                                     (config->cinX_connection_setup[7] << 0);
    const uint16_t afe_offset =
        (config->pos_afe_offset_swap << 15) | (config->pos_afe_offset << 8) |
        (config->neg_afe_offset_swap << 7) | (config->neg_afe_offset << 0);

    const uint8_t reg = AD7147_REG_STAGE0_CONNECTION + stage * 8;
    uint16_t tx[2] = {
        connection_12_7,
        afe_offset,
    };
    esp_err_t ret = _i2c_write_multiple(dev, reg + 1, tx, 2);
#if 0
    printf("stage %u config: %u %u\n", stage, tx[0], tx[1]);
#endif
    return ret;
}

// helper function for ad7147_hw_modulate_stage0_and_reset
static bool _i2c_golf_override_lower_registers(ad7147_hw_t *dev,
                                               uint8_t num_stages) {
    esp_err_t res;
    dev->dev_config.sequence_stage_num = num_stages;
#if 0
    // writing to 0x00: AD7147_REG_PWR_CONTROL
    if ((res = _configure_pwr_control(dev)) != ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }
    // writing to 0x02: AD7147_REG_AMB_COMP_CTRL0
    if(!ad7147_hw_reset_sequencer(dev)) {return false;}
#else
    // ^^ this would be our code in an ideal world. however, we can make it a
    // tiny bit faster by writing to both in a single... uh... protocol session?
    // you catch the dorifto :D bunch of copypasta from the following functions,
    // keep in sync-ish ideally:

    // _configure_pwr_control
    const ad7147_device_config_t *config = &dev->dev_config;
    const uint16_t val0 =
        (config->cdc_bias << 14) | (config->ext_source << 12) |
        (config->int_pol << 11) | (config->sw_reset << 10) |
        (config->decimation << 8) | (config->sequence_stage_num << 4) |
        (config->lp_conv_delay << 2) | (config->power_mode << 0);

    // _configure_stage_cal_en
    const uint16_t val1 =
        (config->avg_lp_skip << 14) | (config->avg_fp_skip << 12) |
        (config->stage11_cal_en << 11) | (config->stage10_cal_en << 10) |
        (config->stage9_cal_en << 9) | (config->stage8_cal_en << 8) |
        (config->stage7_cal_en << 7) | (config->stage6_cal_en << 6) |
        (config->stage5_cal_en << 5) | (config->stage4_cal_en << 4) |
        (config->stage3_cal_en << 3) | (config->stage2_cal_en << 2) |
        (config->stage1_cal_en << 1) | (config->stage0_cal_en << 0);

    // _reset_sequencer
    uint16_t val2 = (0x0 << 0) |   // FF_SKIP_CNT
                    (0xf << 4) |   // FP_PROXIMITY_CNT
                    (0xf << 8) |   // LP_PROXIMITY_CNT
                    (0x0 << 12) |  // PWR_DOWN_TIMEOUT
                    (0x0 << 14) |  // FORCED_CAL
                    (0x1 << 15);   // CONV_RESET

    uint16_t val[3] = { val0, val1, val2 };

    if ((res = _i2c_write_multiple(dev, AD7147_REG_PWR_CONTROL, val, 3)) !=
        ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }
#endif
    return true;
}

// this one is used for dynamic reconfiguration. it's a mouthful to explain,
// check _ad7147.c for usage. be careful about ur locks and isr clears. good
// luck.
bool ad7147_hw_modulate_stage0_and_reset(ad7147_hw_t *dev,
                                         ad7147_sequence_stage_t *s_conf) {
    esp_err_t res;
    // writing to 0x80 + stage * 8:  AD7147_REG_STAGE0_CONNECTION + stage * 8;
    uint8_t num_stages;
    if (s_conf == NULL) {
        num_stages = 11;
        res = _i2c_golf_override_stage(dev, 0, NULL);
    } else {
        // this should be 0 for max performance, but we're deliberately
        // throttling it to match the old 18ms performance in order to not eat
        // too much CPU. this can be modified once we upgrade to espidf5.2 and
        // this thing uses non-blocking i2c ops, or if there is an api that lets
        // users configure performance.
        num_stages = 5;  // 0;
        ad7147_stage_config_t config = { 0 };
        for (uint8_t j = 0; j < 13; j++) {
            if (s_conf->channel_mask & (1 << j)) {
                config.cinX_connection_setup[j] = CIN_CDC_POS;
            } else {
                config.cinX_connection_setup[j] = CIN_CDC_NONE;
            }
        }
        config.pos_afe_offset = afe_limit(s_conf->pos_afe_offset);
        config.neg_afe_offset = afe_limit(s_conf->neg_afe_offset);
        config.neg_afe_offset_swap = true;
        config.pos_afe_offset_swap = false;
        config.se_connection_setup = 0b01;
        res = _i2c_golf_override_stage(dev, 0, &config);
    }

    if (res != ESP_OK) {
        ESP_LOGE(TAG, "captouch i2c failed: %s", esp_err_to_name(res));
        return false;
    }

    return _i2c_golf_override_lower_registers(dev, num_stages);
}
