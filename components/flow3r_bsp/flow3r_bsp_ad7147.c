// note: this code is kind of frankenstein'd out of the
// remains of a refactor that introduced a lot of complexity
// that wasn't needed anymore.
//
// it was an entire thing and we were exhausted and we did not
// clean this up properly. it works, and that's enough for now.
//
// also there is still a major state machine missing so we
// don't see good reason to improve structure at this point.

#include "flow3r_bsp_ad7147.h"
#include "flow3r_bsp_ad7147_hw.h"
#include "flow3r_bsp_captouch.h"
#include "flow3r_bsp_i2c.h"

#include "esp_err.h"
#include "esp_log.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "sdkconfig.h"

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

#include "driver/gpio.h"

// #define CAPTOUCH_PROFILING

#ifdef CAPTOUCH_PROFILING
// not available for building recovery
#include "esp_timer.h"
#endif

static const char *TAG = "flow3r-bsp-ad7147";

// output data that gets continuously written to and
// memcpy'd when the user requests.
static flow3r_bsp_captouch_data_t captouch_data;
// lock for captouch_data
static SemaphoreHandle_t captouch_output_lock = NULL;
// task that generates captouch_data
static TaskHandle_t _captouch_task_handle = NULL;
// helper task for the bottom chip
static TaskHandle_t _cursed_task_handle = NULL;
// container for unprocessed petal data and its lock.
// 10 petals, 4 potential pad positions according to
// petal_kind_t. some fields are never used.
static uint16_t raw_petals[10][4];
// lock for parts of raw_petals: only petal indices
// that are served by the bottom chip (all uneven ones
// and 2).
static SemaphoreHandle_t raw_petal_bot_chip_lock = NULL;

typedef struct {
    size_t petal_number;
    petal_kind_t pad_kind;
} pad_mapping_t;

typedef struct {
    bool press_event_new;
    bool fresh;
} press_latch_t;

static press_latch_t latches[10];

static inline void petal_process(uint8_t index);

// DATASHEET VIOLATION 1
// target value that we ideally wanna see from an idle petal.
// this chip was designed for some sort  of (plastic) case
// between electrode and finger so our signal is coming in
// super hot and we need the extended headroom. datasheet
// suggests to set this to halfpoint (32k).
static const int32_t _calib_target = 6000;
// this is what we assume one step in the chip's AFE
// parameter does to the output reading. this value is used
// in an iterative process so it doesn't have to be super
// precise but it helps to be in the ballpark. we thiink
// the real value is more like 970 but not sure how linear
// this is. anyways, calibration works reasonably well with
// this, let's never touch it again :D
static const int32_t _calib_incr_cap = 1000;

#if defined(CONFIG_FLOW3R_HW_GEN_P3)
static const pad_mapping_t _map_top[12] = {
    { 0, petal_pad_tip },  // 0
    { 0, petal_pad_ccw },  // 1
    { 0, petal_pad_cw },   // 2
    { 8, petal_pad_cw },   // 3
    { 8, petal_pad_ccw },  // 4
    { 8, petal_pad_tip },  // 5
    { 4, petal_pad_tip },  // 6
    { 4, petal_pad_ccw },  // 7
    { 4, petal_pad_cw },   // 8
    { 6, petal_pad_cw },   // 9
    { 6, petal_pad_ccw },  // 10
    { 6, petal_pad_tip },  // 11
};

static const pad_mapping_t _map_bot[13] = {
    { 9, petal_pad_base },  // 0
    { 9, petal_pad_tip },   // 1

    { 7, petal_pad_base },  // 2
    { 7, petal_pad_tip },   // 3

    { 5, petal_pad_base },  // 4
    { 5, petal_pad_tip },   // 5

    { 3, petal_pad_tip },   // 6
    { 3, petal_pad_base },  // 7

    { 1, petal_pad_tip },   // 8
    { 1, petal_pad_base },  // 9

    { 2, petal_pad_tip },  // 10
    { 2, petal_pad_cw },   // 11
    { 2, petal_pad_ccw },  // 12
};

