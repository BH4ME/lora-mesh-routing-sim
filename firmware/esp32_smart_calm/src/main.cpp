#include <Arduino.h>
#include <Preferences.h>
#include <RadioLib.h>

#include <algorithm>
#include <array>
#include <cstring>

#include "../include/meshecho_config.hpp"
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
MeshEchoConfig mesh_config = makeDefaultMeshEchoConfig(
    SMART_CALM_NODE_ID,
    SMART_CALM_LORA_FREQ_MHZ,
    SMART_CALM_LORA_BW_KHZ,
    SMART_CALM_LORA_SF,
    SMART_CALM_LORA_CR,
    SMART_CALM_LORA_POWER_DBM,
    SMART_CALM_RADIO_SX127X != 0);
Snapshot snapshot;
std::uint32_t next_learning_tick_ms = 0;
std::uint32_t next_status_tx_ms = 0;
std::uint32_t next_hello_tx_ms = 0;
std::uint16_t next_seq = 1;
constexpr std::uint32_t kLearningTickMs = 30000;
constexpr std::uint32_t kStatusTxMs = 15000;
constexpr std::uint32_t kHelloTxMs = 45000;

#if SMART_CALM_RADIO_SX127X
constexpr const char* kMeshEchoTarget = "esp32dev_sx127x";
constexpr const char* kMeshEchoRadio = "SX127x";
#else
constexpr const char* kMeshEchoTarget = "esp32dev_sx1262";
constexpr const char* kMeshEchoRadio = "SX1262";
#endif

void setPacketFlag() {
  packet_received = true;
}

void loadPersistentConfig() {
  Preferences prefs;
  if (!prefs.begin("meshecho", true)) {
    return;
  }
  mesh_config.node_id = prefs.getUShort("node_id", mesh_config.node_id);
  prefs.getString("callsign", mesh_config.callsign, sizeof(mesh_config.callsign));
  prefs.getString("region", mesh_config.region, sizeof(mesh_config.region));
  mesh_config.freq_mhz = prefs.getFloat("freq_mhz", mesh_config.freq_mhz);
  mesh_config.bw_khz = prefs.getFloat("bw_khz", mesh_config.bw_khz);
  mesh_config.sf = prefs.getUChar("sf", mesh_config.sf);
  mesh_config.cr = prefs.getUChar("cr", mesh_config.cr);
  mesh_config.tx_power_dbm = prefs.getChar("tx_power", mesh_config.tx_power_dbm);
  mesh_config.max_hops = prefs.getUChar("max_hops", mesh_config.max_hops);
  mesh_config.route_ttl_s = prefs.getUShort("route_ttl_s", mesh_config.route_ttl_s);
  mesh_config.fallback_ttl = prefs.getUChar("fallback_ttl", mesh_config.fallback_ttl);
  mesh_config.ack_timeout_ms = prefs.getUShort("ack_timeout_ms", mesh_config.ack_timeout_ms);
  mesh_config.max_timeout_retries = prefs.getUChar("max_timeout_retries", mesh_config.max_timeout_retries);
  mesh_config.retry_after_fallback = prefs.getBool("retry_after_fallback", mesh_config.retry_after_fallback);
  mesh_config.ble_enabled = prefs.getBool("ble", mesh_config.ble_enabled);
  mesh_config.wifi_enabled = prefs.getBool("wifi", mesh_config.wifi_enabled);
  prefs.end();
}

