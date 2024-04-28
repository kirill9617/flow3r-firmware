#include "py/builtin.h"
#include "py/runtime.h"

#include "flow3r_bsp_captouch.h"

#include <math.h>
#include <string.h>

STATIC mp_obj_t mp_captouch_calibration_active(void) {
    return mp_obj_new_int(flow3r_bsp_captouch_calibrating());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_captouch_calibration_active_obj,
                                 mp_captouch_calibration_active);

STATIC mp_obj_t mp_captouch_calibration_request(void) {
    flow3r_bsp_captouch_calibration_request();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_captouch_calibration_request_obj,
                                 mp_captouch_calibration_request);

typedef struct {
    mp_obj_base_t base;
    mp_obj_t captouch;
    size_t ix;
} mp_captouch_petal_state_t;

const mp_obj_type_t captouch_petal_state_type;

typedef struct {
    mp_obj_base_t base;
    mp_obj_t petals;
    flow3r_bsp_captouch_data_t underlying;
} mp_captouch_state_t;

const mp_obj_type_t captouch_state_type;

STATIC mp_obj_t mp_captouch_petal_get_pos_raw(mp_obj_t self_in, bool get_rad) {
    mp_captouch_petal_state_t *self = MP_OBJ_TO_PTR(self_in);
    mp_captouch_state_t *captouch = MP_OBJ_TO_PTR(self->captouch);
    flow3r_bsp_captouch_petal_data_t *state =
        &captouch->underlying.petals[self->ix];
    float ret[CAPTOUCH_POS_RING_LEN];
    if (get_rad) {
        flow3r_bsp_captouch_get_rad_raw(state, ret);
    } else {
        flow3r_bsp_captouch_get_phi_raw(state, ret);
    }
    mp_obj_t items[CAPTOUCH_POS_RING_LEN];
    for (uint8_t i = 0; i < CAPTOUCH_POS_RING_LEN; i++) {
        if (isnan(ret[i])) {
            items[i] = mp_const_none;
        } else {
            items[i] = mp_obj_new_float(ret[i]);
        }
    }
    return mp_obj_new_tuple(CAPTOUCH_POS_RING_LEN, items);
}

STATIC mp_obj_t mp_captouch_petal_get_rad_raw(mp_obj_t self_in) {
    return mp_captouch_petal_get_pos_raw(self_in, true);
}
MP_DEFINE_CONST_FUN_OBJ_1(mp_captouch_petal_get_rad_raw_obj,
                          mp_captouch_petal_get_rad_raw);

STATIC mp_obj_t mp_captouch_petal_get_phi_raw(mp_obj_t self_in) {
    return mp_captouch_petal_get_pos_raw(self_in, false);
}
MP_DEFINE_CONST_FUN_OBJ_1(mp_captouch_petal_get_phi_raw_obj,
                          mp_captouch_petal_get_phi_raw);

STATIC mp_obj_t mp_captouch_petal_get_pos(size_t n_args,
                                          const mp_obj_t *pos_args,
                                          mp_map_t *kw_args, bool get_rad) {
    mp_captouch_petal_state_t *self = MP_OBJ_TO_PTR(pos_args[0]);
    if ((!get_rad) && (self->ix % 2)) return mp_const_none;

    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_smooth, MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 2 } },
        { MP_QSTR_drop_first, MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 0 } },
        { MP_QSTR_drop_last, MP_ARG_KW_ONLY | MP_ARG_INT, { .u_int = 0 } },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args - 1, pos_args + 1, kw_args,
                     MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    uint16_t smooth = args[0].u_int;
    uint16_t drop_first = args[1].u_int;
    uint16_t drop_last = args[2].u_int;

    mp_captouch_state_t *captouch = MP_OBJ_TO_PTR(self->captouch);
    flow3r_bsp_captouch_petal_data_t *state =
        &captouch->underlying.petals[self->ix];
    float ret;
    if (get_rad) {
        ret = flow3r_bsp_captouch_get_rad(state, smooth, drop_first, drop_last);
    } else {
        ret = flow3r_bsp_captouch_get_phi(state, smooth, drop_first, drop_last);
    }
    if (isnan(ret)) return mp_const_none;
    return mp_obj_new_float(ret);
}

