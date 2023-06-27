#include "st3m_gfx.h"
#include "st3m_fs.h"
#include "st3m_audio.h"
#include "st3m_scope.h"
#include "st3m_leds.h"

#include "bl00mbox.h"

#include "flow3r_bsp.h"

// Declared by badge23 codebase. To be removed and slurped up into st3m.
void badge23_main(void);

// Called by micropython via MICROPY_BOARD_STARTUP.
void st3m_board_startup(void) {
    // Initialize display first as that gives us a nice splash screen.
    st3m_gfx_init();
    // Submit splash a couple of times to make sure we've fully flushed out the
    // initial framebuffer (both on-ESP and in-screen) noise before we turn on
    // the backlight.
    for (int i = 0; i < 4; i++) {
        st3m_gfx_splash("st3m loading...");
    }
    flow3r_bsp_display_set_backlight(100);

    flow3r_bsp_i2c_init();
    st3m_fs_init();
    st3m_scope_init();
    st3m_audio_init();
    st3m_audio_set_player_function(bl00mbox_player_function);
    st3m_leds_init();

    // Handoff to badge23.
    badge23_main();
}