static gpio_num_t _interrupt_gpio_top = GPIO_NUM_15;
static gpio_num_t _interrupt_gpio_bot = GPIO_NUM_15;
static bool _interrupt_shared = true;
#elif defined(CONFIG_FLOW3R_HW_GEN_P4) || defined(CONFIG_FLOW3R_HW_GEN_C23)
static const pad_mapping_t _map_top[12] = {
    { 0, petal_pad_ccw },   // 0
    { 0, petal_pad_base },  // 1
    { 0, petal_pad_cw },    // 2
    { 8, petal_pad_cw },    // 3
    { 8, petal_pad_base },  // 4
    { 8, petal_pad_ccw },   // 5
    { 4, petal_pad_ccw },   // 6
    { 4, petal_pad_base },  // 7
    { 4, petal_pad_cw },    // 8
    { 6, petal_pad_ccw },   // 9
    { 6, petal_pad_base },  // 10
    { 6, petal_pad_cw },    // 11
};
static const pad_mapping_t _map_bot[13] = {
    { 9, petal_pad_base },  // 0
    { 9, petal_pad_tip },   // 1

    { 7, petal_pad_base },  // 2
    { 7, petal_pad_tip },   // 3

    { 5, petal_pad_base },  // 4
    { 5, petal_pad_tip },   // 5

    { 3, petal_pad_tip },   // 6
    { 3, petal_pad_base },  // 7

    { 1, petal_pad_tip },   // 8
    { 1, petal_pad_base },  // 9

    { 2, petal_pad_ccw },   // 10
    { 2, petal_pad_cw },    // 11
    { 2, petal_pad_base },  // 12
};
#if defined(CONFIG_FLOW3R_HW_GEN_P4)
static gpio_num_t _interrupt_gpio_top = GPIO_NUM_15;
static gpio_num_t _interrupt_gpio_bot = GPIO_NUM_15;
static bool _interrupt_shared = true;
#else
static gpio_num_t _interrupt_gpio_top = GPIO_NUM_15;
static gpio_num_t _interrupt_gpio_bot = GPIO_NUM_16;
static bool _interrupt_shared = false;
#endif
#else
#error "captouch not implemented for this badge generation"
#endif

static ad7147_chip_t _top = {
    .name = "top",
    .is_bot = false,
    .nchannels = 12,
    .sequence = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, -1 },
};

static ad7147_chip_t _bot = {
    .name = "bot",
    .is_bot = true,
    // don't change this field pls there's a bunch of hardcoded stuff around :3
    .nchannels = 13,
    // first and last must be >= 7 bc i2c golf reasons.
    // keeping petal 2 away from the swap helps w noise a bit.
    .sequence = { 8, 0, 1, 2, 3, 10, 11, 12, 4, 5, 6, 7, 9 },
};

static ad7147_sequence_stage_t _cursed_swap_stage;

void get_stage_hw_config(ad7147_chip_t *chip, ad7147_sequence_t *seq_out,
                         uint8_t i, uint8_t channel) {
    int8_t offset = chip->channels[channel].afe_offset;
    seq_out->stages[i].channel_mask = 1 << channel;
    // DATASHEET VIOLATION 2
    // the datasheet recommends to connect captouch pads to the internal bias
    // while they are not being measured. here's why we're not doing that:
    //
    // there was a strong cross talk issue on the bottom chip petals that
    // varied with grounding setup (e.g., plugging in a usb cable and putting
    // the other end in ur pocket changed behavior). we suspected that this
    // might be due to a capacitive interaction between device ground, chip bias
    // and chip shield driver. our wild theories were rewarded, and while
    // introducing a bit of noise (well within budget, mind you) this resolved
    // the issue.
    //
    // a few months later, a rare edge case was brought to our attention: when
    // many channels on the top chip petals were saturated, similar cross talk
    // could be generated. we applied the fix to the top chip too, and sure
    // enough it resolved the issue. which makes sense except for fact that the
    // top chip petals don't couple to a shield driver.
    //
    // we currently have no fully sensical mental model for why this works but
    // that's okay.

    // datasheet recommendation-ish (13-seq has hardcoded bits that violate
    // this, change manually!)
    // seq_out->stages[i].idle_to_bias = true;
    // experiment A: only top pads
    // seq_out->stages[i].idle_to_bias = !(chip->is_bot && (channel < 10));
    // experiment B: only top chip pads
    // seq_out->stages[i].idle_to_bias = !chip->is_bot;
    // experiment C: none (winner)
    seq_out->stages[i].idle_to_bias = false;
    if (offset < 63) {
        seq_out->stages[i].neg_afe_offset = offset;
        seq_out->stages[i].pos_afe_offset = 0;
    } else {
        seq_out->stages[i].neg_afe_offset = 63;
        seq_out->stages[i].pos_afe_offset = offset - 63;
    }
}

