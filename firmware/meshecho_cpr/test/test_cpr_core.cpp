#include <unity.h>
#include <cstdint>

#include "../include/meshecho_cpr_core.hpp"
#include "../include/meshecho_cpr_node.hpp"
#include "../include/meshecho_cpr_budget.hpp"
#include "../include/meshecho_cpr_runtime.hpp"

using namespace meshecho_cpr;

namespace {

void testControllerRejectsDuplicateLiveFlow() {
  CprController controller;
  const CprDecision first = controller.beginFlow(
      400, 1, 3, 10, 10000, nullptr, 0, 1000, 2500);
  TEST_ASSERT(first.action == CprAction::F_INITIAL);
  const CprDecision duplicate = controller.beginFlow(
      400, 1, 4, 20, 20000, nullptr, 0, 1000, 2500);
  TEST_ASSERT(duplicate.action == CprAction::DROP);
  const CprFlowRecord* original = controller.flow(400);
  TEST_ASSERT(original != nullptr && original->destination == 3);
  TEST_ASSERT(original->enqueue_at_ms == 10 && original->deadline_ms == 10000);
}

void testNodeRejectsDuplicateLiveFlow() {
  CprNode source(1);
  CprOutboundFrame first[2]{};
  CprOutboundFrame duplicate[2]{};
  const std::uint8_t payload[] = {'x'};
  TEST_ASSERT(source.sendApp(3, 401, payload, 1, 0, 10000, 1000, 2500,
                        first, 2) == 1);
  TEST_ASSERT(source.sendApp(4, 401, payload, 1, 1, 10000, 1000, 2500,
                        duplicate, 2) == 0);
}

void testNodeRejectsRouteWithAnotherSource() {
  CprNode source(1);
  Path foreign{};
  foreign.length = 3;
  foreign.nodes[0] = 4;
  foreign.nodes[1] = 2;
  foreign.nodes[2] = 3;
  TEST_ASSERT_FALSE_MESSAGE(source.installRoute(3, foreign).accepted,
                            "A route must originate at this node");
}

void testInfeasibleInitialFlowsDoNotConsumeControllerCapacity() {
  CprNode source(1);
  const std::uint8_t payload[] = {'x'};
  CprOutboundFrame out[2]{};
  for (std::uint32_t id = 1; id <= kMaxCprFlows; ++id) {
    TEST_ASSERT_EQUAL_UINT32(0, source.sendApp(3, id, payload, 1, 0, 500,
                                              1000, 2500, out, 2));
  }
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      1, source.sendApp(3, 900, payload, 1, 0, 10000, 1000, 2500, out, 2),
      "Rejected initial flows must not occupy the bounded controller");
}

void testRuntimeUsesReceivedWireLengthForAirtime() {
  CprRuntime destination(2);
  CprLoRaBudgetConfig config{};
  config.spreading_factor = 12;
  TEST_ASSERT_TRUE(destination.setAirtimeConfig(config));
  CprWireFrame data{};
  data.type = CprFrameType::Data;
  data.src = 1;
  data.dst = 2;
  data.flow_id = data.request_id = 960;
  data.ttl = 8;
  data.path.length = 2;
  data.path.nodes[0] = 1;
  data.path.nodes[1] = 2;
  data.path_index = 1;
  data.payload_len = 1;
  data.payload[0] = 'x';
  const std::uint32_t data_ms = cprFrameAirtimeMs(config, encodeCprFrame(data).size);
  TEST_ASSERT_GREATER_THAN_UINT32(0, data_ms);
  data.remaining_budget_ms = data_ms + 500U;
  const CprEncodedFrame wire = encodeCprFrame(data);
  TEST_ASSERT_EQUAL_UINT32(1, destination.receive(wire.bytes.data(), wire.size, 100));
  TEST_ASSERT_EQUAL_UINT32(0, destination.stats().rx_budget_drops);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(500, destination.peekTx()->outbound.frame.remaining_budget_ms,
                                  "RX must subtract this frame's airtime, not maximum DATA airtime");
  TEST_ASSERT_FALSE_MESSAGE(destination.prepareTx(100),
                            "The returning ACK must also fit its own actual airtime");
}

