#if defined(MESHECHO_CPR_NATIVE)

#include "meshecho_cpr_core.hpp"

int main() {
  meshecho_cpr::RouteTable routes;
  return routes.generation(0) == 0 ? 0 : 1;
}

#else

#include <Arduino.h>

// The legacy nRF5 Arduino core defines min/max macros before the C++ runtime
// headers below are parsed.
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "meshecho_cpr_budget.hpp"
#include "meshecho_cpr_radio.hpp"
#include "meshecho_cpr_runtime.hpp"
#include "meshecho_cpr_version.hpp"

#ifndef MESHECHO_CPR_NODE_ID
#define MESHECHO_CPR_NODE_ID 1
#endif
#ifndef MESHECHO_CPR_APP_DEADLINE_MS
#define MESHECHO_CPR_APP_DEADLINE_MS 30000U
#endif
#ifndef MESHECHO_CPR_HOP_GUARD_MS
#define MESHECHO_CPR_HOP_GUARD_MS 200U
#endif

namespace {

using namespace meshecho_cpr;

#if MESHECHO_CPR_RADIO_SX127X
using CprBoardRadio = CprSx127xRadio;
constexpr const char* kCprRadioName = "SX127x";
#else
using CprBoardRadio = CprSx1262Radio;
constexpr const char* kCprRadioName = "SX1262";
#endif

CprBoardRadio radio;
CprRuntime runtime(static_cast<NodeId>(MESHECHO_CPR_NODE_ID));
constexpr CprRadioConfig radio_config = CprRadioConfig::fromBuildFlags();
// Both adapters begin with explicit headers, PHY CRC and automatic LDRO.
constexpr CprLoRaBudgetConfig budget_config{
    static_cast<double>(radio_config.bandwidth_khz),
    radio_config.spreading_factor,
    radio_config.coding_rate,
    radio_config.preamble_length,
    true,
    false,
    CprLoRaLdro::Auto,
    MESHECHO_CPR_HOP_GUARD_MS,
};
static_assert(MESHECHO_CPR_APP_DEADLINE_MS > 0U &&
                  MESHECHO_CPR_APP_DEADLINE_MS <= 0x7FFFFFFFULL,
              "Application deadline must fit the modular millis clock horizon");
static_assert(MESHECHO_CPR_HOP_GUARD_MS >= kDefaultCprRelayJitterMs + 60U,
              "Hop guard must cover the maximum configured flood relay jitter");

std::uint32_t next_status_ms = 0;
char serial_line[96]{};
std::size_t serial_length = 0;

void printDelivery(const CprDelivery& delivery) {
  Serial.print(F("[MeshEcho-CPR] rx flow="));
  Serial.print(static_cast<unsigned long>(delivery.flow_id));
  Serial.print(F(" src="));
  Serial.print(delivery.source);
  Serial.print(F(" payload="));
  for (std::uint8_t i = 0; i < delivery.payload_len; ++i) {
    Serial.write(delivery.payload[i]);
  }
  Serial.println();
}

void processRadio() {
  if (!radio.packetAvailable()) {
    return;
  }
  CprRadioPacket packet{};
  if (radio.receive(&packet)) {
    (void)runtime.receive(packet.bytes.data(), packet.size, millis());
  }
}

void processTx(std::uint32_t now_ms) {
  CprRuntimeTx* tx = runtime.peekTx();
  if (tx == nullptr || !runtime.txDue(now_ms)) {
    return;
  }
  if (!runtime.prepareTx(now_ms)) {
    return;
  }
  tx = runtime.peekTx();
  if (tx == nullptr) {
    return;
  }

  // RadioLib startTransmit() is asynchronous. A successful start is already
  // a physical TX event for CPR; finishTransmit() only waits for completion
  // and returns the radio to RX, so a failed wait must not replay the frame.
  if (!radio.transmit(tx->encoded.bytes.data(), tx->encoded.size)) {
    (void)runtime.discardTx();
    return;
  }
  (void)runtime.onTxStarted(millis());
  if (!radio.finishTransmit()) {
    runtime.noteTxCompletionFailure();
  }
}

void processSerialLine() {
  if (serial_length == 0) {
    return;
  }
  serial_line[serial_length] = '\0';
  unsigned long destination = 0;
  unsigned long flow_id = 0;
  char payload[33]{};
  if (std::sscanf(serial_line, "send %lu %lu %32s", &destination, &flow_id, payload) == 3 &&
      destination > 0 && destination < 0xFFFFUL && flow_id > 0) {
    const std::size_t payload_len = std::strlen(payload);
    const std::uint32_t now_ms = millis();
    const CprExchangeBudget budget =
        cprExchangeBudgets(budget_config, payload_len, kMaxPathNodes);
    const std::size_t queued = budget.valid
        ? runtime.sendApp(
              static_cast<NodeId>(destination), static_cast<std::uint32_t>(flow_id),
              reinterpret_cast<const std::uint8_t*>(payload), payload_len, now_ms,
              now_ms + static_cast<std::uint32_t>(MESHECHO_CPR_APP_DEADLINE_MS),
              budget.route_bound_ms, budget.flood_bound_ms)
        : 0U;
    Serial.print(F("[MeshEcho-CPR] queued="));
    Serial.println(static_cast<unsigned long>(queued));
  } else {
    Serial.println(F("usage: send <destination> <flow_id> <payload>"));
  }
  serial_length = 0;
}

void processSerial() {
  while (Serial.available() > 0) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n' || value == '\r') {
      processSerialLine();
      continue;
    }
    if (serial_length + 1U < sizeof(serial_line)) {
      serial_line[serial_length++] = value;
    }
  }
}

void processDeliveries() {
  CprDelivery delivery{};
  while (runtime.pollDelivery(&delivery)) {
    printDelivery(delivery);
  }
}

void printStatus(std::uint32_t now_ms) {
  if (now_ms < next_status_ms) {
    return;
  }
  next_status_ms = now_ms + 10000U;
  const CprRuntimeStats& stats = runtime.stats();
  Serial.print(F("[MeshEcho-CPR] node="));
  Serial.print(static_cast<unsigned int>(MESHECHO_CPR_NODE_ID));
  Serial.print(F(" rx="));
  Serial.print(static_cast<unsigned long>(stats.rx_frames));
  Serial.print(F(" tx="));
  Serial.println(static_cast<unsigned long>(stats.tx_started));
}

}  // namespace

void setup() {
  Serial.begin(115200);
  const CprExchangeBudget startup_budget =
      cprExchangeBudgets(budget_config, kCprAppPayloadSize, kMaxPathNodes);
  const bool ready = startup_budget.valid && runtime.setAirtimeConfig(budget_config) &&
                     radio.begin(radio_config);
  Serial.print(F("[MeshEcho-CPR] firmware="));
  Serial.println(kCprFirmwareIdentity);
  Serial.print(F("[MeshEcho-CPR] radio="));
  Serial.print(kCprRadioName);
  Serial.println(ready ? F(" initialized") : F(" initialization failed"));
}

void loop() {
  processSerial();
  processRadio();
  (void)runtime.poll(millis());
  processTx(millis());
  processDeliveries();
  printStatus(millis());
}

#endif