// bad hack, see below
static esp_err_t _cursed_sequence_request(ad7147_chip_t *chip, bool init,
                                          bool recalib) {
    int8_t *seq = chip->sequence;
    ad7147_sequence_t seq_out;
    get_stage_hw_config(chip, &seq_out, 0, seq[12]);
    memcpy(&_cursed_swap_stage, &(seq_out.stages[0]),
           sizeof(ad7147_sequence_stage_t));
    return ESP_OK;
}

// This takes a sequence of stages from the chip config, gets
// the configuration data for the individual stages
// and writes it to the respective captouch chip.
// In case of the bottom chip we request a 13-sequence, so that's
// not possible, so we use a hardcoded hack to save the 13th
// sequence step configuration data for later use.
static esp_err_t _sequence_request(ad7147_chip_t *chip, bool init,
                                   bool recalib) {
    if (chip->is_bot) {
        _cursed_sequence_request(chip, init, recalib);
    }
    int8_t *seq = chip->sequence;
    ad7147_sequence_t seq_out = {
        .len = chip->nchannels,
    };
    seq_out.len = seq_out.len > 12 ? 12 : seq_out.len;
    for (size_t i = 0; i < seq_out.len; i++) {
        get_stage_hw_config(chip, &seq_out, i, seq[i]);
    }

    esp_err_t ret;
    if ((ret = ad7147_hw_configure_stages(&chip->dev, &seq_out)) != ESP_OK) {
        return ret;
    }
    return ESP_OK;
}

static bool _channel_afe_tweak(ad7147_chip_t *chip, size_t cix) {
    int32_t cur = chip->channels[cix].amb;
    int32_t target = _calib_target;
    int32_t diff = (cur - target) / _calib_incr_cap;
    if (diff < 1 && diff > -1) {
        return false;
    }
    int32_t offset = chip->channels[cix].afe_offset;
    if (offset <= 0 && diff < 0) {
        return false;
    }
    if (offset >= 126 && diff > 0) {
        return false;
    }
    offset += diff;
    if (offset < 0) {
        offset = 0;
    }
    if (offset > 126) {
        offset = 126;
    }
    chip->channels[cix].afe_offset = offset;
    return true;
}

// Takes data from captouch chip readout, looks up which petal pad
// it belongs to according to the chip map and puts it there.
// May need to take lock for raw_petals access depending on circumstances
// (atm just for bottom chip).
// Should maybe get a proper name someday. Sorry. Only used by
// raw_data_to_petal_pads atm, maybe it should just absorb it, it's
// not that big.
static void _on_chip_data(ad7147_chip_t *chip, uint16_t *values, size_t len) {
    assert(chip == &_top || chip == &_bot);
    bool top = chip == &_top;
    const pad_mapping_t *map = top ? _map_top : _map_bot;

    for (uint8_t i = 0; i < len; i++) {
        raw_petals[map[i].petal_number][map[i].pad_kind] = values[i];
    }
}

