#pragma once
#include <radspa.h>
#include <radspa_helpers.h>

typedef struct {
    uint64_t write_head_pos_long;
    uint64_t read_head_pos_long;
    uint32_t write_head_pos;
    uint32_t read_head_pos;
    int16_t pitch_shift_prev;
    int16_t trigger_prev;
    int16_t rec_trigger_prev;
    int16_t volume;
    uint32_t pitch_shift_mult;
    bool rec_active;
    bool buffer_all_zeroes;
} sampler_data_t;

extern radspa_descriptor_t sampler_desc;
radspa_t * sampler_create(uint32_t init_var);
void sampler_run(radspa_t * osc, uint16_t num_samples, uint32_t render_pass_id);
