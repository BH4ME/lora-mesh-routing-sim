#include <unity.h>

#include "meshecho_cpr_node.hpp"

using namespace meshecho_cpr;

namespace {

CprWireFrame relayFlood(std::uint32_t flow_id) {
  CprWireFrame frame{};
  frame.type = CprFrameType::Flood;
  frame.src = 1U;
  frame.dst = 9U;
  frame.flow_id = flow_id;
  frame.request_id = flow_id;
  frame.remaining_budget_ms = 10000U;
  frame.route_generation = 7U;
  frame.ttl = static_cast<std::uint8_t>(kMaxPathNodes);
  frame.repair_index = kRecoveryRepair;
  frame.path.length = 1U;
  frame.path.nodes[0] = 1U;
  frame.payload_len = 1U;
  frame.payload[0] = 'x';
  return frame;
}

CprWireFrame offPathAck(std::uint32_t flow_id) {
  CprWireFrame frame{};
  frame.type = CprFrameType::Ack;
  frame.src = 3U;
  frame.dst = 1U;
  frame.flow_id = flow_id;
  frame.request_id = flow_id;
  frame.remaining_budget_ms = 9000U;
  frame.route_generation = 7U;
  frame.ttl = static_cast<std::uint8_t>(kMaxPathNodes);
  frame.repair_index = kRecoveryRepair;
  frame.path.length = 3U;
  frame.path.nodes[0] = 1U;
  frame.path.nodes[1] = 3U;
  frame.path.nodes[2] = 9U;
  return frame;
}

void testRelayCanceledHandleCannotActOnReusedSlot() {
  CprNode relay(2U);
  CprOutboundFrame offered[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(100U), 0U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(100U, offered, 1U));
  const CprOutboundFrame canceled = offered[0];
  TEST_ASSERT_TRUE(relay.canTransmit(canceled, 100U));

  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(offPathAck(100U), 110U, offered, 1U));
  TEST_ASSERT_FALSE(relay.canTransmit(canceled, 110U));
  TEST_ASSERT_EQUAL_UINT32(0U, relay.poll(111U, offered, 1U));

  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(101U), 120U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(220U, offered, 1U));
  const CprOutboundFrame replacement = offered[0];
  TEST_ASSERT_TRUE(relay.canTransmit(replacement, 220U));
  TEST_ASSERT_FALSE_MESSAGE(
      relay.canTransmit(canceled, 220U),
      "A canceled relay handle must stay invalid after its slot is reused");
  TEST_ASSERT_FALSE(relay.onTxStarted(canceled, 220U));
  TEST_ASSERT_TRUE(relay.canTransmit(replacement, 220U));
  relay.onTxDiscarded(canceled);
  TEST_ASSERT_TRUE_MESSAGE(
      relay.canTransmit(replacement, 220U),
      "Discarding an old handle must not cancel the replacement relay");
}

void testRelayCommittedTransmissionCannotBeCanceledByAck() {
  CprNode relay(2U);
  CprOutboundFrame offered[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(102U), 0U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(100U, offered, 1U));
  const CprOutboundFrame committed = offered[0];
  TEST_ASSERT_TRUE(relay.onTxStarted(committed, 100U));
  TEST_ASSERT_NOT_NULL(committed.pending);
  TEST_ASSERT_TRUE(committed.pending->committed);

  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(offPathAck(102U), 110U, offered, 1U));
  TEST_ASSERT_TRUE(committed.pending->committed);
  TEST_ASSERT_FALSE_MESSAGE(
      committed.pending->canceled,
      "An ACK may suppress a pending relay but cannot undo a physical TX start");
  TEST_ASSERT_FALSE(relay.canTransmit(committed, 110U));
  TEST_ASSERT_EQUAL_UINT32(0U, relay.poll(111U, offered, 1U));
}

void testRelayWrongEpochAckCannotCancelPendingTransmission() {
  CprNode relay(2U);
  CprOutboundFrame offered[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(103U), 0U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(100U, offered, 1U));
  const CprOutboundFrame pending = offered[0];
  CprWireFrame wrong = offPathAck(103U);
  wrong.route_generation = 8U;
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(wrong, 110U, offered, 1U));
  TEST_ASSERT_TRUE_MESSAGE(relay.canTransmit(pending, 110U),
                           "A different route epoch must not suppress this relay");
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(offPathAck(103U), 120U, offered, 1U));
  TEST_ASSERT_FALSE(relay.canTransmit(pending, 120U));
}

