#include <Arduino.h>
#include <RadioLib.h>

#include <algorithm>
#include <array>
#include <cstring>

#include "../include/smart_calm_controller.hpp"
#include "../include/smart_calm_mesh.hpp"
#include "../include/smart_calm_prior.hpp"
#include "../include/smart_calm_wire.hpp"

#ifndef SMART_CALM_LORA_NSS
#define SMART_CALM_LORA_NSS 18
#endif

#ifndef SMART_CALM_LORA_DIO1
#define SMART_CALM_LORA_DIO1 26
#endif

#ifndef SMART_CALM_LORA_RST
#define SMART_CALM_LORA_RST 14
#endif

#ifndef SMART_CALM_LORA_BUSY
#define SMART_CALM_LORA_BUSY 27
#endif

#ifndef SMART_CALM_LORA_FREQ_MHZ
#define SMART_CALM_LORA_FREQ_MHZ 915.0f
#endif

#ifndef SMART_CALM_LORA_BW_KHZ
#define SMART_CALM_LORA_BW_KHZ 125.0f
#endif

#ifndef SMART_CALM_LORA_SF
#define SMART_CALM_LORA_SF 9
#endif

#ifndef SMART_CALM_LORA_CR
#define SMART_CALM_LORA_CR 7
#endif

#ifndef SMART_CALM_LORA_POWER_DBM
#define SMART_CALM_LORA_POWER_DBM 17
#endif

#ifndef SMART_CALM_LORA_TCXO_VOLTAGE
#define SMART_CALM_LORA_TCXO_VOLTAGE 1.6f
#endif

#ifndef SMART_CALM_LORA_USE_LDO
#define SMART_CALM_LORA_USE_LDO false
#endif

#ifndef SMART_CALM_LORA_GAIN
#define SMART_CALM_LORA_GAIN 0
#endif

#ifndef SMART_CALM_NODE_ID
#define SMART_CALM_NODE_ID 1
#endif

#ifndef SMART_CALM_RADIO_SX127X
#define SMART_CALM_RADIO_SX127X 0
#endif

using namespace smart_calm;

#if SMART_CALM_RADIO_SX127X
SX1276 radio = new Module(SMART_CALM_LORA_NSS, SMART_CALM_LORA_DIO1, SMART_CALM_LORA_RST, SMART_CALM_LORA_BUSY);
#else
SX1262 radio = new Module(SMART_CALM_LORA_NSS, SMART_CALM_LORA_DIO1, SMART_CALM_LORA_RST, SMART_CALM_LORA_BUSY);
#endif