// Generates raw data and sends it to raw_petals[][].
// Yes, raw data is processed. Hah. You have been lied to.
// A summary of lies:
// - While a calibration is running, data output isn't updated. This means
//   we don't need to waste our time with updating raw_petals either. Not so
//   bad right?
// - Calibration is a composition of "coarse" hardware biasing (that AFE thing
//   that  keeps popping up), plus a residual "fine" software offset.
//   Since they both work in tandem, we decided to consider raw data whatever
//   is left after both of them are applied, so raw_petals doesn't hold the
//   raw readings, but already has the fine offset applied. This makes it
//   considerably harder to forget to apply it.
static void raw_data_to_petal_pads(ad7147_chip_t *chip, uint16_t *data,
                                   size_t len) {
    if (chip->calibration_cycles > 0) {
        // We're doing a calibration cycle on our channels. Instead of writing
        // the data to channel->cdc, write it to channel->amb_meas.
        int8_t j = chip->calibration_cycles - 1;
        if (j < _AD7147_CALIB_CYCLES) {  // throw away first few datapoints
            for (int8_t i = 0; i < len; i++) {
                uint8_t k = chip->sequence[i];
                chip->channels[k].amb_meas[j] = data[i];
            }
        }
    } else {
        // Normal measurement, apply to channel->cdc.
        for (size_t i = 0; i < len; i++) {
            uint8_t k = chip->sequence[i];
            chip->channels[k].cdc = data[i];
        }
    }

    bool recalib = chip->calibration_external;

    // Deal with calibration pending flag, possibly starting calibration.
    if (chip->calibration_pending) {
        if (!chip->calibration_active) {
            ESP_LOGI(TAG, "%s: calibration starting...", chip->name);
            chip->calibration_cycles = _AD7147_CALIB_CYCLES + 2;
            chip->calibration_active = true;
        }
        chip->calibration_pending = false;
    }

    if (chip->calibration_active) {
        // Deal with active calibration.
        chip->calibration_cycles--;
        if (chip->calibration_cycles <= 0) {
            // Calibration measurements done. Calculate average amb data for
            // each channel.
            for (size_t i = 0; i < chip->nchannels; i++) {
                uint32_t avg = 0;
                for (uint8_t j = 0; j < _AD7147_CALIB_CYCLES; j++) {
                    avg += chip->channels[i].amb_meas[j];
                }
                chip->channels[i].amb = avg / _AD7147_CALIB_CYCLES;
            }

            // Can we tweak the AFE to get a better measurement?
            uint16_t rerun = 0;
            for (size_t i = 0; i < chip->nchannels; i++) {
                if (_channel_afe_tweak(chip, i)) {
                    rerun |= (1 << i);
                }
            }
            if (rerun != 0) {
                chip->calibration_cycles = _AD7147_CALIB_CYCLES + 2;
                recalib = true;
            } else {
                chip->calibration_active = false;
                ESP_LOGI(TAG, "%s: calibration done.", chip->name);
            }
        }
    } else {
        // Submit data to higher level for processing.
        uint16_t val[13];
        for (size_t i = 0; i < chip->nchannels; i++) {
            int32_t cdc = chip->channels[i].cdc;
            int32_t amb = chip->channels[i].amb;
            int32_t diff = cdc - amb;
            val[i] = diff < 0 ? 0 : (diff > 65535 ? 65535 : diff);
        }
        _on_chip_data(chip, val, chip->nchannels);
    }

    if (recalib) {
        esp_err_t ret;
        if ((ret = _sequence_request(chip, false, recalib)) != ESP_OK) {
            ESP_LOGE(TAG, "%s: requesting next sequence failed: %s", chip->name,
                     esp_err_to_name(ret));
        }
        if (chip->calibration_external) {
            chip->calibration_external = false;
            ESP_LOGI(TAG, "%s: captouch calibration updated", chip->name);
        }
    }
}

// could probably delete half of this but meh who cares
esp_err_t flow3r_bsp_ad7147_chip_init(ad7147_chip_t *chip) {
    esp_err_t ret;
    for (size_t i = 0; i < chip->nchannels; i++) {
        chip->channels[i].amb = 0;
    }
    if ((ret = ad7147_hw_init(&chip->dev)) != ESP_OK) {
        return ret;
    }
    chip->calibration_pending = true;
    if ((ret = _sequence_request(chip, true, true)) != ESP_OK) {
        return ret;
    }
    return ESP_OK;
}

static bool _chip_process(ad7147_chip_t *chip) {
    ad7147_hw_t *device = &chip->dev;
    // Read complete status register. This acknowledges interrupts.
    uint16_t st = 0;
    if (!ad7147_hw_get_and_clear_completed(device, &st)) {
        return false;
    }

    // Nothing to do if no stages are expected to be read.
    if (device->num_stages < 1) {
        return false;
    }

    // Bit indicating the conversion has been complete for the requested number
    // of stages.
    uint16_t complete_bit = (1 << (device->num_stages - 1));
    if (!(st & complete_bit)) return false;

    uint16_t data[12];
    size_t count = device->num_stages;
    if (!ad7147_hw_get_cdc_data(device, data, count)) {
        return false;
    }
    raw_data_to_petal_pads(chip, data, count);
    return true;
}

static void _notify_from_isr(uint32_t mask, TaskHandle_t handle) {
    if (handle == NULL) return;
    BaseType_t xHigherPriorityTaskWoken;
    xTaskNotifyFromISR(handle, mask, eSetBits, &xHigherPriorityTaskWoken);
    portYIELD_FROM_ISR(xHigherPriorityTaskWoken);
}

static void _notify(uint32_t mask, TaskHandle_t handle) {
    if (handle == NULL) return;
    xTaskNotify(handle, mask, eSetBits);
    portYIELD();
}

// (sunshine emoji) tell the captouch task that top chip data is available :D
static void _top_isr(void *data) { _notify_from_isr(2, _captouch_task_handle); }

// (dark cloud emoji) tell the cursed task that it is time for THE PROCEDURE
static void _bot_isr(void *data) { _notify_from_isr(1, _cursed_task_handle); }