bool savePersistentConfig() {
  Preferences prefs;
  if (!prefs.begin("meshecho", false)) {
    return false;
  }
  bool ok = true;
  ok = prefs.putUShort("node_id", mesh_config.node_id) > 0 && ok;
  ok = prefs.putString("callsign", mesh_config.callsign) > 0 && ok;
  ok = prefs.putString("region", mesh_config.region) > 0 && ok;
  ok = prefs.putFloat("freq_mhz", mesh_config.freq_mhz) > 0 && ok;
  ok = prefs.putFloat("bw_khz", mesh_config.bw_khz) > 0 && ok;
  ok = prefs.putUChar("sf", mesh_config.sf) > 0 && ok;
  ok = prefs.putUChar("cr", mesh_config.cr) > 0 && ok;
  ok = prefs.putChar("tx_power", mesh_config.tx_power_dbm) > 0 && ok;
  ok = prefs.putUChar("max_hops", mesh_config.max_hops) > 0 && ok;
  ok = prefs.putUShort("route_ttl_s", mesh_config.route_ttl_s) > 0 && ok;
  ok = prefs.putUChar("fallback_ttl", mesh_config.fallback_ttl) > 0 && ok;
  ok = prefs.putUShort("ack_timeout_ms", mesh_config.ack_timeout_ms) > 0 && ok;
  ok = prefs.putUChar("max_timeout_retries", mesh_config.max_timeout_retries) > 0 && ok;
  ok = prefs.putBool("retry_after_fallback", mesh_config.retry_after_fallback) > 0 && ok;
  ok = prefs.putBool("ble", mesh_config.ble_enabled) > 0 && ok;
  ok = prefs.putBool("wifi", mesh_config.wifi_enabled) > 0 && ok;
  prefs.end();
  return ok;
}

MeshRuntimeLimits makeMeshRuntimeLimits() {
  MeshRuntimeLimits limits{};
  limits.max_hops = mesh_config.max_hops;
  limits.route_ttl_s = mesh_config.route_ttl_s;
  limits.fallback_ttl = mesh_config.fallback_ttl;
  limits.ack_timeout_ms = mesh_config.ack_timeout_ms;
  limits.max_timeout_retries = mesh_config.max_timeout_retries;
  limits.retry_after_fallback = mesh_config.retry_after_fallback;
  return limits;
}

MeshEchoRuntimeInfo makeRuntimeInfo(std::uint32_t now_ms) {
  MeshEchoRuntimeInfo runtime{};
  runtime.target = kMeshEchoTarget;
  runtime.chip = "ESP32";
  runtime.radio = kMeshEchoRadio;
  runtime.active_profile = controller.activeProfile().name;
  runtime.uptime_ms = now_ms;
  runtime.tx_count = snapshot.tx_count;
  runtime.control_tx = snapshot.control_tx;
  runtime.rx_success = snapshot.rx_success;
  runtime.rx_fail = snapshot.rx_fail;
  runtime.collision_fail = snapshot.collision_fail;
  runtime.route_cache_hits = snapshot.route_cache_hits;
  runtime.route_cache_misses = snapshot.route_cache_misses;
  runtime.route_repair_count = snapshot.route_repair_count;
  runtime.route_expired_count = snapshot.route_expired_count;
  runtime.neighbor_updates = snapshot.neighbor_updates;
  runtime.neighbor_expired_count = snapshot.neighbor_expired_count;
  runtime.fallback_forward_count = snapshot.fallback_forward_count;
  runtime.fallback_delivery_count = snapshot.fallback_delivery_count;
  runtime.unicast_deliveries = snapshot.unicast_deliveries;
  runtime.unicast_acks = snapshot.unicast_acks;
  runtime.unicast_failures = snapshot.unicast_failures;
  runtime.delivery_delay_total_s = snapshot.delivery_delay_total_s;
  runtime.delivery_delay_samples = snapshot.delivery_delay_samples;
  runtime.policy_switch_count = controller.policySwitchCount();
  runtime.policy_update_count = controller.policyUpdateCount();
  runtime.active_routes = static_cast<std::uint32_t>(mesh.activeRouteCount());
  runtime.pending_flows = static_cast<std::uint32_t>(mesh.pendingFlowCount());
  runtime.neighbors = static_cast<std::uint32_t>(mesh.neighborCount());
  return runtime;
}

