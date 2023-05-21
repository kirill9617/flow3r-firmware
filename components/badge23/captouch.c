//#include <stdio.h>
//#include <string.h>
#include "esp_log.h"
#include "driver/i2c.h"
#include "badge23_hwconfig.h"
#include <stdint.h>

#if defined(CONFIG_BADGE23_HW_GEN_P3) || defined(CONFIG_BADGE23_HW_GEN_P4)
static const uint8_t top_map[] = {1, 1, 3, 3, 5, 5, 7, 7, 9, 9, 8, 8}; //flipped top and bottom from bootstrap reference
static const uint8_t top_stages = 12;
static const uint8_t bot_map[] = {0, 0, 0, 2, 2, 2, 6, 6, 6, 4, 4, 4}; //idk y :~)
static const uint8_t bottom_stages = 12;

#elif defined(CONFIG_BADGE23_HW_GEN_P1)
static const uint8_t top_map[] = {2, 2, 2, 0, 0, 8, 8, 8, 6, 6, 4, 4};
static const uint8_t top_stages = 12;
static const uint8_t bot_map[] = {1, 1, 3, 3, 5, 5, 7, 7, 9, 9};
static const uint8_t bottom_stages = 10;

#else
#error "captouch not implemented for this badge generation"
#endif

static const char *TAG = "captouch";

#define I2C_MASTER_NUM              0                          /*!< I2C master i2c port number, the number of i2c peripheral interfaces available will depend on the chip */

#define AD7147_BASE_ADDR            0x2C

#define AD7147_REG_PWR_CONTROL              0x00
#define AD7147_REG_STAGE_CAL_EN             0x01
#define AD7147_REG_STAGE_HIGH_INT_ENABLE    0x06
#define AD7147_REG_DEVICE_ID                0x17

#define TIMEOUT_MS                  1000
static const struct ad714x_chip *chip_top;
static const struct ad714x_chip *chip_bot;


struct ad714x_chip {
    uint8_t addr;
    uint8_t gpio;
    int pos_afe_offsets[13];
    int neg_afe_offsets[13];
    int neg_afe_offset_swap;
    int stages;
};  

// Captouch sensor chips addresses are swapped on proto3. Whoops.
#if defined(CONFIG_BADGE23_HW_GEN_P3)
#define AD7147_BASE_ADDR_TOP (AD7147_BASE_ADDR)
#define AD7147_BASE_ADDR_BOT (AD7147_BASE_ADDR + 1)
#else
#define AD7147_BASE_ADDR_TOP (AD7147_BASE_ADDR + 1)
#define AD7147_BASE_ADDR_BOT (AD7147_BASE_ADDR)
#endif

static const struct ad714x_chip chip_top_rev5 = {.addr = AD7147_BASE_ADDR_TOP, .gpio = 15,
    .pos_afe_offsets = {4, 2, 2, 2, 2, 3, 4, 2, 2, 2, 2, 0},
    .stages=12};
static const struct ad714x_chip chip_bot_rev5 = {.addr = AD7147_BASE_ADDR_BOT, .gpio = 15,
    .pos_afe_offsets = {3, 2, 1, 1 ,1, 1, 1, 1, 2, 3, 3, 3},
    .stages=12};
/*
static const struct ad714x_chip chip_top = {.addr = AD7147_BASE_ADDR_TOP, .gpio = 48, .afe_offsets = {24, 12, 16, 33, 30, 28, 31, 27, 22, 24, 18, 19, }, .stages=top_stages};
static const struct ad714x_chip chip_bot = {.addr = AD7147_BASE_ADDR_BOT, .gpio = 3, .afe_offsets = {3, 2, 1, 1 ,1, 1, 1, 1, 2, 3}, .stages=bottom_stages};
*/
//static void captouch_task(void* arg);