STATIC mp_obj_t mp_captouch_petal_get_rad(size_t n_args,
                                          const mp_obj_t *pos_args,
                                          mp_map_t *kw_args) {
    return mp_captouch_petal_get_pos(n_args, pos_args, kw_args, true);
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_captouch_petal_get_rad_obj, 1,
                           mp_captouch_petal_get_rad);

STATIC mp_obj_t mp_captouch_petal_get_phi(size_t n_args,
                                          const mp_obj_t *pos_args,
                                          mp_map_t *kw_args) {
    return mp_captouch_petal_get_pos(n_args, pos_args, kw_args, false);
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_captouch_petal_get_phi_obj, 1,
                           mp_captouch_petal_get_phi);

STATIC const mp_rom_map_elem_t mp_captouch_petal_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get_rad),
      MP_ROM_PTR(&mp_captouch_petal_get_rad_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_phi),
      MP_ROM_PTR(&mp_captouch_petal_get_phi_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_rad_raw),
      MP_ROM_PTR(&mp_captouch_petal_get_rad_raw_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_phi_raw),
      MP_ROM_PTR(&mp_captouch_petal_get_phi_raw_obj) },
};

STATIC MP_DEFINE_CONST_DICT(mp_captouch_petal_state_locals_dict,
                            mp_captouch_petal_locals_dict_table);

STATIC void mp_captouch_petal_state_attr(mp_obj_t self_in, qstr attr,
                                         mp_obj_t *dest) {
    mp_captouch_petal_state_t *self = MP_OBJ_TO_PTR(self_in);
    if (dest[0] != MP_OBJ_NULL) {
        return;
    }

    mp_captouch_state_t *captouch = MP_OBJ_TO_PTR(self->captouch);
    flow3r_bsp_captouch_petal_data_t *state =
        &captouch->underlying.petals[self->ix];

    bool top = (self->ix % 2) == 0;

    switch (attr) {
        case MP_QSTR_top:
            dest[0] = mp_obj_new_bool(top);
            break;
        case MP_QSTR_bottom:
            dest[0] = mp_obj_new_bool(!top);
            break;
        case MP_QSTR_pressed:
            dest[0] = mp_obj_new_bool(state->press_event);
            break;
        case MP_QSTR_pressure:
            dest[0] = mp_obj_new_int(state->raw_coverage);
            break;
        case MP_QSTR_position: {
            // legacy
            float ret[2];
            ret[0] = flow3r_bsp_captouch_get_rad(state, 1, 0, 0);
            ret[1] = flow3r_bsp_captouch_get_phi(state, 1, 0, 0);
            if (isnan(ret[0]) || isnan(ret[1])) {
                mp_obj_t items[2] = { mp_obj_new_int(0), mp_obj_new_int(0) };
                dest[0] = mp_obj_new_tuple(2, items);
            } else if (top) {
                mp_obj_t items[2] = {
                    mp_obj_new_int((int32_t)(35000 * ret[0])),
                    mp_obj_new_int((int32_t)(35000 * ret[1])),
                };
                dest[0] = mp_obj_new_tuple(2, items);
            } else {
                mp_obj_t items[2] = {
                    mp_obj_new_int((int32_t)(25000 * ret[0] + 5000)),
                    mp_obj_new_int(0),
                };
                dest[0] = mp_obj_new_tuple(2, items);
            }
            break;
            default:
                dest[1] = MP_OBJ_SENTINEL;
        }
    }
}

STATIC void mp_captouch_state_attr(mp_obj_t self_in, qstr attr,
                                   mp_obj_t *dest) {
    mp_captouch_state_t *self = MP_OBJ_TO_PTR(self_in);
    if (dest[0] != MP_OBJ_NULL) {
        return;
    }

    switch (attr) {
        case MP_QSTR_petals:
            dest[0] = self->petals;
            break;
    }
}