void testDeadlineInvalidatesOnlyTheRecordedRouteGeneration() {
  Path original{};
  original.length = 2;
  original.nodes[0] = 1;
  original.nodes[1] = 2;
  const std::uint8_t payload[] = {'x'};
  CprOutboundFrame out[2]{};
  CprNode source(1);
  TEST_ASSERT_TRUE(source.installRoute(2, original).accepted);
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 970, payload, 1, 0, 1000,
                                           200, 200, out, 2));
  TEST_ASSERT_TRUE(source.onTxStarted(out[0], 10));
  TEST_ASSERT_EQUAL_UINT32(0, source.poll(1000, out, 2));
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 971, payload, 1, 1001, 10000,
                                           200, 200, out, 2));
  TEST_ASSERT_TRUE_MESSAGE(out[0].frame.type == CprFrameType::Flood,
                           "An unacknowledged routed flow must quarantine its route at deadline");

  CprNode refreshed(1);
  TEST_ASSERT_TRUE(refreshed.installRoute(2, original).accepted);
  TEST_ASSERT_EQUAL_UINT32(1, refreshed.sendApp(2, 972, payload, 1, 0, 1000,
                                              200, 200, out, 2));
  TEST_ASSERT_TRUE(refreshed.onTxStarted(out[0], 10));
  Path newer{};
  newer.length = 3;
  newer.nodes[0] = 1;
  newer.nodes[1] = 3;
  newer.nodes[2] = 2;
  TEST_ASSERT_TRUE(refreshed.installRoute(2, newer).accepted);
  TEST_ASSERT_EQUAL_UINT32(0, refreshed.poll(1000, out, 2));
  TEST_ASSERT_EQUAL_UINT32(1, refreshed.sendApp(2, 973, payload, 1, 1001, 10000,
                                              200, 200, out, 2));
  TEST_ASSERT_TRUE(out[0].frame.type == CprFrameType::Data);
  TEST_ASSERT_TRUE_MESSAGE(out[0].frame.path == newer,
                           "A stale flow must not invalidate a newly installed route");
}

void testUnstartedDeadlineReleasesCapacity() {
  CprNode source(1);
  const std::uint8_t payload[] = {'x'};
  CprOutboundFrame out[2]{};
  for (std::uint32_t id = 1; id <= kMaxCprFlows; ++id) {
    TEST_ASSERT(source.sendApp(3, id, payload, 1, 0, 10000, 1000, 2500,
                          out, 2) == 1);
  }
  TEST_ASSERT(source.poll(10000, out, 2) == 0);
  TEST_ASSERT(source.sendApp(3, 100, payload, 1, 10001, 20000, 1000, 2500,
                        out, 2) == 1);
}

void testUnsolicitedRouteReplyCannotConfirmRoute() {
  CprNode source(1);
  CprWireFrame reply{};
  reply.type = CprFrameType::RouteReply;
  reply.src = 2;
  reply.dst = 1;
  reply.flow_id = reply.request_id = 600;
  reply.ttl = 8;
  reply.path.length = 3;
  reply.path.nodes[0] = 1;
  reply.path.nodes[1] = 2;
  reply.path.nodes[2] = 3;
  CprOutboundFrame out[2]{};
  TEST_ASSERT_EQUAL_UINT32(0, source.onFrame(reply, 100, out, 2));
  const std::uint8_t payload[] = {'x'};
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(3, 601, payload, 1, 200,
                                           10000, 1000, 2500, out, 2));
  TEST_ASSERT_TRUE_MESSAGE(out[0].frame.type == CprFrameType::Flood,
                          "RREP is not ACK-confirmed route evidence");
}

void testProductionRouteDataAck() {
  CprNode source(1);
  CprNode relay(2);
  CprNode destination(3);

  Path route{};
  route.length = 3;
  route.nodes[0] = 1;
  route.nodes[1] = 2;
  route.nodes[2] = 3;
  const RouteInstallResult installed = source.installRoute(3, route);
  TEST_ASSERT(installed.accepted);

  const std::uint8_t payload[] = {'o', 'k'};
  CprOutboundFrame source_out[4]{};
  TEST_ASSERT(source.sendApp(3, 100, payload, 2, 0, 10000, 1000, 2500,
                        source_out, 4) == 1);
  TEST_ASSERT(source_out[0].frame.type == CprFrameType::Data);
  TEST_ASSERT(source_out[0].frame.path == route);
  TEST_ASSERT(source_out[0].frame.path_index == 1);
  TEST_ASSERT(source.onTxStarted(source_out[0], 100));

  CprOutboundFrame relay_out[4]{};
  TEST_ASSERT(relay.onFrame(source_out[0].frame, 120, relay_out, 4) == 1);
  TEST_ASSERT(relay_out[0].frame.src == 2);
  TEST_ASSERT(relay_out[0].frame.dst == 3);
  TEST_ASSERT(relay_out[0].frame.path_index == 2);

  CprOutboundFrame destination_out[4]{};
  TEST_ASSERT(destination.onFrame(relay_out[0].frame, 140, destination_out, 4) == 1);
  TEST_ASSERT(destination_out[0].frame.type == CprFrameType::Ack);
  TEST_ASSERT(destination_out[0].frame.path == route);
  TEST_ASSERT(destination_out[0].frame.path_index == 1);

  CprOutboundFrame relay_ack_out[4]{};
  TEST_ASSERT(relay.onFrame(destination_out[0].frame, 160, relay_ack_out, 4) == 1);
  TEST_ASSERT(relay_ack_out[0].frame.path_index == 0);

  CprOutboundFrame source_ack_out[4]{};
  TEST_ASSERT(source.onFrame(relay_ack_out[0].frame, 180, source_ack_out, 4) == 0);
  TEST_ASSERT(source.flowAcked(100));

  CprDelivery delivery{};
  TEST_ASSERT(destination.pollDelivery(&delivery));
  TEST_ASSERT(delivery.flow_id == 100);
  TEST_ASSERT(delivery.payload_len == 2);
  TEST_ASSERT(delivery.payload[0] == 'o' && delivery.payload[1] == 'k');
}