// So here's a thing to generally keep in mind with this driver:
// It runs on interrupts. Which come from a hardware. Which
// needs to know that the interrupt has been read in order to
// be able to send another. So each time u receive an interrupt
// you need to clear it else the machinery will just halt.
// Unless maybe you put a timeout somewhere but that would be too
// reasonable.
// Not sure why we mention this here.
static void _kickstart(void) {
    if (_captouch_task_handle == NULL) return;
    ulTaskNotifyValueClear(_captouch_task_handle, 0xffffffff);
    _notify(2, _captouch_task_handle);
    _notify(1, _cursed_task_handle);
}

#ifdef CAPTOUCH_PROFILING
static int64_t _cursed_step_time = 0;
static uint32_t _cursed_step_to_step_time[4];
static uint32_t _cursed_step_execution_time[4];
#endif

// THE PROCEDURE
// we need to reconfigure the bottom chip on the fly to read all 13 channels.
// this here is pretty much a shim between the bottom chip isr and the main
// captouch task that manages the i2c traffic to the bottom chip as well as
// poking the main captouch task when data is ready.
// this is kinda sensitive and overall weird so we keep our lil crappy profiler
// hooked up for now, we're sure we'll need it in the future again.
static bool _cursed_chip_process(ad7147_chip_t *chip, uint8_t *step,
                                 uint16_t *data) {
    ad7147_hw_t *device = &chip->dev;
    uint16_t st = 0;
#ifdef CAPTOUCH_PROFILING
    int64_t time = esp_timer_get_time();
#endif
    // this boi clears the interrupt flag of the captouch chip so it must
    // run _every time_ we receive an interrupt. &st tells us which stages
    // have been completed since the last call.
    if (!ad7147_hw_get_and_clear_completed(device, &st)) {
        return false;
    }
    // since we can only reset the chip sequencer to stage 0, for the 13th
    // stage the hardware interrupt should trigger when state 0 is completed.
    // this is okay for all steps of the prodecure, so to keep i2c traffic low
    // we have it hardcoded to that at all times.
    if (!(st & 1)) {
#ifdef CAPTOUCH_PROFILING
        // if u trigger this it's not bad, it just means that u generate more
        // i2c traffic than absolutely necessary. remove bofh
        // xTaskNotifyStateClear below for a demonstrations. with stock config
        // this rarely triggers on step 1. don't really care to look into it.
        ESP_LOGE(TAG, "cursed chip isr clear fail (step %u, mask %u\n)",
                 (uint16_t)(*step), st);
#endif
        return false;
    }
    // let's pretend for fun that channel0 is read by stage0 and so forth.
    // makes describing this a lot easier.
    // also i2c traffic functions are highly golfed, pls don't tear them apart
    // it saves like 1% cpu so be cool~
    switch (*step) {
        case 0:
            // read all 12 "regular" channels into the array
            if (!ad7147_hw_get_cdc_data(device, data, 12)) {
                return false;
            }
            // reconfigures stage0 to channel 13 config, set up sequencer
            // to loop only stage0 (<-actually a lie but dw abt it~)
            if (!ad7147_hw_modulate_stage0_and_reset(device,
                                                     &_cursed_swap_stage)) {
                return false;
            }
            // clear stray freertos interrupts, then clear hw interrupts.
            // must be done in that order.
            xTaskNotifyStateClear(NULL);
            if (!ad7147_hw_get_and_clear_completed(device, &st)) {
                return false;
            }
            break;
        // case 1: the data right after reconfiguration might be junk
        //         so we wait for another cycle.
        case 2:
            // grab data for channel 13
            if (!ad7147_hw_get_cdc_data(device, &(data[12]), 1)) {
                return false;
            }
            // reconfigure stage0 to channel 0 config, set up sequencer
            // to loop all stages
            if (!ad7147_hw_modulate_stage0_and_reset(device, NULL)) {
                return false;
            }
            // clear stray freertos interrupts, then clear hw interrupts.
            // must be done in that order.
            xTaskNotifyStateClear(NULL);
            if (!ad7147_hw_get_and_clear_completed(device, &st)) {
                return false;
            }
            // processing data here.
            xSemaphoreTake(raw_petal_bot_chip_lock, portMAX_DELAY);
            raw_data_to_petal_pads(chip, data, 13);
            xSemaphoreGive(raw_petal_bot_chip_lock);
            // notify the main captouch task that data is ready
            _notify(1, _captouch_task_handle);
            break;
            // case 3: "whoa whoa whoa if you do the same here as with case 1
            //         you'd wait for the whole 12-sequence without any good
            //         reason!"
            // observant, but there's a hidden trick! both case2->case3 and
            // case 3->case0 have the sequencer configure to 12 steps but
            // consider: case 2 resets to stage0 (only stage we can reset to,
            // remember?), and the next interrupt is triggered once that is
            // complete! that is the magic of ISR trigger reconf laziness!
    }
#ifdef CAPTOUCH_PROFILING
    _cursed_step_to_step_time[*step] = time - _cursed_step_time;
    _cursed_step_time = esp_timer_get_time();
    _cursed_step_execution_time[*step] = _cursed_step_time - time;
#endif
    *step = ((*step) + 1) % 4;
    return true;
}