static esp_err_t ad714x_i2c_write(const struct ad714x_chip *chip, const uint16_t reg, const uint16_t data)
{
    const uint8_t tx[] = {reg >> 8, reg & 0xFF, data >> 8, data & 0xFF};
    ESP_LOGI(TAG, "AD7147 write reg %X-> %X", reg, data);
    return i2c_master_write_to_device(I2C_MASTER_NUM, chip->addr, tx, sizeof(tx), TIMEOUT_MS / portTICK_PERIOD_MS);
}

static esp_err_t ad714x_i2c_read(const struct ad714x_chip *chip, const uint16_t reg, uint16_t *data, const size_t len)
{
    const uint8_t tx[] = {reg >> 8, reg & 0xFF};
    uint8_t rx[len * 2];
    esp_err_t ret = i2c_master_write_read_device(I2C_MASTER_NUM, chip->addr, tx, sizeof(tx), rx, sizeof(rx), TIMEOUT_MS / portTICK_PERIOD_MS);
    for(int i = 0; i < len; i++) {
        data[i] = (rx[i * 2] << 8) | rx[i * 2 + 1];
    }
    return ret;
}

struct ad7147_stage_config {
    unsigned int cinX_connection_setup[13];
    unsigned int se_connection_setup:2;
    unsigned int neg_afe_offset_disable:1;
    unsigned int pos_afe_offset_disable:1;
    unsigned int neg_afe_offset:6;
    unsigned int neg_afe_offset_swap:1;
    unsigned int pos_afe_offset:6;
    unsigned int pos_afe_offset_swap:1;
    unsigned int neg_threshold_sensitivity:4;
    unsigned int neg_peak_detect:3;
    unsigned int pos_threshold_sensitivity:4;
    unsigned int pos_peak_detect:3;
};

#define CIN CDC_NONE    0
#define CIN_CDC_NEG     1
#define CIN_CDC_POS     2
#define CIN_BIAS        3

static const uint16_t bank2 = 0x80;

static void ad714x_set_stage_config(const struct ad714x_chip *chip, const uint8_t stage, const struct ad7147_stage_config * config)
{
    const uint16_t connection_6_0 = (config->cinX_connection_setup[6] << 12) | (config->cinX_connection_setup[5] << 10) | (config->cinX_connection_setup[4] << 8) | (config->cinX_connection_setup[3] << 6) | (config->cinX_connection_setup[2] << 4) | (config->cinX_connection_setup[1] << 2) | (config->cinX_connection_setup[0] << 0);
    const uint16_t connection_12_7 = (config->pos_afe_offset_disable << 15) | (config->neg_afe_offset_disable << 14) | (config->se_connection_setup << 12) | (config->cinX_connection_setup[12] << 10) | (config->cinX_connection_setup[11] << 8) | (config->cinX_connection_setup[10] << 6) | (config->cinX_connection_setup[9] << 4) | (config->cinX_connection_setup[8] << 2) | (config->cinX_connection_setup[7] << 0);
    const uint16_t afe_offset = (config->pos_afe_offset_swap << 15) | (config->pos_afe_offset << 8) | (config->neg_afe_offset_swap << 7) | (config->neg_afe_offset << 0);
    const uint16_t sensitivity = (config->pos_peak_detect << 12) | (config->pos_threshold_sensitivity << 8) | (config->neg_peak_detect << 4) | (config->neg_threshold_sensitivity << 0);

    //ESP_LOGI(TAG, "Stage %d config-> %X %X %X %X", stage, connection_6_0, connection_12_7, afe_offset, sensitivity);
    //ESP_LOGI(TAG, "Config: %X %X %X %X %X %X %X %X %X", config->pos_afe_offset_disable, config->pos_afe_offset_disable, config->se_connection_setup, config->cinX_connection_setup[12], config->cinX_connection_setup[11], config->cinX_connection_setup[10], config->cinX_connection_setup[9], config->cinX_connection_setup[8], config->cinX_connection_setup[7]);

    ad714x_i2c_write(chip, bank2 + stage * 8, connection_6_0);
    ad714x_i2c_write(chip, bank2 + stage * 8 + 1, connection_12_7);
    ad714x_i2c_write(chip, bank2 + stage * 8 + 2, afe_offset);
    ad714x_i2c_write(chip, bank2 + stage * 8 + 3, sensitivity);
}