namespace {

volatile bool packet_received = false;
SmartCalmController controller;
SmartCalmMesh mesh(SMART_CALM_NODE_ID);
Snapshot snapshot;
std::uint32_t next_learning_tick_ms = 0;
std::uint32_t next_status_tx_ms = 0;
std::uint32_t next_hello_tx_ms = 0;
std::uint16_t next_seq = 1;
constexpr std::uint32_t kLearningTickMs = 30000;
constexpr std::uint32_t kStatusTxMs = 15000;
constexpr std::uint32_t kHelloTxMs = 45000;

bool timeReached(std::uint32_t now_ms, std::uint32_t deadline_ms) {
  return static_cast<std::int32_t>(now_ms - deadline_ms) >= 0;
}

void setPacketFlag() {
  packet_received = true;
}

void copyPayload(WireFrame& frame, const char* text) {
  if (text == nullptr) {
    frame.payload_len = 0;
    frame.payload[0] = '\0';
    return;
  }
  const std::size_t len = std::min<std::size_t>(std::strlen(text), kWirePayloadSize);
  frame.payload_len = static_cast<std::uint16_t>(len);
  std::memcpy(frame.payload, text, len);
  if (len < kWirePayloadSize) {
    frame.payload[len] = '\0';
  }
}

void sendFrame(const WireFrame& frame) {
  const auto bytes = encodeWireFrame(frame);
  if (bytes.size == 0) {
    Serial.println(F("[Smart-CALM] encode failed, frame dropped"));
    return;
  }
  const int16_t state = radio.transmit(bytes.bytes.data(), bytes.size);
  saturatingIncrement(snapshot.tx_count);
  if (frame.type != FrameType::Data) {
    saturatingIncrement(snapshot.control_tx);
  }
  if (state != RADIOLIB_ERR_NONE) {
    // Firmware uses transmit failures as a channel-pressure proxy.
    saturatingIncrement(snapshot.collision_fail);
    Serial.print(F("[Smart-CALM] transmit failed, code "));
    Serial.println(state);
  }
}

void sendOutboundFrames(const OutboundFrame* frames, std::size_t count) {
  if (frames == nullptr) {
    return;
  }
  for (std::size_t i = 0; i < count; ++i) {
    if (frames[i].frame.type == FrameType::Fallback) {
      delay(static_cast<unsigned long>(controller.activeProfile().fallback_delay_margin_s * 1000.0f));
    }
    sendFrame(frames[i].frame);
  }
}

void sendStatusBeacon(std::uint32_t now_ms) {
  char summary[64];
  controller.formatStatus(summary, sizeof(summary));

  WireFrame frame{};
  frame.type = FrameType::Status;
  frame.src = SMART_CALM_NODE_ID;
  frame.dst = kBroadcastAddress;
  frame.seq = next_seq++;
  frame.flow_id = now_ms;
  frame.created_at_ms = now_ms;
  frame.ttl = 1;
  frame.state_index = controller.activeStateIndex();
  frame.action_index = controller.activeProfileIndex();
  frame.confidence_milli = 950;
  copyPayload(frame, summary);
  sendFrame(frame);
  Serial.print(F("[Smart-CALM] beacon: "));
  Serial.println(summary);
}

void sendHello(std::uint32_t now_ms) {
  WireFrame frame{};
  frame.type = FrameType::Hello;
  frame.src = SMART_CALM_NODE_ID;
  frame.dst = kBroadcastAddress;
  frame.seq = next_seq++;
  frame.flow_id = now_ms ^ 0xA5A5U;
  frame.created_at_ms = now_ms;
  frame.ttl = 1;
  frame.state_index = controller.activeStateIndex();
  frame.action_index = controller.activeProfileIndex();
  frame.confidence_milli = 1000;
  copyPayload(frame, "hello");
  sendFrame(frame);
}

void handleReceivedFrame(const WireFrame& frame, float rssi, float snr, std::uint32_t now_ms) {
  if (frame.type == FrameType::Status) {
    saturatingIncrement(snapshot.broadcast_flows);
    saturatingIncrement(snapshot.broadcast_deliveries);
    if (frame.payload_len > 0) {
      Serial.print(F("[Smart-CALM] status from "));
      Serial.print(frame.src);
      Serial.print(F(": "));
      for (std::size_t i = 0; i < frame.payload_len; ++i) {
        Serial.print(frame.payload[i]);
      }
      Serial.println();
    }
    return;
  }

  OutboundFrame outbound[kMaxOutboundFrames]{};
  const std::size_t count = mesh.handleFrame(frame, now_ms, rssi, snr, controller, snapshot, outbound, kMaxOutboundFrames);
  if (count > 0) {
    Serial.print(F("[Smart-CALM] mesh response count="));
    Serial.println(static_cast<unsigned>(count));
    sendOutboundFrames(outbound, count);
  }
}

void pollRadio(std::uint32_t now_ms) {
  if (!packet_received) {
    return;
  }

  packet_received = false;
  std::array<std::uint8_t, kWireMaxFrameSize> buffer{};
  const std::size_t packet_len =
      std::min<std::size_t>(static_cast<std::size_t>(radio.getPacketLength()), buffer.size());
  const int16_t state = radio.readData(buffer.data(), packet_len);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print(F("[Smart-CALM] read failed, code "));
    Serial.println(state);
    radio.startReceive();
    return;
  }

  WireFrame frame{};
  if (!decodeWireFrame(buffer.data(), packet_len, &frame)) {
    Serial.println(F("[Smart-CALM] dropped malformed frame"));
    radio.startReceive();
    return;
  }

  handleReceivedFrame(frame, radio.getRSSI(), radio.getSNR(), now_ms);
  radio.startReceive();
}

void updateLearning(std::uint32_t now_ms) {
  if (!timeReached(now_ms, next_learning_tick_ms)) {
    return;
  }
  controller.learningTick(snapshot, esp_random());
  char summary[96];
  controller.formatStatus(summary, sizeof(summary));
  Serial.print(F("[Smart-CALM] learn: "));
  Serial.println(summary);
  next_learning_tick_ms = now_ms + kLearningTickMs;
}

