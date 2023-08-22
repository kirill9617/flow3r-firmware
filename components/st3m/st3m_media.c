#include "st3m_media.h"
#include "st3m_audio.h"

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"

#ifdef CONFIG_FLOW3R_CTX_FLAVOUR_FULL
static st3m_media *audio_media = NULL;

static int16_t *audio_buffer = NULL;

void st3m_media_audio_render(int16_t *rx, int16_t *tx, uint16_t len) {
    if (!audio_media) return;
    for (int i = 0; i < len; i++) {
        if ((audio_media->audio_r + 1 != audio_media->audio_w) &&
            (audio_media->audio_r + 1 - AUDIO_BUF_SIZE !=
             audio_media->audio_w)) {
            tx[i] = audio_media->audio_buffer[audio_media->audio_r++];
            if (audio_media->audio_r >= AUDIO_BUF_SIZE)
                audio_media->audio_r = 0;
        } else
            tx[i] = 0;
    }
}
int st3m_media_samples_queued(void) {
    if (!audio_media) return 0;
    if (audio_media->audio_r > audio_media->audio_w)
        return (AUDIO_BUF_SIZE - audio_media->audio_r) + audio_media->audio_w;
    return audio_media->audio_w - audio_media->audio_r;
}

// XXX : it would be better to be able to push and pop the
//       st3m_audio_player_function
void bl00mbox_audio_render(int16_t *rx, int16_t *tx, uint16_t len);

void st3m_media_stop(void) {
    if (audio_media && audio_media->destroy) audio_media->destroy(audio_media);
    audio_media = 0;
    st3m_audio_set_player_function(bl00mbox_audio_render);
    if (audio_buffer) {
        free(audio_buffer);
        audio_buffer = NULL;
    }
}

void st3m_media_pause(void) {
    if (!audio_media) return;
    audio_media->paused = 1;
}

void st3m_media_play(void) {
    if (!audio_media) return;
    audio_media->paused = 0;
}

int st3m_media_is_playing(void) {
    if (!audio_media) return 0;
    return !audio_media->paused;
}

float st3m_media_get_duration(void) {
    if (!audio_media) return 0;
    return audio_media->duration;
}

float st3m_media_get_position(void) {
    if (!audio_media) return 0;
    return audio_media->position;
}

float st3m_media_get_time(void) {
    if (!audio_media) return 0;
    return audio_media->time;
}

void st3m_media_seek(float position) {
    if (!audio_media) return;
    audio_media->seek = position;
}

void st3m_media_seek_relative(float time) {
    if (!audio_media) return;
    st3m_media_seek((audio_media->position * audio_media->duration) + time);
}

void st3m_media_draw(Ctx *ctx) {
    if (audio_media && audio_media->draw) audio_media->draw(audio_media, ctx);
}

void st3m_media_think(float ms) {
    if (audio_media && audio_media->think) audio_media->think(audio_media, ms);
}

char *st3m_media_get_string(const char *key) {
    if (!audio_media) return NULL;
    if (!audio_media->get_string) return NULL;
    return audio_media->get_string(audio_media, key);
}

float st3m_media_get(const char *key) {
    if (!audio_media || !audio_media->get_string) return -1.0f;
    return audio_media->get(audio_media, key);
}

void st3m_media_set(const char *key, float value) {
    if (!audio_media || !audio_media->set) return;
    return audio_media->set(audio_media, key, value);
}

st3m_media *st3m_media_load_mpg1(const char *path);
st3m_media *st3m_media_load_mod(const char *path);
st3m_media *st3m_media_load_mp3(const char *path);
st3m_media *st3m_media_load_txt(const char *path);
st3m_media *st3m_media_load_bin(const char *path);

static int file_get_contents(const char *path, uint8_t **contents,
                             size_t *length) {
    FILE *file;
    long size;
    long remaining;
    uint8_t *buffer;
    file = fopen(path, "rb");
    if (!file) {
        return -1;
    }
    fseek(file, 0, SEEK_END);
    size = remaining = ftell(file);

    if (length) {
        *length = size;
    }
    rewind(file);
    buffer = malloc(size + 2);
    if (!buffer) {
        fclose(file);
        return -1;
    }
    remaining -= fread(buffer, 1, remaining, file);
    if (remaining) {
        fclose(file);
        free(buffer);
        return -1;
    }
    fclose(file);
    *contents = (unsigned char *)buffer;
    buffer[size] = 0;
    return 0;
}

