#pragma once

#include <stdint.h>
#include <stdbool.h>

typedef enum {
	st3m_audio_input_source_none = 0,
	// Line in on riht jack.
	st3m_audio_input_source_line_in = 1,
	// Headset microphone on left jack.
	st3m_audio_input_source_headset_mic = 2,
	// Onboard microphone (enabled red LED).
	st3m_audio_input_source_onboard_mic = 3
} st3m_audio_input_source_t;

typedef void (*st3m_audio_player_function_t)(int16_t * tx, int16_t * rx, uint16_t len);

/* The default audio task takes a function of prototype
 * &st3m_audio_player_function_t, loops it and sets software volume/adds software
 * thru. tx is the stereo zipped l/r output, rx is the stereo zipped input, each
 * buffer the size of len.
 */
void st3m_audio_set_player_function(st3m_audio_player_function_t fun);

/* Dummy for st3m_audio_set_player_function that just writes zeros to the output.
 * Default state.
 */
void st3m_audio_player_function_dummy(int16_t * rx, int16_t * tx, uint16_t len);

/* Initializes I2S bus, the audio task and required data structures.
 * Expects an initialized I2C bus, will fail ungracefully otherwise (TODO).
 */
void st3m_audio_init(void);

/* Returns true if headphones with or without microphone were connected to the
 * headphone jack at the last call of st3m_audio_update_jacksense.
 */
bool st3m_audio_headphones_are_connected(void);

/* Returns true if headphones with microphone were connected to the headphone
 * jack at the last call of audio_update_jacksense.
 */
bool st3m_audio_headset_is_connected(void);

/* If a sleeve contact mic doesn't pull the detection pin low enough the
 * codec's built in headphone detection might fail. Calling this function
 * with 'enable = 1' overrides the detection and assumes there's headphones
 * plugged in. Call with 'enable = 0' to revert to automatic detection.
 */
void st3m_audio_headphones_detection_override(bool enable);

/* Attempts to set target volume for the headphone output/onboard speakers
 * respectively, clamps/rounds if necessary and returns the actual volume.
 * Absolute reference arbitrary.
 * Does not unmute, use st3m_audio_{headphones_/speaker_/}set_mute as needed.
 * Enters fake mute if requested volume is below the value set by
 * st3m_audio_{headphones/speaker}_set_minimum_volume_user.
 *
 * Note: This function uses a hardware PGA for the coarse value and software
 * for the fine value. These two methods are as of yet not synced so that there
 * may be a transient volume "hiccup". "p1" badges only use software volume.
 * The unspecified variant automatically chooses the adequate channel (**).
 */
float st3m_audio_headphones_set_volume_dB(float vol_dB);
float st3m_audio_speaker_set_volume_dB(float vol_dB);
float st3m_audio_set_volume_dB(float vol_dB);

/* Like the st3m_audio_{headphones_/speaker_/}set_volume family but changes
 * relative to last volume value.
 */
float st3m_audio_headphones_adjust_volume_dB(float vol_dB);
float st3m_audio_speaker_adjust_volume_dB(float vol_dB);
float st3m_audio_adjust_volume_dB(float vol_dB);

/* Returns volume as set with st3m_audio_{headphones/speaker}_set_volume_dB.  The
 * unspecified variant automatically chooses the adequate channel (**).
 */
float st3m_audio_headphones_get_volume_dB(void);
float st3m_audio_speaker_get_volume_dB(void);
float st3m_audio_get_volume_dB(void);

/* Mutes (mute = 1) or unmutes (mute = 0) the specified channel.
 * The unspecified variant automatically chooses the adequate channel (**).
 *
 * Note: Even if a channel is unmuted it might not play sound depending on
 * the return value of st3m_audio_headphone_are_connected. There is no override
 * for this (see HEADPHONE PORT POLICY below).
 */
void st3m_audio_headphones_set_mute(bool mute);
void st3m_audio_speaker_set_mute(bool mute);
void st3m_audio_set_mute(bool mute);

/* Returns true if channel is muted, false otherwise.
 * The unspecified variant automatically chooses the adequate channel (**).
 */
bool st3m_audio_headphones_get_mute(void);
bool st3m_audio_speaker_get_mute(void);
bool st3m_audio_get_mute(void);

/* Set the minimum and maximum allowed volume levels for speakers and headphones
 * respectively. Clamps with hardware limitations. Maximum clamps below the minimum
 * value, minimum clamps above the maximum. Returns clamped value.
 */
float st3m_audio_headphones_set_minimum_volume_dB(float vol_dB);
float st3m_audio_headphones_set_maximum_volume_dB(float vol_dB);
float st3m_audio_speaker_set_minimum_volume_dB(float vol_dB);
float st3m_audio_speaker_set_maximum_volume_dB(float vol_dB);

