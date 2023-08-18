#pragma once

#include <stdbool.h>
#include <stdint.h>

void st3m_io_init(void);

// A 'tripos' button is what we're calling the shoulder buttons. As the name
// indicates, it has three positions: left, middle (a.k.a. down/press) and
// right.
typedef enum {
    // Not pressed.
    st3m_tripos_none = 0,
    // Pressed towards the left.
    st3m_tripos_left = -1,
    // Pressed down.
    st3m_tripos_mid = 2,
    // Pressed towards the right.
    st3m_tripos_right = 1,
} st3m_tripos;

/* Read the state of the left/right button.
 * This ignores user preference and should be used only with good reason.
 */
st3m_tripos st3m_io_left_button_get();
st3m_tripos st3m_io_right_button_get();

#define BADGE_LINK_PIN_MASK_LINE_IN_TIP 0b0001
#define BADGE_LINK_PIN_MASK_LINE_IN_RING 0b0010
#define BADGE_LINK_PIN_MASK_LINE_OUT_TIP 0b0100
#define BADGE_LINK_PIN_MASK_LINE_OUT_RING 0b1000
#define BADGE_LINK_PIN_MASK_LINE_IN \
    ((BADGE_LINK_PIN_MASK_LINE_IN_TIP) | (BADGE_LINK_PIN_MASK_LINE_IN_RING))
#define BADGE_LINK_PIN_MASK_LINE_OUT \
    ((BADGE_LINK_PIN_MASK_LINE_OUT_TIP) | (BADGE_LINK_PIN_MASK_LINE_OUT_RING))
#define BADGE_LINK_PIN_MASK_ALL \
    ((BADGE_LINK_PIN_MASK_LINE_IN) | (BADGE_LINK_PIN_MASK_LINE_OUT))

/* Gets active badge links ports. Mask with
 * BADGE_LINK_PIN_MASK_LINE_{IN/OUT}_{TIP/RING}. The corresponding GPIO indices
 * are listed in BADGE_LINK_PIN_INDEX_LINE_{OUT/IN}_{TIP/RING}.
 */
uint8_t st3m_io_badge_link_get_active(uint8_t pin_mask);

/* Disables badge link ports. Mask with
 * BADGE_LINK_PIN_MASK_LINE_{IN/OUT}_{TIP/RING}. The corresponding GPIO indices
 * are listed in BADGE_LINK_PIN_INDEX_LINE_{OUT/IN}_{TIP/RING}. Returns the
 * output of st3m_io_badge_link_get_active after execution.
 */
uint8_t st3m_io_badge_link_disable(uint8_t pin_mask);

/* Enables badge link ports. Mask with
 * BADGE_LINK_PIN_MASK_LINE_{IN/OUT}_{TIP/RING}. The corresponding GPIO indices
 * are listed in BADGE_LINK_PIN_INDEX_LINE_{OUT/IN}_{TIP/RING}_PIN. Returns the
 * output of st3m_io_badge_link_get_active after execution.
 *
 * Do NOT connect headphones to a badge link port. You might hear a ringing for
 * a while. Warn user.
 */
uint8_t st3m_io_badge_link_enable(uint8_t pin_mask);

/* Returns true if the battery is currently being charged.
 */
bool st3m_io_charger_state_get();
