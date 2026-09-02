#include <cassert>
#include <cstring>

#include "../include/meshecho_config.hpp"
#include "../include/smart_calm_controller.hpp"
#include "../include/smart_calm_mesh.hpp"
#include "../include/smart_calm_prior.hpp"
#include "../include/smart_calm_wire.hpp"

using namespace smart_calm;

int main() {
  MeshEchoConfig config = makeDefaultMeshEchoConfig(1, 915.0f, 125.0f, 9, 7, 17, false);
  MeshEchoRuntimeInfo runtime{};
  runtime.target = "esp32dev_sx1262";
  runtime.chip = "ESP32";
  runtime.radio = "SX1262";
  runtime.uptime_ms = 42;
  char config_response[1024]{};

  MeshEchoConfigCommandResult command =
      handleMeshEchoConfigCommand("version", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(command.ok);
  assert(std::strstr(config_response, "\"version\":\"meshecho-firmware-v2.1.2\"") != nullptr);
  assert(std::strstr(config_response, "\"target\":\"esp32dev_sx1262\"") != nullptr);

  command = handleMeshEchoConfigCommand("get config", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(command.ok);
  assert(std::strstr(config_response, "\"node_id\":1") != nullptr);
  assert(std::strstr(config_response, "\"freq_mhz\":915.000") != nullptr);

  runtime.tx_count = 12;
  runtime.rx_success = 9;
  runtime.rx_fail = 1;
  runtime.unicast_deliveries = 4;
  runtime.unicast_acks = 3;
  runtime.delivery_delay_total_s = 3.0f;
  runtime.delivery_delay_samples = 3;
  runtime.policy_update_count = 2;
  command = handleMeshEchoConfigCommand("show", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(command.ok);
  assert(std::strstr(config_response, "\"rx_success\":9") != nullptr);
  assert(std::strstr(config_response, "\"unicast_acks\":3") != nullptr);
  assert(std::strstr(config_response, "\"avg_ack_delay_s\":1.000") != nullptr);
  assert(std::strstr(config_response, "\"policy_update_count\":2") != nullptr);

  command = handleMeshEchoConfigCommand("set node_id 12", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(command.ok);
  assert(command.node_id_changed);
  assert(config.node_id == 12);
  assert(std::strstr(config_response, "\"field\":\"node_id\"") != nullptr);

  command = handleMeshEchoConfigCommand("set callsign BH4ME", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(command.ok);
  assert(std::strcmp(config.callsign, "BH4ME") == 0);

  command = handleMeshEchoConfigCommand("set sf 13", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(!command.ok);
  assert(config.sf == 9);

  command = handleMeshEchoConfigCommand("send 2 hello", config, runtime, config_response, sizeof(config_response));
  assert(!command.handled);

  command = handleMeshEchoConfigCommand("unknown", config, runtime, config_response, sizeof(config_response));
  assert(command.handled);
  assert(!command.ok);
  assert(std::strstr(config_response, "unknown command") != nullptr);

  SmartCalmController controller;
  controller.loadPrior(kSmartCalmPrior);

  Snapshot snapshot{};
  snapshot.unicast_flows = 10;
  snapshot.unicast_deliveries = 9;
  snapshot.unicast_acks = 9;
  snapshot.route_cache_hits = 8;
  snapshot.route_cache_misses = 2;
  snapshot.collision_fail = 5;
  snapshot.tx_count = 100;
  assert(controller.stateIndexFromSnapshot(snapshot) == 4);

  Snapshot low{};
  low.unicast_flows = 10;
  low.unicast_deliveries = 2;
  low.unicast_acks = 2;
  low.route_cache_hits = 1;
  low.route_cache_misses = 6;
  low.collision_fail = 20;
  low.tx_count = 10;
  assert(controller.stateIndexFromSnapshot(low) == 0);

  const std::uint8_t action = controller.beginFlow(42, low, 7, 1234);
  assert(action < kActionCount);

  SmartCalmController overflow_controller;
  for (std::size_t i = 0; i < kMaxTrackedFlows; ++i) {
    overflow_controller.beginFlow(1000 + static_cast<std::uint32_t>(i), low, 7, 2000 + static_cast<std::uint32_t>(i));
  }
  assert(overflow_controller.decisionOverflowCount() == 0);
  overflow_controller.beginFlow(9000, low, 7, 3000);
  assert(overflow_controller.decisionOverflowCount() == 1);

  WireFrame frame{};
  frame.type = FrameType::Data;
  frame.src = 1;
  frame.dst = 2;
  frame.seq = 9;
  frame.flow_id = 42;
  frame.created_at_ms = 99;
  frame.ttl = 7;
  frame.state_index = 3;
  frame.action_index = 1;
  frame.confidence_milli = 881;
  std::strncpy(frame.payload, "hello", sizeof(frame.payload));
  frame.payload_len = 5;
  const auto bytes = encodeWireFrame(frame);
  WireFrame decoded{};
  assert(bytes.size == kWirePrefixSize + frame.payload_len + kWireCrcSize);
  assert(decodeWireFrame(bytes.bytes.data(), bytes.size, &decoded));
  assert(decoded.type == FrameType::Data);
  assert(decoded.src == 1);
  assert(decoded.dst == 2);
  assert(decoded.seq == 9);
  assert(decoded.flow_id == 42);
  assert(decoded.confidence_milli == 881);
  assert(decoded.payload_len == 5);
  assert(std::memcmp(decoded.payload, "hello", 5) == 0);

  auto corrupted = bytes;
  corrupted.bytes[5] ^= 0x01;
  assert(!decodeWireFrame(corrupted.bytes.data(), corrupted.size, &decoded));
  assert(!decodeWireFrame(bytes.bytes.data(), kWireMinFrameSize - 1, &decoded));

  WireFrame long_payload{};
  long_payload.type = FrameType::Status;
  long_payload.payload_len = 255;
  std::memset(long_payload.payload, 'x', sizeof(long_payload.payload));
  const auto clamped = encodeWireFrame(long_payload);
  assert(clamped.size == kWireMaxFrameSize);
  assert(decodeWireFrame(clamped.bytes.data(), clamped.size, &decoded));
  assert(decoded.payload_len == kWirePayloadSize);

  SmartCalmMesh node1(1);
  SmartCalmMesh node2(2);
  SmartCalmMesh node3(3);
  SmartCalmController mesh_controller;
  Snapshot mesh_snapshot{};
  OutboundFrame out[kMaxOutboundFrames]{};
  MeshRuntimeLimits limits{};

  const std::uint8_t app_payload[] = {'p', 'i', 'n', 'g'};
  std::size_t count = node1.sendApp(limits, 3, 77, app_payload, sizeof(app_payload), 1000, 123, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rreq);
  assert(out[0].frame.dst == 3);
  RoutePayload route{};
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 1);
  assert(route.path[0] == 1);

  WireFrame rreq = out[0].frame;
  count = node2.handleFrame(limits, rreq, 1100, -96.0f, 7.5f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rreq);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 2);
  assert(route.path[0] == 1);
  assert(route.path[1] == 2);

  rreq = out[0].frame;
  count = node3.handleFrame(limits, rreq, 1200, -92.0f, 8.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rrep);
  assert(out[0].frame.dst == 2);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 3);
  assert(route.path_index == 1);
  assert(route.path[2] == 3);

  WireFrame rrep = out[0].frame;
  count = node2.handleFrame(limits, rrep, 1300, -91.0f, 7.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rrep);
  assert(out[0].frame.dst == 1);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 0);

  rrep = out[0].frame;
  count = node1.handleFrame(limits, rrep, 1400, -90.0f, 8.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Data);
  assert(out[0].frame.dst == 2);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 1);
  assert(route.app_len == sizeof(app_payload));
  assert(std::memcmp(route.app, app_payload, sizeof(app_payload)) == 0);

  WireFrame data = out[0].frame;
  count = node2.handleFrame(limits, data, 1500, -88.0f, 9.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Data);
  assert(out[0].frame.dst == 3);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 2);

  data = out[0].frame;
  count = node3.handleFrame(limits, data, 1600, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Ack);
  assert(out[0].frame.dst == 2);
  assert(mesh_snapshot.unicast_deliveries == 1);

  WireFrame ack = out[0].frame;
  const std::uint32_t ack_created_at_ms = ack.created_at_ms;
  count = node2.handleFrame(limits, ack, 1700, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Ack);
  assert(out[0].frame.dst == 1);
  assert(out[0].frame.created_at_ms == ack_created_at_ms);

  ack = out[0].frame;
  count = node1.handleFrame(limits, ack, 1800, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 0);
  assert(mesh_snapshot.unicast_acks == 1);
  assert(mesh_snapshot.delivery_delay_samples == 1);
  assert(mesh_snapshot.delivery_delay_total_s > 0.0f);
  assert(node1.pendingFlowCount() == 0);
  count = node1.tick(limits, 4000, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 0);

  SmartCalmMesh fallback_source(10);
  SmartCalmMesh fallback_relay(11);
  SmartCalmMesh fallback_destination(12);
  SmartCalmController fallback_source_controller;
  SmartCalmController fallback_relay_controller;
  SmartCalmController fallback_destination_controller;
  Snapshot fallback_source_snapshot{};
  Snapshot fallback_relay_snapshot{};
  Snapshot fallback_destination_snapshot{};
  MeshRuntimeLimits fallback_limits{};
  fallback_limits.ack_timeout_ms = 1000;
  fallback_limits.max_timeout_retries = 1;
  fallback_limits.fallback_ttl = 2;
  const std::uint8_t fallback_payload[] = {'o', 'k'};

  count = fallback_source.sendApp(
      fallback_limits,
      12,
      88,
      fallback_payload,
      sizeof(fallback_payload),
      1000,
      17,
      fallback_source_controller,
      fallback_source_snapshot,
      out,
      2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rreq);

  count = fallback_source.tick(
      fallback_limits, 2100, fallback_source_controller, fallback_source_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Fallback);
  WireFrame fallback = out[0].frame;

  count = fallback_relay.handleFrame(
      fallback_limits,
      fallback,
      2200,
      -90.0f,
      8.0f,
      fallback_relay_controller,
      fallback_relay_snapshot,
      out,
      2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Fallback);
  assert(fallback_relay.neighborCount() == 1);
  fallback = out[0].frame;

  count = fallback_destination.handleFrame(
      fallback_limits,
      fallback,
      2300,
      -88.0f,
      9.0f,
      fallback_destination_controller,
      fallback_destination_snapshot,
      out,
      2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Ack);
  assert(out[0].frame.dst == 11);
  assert(fallback_destination_snapshot.unicast_deliveries == 1);
  assert(fallback_destination_snapshot.fallback_delivery_count == 1);

  WireFrame fallback_ack = out[0].frame;
  count = fallback_relay.handleFrame(
      fallback_limits,
      fallback_ack,
      2400,
      -88.0f,
      9.0f,
      fallback_relay_controller,
      fallback_relay_snapshot,
      out,
      2);
  assert(count == 1);
  fallback_ack = out[0].frame;
  count = fallback_source.handleFrame(
      fallback_limits,
      fallback_ack,
      2500,
      -88.0f,
      9.0f,
      fallback_source_controller,
      fallback_source_snapshot,
      out,
      2);
  assert(count == 0);
  assert(fallback_source_snapshot.unicast_acks == 1);
  assert(fallback_source.pendingFlowCount() == 0);

  char summary[128];
  controller.formatStatus(summary, sizeof(summary));
  assert(std::strstr(summary, "profile=") != nullptr);
  assert(std::strstr(summary, "overflow=") != nullptr);

  return 0;
}
