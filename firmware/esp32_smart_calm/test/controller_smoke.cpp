#include <cassert>
#include <cstring>

#include "../include/smart_calm_controller.hpp"
#include "../include/smart_calm_mesh.hpp"
#include "../include/smart_calm_prior.hpp"
#include "../include/smart_calm_wire.hpp"

using namespace smart_calm;

int main() {
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

  const std::uint8_t app_payload[] = {'p', 'i', 'n', 'g'};
  std::size_t count = node1.sendApp(3, 77, app_payload, sizeof(app_payload), 1000, 123, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rreq);
  assert(out[0].frame.dst == 3);
  RoutePayload route{};
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 1);
  assert(route.path[0] == 1);

  WireFrame rreq = out[0].frame;
  count = node2.handleFrame(rreq, 1100, -96.0f, 7.5f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rreq);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 2);
  assert(route.path[0] == 1);
  assert(route.path[1] == 2);

  rreq = out[0].frame;
  count = node3.handleFrame(rreq, 1200, -92.0f, 8.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rrep);
  assert(out[0].frame.dst == 2);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_len == 3);
  assert(route.path_index == 1);
  assert(route.path[2] == 3);

  WireFrame rrep = out[0].frame;
  count = node2.handleFrame(rrep, 1300, -91.0f, 7.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Rrep);
  assert(out[0].frame.dst == 1);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 0);

  rrep = out[0].frame;
  count = node1.handleFrame(rrep, 1400, -90.0f, 8.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Data);
  assert(out[0].frame.dst == 2);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 1);
  assert(route.app_len == sizeof(app_payload));
  assert(std::memcmp(route.app, app_payload, sizeof(app_payload)) == 0);

  WireFrame data = out[0].frame;
  count = node2.handleFrame(data, 1500, -88.0f, 9.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Data);
  assert(out[0].frame.dst == 3);
  assert(decodeRoutePayload(out[0].frame, &route));
  assert(route.path_index == 2);

  data = out[0].frame;
  count = node3.handleFrame(data, 1600, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Ack);
  assert(out[0].frame.dst == 2);
  assert(mesh_snapshot.unicast_deliveries == 1);

  WireFrame ack = out[0].frame;
  const std::uint32_t ack_created_at_ms = ack.created_at_ms;
  count = node2.handleFrame(ack, 1700, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 1);
  assert(out[0].frame.type == FrameType::Ack);
  assert(out[0].frame.dst == 1);
  assert(out[0].frame.created_at_ms == ack_created_at_ms);

  ack = out[0].frame;
  count = node1.handleFrame(ack, 1800, -85.0f, 10.0f, mesh_controller, mesh_snapshot, out, 2);
  assert(count == 0);
  assert(mesh_snapshot.unicast_acks == 1);
  assert(mesh_snapshot.delivery_delay_samples == 1);
  assert(mesh_snapshot.delivery_delay_total_s > 0.0f);

  char summary[128];
  controller.formatStatus(summary, sizeof(summary));
  assert(std::strstr(summary, "profile=") != nullptr);
  assert(std::strstr(summary, "overflow=") != nullptr);

  return 0;
}
