#include "meshecho_cpr_radio.hpp"

#if !defined(MESHECHO_CPR_NATIVE)
namespace meshecho_cpr {
namespace {

// Keep the adapters in the board build even when an application chooses to
// inject a different CprRadioPort. These link probes force both RadioLib API
// surfaces to be type-checked by the corresponding PlatformIO targets.
[[maybe_unused]] bool cprRadioLinkProbe(CprSx1262Radio& radio, const CprRadioConfig& config,
                       const std::uint8_t* bytes, std::size_t length,
                       CprRadioPacket* packet) {
  (void)radio.begin(config);
  (void)radio.transmit(bytes, length);
  (void)radio.finishTransmit();
  (void)radio.startReceive();
  (void)radio.packetAvailable();
  (void)radio.receive(packet);
  return true;
}

[[maybe_unused]] bool cprRadioLinkProbeSx127x(CprSx127xRadio& radio, const CprRadioConfig& config,
                             const std::uint8_t* bytes, std::size_t length,
                             CprRadioPacket* packet) {
  (void)radio.begin(config);
  (void)radio.transmit(bytes, length);
  (void)radio.finishTransmit();
  (void)radio.startReceive();
  (void)radio.packetAvailable();
  (void)radio.receive(packet);
  return true;
}

}  // namespace
}  // namespace meshecho_cpr
#endif