void maybeTransmitPeriodicFrames(std::uint32_t now_ms) {
  if (timeReached(now_ms, next_hello_tx_ms)) {
    sendHello(now_ms);
    next_hello_tx_ms = now_ms + kHelloTxMs;
  }
  if (timeReached(now_ms, next_status_tx_ms)) {
    sendStatusBeacon(now_ms);
    next_status_tx_ms = now_ms + kStatusTxMs;
  }
}

void pollSerialApp(std::uint32_t now_ms) {
  if (!Serial.available()) {
    return;
  }
  const String line = Serial.readStringUntil('\n');
  if (!line.startsWith("send ")) {
    Serial.println(F("[Smart-CALM] command: send <dst> <text>"));
    return;
  }
  const int space = line.indexOf(' ', 5);
  if (space < 0) {
    Serial.println(F("[Smart-CALM] command: send <dst> <text>"));
    return;
  }
  const std::uint16_t dst = static_cast<std::uint16_t>(line.substring(5, space).toInt());
  const String text = line.substring(space + 1);
  const std::size_t len = std::min<std::size_t>(text.length(), sizeof(RoutePayload::app));
  std::uint8_t payload[sizeof(RoutePayload::app)]{};
  for (std::size_t i = 0; i < len; ++i) {
    payload[i] = static_cast<std::uint8_t>(text[i]);
  }

  OutboundFrame outbound[kMaxOutboundFrames]{};
  const std::uint32_t flow_id = (static_cast<std::uint32_t>(SMART_CALM_NODE_ID) << 24U) ^ now_ms;
  const std::size_t count =
      mesh.sendApp(dst, flow_id, payload, len, now_ms, esp_random(), controller, snapshot, outbound, kMaxOutboundFrames);
  Serial.print(F("[Smart-CALM] app send dst="));
  Serial.print(dst);
  Serial.print(F(" flow="));
  Serial.print(flow_id);
  Serial.print(F(" frames="));
  Serial.println(static_cast<unsigned>(count));
  sendOutboundFrames(outbound, count);
}

int16_t beginRadio() {
#if SMART_CALM_RADIO_SX127X
  return radio.begin(
      SMART_CALM_LORA_FREQ_MHZ,
      SMART_CALM_LORA_BW_KHZ,
      SMART_CALM_LORA_SF,
      SMART_CALM_LORA_CR,
      RADIOLIB_SX127X_SYNC_WORD,
      SMART_CALM_LORA_POWER_DBM,
      8,
      SMART_CALM_LORA_GAIN);
#else
  return radio.begin(
      SMART_CALM_LORA_FREQ_MHZ,
      SMART_CALM_LORA_BW_KHZ,
      SMART_CALM_LORA_SF,
      SMART_CALM_LORA_CR,
      RADIOLIB_SX126X_SYNC_WORD_PRIVATE,
      SMART_CALM_LORA_POWER_DBM,
      8,
      SMART_CALM_LORA_TCXO_VOLTAGE,
      SMART_CALM_LORA_USE_LDO);
#endif
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);

  controller.loadPrior(kSmartCalmPrior);

  const int16_t state = beginRadio();

  if (state != RADIOLIB_ERR_NONE) {
    Serial.print(F("[Smart-CALM] radio init failed, code "));
    Serial.println(state);
    while (true) {
      delay(1000);
    }
  }

  radio.setPacketReceivedAction(setPacketFlag);
  radio.startReceive();

  const std::uint32_t now_ms = millis();
  next_learning_tick_ms = now_ms + kLearningTickMs;
  next_status_tx_ms = now_ms + 1000;
  next_hello_tx_ms = now_ms + 2000;

  char summary[96];
  controller.formatStatus(summary, sizeof(summary));
  Serial.println(F("[Smart-CALM] ESP32 controller ready"));
  Serial.println(summary);
}

void loop() {
  const std::uint32_t now_ms = millis();
  pollRadio(now_ms);
  pollSerialApp(now_ms);
  updateLearning(now_ms);
  maybeTransmitPeriodicFrames(now_ms);
  delay(5);
}