// wrapper/data storage for the above.
static void _cursed_task(void *data) {
    uint8_t step = 0;
    uint16_t buffer[13];
    for (;;) {
        uint32_t notif;  // ignoring this
        if (xTaskNotifyWait(0, 3, &notif, portMAX_DELAY) == pdFALSE) {
            ESP_LOGE(TAG, "Notification receive failed: cursed task");
            continue;
        }
        _cursed_chip_process(&_bot, &step, buffer);
    }
}

static void _task(void *data) {
    (void)data;

#ifdef CAPTOUCH_PROFILING
    int64_t top_timer[100];
    uint8_t top_timer_index = 0;
    int64_t bot_timer[100];
    uint8_t bot_timer_index = 0;
#endif
    for (;;) {
#if defined(CONFIG_FLOW3R_HW_GEN_P4)
        bool top = true, bot = true;
        vTaskDelay(10 / portTICK_PERIOD_MS);
#else
        uint32_t notif;
        if (xTaskNotifyWait(0, 3, &notif, portMAX_DELAY) == pdFALSE) {
            ESP_LOGE(TAG, "Notification receive failed");
            continue;
        }
        notif = notif & 3;
        if (!notif) continue;
        bool bot = notif & 1;
        bool top = notif & 2;

        if (_interrupt_shared) {
            // No way to know which captouch chip triggered the interrupt, so
            // process both.
            top = true;
            bot = true;
        }
#endif
        if (top) {
            uint8_t top_chip_petals[] = { 0, 4, 6, 8 };
            // _chip_process grabs data from i2c and writes it to
            // the respective raw petal pad
            if (_chip_process(&_top)) {
                xSemaphoreTake(captouch_output_lock, portMAX_DELAY);
                // this one processes the raw data to user-facing
                // parameters (mostly "pressed" and "position")
                for (uint8_t i = 0; i < 4; i++) {
                    petal_process(top_chip_petals[i]);
                }
                xSemaphoreGive(captouch_output_lock);
            }
#ifdef CAPTOUCH_PROFILING
            if (top_timer_index < 100) {
                top_timer[top_timer_index] = esp_timer_get_time();
                top_timer_index++;
            } else {
                int32_t avg = top_timer[99] - top_timer[3];
                avg /= 1000 * (99 - 3);
                printf("average top captouch cycle time: %ldms\n", avg);
                top_timer_index = 0;
            }
#endif
        }
        if (bot) {
            uint8_t bot_chip_petals[] = { 1, 2, 3, 5, 7, 9 };
            // same as top, but _chip_process has been done already by
            // the helper task - we do need to grab an extra lock tho
            xSemaphoreTake(captouch_output_lock, portMAX_DELAY);
            // grab this one l8r bc higher prio
            xSemaphoreTake(raw_petal_bot_chip_lock, portMAX_DELAY);
            for (uint8_t i = 0; i < 6; i++) {
                petal_process(bot_chip_petals[i]);
            }
            xSemaphoreGive(raw_petal_bot_chip_lock);
            xSemaphoreGive(captouch_output_lock);
#ifdef CAPTOUCH_PROFILING
            if (bot_timer_index < 100) {
                bot_timer[bot_timer_index] = esp_timer_get_time();
                bot_timer_index++;
            } else {
                int32_t avg = bot_timer[99] - bot_timer[3];
                avg /= 1000 * (99 - 3);
                printf("average bot captouch cycle time: %ldms\n", avg);
                bot_timer_index = 0;
                for (uint16_t i = 0; i < 4; i++) {
                    uint16_t k = (i + 3) % 4;
                    printf("last bot step %u to step %u time: %luus\n", k, i,
                           _cursed_step_to_step_time[i]);
                }
                for (uint16_t i = 0; i < 4; i++) {
                    printf("last bot step %u execution time: %luus\n", i,
                           _cursed_step_execution_time[i]);
                }
            }
#endif
        }
    }
}