void testCompletedFlowReleasesControllerSlot() {
  CprNode source(1);
  CprNode destination(2);

  Path route{};
  route.length = 2;
  route.nodes[0] = 1;
  route.nodes[1] = 2;
  TEST_ASSERT(source.installRoute(2, route).accepted);

  const std::uint8_t payload[] = {'x'};
  for (std::uint32_t flow_id = 1; flow_id <= kMaxCprFlows + 1U; ++flow_id) {
    CprOutboundFrame source_out[2]{};
    TEST_ASSERT(source.sendApp(2, flow_id, payload, 1, 0, 10000, 1000, 2500,
                          source_out, 2) == 1);
    TEST_ASSERT(source_out[0].frame.type == CprFrameType::Data);
    TEST_ASSERT(source.onTxStarted(source_out[0], 100 + flow_id));

    CprOutboundFrame destination_out[2]{};
    TEST_ASSERT(destination.onFrame(source_out[0].frame, 200 + flow_id,
                               destination_out, 2) == 1);
    TEST_ASSERT(destination_out[0].frame.type == CprFrameType::Ack);

    CprOutboundFrame source_ack_out[2]{};
    TEST_ASSERT(source.onFrame(destination_out[0].frame, 300 + flow_id,
                          source_ack_out, 2) == 0);
    TEST_ASSERT(source.flowAcked(flow_id));
    CprDelivery delivery{};
    TEST_ASSERT(destination.pollDelivery(&delivery));
    TEST_ASSERT(delivery.flow_id == flow_id);
  }
}

void testSamePathAckDoesNotInvalidateConcurrentRoutedFlow() {
  CprNode source(1);
  CprNode destination(2);
  Path route{};
  route.length = 2;
  route.nodes[0] = 1;
  route.nodes[1] = 2;
  TEST_ASSERT_TRUE(source.installRoute(2, route).accepted);
  const std::uint8_t payload[] = {'x'};
  CprOutboundFrame first[2]{}, second[2]{}, ack[2]{}, ignored[2]{};
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 950, payload, 1, 0, 10000,
                                           1000, 2500, first, 2));
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 951, payload, 1, 0, 10000,
                                           1000, 2500, second, 2));
  TEST_ASSERT_TRUE(source.onTxStarted(first[0], 100));
  TEST_ASSERT_TRUE(source.onTxStarted(second[0], 110));
  TEST_ASSERT_EQUAL_UINT32(1, destination.onFrame(first[0].frame, 200, ack, 2));
  source.onFrame(ack[0].frame, 220, ignored, 2);
  TEST_ASSERT_TRUE(source.flowAcked(950));
  TEST_ASSERT_EQUAL_UINT32(1, destination.onFrame(second[0].frame, 230, ack, 2));
  source.onFrame(ack[0].frame, 250, ignored, 2);
  TEST_ASSERT_TRUE_MESSAGE(source.flowAcked(951),
                           "An ACK for the same route must not stale a concurrent flow");
}