struct ad7147_device_config {
    unsigned int power_mode:2;
    unsigned int lp_conv_delay:2;
    unsigned int sequence_stage_num:4;
    unsigned int decimation:2;
    unsigned int sw_reset:1;
    unsigned int int_pol:1;
    unsigned int ext_source:1;
    unsigned int cdc_bias:2;

    unsigned int stage0_cal_en:1;
    unsigned int stage1_cal_en:1;
    unsigned int stage2_cal_en:1;
    unsigned int stage3_cal_en:1;
    unsigned int stage4_cal_en:1;
    unsigned int stage5_cal_en:1;
    unsigned int stage6_cal_en:1;
    unsigned int stage7_cal_en:1;
    unsigned int stage8_cal_en:1;
    unsigned int stage9_cal_en:1;
    unsigned int stage10_cal_en:1;
    unsigned int stage11_cal_en:1;
    unsigned int avg_fp_skip:2;
    unsigned int avg_lp_skip:2;

    unsigned int stage0_high_int_enable:1;
    unsigned int stage1_high_int_enable:1;
    unsigned int stage2_high_int_enable:1;
    unsigned int stage3_high_int_enable:1;
    unsigned int stage4_high_int_enable:1;
    unsigned int stage5_high_int_enable:1;
    unsigned int stage6_high_int_enable:1;
    unsigned int stage7_high_int_enable:1;
    unsigned int stage8_high_int_enable:1;
    unsigned int stage9_high_int_enable:1;
    unsigned int stage10_high_int_enable:1;
    unsigned int stage11_high_int_enable:1;
};


static void ad714x_set_device_config(const struct ad714x_chip *chip, const struct ad7147_device_config * config)
{
    const uint16_t pwr_control = (config->cdc_bias << 14) | (config->ext_source << 12) | (config->int_pol << 11) | (config->sw_reset << 10) | (config->decimation << 8) | (config->sequence_stage_num << 4) | (config->lp_conv_delay << 2) | (config->power_mode << 0);
    const uint16_t stage_cal_en = (config->avg_lp_skip << 14) | (config->avg_fp_skip << 12) | (config->stage11_cal_en << 11) | (config->stage10_cal_en << 10) | (config->stage9_cal_en << 9) | (config->stage8_cal_en << 8) | (config->stage7_cal_en << 7) | (config->stage6_cal_en << 6) | (config->stage5_cal_en << 5) | (config->stage4_cal_en << 4) | (config->stage3_cal_en << 3) | (config->stage2_cal_en << 2) | (config->stage1_cal_en << 1) | (config->stage0_cal_en << 0);
    const uint16_t stage_high_int_enable = (config->stage11_high_int_enable << 11) | (config->stage10_high_int_enable << 10) | (config->stage9_high_int_enable << 9) | (config->stage8_high_int_enable << 8) | (config->stage7_high_int_enable << 7) | (config->stage6_high_int_enable << 6) | (config->stage5_high_int_enable << 5) | (config->stage4_high_int_enable << 4) | (config->stage3_high_int_enable << 3) | (config->stage2_high_int_enable << 2) | (config->stage1_high_int_enable << 1) | (config->stage0_high_int_enable << 0);

    ad714x_i2c_write(chip, AD7147_REG_PWR_CONTROL, pwr_control);
    ad714x_i2c_write(chip, AD7147_REG_STAGE_CAL_EN, stage_cal_en);
    ad714x_i2c_write(chip, AD7147_REG_STAGE_HIGH_INT_ENABLE, stage_high_int_enable);
}

static struct ad7147_stage_config ad714x_default_config(void)
{
    return (struct ad7147_stage_config) {
            .cinX_connection_setup={CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS, CIN_BIAS},
            .se_connection_setup=0b01,
            .pos_afe_offset=0,
        };
}

static uint16_t pressed_top, pressed_bot;

