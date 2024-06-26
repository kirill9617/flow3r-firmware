//SPDX-License-Identifier: CC0-1.0
#pragma once

#include <stdio.h>
#include <math.h>
#include <string.h>

#include "bl00mbox_plugin_registry.h"
#include "bl00mbox_audio.h"
#include <stdint.h>
#include "bl00mbox_audio.h"
#include "radspa_helpers.h"

uint16_t bl00mbox_channel_buds_num(uint8_t channel);
uint64_t bl00mbox_channel_get_bud_by_list_pos(uint8_t channel, uint32_t pos);
uint16_t bl00mbox_channel_conns_num(uint8_t channel);
uint16_t bl00mbox_channel_mixer_num(uint8_t channel);
uint64_t bl00mbox_channel_get_bud_by_mixer_list_pos(uint8_t channel, uint32_t pos);
uint32_t bl00mbox_channel_get_signal_by_mixer_list_pos(uint8_t channel, uint32_t pos);
bool bl00mbox_channel_clear(uint8_t channel);

bool bl00mbox_channel_connect_signal_to_output_mixer(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
bool bl00mbox_channel_connect_signal(uint8_t channel, uint32_t bud_rx_index, uint32_t bud_rx_signal_index,
                                               uint32_t bud_tx_index, uint32_t bud_tx_signal_index);
bool bl00mbox_channel_disconnect_signal_rx(uint8_t channel, uint32_t bud_rx_index, uint32_t bud_rx_signal_index);
bool bl00mbox_channel_disconnect_signal_tx(uint8_t channel, uint32_t bud_tx_index, uint32_t bud_tx_signal_index);
bool bl00mbox_channel_disconnect_signal(uint8_t channel, uint32_t bud_tx_index, uint32_t bud_tx_signal_index);
bool bl00mbox_channel_disconnect_signal_from_output_mixer(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);

bl00mbox_bud_t * bl00mbox_channel_new_bud(uint8_t channel, uint32_t id, uint32_t init_var);
bool bl00mbox_channel_delete_bud(uint8_t channel, uint32_t bud_index);
bool bl00mbox_channel_bud_exists(uint8_t channel, uint32_t bud_index);
char * bl00mbox_channel_bud_get_name(uint8_t channel, uint32_t bud_index);
char * bl00mbox_channel_bud_get_description(uint8_t channel, uint32_t bud_index);
uint32_t bl00mbox_channel_bud_get_plugin_id(uint8_t channel, uint32_t bud_index);
uint32_t bl00mbox_channel_bud_get_init_var(uint8_t channel, uint32_t bud_index);
uint16_t bl00mbox_channel_bud_get_num_signals(uint8_t channel, uint32_t bud_index);

char * bl00mbox_channel_bud_get_signal_name(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
int8_t bl00mbox_channel_bud_get_signal_name_multiplex(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
char * bl00mbox_channel_bud_get_signal_description(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
char * bl00mbox_channel_bud_get_signal_unit(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
bool bl00mbox_channel_bud_get_always_render(uint8_t channel, uint32_t bud_index);
bool bl00mbox_channel_bud_set_always_render(uint8_t channel, uint32_t bud_index, bool value);
bool bl00mbox_channel_bud_set_signal_value(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index, int16_t value);
int16_t bl00mbox_channel_bud_get_signal_value(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
uint32_t bl00mbox_channel_bud_get_signal_hints(uint8_t channel, uint32_t bud_index, uint32_t bud_signal_index);
uint16_t bl00mbox_channel_subscriber_num(uint8_t channel, uint64_t bud_index, uint16_t signal_index);
uint64_t bl00mbox_channel_get_bud_by_subscriber_list_pos(uint8_t channel, uint64_t bud_index,
                uint16_t signal_index, uint8_t pos);
int32_t bl00mbox_channel_get_signal_by_subscriber_list_pos(uint8_t channel, uint64_t bud_index,
                uint16_t signal_index, uint8_t pos);
uint64_t bl00mbox_channel_get_source_bud(uint8_t channel, uint64_t bud_index, uint16_t signal_index);
uint16_t bl00mbox_channel_get_source_signal(uint8_t channel, uint64_t bud_index, uint16_t signal_index);

bool bl00mbox_channel_bud_set_table_value(uint8_t channel, uint32_t bud_index, uint32_t table_index, int16_t value);
int16_t bl00mbox_channel_bud_get_table_value(uint8_t channel, uint32_t bud_index, uint32_t table_index);
uint32_t bl00mbox_channel_bud_get_table_len(uint8_t channel, uint32_t bud_index);
int16_t * bl00mbox_channel_bud_get_table_pointer(uint8_t channel, uint32_t bud_index);