void testConcurrentColdFloodsCanBothReceiveTerminalAck() {
  CprNode source(1);
  CprNode destination(2);
  const std::uint8_t payload[] = {'x'};
  CprOutboundFrame first[2]{}, second[2]{}, ack[2]{}, ignored[2]{};
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 980, payload, 1, 0, 10000,
                                           1000, 2500, first, 2));
  TEST_ASSERT_EQUAL_UINT32(1, source.sendApp(2, 981, payload, 1, 0, 10000,
                                           1000, 2500, second, 2));
  TEST_ASSERT_TRUE(source.onTxStarted(first[0], 100));
  TEST_ASSERT_TRUE(source.onTxStarted(second[0], 110));
  TEST_ASSERT_EQUAL_UINT32(1, destination.onFrame(first[0].frame, 200, ack, 2));
  source.onFrame(ack[0].frame, 220, ignored, 2);
  TEST_ASSERT_TRUE(source.flowAcked(980));
  TEST_ASSERT_EQUAL_UINT32(1, destination.onFrame(second[0].frame, 230, ack, 2));
  source.onFrame(ack[0].frame, 250, ignored, 2);
  TEST_ASSERT_TRUE_MESSAGE(source.flowAcked(981),
                           "Learning a route must not reject another already-started initial flood ACK");
}

CprWireFrame makeAck(std::uint32_t flow_id,
                     std::uint32_t generation,
                     const Path& path,
                     std::uint8_t path_index) {
  CprWireFrame ack{};
  ack.type = CprFrameType::Ack;
  ack.src = path.nodes[path_index + 1U];
  ack.dst = 2;
  ack.sequence = 7;
  ack.flow_id = flow_id;
  ack.request_id = flow_id;
  ack.created_at_ms = 0;
  ack.remaining_budget_ms = 10000;
  ack.route_generation = generation;
  ack.ttl = 8;
  ack.path = path;
  ack.path_index = path_index;
  ack.repair_index = kRecoveryRepair;
  return ack;
}

void testOnPathAckDoesNotCancelRequiredRelay() {
  CprNode relay(2);
  CprWireFrame flood{};
  flood.type = CprFrameType::Flood;
  flood.src = 1;
  flood.dst = 3;
  flood.sequence = 1;
  flood.flow_id = 200;
  flood.request_id = 200;
  flood.created_at_ms = 0;
  flood.remaining_budget_ms = 10000;
  flood.route_generation = 9;
  flood.ttl = 8;
  flood.repair_index = kRecoveryRepair;
  flood.path.length = 1;
  flood.path.nodes[0] = 1;

  CprOutboundFrame ignored[4]{};
  TEST_ASSERT(relay.onFrame(flood, 100, ignored, 4) == 0);

  Path direct_ack_path{};
  direct_ack_path.length = 3;
  direct_ack_path.nodes[0] = 1;
  direct_ack_path.nodes[1] = 2;
  direct_ack_path.nodes[2] = 3;
  CprOutboundFrame wrong_generation_out[4]{};
  const CprWireFrame wrong_generation = makeAck(
      200, 10, direct_ack_path, 1);
  TEST_ASSERT(relay.onFrame(wrong_generation, 150, wrong_generation_out, 4) == 1);
  CprOutboundFrame relay_after_wrong_generation[4]{};
  TEST_ASSERT(relay.poll(201, relay_after_wrong_generation, 4) == 1);

  CprNode prefix_relay(2);
  TEST_ASSERT(prefix_relay.onFrame(flood, 100, ignored, 4) == 0);
  Path wrong_prefix{};
  wrong_prefix.length = 5;
  wrong_prefix.nodes[0] = 1;
  wrong_prefix.nodes[1] = 5;
  wrong_prefix.nodes[2] = 2;
  wrong_prefix.nodes[3] = 4;
  wrong_prefix.nodes[4] = 3;
  CprOutboundFrame wrong_prefix_out[4]{};
  const CprWireFrame wrong_prefix_ack = makeAck(
      200, 9, wrong_prefix, 2);
  TEST_ASSERT(prefix_relay.onFrame(wrong_prefix_ack, 150, wrong_prefix_out, 4) == 1);
  CprOutboundFrame relay_after_wrong_prefix[4]{};
  TEST_ASSERT(prefix_relay.poll(201, relay_after_wrong_prefix, 4) == 1);

  CprNode matching_relay(2);
  TEST_ASSERT(matching_relay.onFrame(flood, 100, ignored, 4) == 0);
  CprOutboundFrame matching_ack_out[4]{};
  const CprWireFrame matching_ack = makeAck(
      200, 9, direct_ack_path, 1);
  TEST_ASSERT(matching_relay.onFrame(matching_ack, 150, matching_ack_out, 4) == 1);
  CprOutboundFrame relay_after_match[4]{};
  TEST_ASSERT(matching_relay.poll(201, relay_after_match, 4) == 1);
}

}  // namespace