static void captouch_chip_readout(struct ad714x_chip * chip){
    uint16_t pressed;
    ad714x_i2c_read(chip, 9, &pressed, 1);
    ESP_LOGI(TAG, "Addr %x, High interrupt %X", chip->addr, pressed);

    pressed &= ((1 << chip->stages) - 1);

    if(chip == chip_top) pressed_top = pressed;
    if(chip == chip_bot) pressed_bot = pressed;
}

void manual_captouch_readout(uint8_t top)
{
    struct ad714x_chip* chip = top ? (chip_top) : (chip_bot);
    captouch_chip_readout(chip);
    //xQueueSend(gpio_evt_queue, &chip, NULL);
}

/*
void gpio_event_handler(void* arg)
{
    static unsigned long counter = 0;
    struct ad714x_chip* chip;
    while(true) {
        if(xQueueReceive(gpio_evt_queue, &chip, portMAX_DELAY)) {
            captouch_chip_readout(chip);
        }
    }
}
*/

uint16_t read_captouch(){
    uint16_t petals = 0;
    uint16_t top = pressed_top;
    uint16_t bot = pressed_bot;

    for(int i=0; i<top_stages; i++) {
        if(top  & (1 << i)) {
            petals |= (1<<top_map[i]);
        }
    }

    for(int i=0; i<bottom_stages; i++) {
        if(bot  & (1 << i)) {
            petals |= (1<<bot_map[i]);
        }
    }

    return petals;
}

static void captouch_init_chip(const struct ad714x_chip* chip, const struct ad7147_device_config device_config)
{
    uint16_t data;
    ad714x_i2c_read(chip, AD7147_REG_DEVICE_ID, &data, 1);
    ESP_LOGI(TAG, "DEVICE ID = %X", data);

    ad714x_set_device_config(chip, &device_config);

    for(int i=0; i<chip->stages; i++) {
        struct ad7147_stage_config stage_config;
        stage_config = ad714x_default_config();
        stage_config.cinX_connection_setup[i] = CIN_CDC_POS;
        stage_config.pos_afe_offset=chip->pos_afe_offsets[i];
        ad714x_set_stage_config(chip, i, &stage_config);
    }
}

void captouch_init(void)
{
#if 0
    //gpio_install_isr_service(ESP_INTR_FLAG_DEFAULT);
    captouch_init_chip(&chip_top, (struct ad7147_device_config){.sequence_stage_num = 11,
                                                 .decimation = 1,
                                                 .stage0_cal_en = 1,
                                                 .stage1_cal_en = 1,
                                                 .stage2_cal_en = 1,
                                                 .stage3_cal_en = 1,
                                                 .stage4_cal_en = 1,
                                                 .stage5_cal_en = 1,
                                                 .stage6_cal_en = 1,
                                                 .stage7_cal_en = 1,
                                                 .stage8_cal_en = 1,
                                                 .stage9_cal_en = 1,
                                                 .stage10_cal_en = 1,
                                                 .stage11_cal_en = 1,

                                                 .stage0_high_int_enable = 1,
                                                 .stage1_high_int_enable = 1,
                                                 .stage2_high_int_enable = 1,
                                                 .stage3_high_int_enable = 1,
                                                 .stage4_high_int_enable = 1,
                                                 .stage5_high_int_enable = 1,
                                                 .stage6_high_int_enable = 1,
                                                 .stage7_high_int_enable = 1,
                                                 .stage8_high_int_enable = 1,
                                                 .stage9_high_int_enable = 1,
                                                 .stage10_high_int_enable = 1,
                                                 .stage11_high_int_enable = 1,
#endif
//    if(portexpander_rev6()) {
//        chip_top = &chip_top_rev6;
//        chip_bot = &chip_bot_rev6;
//    } else {
        chip_top = &chip_top_rev5;
        chip_bot = &chip_bot_rev5;
//    }

    captouch_init_chip(chip_top, (struct ad7147_device_config){.sequence_stage_num = 11,
                                                 .decimation = 1,
                                                 });

    captouch_init_chip(chip_bot, (struct ad7147_device_config){.sequence_stage_num = 11,
                                                 .decimation = 1,
#if 0
                                                 .stage0_cal_en = 1,
                                                 .stage1_cal_en = 1,
                                                 .stage2_cal_en = 1,
                                                 .stage3_cal_en = 1,
                                                 .stage4_cal_en = 1,
                                                 .stage5_cal_en = 1,
                                                 .stage6_cal_en = 1,
                                                 .stage7_cal_en = 1,
                                                 .stage8_cal_en = 1,
                                                 .stage9_cal_en = 1,

                                                 .stage0_high_int_enable = 1,
                                                 .stage1_high_int_enable = 1,
                                                 .stage2_high_int_enable = 1,
                                                 .stage3_high_int_enable = 1,
                                                 .stage4_high_int_enable = 1,
                                                 .stage5_high_int_enable = 1,
                                                 .stage6_high_int_enable = 1,
                                                 .stage7_high_int_enable = 1,
                                                 .stage8_high_int_enable = 1,
                                                 .stage9_high_int_enable = 1,
                                                 });

    gpio_evt_queue = xQueueCreate(10, sizeof(const struct ad714x_chip*));
    //xTaskCreate(gpio_event_handler, "gpio_event_handler", 2048 * 2, NULL, configMAX_PRIORITIES - 2, NULL);
#endif
                                                 });

    TaskHandle_t handle;
    //xTaskCreatePinnedToCore(&captouch_task, "captouch", 4096, NULL, configMAX_PRIORITIES - 2, &handle, 1);
    //xTaskCreate(&captouch_task, "captouch", 4096, NULL, configMAX_PRIORITIES - 2, &handle);
}