/* Returns the minimum and maximum allowed volume levels for speakers and headphones
 * respectively. Change with
 * st3m_audio_{headphones/speaker}_set_{minimum/maximum}_volume_dB.
 */
float st3m_audio_headphones_get_minimum_volume_dB(void);
float st3m_audio_headphones_get_maximum_volume_dB(void);
float st3m_audio_speaker_get_minimum_volume_dB(void);
float st3m_audio_speaker_get_maximum_volume_dB(void);

/* Syntactic sugar for drawing UI: Returns channel volume in a 0..1 range,
 * scaled into a 0.01..1 range according to the values set with
 * st3m_audio_{headphones_/speaker_/}set_{maximum/minimum}_volume_ and 0 if in a
 * fake mute condition.
 *
 * The unspecified variant automatically chooses the adequate channel (**).
 */
float st3m_audio_headphones_get_volume_relative(void);
float st3m_audio_speaker_get_volume_relative(void);
float st3m_audio_get_volume_relative(void);

/* (**) if st3m_audio_headphones_are_connected returns 1 the "headphone" variant
 *      is chosen, else the "speaker" variant is chosen.
 */

/* These route whatever is on the line in port directly to the headphones or
 * speaker respectively (enable = 1), or don't (enable = 0). Is affected by mute
 * and coarse hardware volume settings, however software fine volume is not applied.
 *
 * Good for testing, might deprecate later, idk~
 */
void st3m_audio_headphones_line_in_set_hardware_thru(bool enable);
void st3m_audio_speaker_line_in_set_hardware_thru(bool enable);
void st3m_audio_line_in_set_hardware_thru(bool enable);

/* The codec can transmit audio data from different sources. This function enables
 * one or no source as provided by the st3m_audio_input_source_t enum.
 *
 * Note: The onboard digital mic turns on an LED on the top board if it receives
 * a clock signal which is considered a good proxy for its capability of reading data.
 *
 * TODO: check if sources are available
 */
void st3m_audio_input_set_source(st3m_audio_input_source_t source);

/* Returns the currently selected input source.
 */
st3m_audio_input_source_t st3m_audio_input_get_source(void);

/* Hardware preamp gain, 0dB-50dB. TODO: figure out if int/float inconsistency
 * is a good thing here compared to all other _dB functions.
 */
uint8_t st3m_audio_headset_set_gain_dB(uint8_t gain_dB);
uint8_t st3m_audio_headset_get_gain_dB(void);

/* You can route whatever source is selected with st3m_audio_input_set_source to
 * the audio output. Use these to control volume and mute.
 */
float st3m_audio_input_thru_set_volume_dB(float vol_dB);
float st3m_audio_input_thru_get_volume_dB(void);
void st3m_audio_input_thru_set_mute(bool mute);
bool st3m_audio_input_thru_get_mute(void);

/*
HEADPHONE PORT POLICY

Under normal circumstances it is an important feature to have a reliable speaker
mute when plugging in headphones. However, since the headphone port on the badge
can also be used for badge link, there are legimate cases where it is desirable to
have the speakers unmuted while a cable is plugged into the jack.

As a person who plugs in the headphones on the tram, doesn't put them on, turns on
music to check if it's not accidentially playing on speakers and then finally puts
on headphones (temporarily, of course, intermittent checks if the speakers didn't
magically turn on are scheduled according to our general anxiety level) we wish to
make it difficult to accidentially have sound coming from the speakers.

Our proposed logic is as follows (excluding boot conditions):

1) Badge link TX cannot be enabled for any of the headphone jack pins without a
cable detected in the jack. This is to protect users from plugging in headphones
while badge link is active and receiving a short but potentially very loud burst
of digital data before the software can react to the state change.

2) If the software detects that the headphone jack has changed from unplugged to
plugged it *always* turns off speakers, no exceptions.

3) If a user wishes to TX on headphone badge link, they must confirm a warning that
having headphones plugged in may potentially cause hearing damage *every time*.

4) If a user wishes to RX or TX on headphone badge link while playing sound on the
onboard speakers, they must confirm a warning *every time*.

We understand that these means seem extreme, but we find them to be a sensible
default configuration to make sure people can safely operate the device without
needing to refer to a manual.

(TX here means any state that is not constantly ~GND with whatever impedance.
While there are current limiting resistors (value TBD at the time of writing, but
presumably 100R-470R) in series with the GPIOs, they still can generate quite some
volume with standard 40Ohm-ish headphones. Ideally the analog switch will never
switch to the GPIOs without a cable plugged in.)
*/