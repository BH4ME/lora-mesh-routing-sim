#pragma once

// The legacy nRF5 Arduino core used by PlatformIO's nrf52840_dk board does
// not declare tone/noTone, while RadioLib's generic Arduino HAL references
// them. The CPR firmware does not use a buzzer; these no-op shims only make
// that optional HAL surface linkable on this board.
#if !defined(MESHECHO_CPR_NRF_TONE_COMPAT)
#define MESHECHO_CPR_NRF_TONE_COMPAT 1
#ifdef __cplusplus
inline void tone(unsigned long pin, unsigned int frequency, unsigned long duration = 0UL) {
  (void)pin;
  (void)frequency;
  (void)duration;
}
inline void noTone(unsigned long pin) { (void)pin; }
#else
static inline void tone(unsigned long pin, unsigned int frequency, unsigned long duration) {
  (void)pin;
  (void)frequency;
  (void)duration;
}
static inline void noTone(unsigned long pin) { (void)pin; }
#endif
#endif