static void print_cdc(uint16_t *data)
{
    ESP_LOGI(TAG, "CDC results: %X %X %X %X %X %X %X %X %X %X %X %X", data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]);
}

static void print_ambient(uint16_t *data)
{
    ESP_LOGI(TAG, "AMB results: %X %X %X %X %X %X %X %X %X %X %X %X", data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]);
}


static uint16_t trigger(uint16_t *data, uint16_t *ambient)
{
    uint16_t pressed = 0;
    for(int i=0; i<12; i++) {
        // TODO: random value
        if(data[i] - ambient[i] > 2000) {
            pressed |= (1<<i);
        }
    }
    return pressed;
}

uint16_t cdc_data[2][12] = {0,};
uint16_t cdc_ambient[2][12] = {0,};

//extern void espan_handle_captouch(uint16_t pressed_top, uint16_t pressed_bot);

static uint8_t calib_cycles = 0;
void captouch_force_calibration(){
    if(!calib_cycles){ //last calib has finished
        calib_cycles = 16; //goal cycles, can be argument someday
    }
}

void captouch_read_cycle(){
        static int cycle = 0;
        static uint8_t calib_cycle = 0; 
        vTaskDelay(10 / portTICK_PERIOD_MS);
        if(calib_cycles){
            if(calib_cycle == 0){ // last cycle has finished
                calib_cycle = calib_cycles;
            }
            uint32_t ambient_acc[2][12] = {{0,}, {0,}};
            for(int i = 0; i < 16; i++) {
                vTaskDelay(10 / portTICK_PERIOD_MS);
                ad714x_i2c_read(chip_top, 0xB, cdc_ambient[0], chip_top->stages);
                print_ambient(cdc_ambient[0]);
                ad714x_i2c_read(chip_bot, 0xB, cdc_ambient[1], chip_bot->stages);
                print_ambient(cdc_ambient[1]);
                for(int j=0;j<12;j++){
                    ambient_acc[0][j] += cdc_ambient[0][j];
                    ambient_acc[1][j] += cdc_ambient[1][j];
                }
            }

            // TODO: use median instead of average
            calib_cycle--;
            if(!calib_cycle){ //calib cycle is complete
                for(int i=0;i<12;i++){
                    cdc_ambient[0][i] = ambient_acc[0][i] / calib_cycles;
                    cdc_ambient[1][i] = ambient_acc[1][i] / calib_cycles;
                }
                calib_cycles = 0;
            }
        } else {
            cycle++;

            ad714x_i2c_read(chip_top, 0xB, cdc_data[0], chip_top->stages);
            pressed_top = trigger(cdc_data[0], cdc_ambient[0]);

            if(cycle % 100 == 0) {
                print_ambient(cdc_ambient[0]);
                print_cdc(cdc_data[0]);
            }

            ad714x_i2c_read(chip_bot, 0xB, cdc_data[1], chip_bot->stages);
            pressed_bot = trigger(cdc_data[1], cdc_ambient[1]);
            if(cycle % 100 == 0) {
                print_ambient(cdc_ambient[1]);
                print_cdc(cdc_data[1]);
            }
        }
}

