// probably doesn't need all of these idk
#include <stdio.h>
#include <string.h>

#include "extmod/virtpin.h"
#include "machine_rtc.h"
#include "modmachine.h"
#include "mphalport.h"
#include "py/builtin.h"
#include "py/mphal.h"
#include "py/runtime.h"

#include "flow3r_bsp.h"
#include "st3m_console.h"
#include "st3m_gfx.h"
#include "st3m_io.h"
#include "st3m_scope.h"
#include "st3m_usb.h"

// clang-format off
#include "ctx_config.h"
#include "ctx.h"
// clang-format on

mp_obj_t mp_ctx_from_ctx(Ctx *ctx);

STATIC mp_obj_t mp_display_set_backlight(mp_obj_t percent_in) {
    uint8_t percent = mp_obj_get_int(percent_in);
    flow3r_bsp_display_set_backlight(percent);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_display_set_backlight_obj,
                                 mp_display_set_backlight);

STATIC mp_obj_t mp_menu_button_set_left(mp_obj_t left) {
    st3m_io_menu_button_set_left(mp_obj_get_int(left));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_menu_button_set_left_obj,
                                 mp_menu_button_set_left);

STATIC mp_obj_t mp_menu_button_get_left() {
    return mp_obj_new_int(st3m_io_menu_button_get_left());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_menu_button_get_left_obj,
                                 mp_menu_button_get_left);

STATIC mp_obj_t mp_menu_button_get() {
    return mp_obj_new_int(st3m_io_menu_button_get());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_menu_button_get_obj, mp_menu_button_get);

STATIC mp_obj_t mp_application_button_get() {
    return mp_obj_new_int(st3m_io_application_button_get());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_application_button_get_obj,
                                 mp_application_button_get);

STATIC mp_obj_t mp_left_button_get() {
    return mp_obj_new_int(st3m_io_left_button_get());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_left_button_get_obj, mp_left_button_get);

STATIC mp_obj_t mp_right_button_get() {
    return mp_obj_new_int(st3m_io_right_button_get());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_right_button_get_obj, mp_right_button_get);

STATIC mp_obj_t mp_version(void) {
    mp_obj_t str =
        mp_obj_new_str(flow3r_bsp_hw_name, strlen(flow3r_bsp_hw_name));
    return str;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_version_obj, mp_version);

static st3m_ctx_desc_t *gfx_last_desc = NULL;

STATIC mp_obj_t mp_get_ctx(void) {
    if (gfx_last_desc == NULL) {
        gfx_last_desc = st3m_gfx_drawctx_free_get(0);
        if (gfx_last_desc == NULL) {
            return mp_const_none;
        }
    }
    mp_obj_t mp_ctx = mp_ctx_from_ctx(gfx_last_desc->ctx);
    return mp_ctx;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_get_ctx_obj, mp_get_ctx);

STATIC mp_obj_t mp_freertos_sleep(mp_obj_t ms_in) {
    uint32_t ms = mp_obj_get_int(ms_in);
    MP_THREAD_GIL_EXIT();
    vTaskDelay(ms / portTICK_PERIOD_MS);
    MP_THREAD_GIL_ENTER();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_freertos_sleep_obj, mp_freertos_sleep);