esp_err_t _gpio_interrupt_setup(gpio_num_t num, gpio_isr_t isr) {
    esp_err_t ret;

    gpio_config_t io_conf = {
        .intr_type = GPIO_INTR_NEGEDGE,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = true,
        .pin_bit_mask = (1 << num),
    };
    if ((ret = gpio_config(&io_conf)) != ESP_OK) {
        return ret;
    }
    if ((ret = gpio_isr_handler_add(num, isr, NULL)) != ESP_OK) {
        return ret;
    }
    return ESP_OK;
}

esp_err_t flow3r_bsp_ad7147_init() {
    assert(captouch_output_lock == NULL);
    captouch_output_lock = xSemaphoreCreateMutex();
    assert(captouch_output_lock != NULL);
    assert(raw_petal_bot_chip_lock == NULL);
    raw_petal_bot_chip_lock = xSemaphoreCreateMutex();
    assert(raw_petal_bot_chip_lock != NULL);

    esp_err_t ret;

    for (uint8_t i = 0; i < 10; i++) {
        captouch_data.petals[i].index = i;
    }

    _top.dev.dev_config.decimation = 0b01;
    _top.dev.addr = flow3r_i2c_addresses.touch_top;
    _bot.dev.dev_config.decimation = 0b10;
    _bot.dev.addr = flow3r_i2c_addresses.touch_bottom;

    if ((ret = flow3r_bsp_ad7147_chip_init(&_top)) != ESP_OK) {
        return ret;
    }
    if ((ret = flow3r_bsp_ad7147_chip_init(&_bot)) != ESP_OK) {
        return ret;
    }
    ESP_LOGI(TAG, "Captouch initialized");

    xTaskCreate(&_task, "captouch", 4096, NULL, configMAX_PRIORITIES - 2,
                &_captouch_task_handle);
    xTaskCreate(&_cursed_task, "ad7147", 4096, NULL, configMAX_PRIORITIES - 1,
                &_cursed_task_handle);

    if ((ret = gpio_install_isr_service(ESP_INTR_FLAG_SHARED |
                                        ESP_INTR_FLAG_LOWMED)) != ESP_OK) {
        ESP_LOGE(TAG, "Failed to install GPIO ISR service");
        return ret;
    }
    if ((ret = _gpio_interrupt_setup(_interrupt_gpio_bot, _bot_isr)) !=
        ESP_OK) {
        ESP_LOGE(TAG, "Failed to add bottom captouch ISR");
        return ret;
    }
    if (!_interrupt_shared) {
        // On badges with shared interrupts, only install the 'bot' ISR as a
        // shared ISR.
        if ((ret = _gpio_interrupt_setup(_interrupt_gpio_top, _top_isr)) !=
            ESP_OK) {
            ESP_LOGE(TAG, "Failed to add top captouch ISR");
            return ret;
        }
    }

    _kickstart();
    return ESP_OK;
}

void flow3r_bsp_ad7147_calibrate() {
    _bot.calibration_pending = true;
    _top.calibration_pending = true;
}

bool flow3r_bsp_ad7147_calibrating() {
    bool bot = _bot.calibration_pending || _bot.calibration_active;
    bool top = _top.calibration_pending || _top.calibration_active;
    return bot || top;
}

void flow3r_bsp_ad7147_get_calibration_data(int32_t *data) {
    while (flow3r_bsp_captouch_calibrating()) {
    };
    for (uint8_t i = 0; i < 13; i++) {
        if (i < 12) {
            data[2 * i] = _top.channels[i].afe_offset;
            data[2 * i + 1] = _top.channels[i].amb;
        }
        data[2 * i + 24] = _bot.channels[i].afe_offset;
        data[2 * i + 25] = _bot.channels[i].amb;
    }
}

static uint16_t amb_limit(int32_t data) {
    return data > 65535 ? 65535 : (data < 0 ? 0 : data);
}

static uint8_t afe_limit(int32_t data) {
    return data > 126 ? 126 : (data < 0 ? 0 : data);
}