void testCompatibilityScaffoldFlowAndLedger() {
  CprCore core(1);
  const std::uint16_t route[] = {1, 2, 3};
  TEST_ASSERT(core.confirmRoute(1, 3, route, 3, 7, 0, 60000));

  FlowRequest request{};
  request.flow_id = 42;
  request.source = 1;
  request.destination = 3;
  request.enqueue_ms = 0;
  request.deadline_ms = 10000;
  request.route_bound_ms = 1000;
  request.flood_bound_ms = 2500;

  Decision decision = core.beginFlow(request);
  TEST_ASSERT(decision.action == Action::R_INITIAL);
  TEST_ASSERT(core.onTxStarted(42, Action::R_INITIAL, 100));

  decision = core.onAttemptTimeout(42, 1200);
  TEST_ASSERT(decision.action == Action::R_REPEAT);
  TEST_ASSERT(core.onTxStarted(42, Action::R_REPEAT, 1250));

  decision = core.onAttemptTimeout(42, 2400);
  TEST_ASSERT(decision.action == Action::F_RECOVERY);
  TEST_ASSERT(core.onTxStarted(42, Action::F_RECOVERY, 2450));
  TEST_ASSERT(core.onAttemptTimeout(42, 5000).action == Action::DROP);

  AckInfo ack{};
  ack.flow_id = 42;
  ack.request_id = 42;
  ack.source = 1;
  ack.destination = 3;
  ack.generation = 7;
  ack.marker = 2;
  ack.sender = 3;
  ack.path_index = 1;
  ack.path_len = 3;
  ack.path[0] = 1;
  ack.path[1] = 2;
  ack.path[2] = 3;
  TEST_ASSERT(!core.acceptAck(ack, 2600));

  PendingRelay pending{};
  pending.relay = 2;
  pending.origin = 1;
  pending.destination = 3;
  pending.flow_id = 99;
  pending.request_id = 99;
  pending.generation = 8;
  pending.marker = 2;
  pending.sender = 3;
  pending.path_len = 3;
  pending.path[0] = 3;
  pending.path[1] = 2;
  pending.path[2] = 1;
  TEST_ASSERT(core.enrollRelay(pending));

  AckInfo relay_ack{};
  relay_ack.flow_id = 99;
  relay_ack.request_id = 99;
  relay_ack.source = 1;
  relay_ack.destination = 3;
  relay_ack.generation = 8;
  relay_ack.marker = 2;
  relay_ack.sender = 3;
  relay_ack.path_index = 0;
  relay_ack.path_len = 3;
  relay_ack.path[0] = 3;
  relay_ack.path[1] = 2;
  relay_ack.path[2] = 1;
  TEST_ASSERT(core.cancelRelayForAck(2, relay_ack));

  pending.committed = true;
  TEST_ASSERT(core.enrollRelay(pending));
  TEST_ASSERT(!core.cancelRelayForAck(2, relay_ack));
}

void runCprWireTests();
void runCprRuntimeTests();
void runCprLifecycleTests();
void runCprBudgetTests();
void runCprRelayTests();
void setUp() {}
void tearDown() {}

int main() {
  UNITY_BEGIN();
  RUN_TEST(testControllerRejectsDuplicateLiveFlow);
  RUN_TEST(testNodeRejectsDuplicateLiveFlow);
  RUN_TEST(testNodeRejectsRouteWithAnotherSource);
  RUN_TEST(testInfeasibleInitialFlowsDoNotConsumeControllerCapacity);
  RUN_TEST(testRuntimeUsesReceivedWireLengthForAirtime);
  RUN_TEST(testDeadlineInvalidatesOnlyTheRecordedRouteGeneration);
  RUN_TEST(testUnstartedDeadlineReleasesCapacity);
  RUN_TEST(testUnsolicitedRouteReplyCannotConfirmRoute);
  RUN_TEST(testProductionRouteDataAck);
  RUN_TEST(testCompletedFlowReleasesControllerSlot);
  RUN_TEST(testSamePathAckDoesNotInvalidateConcurrentRoutedFlow);
  RUN_TEST(testConcurrentColdFloodsCanBothReceiveTerminalAck);
  RUN_TEST(testOnPathAckDoesNotCancelRequiredRelay);
  RUN_TEST(testCompatibilityScaffoldFlowAndLedger);
  runCprWireTests();
  runCprRuntimeTests();
  runCprLifecycleTests();
  runCprBudgetTests();
  runCprRelayTests();
  return UNITY_END();
}