void resetMeshIdentity() {
  mesh = SmartCalmMesh(mesh_config.node_id);
  next_seq = 1;
}

void applyRadioConfig() {
  radio.standby();
  int16_t state = radio.setFrequency(mesh_config.freq_mhz);
  if (state == RADIOLIB_ERR_NONE) {
    state = radio.setBandwidth(mesh_config.bw_khz);
  }
  if (state == RADIOLIB_ERR_NONE) {
    state = radio.setSpreadingFactor(mesh_config.sf);
  }
  if (state == RADIOLIB_ERR_NONE) {
    state = radio.setCodingRate(mesh_config.cr);
  }
  if (state == RADIOLIB_ERR_NONE) {
    state = radio.setOutputPower(mesh_config.tx_power_dbm);
  }
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print(F("[MeshEcho] radio config apply failed, code "));
    Serial.println(state);
  }
  radio.startReceive();
}

void copyPayload(WireFrame& frame, const char* text) {
  if (text == nullptr) {
    frame.payload_len = 0;
    frame.payload[0] = '\0';
    return;
  }
  const std::size_t len = std::min<std::size_t>(std::strlen(text), kWirePayloadSize);
  frame.payload_len = static_cast<std::uint8_t>(len);
  std::memcpy(frame.payload, text, len);
  if (len < kWirePayloadSize) {
    frame.payload[len] = '\0';
  }
}

void sendFrame(const WireFrame& frame) {
  const auto bytes = encodeWireFrame(frame);
  const int16_t state = radio.transmit(bytes.bytes.data(), bytes.size);
  ++snapshot.tx_count;
  if (frame.type != FrameType::Data) {
    ++snapshot.control_tx;
  }
  if (state != RADIOLIB_ERR_NONE) {
    ++snapshot.collision_fail;
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
      delay(static_cast<unsigned long>(
          controller.profileAt(frames[i].frame.action_index).fallback_delay_margin_s * 1000.0f));
    }
    sendFrame(frames[i].frame);
  }
}

void sendStatusBeacon(std::uint32_t now_ms) {
  char summary[128];
  controller.formatStatus(summary, sizeof(summary));

  WireFrame frame{};
  frame.type = FrameType::Status;
  frame.src = mesh_config.node_id;
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
  frame.src = mesh_config.node_id;
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
    ++snapshot.broadcast_flows;
    ++snapshot.broadcast_deliveries;
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
  const std::size_t count =
      mesh.handleFrame(makeMeshRuntimeLimits(), frame, now_ms, rssi, snr, controller, snapshot, outbound, kMaxOutboundFrames);
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
    ++snapshot.rx_fail;
    Serial.print(F("[Smart-CALM] read failed, code "));
    Serial.println(state);
    radio.startReceive();
    return;
  }

  WireFrame frame{};
  if (!decodeWireFrame(buffer.data(), packet_len, &frame)) {
    ++snapshot.rx_fail;
    Serial.println(F("[Smart-CALM] dropped malformed frame"));
    radio.startReceive();
    return;
  }

  ++snapshot.rx_success;
  handleReceivedFrame(frame, radio.getRSSI(), radio.getSNR(), now_ms);
  radio.startReceive();
}

void updateLearning(std::uint32_t now_ms) {
  if (now_ms < next_learning_tick_ms) {
    return;
  }
  controller.learningTick(snapshot, esp_random());
  char summary[128];
  controller.formatStatus(summary, sizeof(summary));
  Serial.print(F("[Smart-CALM] learn: "));
  Serial.println(summary);
  next_learning_tick_ms = now_ms + kLearningTickMs;
}

void processTimeouts(std::uint32_t now_ms) {
  OutboundFrame outbound[kMaxOutboundFrames]{};
  const std::size_t count =
      mesh.tick(makeMeshRuntimeLimits(), now_ms, controller, snapshot, outbound, kMaxOutboundFrames);
  if (count > 0) {
    Serial.print(F("[Smart-CALM] timeout recovery count="));
    Serial.println(static_cast<unsigned>(count));
    sendOutboundFrames(outbound, count);
  }
}