static void captouch_task(void* arg)
{
    while(true) {
    }
}


static void captouch_print_debug_info_chip(const struct ad714x_chip* chip)
{
    uint16_t *data;
    uint16_t *ambient;
    const int stages = chip->stages;

    if(chip == chip_top) {
        data = cdc_data[0];
        ambient = cdc_ambient[0];
    } else {
        data = cdc_data[1];
        ambient = cdc_ambient[1];
    }

#if 1
    ESP_LOGI(TAG, "CDC results: %X %X %X %X %X %X %X %X %X %X %X %X", data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]);

    for(int stage=0; stage<stages; stage++) {
        ESP_LOGI(TAG, "stage %d ambient: %X diff: %d", stage, ambient[stage], data[stage] - ambient[stage]);
    }
#endif
#if 0
    ad714x_i2c_read(chip, 8, data, 1);
    ESP_LOGI(TAG, "Low interrupt %X", data[0]);
    ad714x_i2c_read(chip, 9, data, 1);
    ESP_LOGI(TAG, "High interrupt %X", data[0]);
    ad714x_i2c_read(chip, 0x42, data, 1);
    ESP_LOGI(TAG, "Proximity %X", data[0]);
    //ESP_LOGI(TAG, "CDC result = %X", data[0]);
    //if(data[0] > 0xa000) {
        //ESP_LOGI(TAG, "Touch! %X", data[0]);
    //}
#endif
}

void captouch_print_debug_info(void)
{
    captouch_print_debug_info_chip(chip_top);
    captouch_print_debug_info_chip(chip_bot);
}

void captouch_get_cross(int paddle, int *x, int *y)
{
    uint16_t *data;
    uint16_t *ambient;

    int result[2] = {0, 0};
    float total = 0;

    const int paddle_info_1[] = {
        4,
        0,
        1,
        2,
        11,
        4,
        9,
        7,
        6,
        9,
    };
    const int paddle_info_2[] = {
        3,
        1,
        0,
        3,
        10,
        5,
        8,
        6,
        5,
        8,
    };

    struct ad714x_chip* chip;
    if (paddle % 2 == 0) {
        //chip = chip_top;
        data = cdc_data[0];
        ambient = cdc_ambient[0];
    } else {
        //chip = chip_bot;
        data = cdc_data[1];
        ambient = cdc_ambient[1];
    }
    //ESP_LOGI(TAG, "CDC results: %X %X %X %X %X %X %X %X %X %X %X %X", data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]);

    int diff1 = data[paddle_info_1[paddle]] - ambient[paddle_info_1[paddle]];
    int diff2 = data[paddle_info_2[paddle]] - ambient[paddle_info_2[paddle]];

    ESP_LOGI(TAG, "%10d %10d", diff1, diff2);

    int vectors[][2] = {{240, 240}, {240, 0}, {0, 120}};
    total = ((diff1) + (diff2));

    result[0] = vectors[0][0] * (diff1) + vectors[1][0] * (diff2);
    result[1] = vectors[0][1] * (diff1) + vectors[1][1] * (diff2);

    *x = result[0] / total;
    *y = result[1] / total;
}