int st3m_media_load(const char *path) {
    struct stat statbuf;
#if 1
    if (!strncmp(path, "http://", 7)) {
        st3m_media_stop();
        audio_media = st3m_media_load_mp3(path);
    } else if (stat(path, &statbuf)) {
        st3m_media_stop();
        audio_media = st3m_media_load_txt(path);
    } else if (strstr(path, ".mp3") == strrchr(path, '.')) {
        st3m_media_stop();
        audio_media = st3m_media_load_mp3(path);
    } else
#endif
#if 1
        if (strstr(path, ".mpg")) {
        st3m_media_stop();
        audio_media = st3m_media_load_mpg1(path);
    } else
#endif
#if 1
        if ((strstr(path, ".mod") == strrchr(path, '.'))) {
        st3m_media_stop();
        audio_media = st3m_media_load_mod(path);
    } else
#endif
        if ((strstr(path, ".json") == strrchr(path, '.')) ||
            (strstr(path, ".txt") == strrchr(path, '.')) ||
            (strstr(path, "/README") == strrchr(path, '/')) ||
            (strstr(path, ".toml") == strrchr(path, '.')) ||
            (strstr(path, ".py") == strrchr(path, '.'))) {
        st3m_media_stop();
        audio_media = st3m_media_load_txt(path);
    }

    if (!audio_media) {
        st3m_media_stop();
        audio_media = st3m_media_load_txt(path);
    }

    if (!audio_buffer)
        audio_buffer = heap_caps_malloc(AUDIO_BUF_SIZE * 2, MALLOC_CAP_DMA);
    st3m_audio_set_player_function(st3m_media_audio_render);
    audio_media->audio_buffer = audio_buffer;
    audio_media->audio_r = 0;
    audio_media->audio_w = 1;

    return 1;
}

typedef struct {
    st3m_media control;
    char *data;
    size_t size;
    float scroll_pos;
    char *path;
} txt_state;

static void txt_destroy(st3m_media *media) {
    txt_state *self = (void *)media;
    if (self->data) free(self->data);
    if (self->path) free(self->path);
    free(self);
}

static void txt_draw(st3m_media *media, Ctx *ctx) {
    txt_state *self = (void *)media;
    ctx_rectangle(ctx, -120, -120, 240, 240);
    ctx_gray(ctx, 0);
    ctx_fill(ctx);
    ctx_gray(ctx, 1.0);
    ctx_move_to(ctx, -85, -70);
    ctx_font(ctx, "mono");
    ctx_font_size(ctx, 13.0);
    // ctx_text (ctx, self->path);
    ctx_text(ctx, self->data);
}

static void txt_think(st3m_media *media, float ms_elapsed) {
    // txt_state *self = (void*)media;
}

st3m_media *st3m_media_load_txt(const char *path) {
    txt_state *self = (txt_state *)malloc(sizeof(txt_state));
    memset(self, 0, sizeof(txt_state));
    self->control.draw = txt_draw;
    self->control.think = txt_think;
    self->control.destroy = txt_destroy;
    file_get_contents(path, (void *)&self->data, &self->size);
    if (!self->data) {
        self->data = malloc(strlen(path) + 64);
        sprintf(self->data, "40x - %s", path);
        self->size = strlen((char *)self->data);
    }
    self->path = strdup(path);
    return (void *)self;
}

st3m_media *st3m_media_load_bin(const char *path) {
    txt_state *self = (txt_state *)malloc(sizeof(txt_state));
    memset(self, 0, sizeof(txt_state));
    self->control.draw = txt_draw;
    self->control.destroy = txt_destroy;
    file_get_contents(path, (void *)&self->data, &self->size);
    if (!self->data) {
        self->data = malloc(strlen(path) + 64);
        sprintf(self->data, "40x - %s", path);
        self->size = strlen(self->data);
    }
    self->path = strdup(path);
    return (void *)self;
}

#endif