void flow3r_bsp_ad7147_set_calibration_data(int32_t *data) {
    while (flow3r_bsp_captouch_calibrating()) {
    };
    for (uint8_t i = 0; i < 13; i++) {
        if (i < 12) {
            _top.channels[i].afe_offset = afe_limit(data[2 * i]);
            _top.channels[i].amb = amb_limit(data[2 * i + 1]);
        }
        _bot.channels[i].afe_offset = afe_limit(data[2 * i + 24]);
        _bot.channels[i].amb = amb_limit(data[2 * i + 25]);
    }
    _top.calibration_external = true;
    _bot.calibration_external = true;
}

void flow3r_bsp_ad7147_get(flow3r_bsp_captouch_data_t *dest) {
    xSemaphoreTake(captouch_output_lock, portMAX_DELAY);
    memcpy(dest, &captouch_data, sizeof(captouch_data));
    xSemaphoreGive(captouch_output_lock);
}

void flow3r_bsp_ad7147_refresh_events() {
    xSemaphoreTake(captouch_output_lock, portMAX_DELAY);
    for (uint8_t i = 0; i < 10; i++) {
        captouch_data.petals[i].press_event = latches[i].press_event_new;
        latches[i].fresh = true;
    }
    xSemaphoreGive(captouch_output_lock);
}

// roughly matches the behavior of the legacy api. someday we should have more
// meaningful output units.

#define TOP_PETAL_THRESHOLD 8000
#define BOTTOM_PETAL_THRESHOLD 12000
#define PETAL_HYSTERESIS 1000

#define POS_AMPLITUDE 40000
#define POS_AMPLITUDE_SHIFT 2
#define POS_DIV_MIN 1000

static inline void petal_process(uint8_t index) {
    flow3r_bsp_captouch_petal_data_t *petal = &(captouch_data.petals[index]);
    int32_t tip = raw_petals[index][petal_pad_tip];
    int32_t cw = raw_petals[index][petal_pad_cw];
    int32_t ccw = raw_petals[index][petal_pad_ccw];
    int32_t base = raw_petals[index][petal_pad_base];
    bool top = (index % 2) == 0;
    int32_t thres = top ? (TOP_PETAL_THRESHOLD) : (BOTTOM_PETAL_THRESHOLD);
    bool pressed_prev = petal->pressed[petal->last_ring];
    thres = pressed_prev ? thres - (PETAL_HYSTERESIS) : thres;
    int32_t rad;
    int32_t phi;
    int32_t raw_sum;
    int8_t div;
    if (top) {
        raw_sum = base + ccw + cw;
        div = 3;
        tip = (ccw + cw) >> 1;
        phi = cw - ccw;
        phi *= (POS_AMPLITUDE) >> (POS_AMPLITUDE_SHIFT);
        phi /= ((cw + ccw) >> (POS_AMPLITUDE_SHIFT)) + (POS_DIV_MIN);
    } else {
        base += ((base * 3) >> 2);  // tiny gain correction
        raw_sum = base + tip;
        div = 2;
        phi = 0;
    }
    rad = tip - base;
    rad *= (POS_AMPLITUDE) >> (POS_AMPLITUDE_SHIFT);
    rad /= ((tip + base) >> (POS_AMPLITUDE_SHIFT)) + (POS_DIV_MIN);
#if defined(CONFIG_FLOW3R_HW_GEN_P3)
    if (top) rad = -rad;
#endif
    bool pressed = raw_sum > thres;
    if (pressed) {  // backwards compat hack for the few ppl who use
        petal->raw_coverage = raw_sum / div;  // it as a "pressed" proxy
    } else {                                  // by comparing it to
        petal->raw_coverage = 0;              // 0
    }                                         // TODO: undo

    if ((!latches[index].press_event_new) || latches[index].fresh) {
        latches[index].press_event_new = pressed;
        latches[index].fresh = false;
    }
    // value range fine tuning
    if (index == 2) {
        rad = (rad * 19) >> 4;
        phi = (phi * 19) >> 4;
    } else if (top) {
        rad = (rad * 15) >> 4;
        phi = (phi * 15) >> 4;
    } else {
        rad = (rad * 42) >> 5;
    }
    rad = rad > 32767 ? 32767 : (rad < -32768 ? -32768 : rad);
    phi = phi > 32767 ? 32767 : (phi < -32768 ? -32768 : phi);
    petal->last_ring = (petal->last_ring + 1) % (CAPTOUCH_POS_RING_LEN);
    petal->pressed[petal->last_ring] = pressed;
    petal->rad_ring[petal->last_ring] = rad;
    petal->phi_ring[petal->last_ring] = phi;
}