void testRelayWrongRepairMarkerAckCannotCancelPendingTransmission() {
  CprNode relay(2U);
  CprOutboundFrame offered[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(104U), 0U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(100U, offered, 1U));
  const CprOutboundFrame pending = offered[0];
  CprWireFrame wrong = offPathAck(104U);
  wrong.repair_index = kRepeatRepair;
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(wrong, 110U, offered, 1U));
  TEST_ASSERT_TRUE_MESSAGE(relay.canTransmit(pending, 110U),
                           "An ACK for another repair attempt must not suppress this relay");
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(offPathAck(104U), 120U, offered, 1U));
  TEST_ASSERT_FALSE(relay.canTransmit(pending, 120U));
}

void testRelayWrongEndpointAckCannotCancelPendingTransmission() {
  CprNode relay(2U);
  CprOutboundFrame offered[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(105U), 0U, offered, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(100U, offered, 1U));
  const CprOutboundFrame pending = offered[0];
  CprWireFrame wrong = offPathAck(105U);
  wrong.path.nodes[wrong.path.length - 1U] = 8U;
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(wrong, 110U, offered, 1U));
  TEST_ASSERT_TRUE_MESSAGE(relay.canTransmit(pending, 110U),
                           "An ACK from another destination must not suppress this relay");
  wrong = offPathAck(105U);
  wrong.path.nodes[0] = 4U;
  wrong.dst = 4U;
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(wrong, 115U, offered, 1U));
  TEST_ASSERT_TRUE_MESSAGE(relay.canTransmit(pending, 115U),
                           "An ACK to another source must not suppress this relay");
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(offPathAck(105U), 120U, offered, 1U));
  TEST_ASSERT_FALSE(relay.canTransmit(pending, 120U));
}

void testRelayPoolOverflowDoesNotDisturbExistingHandles() {
  CprNode relay(2U);
  CprOutboundFrame offered[kMaxCprRelaySlots]{};
  for (std::size_t i = 0U; i < kMaxCprRelaySlots; ++i) {
    TEST_ASSERT_EQUAL_UINT32(
        0U, relay.onFrame(relayFlood(static_cast<std::uint32_t>(200U + i)),
                          0U, offered, kMaxCprRelaySlots));
  }
  TEST_ASSERT_EQUAL_UINT32(kMaxCprRelaySlots,
                          relay.poll(100U, offered, kMaxCprRelaySlots));
  CprOutboundFrame unused[1]{};
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(300U), 110U, unused, 1U));
  TEST_ASSERT_EQUAL_UINT32(0U, relay.poll(210U, unused, 1U));
  for (std::size_t i = 0U; i < kMaxCprRelaySlots; ++i) {
    TEST_ASSERT_EQUAL_UINT32(200U + i, offered[i].frame.flow_id);
    TEST_ASSERT_TRUE_MESSAGE(
        relay.canTransmit(offered[i], 210U),
        "Dropping a ninth relay must not cancel any of the eight admitted relays");
    TEST_ASSERT_TRUE(relay.onTxStarted(offered[i], 210U));
  }
  TEST_ASSERT_EQUAL_UINT32(0U, relay.poll(211U, unused, 1U));
  TEST_ASSERT_EQUAL_UINT32(0U, relay.onFrame(relayFlood(301U), 220U, unused, 1U));
  TEST_ASSERT_EQUAL_UINT32(1U, relay.poll(320U, unused, 1U));
  TEST_ASSERT_EQUAL_UINT32(301U, unused[0].frame.flow_id);
  TEST_ASSERT_TRUE(relay.canTransmit(unused[0], 320U));
}

}  // namespace

void runCprRelayTests() {
  RUN_TEST(testRelayCanceledHandleCannotActOnReusedSlot);
  RUN_TEST(testRelayCommittedTransmissionCannotBeCanceledByAck);
  RUN_TEST(testRelayWrongEpochAckCannotCancelPendingTransmission);
  RUN_TEST(testRelayWrongRepairMarkerAckCannotCancelPendingTransmission);
  RUN_TEST(testRelayWrongEndpointAckCannotCancelPendingTransmission);
  RUN_TEST(testRelayPoolOverflowDoesNotDisturbExistingHandles);
}