void maybeTransmitPeriodicFrames(std::uint32_t now_ms) {
  if (now_ms >= next_hello_tx_ms) {
    sendHello(now_ms);
    next_hello_tx_ms = now_ms + kHelloTxMs;
  }
  if (now_ms >= next_status_tx_ms) {
    sendStatusBeacon(now_ms);
    next_status_tx_ms = now_ms + kStatusTxMs;
  }
}

void pollSerialApp(std::uint32_t now_ms) {
  if (!Serial.available()) {
    return;
  }
  const String line = Serial.readStringUntil('\n');
  char response[1024]{};
  const MeshEchoConfigCommandResult config_result =
      handleMeshEchoConfigCommand(line.c_str(), mesh_config, makeRuntimeInfo(now_ms), response, sizeof(response));
  if (config_result.handled) {
    if (config_result.node_id_changed) {
      resetMeshIdentity();
    }
    if (config_result.radio_changed) {
      applyRadioConfig();
    }
    if (config_result.save_requested) {
      formatMeshEchoSaveResponse(savePersistentConfig(), response, sizeof(response));
    }
    Serial.println(response);
    if (config_result.reboot_requested) {
      delay(100);
      ESP.restart();
    }
    return;
  }
  if (!line.startsWith("send ")) {
    Serial.println(F("{\"ok\":false,\"error\":\"expected MeshEcho config command or send <dst> <text>\"}"));
    return;
  }
  const int space = line.indexOf(' ', 5);
  if (space < 0) {
    Serial.println(F("{\"ok\":false,\"error\":\"expected send <dst> <text>\"}"));
    return;
  }
  const std::uint16_t dst = static_cast<std::uint16_t>(line.substring(5, space).toInt());
  const String text = line.substring(space + 1);
  const std::size_t len = std::min<std::size_t>(text.length(), kRouteAppPayloadSize);
  std::uint8_t payload[kRouteAppPayloadSize]{};
  for (std::size_t i = 0; i < len; ++i) {
    payload[i] = static_cast<std::uint8_t>(text[i]);
  }

  OutboundFrame outbound[kMaxOutboundFrames]{};
  const std::uint32_t flow_id = (static_cast<std::uint32_t>(mesh_config.node_id) << 24U) ^ now_ms;
  const std::size_t count =
      mesh.sendApp(
          makeMeshRuntimeLimits(),
          dst,
          flow_id,
          payload,
          len,
          now_ms,
          esp_random(),
          controller,
          snapshot,
          outbound,
          kMaxOutboundFrames);
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
      mesh_config.freq_mhz,
      mesh_config.bw_khz,
      mesh_config.sf,
      mesh_config.cr,
      RADIOLIB_SX127X_SYNC_WORD,
      mesh_config.tx_power_dbm,
      8,
      SMART_CALM_LORA_GAIN);
#else
  return radio.begin(
      mesh_config.freq_mhz,
      mesh_config.bw_khz,
      mesh_config.sf,
      mesh_config.cr,
      RADIOLIB_SX126X_SYNC_WORD_PRIVATE,
      mesh_config.tx_power_dbm,
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
  loadPersistentConfig();
  resetMeshIdentity();

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

  char summary[128];
  controller.formatStatus(summary, sizeof(summary));
  Serial.println(F("[MeshEcho] ESP32 controller ready"));
  Serial.println(F("[MeshEcho] commands: version | show | get config | set <field> <value> | save | send <dst> <text>"));
  Serial.println(summary);
}

void loop() {
  const std::uint32_t now_ms = millis();
  pollRadio(now_ms);
  pollSerialApp(now_ms);
  processTimeouts(now_ms);
  updateLearning(now_ms);
  maybeTransmitPeriodicFrames(now_ms);
  delay(5);
}