STATIC mp_obj_t mp_display_update(mp_obj_t in_ctx) {
    // TODO(q3k): check in_ctx? Or just drop from API?

    if (gfx_last_desc != NULL) {
        st3m_gfx_drawctx_pipe_put(gfx_last_desc);
        gfx_last_desc = NULL;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_display_update_obj, mp_display_update);

STATIC mp_obj_t mp_display_pipe_full(void) {
    if (st3m_gfx_drawctx_pipe_full()) {
        return mp_const_true;
    }
    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_display_pipe_full_obj,
                                 mp_display_pipe_full);

STATIC mp_obj_t mp_display_pipe_flush(void) {
    st3m_gfx_flush();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_display_pipe_flush_obj,
                                 mp_display_pipe_flush);

STATIC mp_obj_t mp_scope_draw(mp_obj_t ctx_in) {
    // TODO(q3k): check in_ctx? Or just drop from API?

    if (gfx_last_desc != NULL) {
        st3m_scope_draw(gfx_last_desc->ctx);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_scope_draw_obj, mp_scope_draw);

STATIC mp_obj_t mp_i2c_scan(void) {
    flow3r_bsp_i2c_scan_result_t scan;
    flow3r_bsp_i2c_scan(&scan);

    mp_obj_t res = mp_obj_new_list(0, NULL);
    for (int i = 0; i < 127; i++) {
        size_t ix = i / 32;
        size_t offs = i % 32;
        if (scan.res[ix] & (1 << offs)) {
            mp_obj_list_append(res, mp_obj_new_int_from_uint(i));
        }
    }
    return res;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_i2c_scan_obj, mp_i2c_scan);

STATIC mp_obj_t mp_usb_connected(void) {
    static int64_t last_check = 0;
    static bool value = false;
    int64_t now = esp_timer_get_time();

    if (last_check == 0) {
        last_check = now;
        value = st3m_usb_connected();
    }

    if ((now - last_check) > 10000) {
        value = st3m_usb_connected();
        last_check = now;
    }
    return mp_obj_new_bool(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_usb_connected_obj, mp_usb_connected);

STATIC mp_obj_t mp_usb_console_active(void) {
    static int64_t last_check = 0;
    static bool value = false;
    int64_t now = esp_timer_get_time();

    if (last_check == 0) {
        last_check = now;
        value = st3m_console_active();
    }

    if ((now - last_check) > 10000) {
        value = st3m_console_active();
        last_check = now;
    }
    return mp_obj_new_bool(value);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_usb_console_active_obj,
                                 mp_usb_console_active);

STATIC const mp_rom_map_elem_t mp_module_hardware_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_hardware) },

    { MP_ROM_QSTR(MP_QSTR_menu_button_get),
      MP_ROM_PTR(&mp_menu_button_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_application_button_get),
      MP_ROM_PTR(&mp_application_button_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_left_button_get),
      MP_ROM_PTR(&mp_left_button_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_right_button_get),
      MP_ROM_PTR(&mp_right_button_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_menu_button_set_left),
      MP_ROM_PTR(&mp_menu_button_set_left_obj) },
    { MP_ROM_QSTR(MP_QSTR_menu_button_get_left),
      MP_ROM_PTR(&mp_menu_button_get_left_obj) },

    { MP_ROM_QSTR(MP_QSTR_display_update), MP_ROM_PTR(&mp_display_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_freertos_sleep), MP_ROM_PTR(&mp_freertos_sleep_obj) },
    { MP_ROM_QSTR(MP_QSTR_display_pipe_full),
      MP_ROM_PTR(&mp_display_pipe_full_obj) },
    { MP_ROM_QSTR(MP_QSTR_display_pipe_flush),
      MP_ROM_PTR(&mp_display_pipe_flush_obj) },
    { MP_ROM_QSTR(MP_QSTR_display_set_backlight),
      MP_ROM_PTR(&mp_display_set_backlight_obj) },
    { MP_ROM_QSTR(MP_QSTR_version), MP_ROM_PTR(&mp_version_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_ctx), MP_ROM_PTR(&mp_get_ctx_obj) },
    { MP_ROM_QSTR(MP_QSTR_usb_connected), MP_ROM_PTR(&mp_usb_connected_obj) },
    { MP_ROM_QSTR(MP_QSTR_usb_console_active),
      MP_ROM_PTR(&mp_usb_console_active_obj) },
    { MP_ROM_QSTR(MP_QSTR_i2c_scan), MP_ROM_PTR(&mp_i2c_scan_obj) },

    { MP_ROM_QSTR(MP_QSTR_BUTTON_PRESSED_LEFT), MP_ROM_INT(st3m_tripos_left) },
    { MP_ROM_QSTR(MP_QSTR_BUTTON_PRESSED_RIGHT),
      MP_ROM_INT(st3m_tripos_right) },
    { MP_ROM_QSTR(MP_QSTR_BUTTON_PRESSED_DOWN), MP_ROM_INT(st3m_tripos_mid) },
    { MP_ROM_QSTR(MP_QSTR_BUTTON_NOT_PRESSED), MP_ROM_INT(st3m_tripos_none) },

    { MP_ROM_QSTR(MP_QSTR_scope_draw), MP_ROM_PTR(&mp_scope_draw_obj) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_hardware_globals,
                            mp_module_hardware_globals_table);

const mp_obj_module_t mp_module_hardware = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mp_module_hardware_globals,
};

MP_REGISTER_MODULE(MP_QSTR_hardware, mp_module_hardware);