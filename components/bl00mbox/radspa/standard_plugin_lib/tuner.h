#pragma once
#include "radspa.h"
#include "radspa_helpers.h"
#include <math.h>

typedef struct {
    // int32_t read_head_position;
    // int32_t write_head_position;
    // int32_t max_delay;
    int32_t first_run;
    unsigned int buffer_size;
    unsigned int buffer_count;
    double * data_buf;
    double * maxs;
    double * mins;
    int * distances;
} tuner_data_t;

extern radspa_descriptor_t tuner_desc;
radspa_t * tuner_create(uint32_t init_var);
void tuner_run(radspa_t * osc, uint16_t num_samples, uint32_t render_pass_id);


#define UNPITCHED 0.0
#define NONE      -1

#define SAMPLE_RATE 48000//44100.0
#define FLWT_LEVELS 6
#define DIFFS_LEVELS 3
#define MAX_FREQ 3000.0
#define THRESHOLD_RATIO 0.75

#define SILENCE_THRESHOLD 0.7

/* ring buffer operation macros */
#define RINGSIZE  3 //dimension of the ring buffer, a bigger buffer has more precision in returned values, but less reactive over short (duration) notes
                    // a smaller one gives more reactivity  but less accuracy, when operating in SPEED mode, the suggested size is 3, when in ACCURACY mode is 2
#define PRECISION 5 //precision in Hz

/* Algorithm operating mode parameter*/
#define ACCURACY  0
#define SPEED     1

//sample formats
#define S8  256/2*SILENCE_THRESHOLD
#define U8  256*SILENCE_THRESHOLD
#define S16 65536/2*SILENCE_THRESHOLD
#define U16 65536*SILENCE_THRESHOLD
#define S24 16777216/2*SILENCE_THRESHOLD
#define U24 16777216*SILENCE_THRESHOLD
#define S32 4294967296/2*SILENCE_THRESHOLD
#define U32 4294967296*SILENCE_THRESHOLD

struct pitch_tracker_params;

static inline int abs_val(double num){ return num >= 0. ? num : -num; }

#ifndef max
#define max(x, y) ((x) > (y)) ? x : y
#endif

#ifndef min
#define min(x, y) ((x) < (y)) ? x : y
#endif