MP_DEFINE_CONST_OBJ_TYPE(captouch_petal_state_type, MP_QSTR_CaptouchPetalState,
                         MP_TYPE_FLAG_NONE, attr, mp_captouch_petal_state_attr,
                         locals_dict, &mp_captouch_petal_state_locals_dict);

MP_DEFINE_CONST_OBJ_TYPE(captouch_state_type, MP_QSTR_CaptouchState,
                         MP_TYPE_FLAG_NONE, attr, mp_captouch_state_attr);

STATIC mp_obj_t
mp_captouch_state_new(const flow3r_bsp_captouch_data_t *underlying) {
    mp_captouch_state_t *captouch = m_new_obj(mp_captouch_state_t);
    captouch->base.type = &captouch_state_type;
    memcpy(&captouch->underlying, underlying,
           sizeof(flow3r_bsp_captouch_data_t));

    captouch->petals = mp_obj_new_list(0, NULL);
    for (int i = 0; i < 10; i++) {
        mp_captouch_petal_state_t *petal = m_new_obj(mp_captouch_petal_state_t);
        petal->base.type = &captouch_petal_state_type;
        petal->captouch = MP_OBJ_FROM_PTR(captouch);
        petal->ix = i;

        mp_obj_list_append(captouch->petals, MP_OBJ_FROM_PTR(petal));
    }

    return MP_OBJ_FROM_PTR(captouch);
}

STATIC mp_obj_t mp_captouch_read(void) {
    flow3r_bsp_captouch_data_t dat;
    flow3r_bsp_captouch_get(&dat);
    return mp_captouch_state_new(&dat);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_captouch_read_obj, mp_captouch_read);

STATIC mp_obj_t mp_captouch_refresh_events(void) {
    flow3r_bsp_captouch_refresh_events();
    return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_captouch_refresh_events_obj,
                                 mp_captouch_refresh_events);

STATIC mp_obj_t mp_captouch_calibration_get_data(void) {
    int32_t data[50];
    flow3r_bsp_captouch_get_calibration_data(data);
    mp_obj_t items[50];
    for (uint8_t i = 0; i < 50; i++) {
        items[i] = mp_obj_new_int(data[i]);
    }
    return mp_obj_new_tuple(50, items);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_0(mp_captouch_calibration_get_data_obj,
                                 mp_captouch_calibration_get_data);

STATIC mp_obj_t mp_captouch_calibration_set_data(mp_obj_t mp_data) {
    int32_t data[50];
    mp_obj_iter_buf_t iter_buf;
    mp_obj_t iterable = mp_getiter(mp_data, &iter_buf);
    mp_obj_t item;
    uint8_t i = 0;
    while ((item = mp_iternext(iterable)) != MP_OBJ_STOP_ITERATION) {
        data[i] = mp_obj_get_int(item);
        i++;
        if (i == 50) break;
    }
    // if(i != 50) TODO: Throw error? Maybe?
    flow3r_bsp_captouch_set_calibration_data(data);
    return mp_const_none;
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mp_captouch_calibration_set_data_obj,
                                 mp_captouch_calibration_set_data);

STATIC const mp_rom_map_elem_t globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mp_captouch_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_refresh_events),
      MP_ROM_PTR(&mp_captouch_refresh_events_obj) },
    { MP_ROM_QSTR(MP_QSTR_calibration_active),
      MP_ROM_PTR(&mp_captouch_calibration_active_obj) },
    { MP_ROM_QSTR(MP_QSTR_calibration_request),
      MP_ROM_PTR(&mp_captouch_calibration_request_obj) },
    { MP_ROM_QSTR(MP_QSTR_calibration_get_data),
      MP_ROM_PTR(&mp_captouch_calibration_get_data_obj) },
    { MP_ROM_QSTR(MP_QSTR_calibration_set_data),
      MP_ROM_PTR(&mp_captouch_calibration_set_data_obj) },
};

STATIC MP_DEFINE_CONST_DICT(globals, globals_table);

const mp_obj_module_t mp_module_captouch_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&globals,
};

MP_REGISTER_MODULE(MP_QSTR_captouch, mp_module_captouch_user_cmodule);
