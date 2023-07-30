#pragma once

#include "bmi2_defs.h"

#include "flow3r_bsp_i2c.h"

#include "esp_err.h"

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    struct bmi2_dev bmi;
    uint8_t dev_addr;
} flow3r_bsp_imu_t;

// Init the IMU to default settings
//
// 100 Hz sample rate, 2 g range
esp_err_t flow3r_bsp_imu_init(flow3r_bsp_imu_t *imu);

// Query the IMU for an accelerometer reading.
//
// This directly calls the I2C bus and need to lock the bus for that.
// Returns ESP_ERR_NOT_FOUND if there is no new reading available.
// Return values in m/s.
esp_err_t flow3r_bsp_imu_read_acc_mps(flow3r_bsp_imu_t *imu, float *x, float *y,
                                      float *z);
