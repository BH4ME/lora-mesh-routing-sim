#include <cstddef>
#include <cstdint>

#include <unity.h>

#include "meshecho_cpr_runtime.hpp"

using namespace meshecho_cpr;

namespace {

CprRuntimeTx startOldestTx(CprRuntime& runtime, std::uint32_t now_ms) {
  TEST_ASSERT_TRUE(runtime.prepareTx(now_ms));
  const CprRuntimeTx* pending = runtime.peekTx();
  TEST_ASSERT_NOT_NULL(pending);
  TEST_ASSERT_TRUE(runtime.txDue(now_ms));
  const CprRuntimeTx started = *pending;
  TEST_ASSERT_TRUE(runtime.onTxStarted(now_ms));
  return started;
}

CprWireFrame decodeStartedTx(const CprRuntimeTx& tx) {
  CprWireFrame frame{};
  TEST_ASSERT_TRUE(decodeCprFrame(tx.encoded.bytes.data(), tx.encoded.size,
                                &frame));
  return frame;
}

void receiveStartedTx(CprRuntime& receiver, const CprRuntimeTx& tx,
                      std::uint32_t now_ms) {
  receiver.receive(tx.encoded.bytes.data(), tx.encoded.size, now_ms);
  TEST_ASSERT_EQUAL_UINT32(0, receiver.stats().rx_decode_errors);
}

void testRuntimeColdFloodAckLearnsNextRoutedFlow() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime destination(3);
  const std::uint8_t payload[] = {'c', 'o', 'l', 'd'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 100, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  TEST_ASSERT_NOT_NULL(source.peekTx());
  TEST_ASSERT_EQUAL_UINT8_MESSAGE(
      static_cast<std::uint8_t>(CprFrameType::Flood),
      static_cast<std::uint8_t>(source.peekTx()->outbound.frame.type),
      "A cold CPR source must send initial DATA flood, not discovery");

  const CprRuntimeTx initial = startOldestTx(source, 100);
  const CprWireFrame initial_frame = decodeStartedTx(initial);
  TEST_ASSERT_EQUAL_UINT8(kInitialRepair, initial_frame.repair_index);
  TEST_ASSERT_EQUAL_UINT32(0, initial_frame.route_generation);
  TEST_ASSERT_FALSE(source.node().flowAcked(100));

  receiveStartedTx(relay, initial, 120);
  TEST_ASSERT_EQUAL_UINT32(0, relay.txCount());
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(230));
  const CprRuntimeTx forwarded = startOldestTx(relay, 230);
  receiveStartedTx(destination, forwarded, 250);

  CprDelivery delivery{};
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT16(1, delivery.source);
  TEST_ASSERT_EQUAL_UINT16(3, delivery.destination);
  TEST_ASSERT_EQUAL_UINT32(100, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));
  TEST_ASSERT_FALSE(destination.pollDelivery(&delivery));

  const CprRuntimeTx destination_ack = startOldestTx(destination, 260);
  TEST_ASSERT_EQUAL_UINT8(
      static_cast<std::uint8_t>(CprFrameType::Ack),
      static_cast<std::uint8_t>(decodeStartedTx(destination_ack).type));
  receiveStartedTx(relay, destination_ack, 280);
  const CprRuntimeTx reverse_ack = startOldestTx(relay, 300);
  const CprWireFrame ack_frame = decodeStartedTx(reverse_ack);
  TEST_ASSERT_EQUAL_UINT16(2, ack_frame.src);
  TEST_ASSERT_EQUAL_UINT8(0, ack_frame.path_index);
  receiveStartedTx(source, reverse_ack, 320);
  TEST_ASSERT_TRUE(source.node().flowAcked(100));
  TEST_ASSERT_EQUAL_UINT32(0, source.txCount());

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 101, payload, sizeof(payload), 400, 10400, 1000,
                        2500));
  const CprRuntimeTx next = startOldestTx(source, 410);
  const CprWireFrame next_frame = decodeStartedTx(next);
  TEST_ASSERT_EQUAL_UINT8_MESSAGE(
      static_cast<std::uint8_t>(CprFrameType::Data),
      static_cast<std::uint8_t>(next_frame.type),
      "Only the received valid ACK should establish a reusable route");
  TEST_ASSERT_EQUAL_UINT16(2, next_frame.dst);
  TEST_ASSERT_EQUAL_UINT8(3, next_frame.path.length);
  TEST_ASSERT_EQUAL_UINT16(1, next_frame.path.nodes[0]);
  TEST_ASSERT_EQUAL_UINT16(2, next_frame.path.nodes[1]);
  TEST_ASSERT_EQUAL_UINT16(3, next_frame.path.nodes[2]);
  TEST_ASSERT_GREATER_THAN_UINT32(0, next_frame.route_generation);
  TEST_ASSERT_EQUAL_UINT32(101, next_frame.flow_id);
  TEST_ASSERT_EQUAL_UINT8(kInitialRepair, next_frame.repair_index);
}

void testRuntimeRejectsSerializedAckFromWrongSender() {
  CprRuntime source(1);
  CprRuntime destination(3);
  const std::uint8_t payload[] = {'a', 'c', 'k'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 200, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  const CprRuntimeTx initial = startOldestTx(source, 100);
  receiveStartedTx(destination, initial, 120);
  const CprRuntimeTx valid_ack = startOldestTx(destination, 140);
  CprWireFrame wrong_sender_ack = decodeStartedTx(valid_ack);
  TEST_ASSERT_EQUAL_UINT16(3, wrong_sender_ack.src);
  TEST_ASSERT_EQUAL_UINT16(3, wrong_sender_ack.path.nodes[1]);
  wrong_sender_ack.src = 4;
  const CprEncodedFrame encoded = encodeCprFrame(wrong_sender_ack);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);

  source.receive(encoded.bytes.data(), encoded.size, 160);
  TEST_ASSERT_EQUAL_UINT32(0, source.stats().rx_decode_errors);
  TEST_ASSERT_FALSE_MESSAGE(
      source.node().flowAcked(200),
      "A CRC-valid ACK whose wire sender differs from the reverse hop must be rejected");

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 201, payload, sizeof(payload), 170, 10170, 1000,
                        2500));
  const CprRuntimeTx unproven = startOldestTx(source, 180);
  TEST_ASSERT_EQUAL_UINT8(
      static_cast<std::uint8_t>(CprFrameType::Flood),
      static_cast<std::uint8_t>(decodeStartedTx(unproven).type));

  receiveStartedTx(source, valid_ack, 200);
  TEST_ASSERT_TRUE(source.node().flowAcked(200));
  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 202, payload, sizeof(payload), 210, 10210, 1000,
                        2500));
  const CprRuntimeTx proven = startOldestTx(source, 220);
  TEST_ASSERT_EQUAL_UINT8(
      static_cast<std::uint8_t>(CprFrameType::Data),
      static_cast<std::uint8_t>(decodeStartedTx(proven).type));
}

void testRuntimePreflightRejectsInfeasibleInitialFloodAndReleasesCapacity() {
  CprRuntime source(1);
  const std::uint8_t payload[] = {'l', 'a', 't', 'e'};

  for (std::uint32_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_EQUAL_UINT32(
        1, source.sendApp(3, 300U + i, payload, sizeof(payload), 0, 4000,
                          1000, 2500));
  }
  TEST_ASSERT_EQUAL_UINT32(kMaxCprFlows, source.txCount());

  // The absolute deadline has not passed, but a full flood cannot fit now.
  for (std::size_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_FALSE_MESSAGE(
        source.prepareTx(1501),
        "An initial flood must be rejected before air start when its full bound no longer fits");
  }
  TEST_ASSERT_NULL(source.peekTx());
  TEST_ASSERT_EQUAL_UINT32(0, source.txCount());
  TEST_ASSERT_EQUAL_UINT32(0, source.stats().tx_started);

  for (std::uint32_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(
        1, source.sendApp(3, 400U + i, payload, sizeof(payload), 1501, 9000,
                          1000, 2500),
        "Rejected unstarted floods must release application and controller capacity");
  }
  TEST_ASSERT_EQUAL_UINT32(kMaxCprFlows, source.txCount());
}

void testRuntimeDiscardUnstartedFloodReleasesCapacity() {
  CprRuntime source(1);
  const std::uint8_t payload[] = {'d', 'r', 'o', 'p'};

  for (std::uint32_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_EQUAL_UINT32(
        1, source.sendApp(3, 500U + i, payload, sizeof(payload), 0, 10000,
                          1000, 2500));
  }
  for (std::size_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_TRUE(source.discardTx());
  }
  TEST_ASSERT_FALSE(source.discardTx());
  TEST_ASSERT_EQUAL_UINT32(0, source.txCount());
  TEST_ASSERT_EQUAL_UINT32(0, source.stats().tx_started);

  for (std::uint32_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(
        1, source.sendApp(3, 600U + i, payload, sizeof(payload), 100, 10100,
                          1000, 2500),
        "Discarding an unstarted source frame must release both bounded flow slots");
  }
  TEST_ASSERT_EQUAL_UINT32(kMaxCprFlows, source.txCount());
}

void testRuntimeOverheardAckCancelsOffPathPendingFlood() {
  CprRuntime source(1);
  CprRuntime relay(2);
  const std::uint8_t payload[] = {'o', 'f', 'f'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 700, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  const CprRuntimeTx initial = startOldestTx(source, 100);
  receiveStartedTx(relay, initial, 120);
  TEST_ASSERT_EQUAL_UINT32(0, relay.txCount());

  CprWireFrame terminal_ack = decodeStartedTx(initial);
  terminal_ack.type = CprFrameType::Ack;
  terminal_ack.src = 3;
  terminal_ack.dst = 4;
  terminal_ack.path.length = 3;
  terminal_ack.path.nodes[0] = 1;
  terminal_ack.path.nodes[1] = 4;
  terminal_ack.path.nodes[2] = 3;
  terminal_ack.path_index = 1;
  terminal_ack.payload_len = 0;
  const CprEncodedFrame encoded_ack = encodeCprFrame(terminal_ack);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded_ack.size);

  TEST_ASSERT_EQUAL_UINT32(
      0, relay.receive(encoded_ack.bytes.data(), encoded_ack.size, 150));
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().rx_decode_errors);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.poll(230),
      "An overheard matching terminal ACK must cancel an uncommitted off-path flood relay");
  TEST_ASSERT_NULL(relay.peekTx());
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().tx_started);
}

void testRuntimeBudgetCountsDownAcrossUnsynchronizedRelayClocks() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime shifted_relay(2);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  shifted_relay.setPacketAirtimeMs(10);
  const std::uint8_t payload[] = {'c', 'l', 'k'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 800, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  TEST_ASSERT_TRUE(source.prepareTx(100));
  const CprRuntimeTx initial = startOldestTx(source, 100);
  const CprWireFrame initial_frame = decodeStartedTx(initial);
  TEST_ASSERT_EQUAL_UINT32(9900, initial_frame.remaining_budget_ms);

  receiveStartedTx(relay, initial, 110);
  receiveStartedTx(shifted_relay, initial, 1000110);
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(220));
  TEST_ASSERT_EQUAL_UINT32(1, shifted_relay.poll(1000220));
  TEST_ASSERT_TRUE(relay.prepareTx(310));
  TEST_ASSERT_TRUE(shifted_relay.prepareTx(1000310));

  const CprWireFrame forwarded = decodeStartedTx(startOldestTx(relay, 310));
  const CprWireFrame shifted_forwarded =
      decodeStartedTx(startOldestTx(shifted_relay, 1000310));
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      9690, forwarded.remaining_budget_ms,
      "Forwarded wire budget must subtract RX airtime and all local relay residence");
  TEST_ASSERT_EQUAL_UINT32(forwarded.remaining_budget_ms,
                           shifted_forwarded.remaining_budget_ms);
  TEST_ASSERT_EQUAL_UINT32(initial_frame.created_at_ms,
                           shifted_forwarded.created_at_ms);
  TEST_ASSERT_TRUE(forwarded.path == shifted_forwarded.path);
  TEST_ASSERT_EQUAL_UINT8(2, forwarded.path.length);
  TEST_ASSERT_EQUAL_UINT16(1, forwarded.path.nodes[0]);
  TEST_ASSERT_EQUAL_UINT16(2, forwarded.path.nodes[1]);
}

void testRuntimeRoutedRepeatRecoveryAckUsesPerFlowBudgetAndGeneration() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime destination(3);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  destination.setPacketAirtimeMs(10);
  const std::uint8_t payload[] = {'r', 'e', 's', 'c', 'u', 'e'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 900, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  const CprRuntimeTx warmup = startOldestTx(source, 10);
  receiveStartedTx(relay, warmup, 20);
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(120));
  receiveStartedTx(destination, startOldestTx(relay, 120), 130);
  CprDelivery delivery{};
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(900, delivery.flow_id);
  receiveStartedTx(relay, startOldestTx(destination, 140), 150);
  receiveStartedTx(source, startOldestTx(relay, 160), 170);
  TEST_ASSERT_TRUE(source.node().flowAcked(900));

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 901, payload, sizeof(payload), 200, 12000, 1000,
                        2500));
  const CprWireFrame initial = decodeStartedTx(startOldestTx(source, 210));
  TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(CprFrameType::Data),
                          static_cast<std::uint8_t>(initial.type));
  TEST_ASSERT_EQUAL_UINT8(kInitialRepair, initial.repair_index);
  TEST_ASSERT_GREATER_THAN_UINT32(0, initial.route_generation);

  // Drop the routed attempts to exercise recovery over the real wire path.
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, source.poll(710),
      "A routed attempt must wait its full per-flow route bound before a repeat");
  TEST_ASSERT_EQUAL_UINT32(0, source.poll(1209));
  TEST_ASSERT_EQUAL_UINT32(1, source.poll(1210));
  TEST_ASSERT_EQUAL_UINT32(0, source.poll(1250));
  const CprWireFrame repeat = decodeStartedTx(startOldestTx(source, 1300));
  TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(CprFrameType::Data),
                          static_cast<std::uint8_t>(repeat.type));
  TEST_ASSERT_EQUAL_UINT8(kRepeatRepair, repeat.repair_index);
  TEST_ASSERT_EQUAL_UINT32(initial.route_generation, repeat.route_generation);
  TEST_ASSERT_TRUE(initial.path == repeat.path);

  TEST_ASSERT_EQUAL_UINT32(0, source.poll(1800));
  TEST_ASSERT_EQUAL_UINT32(0, source.poll(2299));
  TEST_ASSERT_EQUAL_UINT32(1, source.poll(2300));
  const CprRuntimeTx recovery = startOldestTx(source, 2310);
  const CprWireFrame recovery_frame = decodeStartedTx(recovery);
  TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(CprFrameType::Flood),
                          static_cast<std::uint8_t>(recovery_frame.type));
  TEST_ASSERT_EQUAL_UINT8(kRecoveryRepair, recovery_frame.repair_index);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      initial.route_generation, recovery_frame.route_generation,
      "Recovery flood and its reverse ACK must retain the confirmed nonzero route epoch");

  receiveStartedTx(relay, recovery, 2320);
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(2420));
  receiveStartedTx(destination, startOldestTx(relay, 2420), 2430);
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(901, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT8(kRecoveryRepair, delivery.repair_index);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));
  TEST_ASSERT_FALSE(destination.pollDelivery(&delivery));

  const CprRuntimeTx destination_ack = startOldestTx(destination, 2440);
  const CprWireFrame ack_frame = decodeStartedTx(destination_ack);
  TEST_ASSERT_EQUAL_UINT8(kRecoveryRepair, ack_frame.repair_index);
  TEST_ASSERT_EQUAL_UINT32(initial.route_generation, ack_frame.route_generation);
  receiveStartedTx(relay, destination_ack, 2450);
  receiveStartedTx(source, startOldestTx(relay, 2460), 2470);
  TEST_ASSERT_TRUE(source.node().flowAcked(901));
  TEST_ASSERT_EQUAL_UINT32(0, source.poll(4000));
  TEST_ASSERT_NULL(source.peekTx());
  TEST_ASSERT_EQUAL_UINT32(4, source.stats().tx_started);
}

void testRuntimeSevenHopFloodAndRoutedDataReceiveReverseAck() {
  CprRuntime nodes[] = {CprRuntime(1), CprRuntime(2), CprRuntime(3),
                        CprRuntime(4), CprRuntime(5), CprRuntime(6),
                        CprRuntime(7), CprRuntime(8)};
  for (auto& node : nodes) {
    node.setPacketAirtimeMs(10);
  }
  const std::uint8_t payload[] = {'s', 'e', 'v', 'e', 'n'};

  TEST_ASSERT_EQUAL_UINT32(
      1, nodes[0].sendApp(8, 1000, payload, sizeof(payload), 0, 10000,
                          2500, 4000));
  CprRuntimeTx in_flight = startOldestTx(nodes[0], 10);
  std::uint32_t now_ms = 20;
  for (std::size_t i = 1; i < 7; ++i) {
    receiveStartedTx(nodes[i], in_flight, now_ms);
    TEST_ASSERT_EQUAL_UINT32(1, nodes[i].poll(now_ms + 200));
    in_flight = startOldestTx(nodes[i], now_ms + 200);
    now_ms += 210;
  }
  receiveStartedTx(nodes[7], in_flight, now_ms);
  CprDelivery delivery{};
  TEST_ASSERT_TRUE(nodes[7].pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(1000, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT16(1, delivery.source);
  TEST_ASSERT_EQUAL_UINT16(8, delivery.destination);
  in_flight = startOldestTx(nodes[7], now_ms + 10);
  TEST_ASSERT_EQUAL_UINT8(kMaxPathNodes,
                          decodeStartedTx(in_flight).path.length);

  for (std::size_t i = 7; i-- > 1;) {
    now_ms += 20;
    receiveStartedTx(nodes[i], in_flight, now_ms);
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(
        1, nodes[i].txCount(),
        "An ACK needs a fresh reverse-hop budget even after a seven-hop initial flood");
    in_flight = startOldestTx(nodes[i], now_ms + 10);
  }
  receiveStartedTx(nodes[0], in_flight, now_ms + 20);
  TEST_ASSERT_TRUE(nodes[0].node().flowAcked(1000));

  TEST_ASSERT_EQUAL_UINT32(
      1, nodes[0].sendApp(8, 1001, payload, sizeof(payload), 2000, 12000,
                          2500, 4000));
  in_flight = startOldestTx(nodes[0], 2010);
  TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(CprFrameType::Data),
                          static_cast<std::uint8_t>(decodeStartedTx(in_flight).type));
  now_ms = 2020;
  for (std::size_t i = 1; i < 7; ++i) {
    receiveStartedTx(nodes[i], in_flight, now_ms);
    TEST_ASSERT_EQUAL_UINT32(1, nodes[i].txCount());
    in_flight = startOldestTx(nodes[i], now_ms + 10);
    now_ms += 20;
  }
  receiveStartedTx(nodes[7], in_flight, now_ms);
  TEST_ASSERT_TRUE(nodes[7].pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(1001, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));
  in_flight = startOldestTx(nodes[7], now_ms + 10);
  for (std::size_t i = 7; i-- > 1;) {
    now_ms += 20;
    receiveStartedTx(nodes[i], in_flight, now_ms);
    TEST_ASSERT_EQUAL_UINT32_MESSAGE(
        1, nodes[i].txCount(),
        "A routed DATA delivery also needs enough TTL for the complete reverse ACK path");
    in_flight = startOldestTx(nodes[i], now_ms + 10);
  }
  receiveStartedTx(nodes[0], in_flight, now_ms + 20);
  TEST_ASSERT_TRUE(nodes[0].node().flowAcked(1001));
  TEST_ASSERT_FALSE(nodes[7].pollDelivery(&delivery));
}

void testRuntimeFloodAckAcrossMillisWrapKeepsLocalDeadlineAndRelayDueTime() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime destination(3);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  destination.setPacketAirtimeMs(10);
  const std::uint32_t base_ms = 0xFFFFFFCDU;
  const std::uint32_t deadline_ms = base_ms + 10000U;
  const std::uint8_t payload[] = {'w', 'r', 'a', 'p'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 1100, payload, sizeof(payload), base_ms,
                        deadline_ms, 1000, 2500));
  TEST_ASSERT_TRUE_MESSAGE(
      source.prepareTx(base_ms + 10U),
      "A future deadline across millis wrap must not reject a feasible source TX");
  const CprRuntimeTx initial = startOldestTx(source, base_ms + 10U);
  TEST_ASSERT_EQUAL_UINT32(9990,
                           decodeStartedTx(initial).remaining_budget_ms);
  receiveStartedTx(relay, initial, base_ms + 20U);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.poll(base_ms + 40U),
      "A wrapped relay due time is still in the future before millis wraps");
  TEST_ASSERT_NULL(relay.peekTx());
  TEST_ASSERT_EQUAL_UINT32(0, relay.poll(68));
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(69));
  const CprRuntimeTx forwarded = startOldestTx(relay, 69);
  TEST_ASSERT_EQUAL_UINT32(9880,
                           decodeStartedTx(forwarded).remaining_budget_ms);
  receiveStartedTx(destination, forwarded, 79);
  CprDelivery delivery{};
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(1100, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT32(base_ms, delivery.created_at_ms);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));

  const CprRuntimeTx destination_ack = startOldestTx(destination, 89);
  receiveStartedTx(relay, destination_ack, 99);
  receiveStartedTx(source, startOldestTx(relay, 109), 119);
  TEST_ASSERT_TRUE(source.node().flowAcked(1100));
  TEST_ASSERT_NULL(source.peekTx());
}

void testRuntimeRejectsRoutedDataWithWrongPhysicalHopIdentity() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime destination(3);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  destination.setPacketAirtimeMs(10);
  const std::uint8_t payload[] = {'h', 'o', 'p'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 1200, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  CprWireFrame routed = decodeStartedTx(startOldestTx(source, 100));
  routed.type = CprFrameType::Data;
  routed.dst = 2;
  routed.path.length = 3;
  routed.path.nodes[0] = 1;
  routed.path.nodes[1] = 2;
  routed.path.nodes[2] = 3;
  routed.path_index = 1;

  CprWireFrame wrong_sender = routed;
  wrong_sender.src = 4;
  CprEncodedFrame encoded = encodeCprFrame(wrong_sender);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.receive(encoded.bytes.data(), encoded.size, 120),
      "A CRC-valid routed DATA must come from the preceding physical path hop");
  TEST_ASSERT_NULL(relay.peekTx());

  CprWireFrame wrong_destination = routed;
  wrong_destination.dst = 4;
  encoded = encodeCprFrame(wrong_destination);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.receive(encoded.bytes.data(), encoded.size, 130),
      "A routed DATA receiver must match both the wire destination and path index");
  TEST_ASSERT_NULL(relay.peekTx());
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().rx_decode_errors);

  encoded = encodeCprFrame(routed);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  TEST_ASSERT_EQUAL_UINT32(
      1, relay.receive(encoded.bytes.data(), encoded.size, 140));
  receiveStartedTx(destination, startOldestTx(relay, 150), 160);
  CprDelivery delivery{};
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(1200, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));
}

void testRuntimeRejectsFloodWhoseSenderDiffersFromPathTail() {
  CprRuntime source(1);
  CprRuntime relay(2);
  CprRuntime destination(3);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  destination.setPacketAirtimeMs(10);
  const std::uint8_t payload[] = {'f', 'l', 'o', 'o', 'd'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 1300, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  const CprRuntimeTx initial = startOldestTx(source, 100);
  CprWireFrame wrong_sender = decodeStartedTx(initial);
  wrong_sender.src = 4;
  const CprEncodedFrame encoded = encodeCprFrame(wrong_sender);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  TEST_ASSERT_EQUAL_UINT32(
      0, relay.receive(encoded.bytes.data(), encoded.size, 120));
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().rx_decode_errors);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.poll(230),
      "A flood sender inconsistent with its accumulated path must never create a relay offer");
  TEST_ASSERT_NULL(relay.peekTx());

  receiveStartedTx(relay, initial, 240);
  TEST_ASSERT_EQUAL_UINT32(1, relay.poll(340));
  receiveStartedTx(destination, startOldestTx(relay, 340), 350);
  CprDelivery delivery{};
  TEST_ASSERT_TRUE(destination.pollDelivery(&delivery));
  TEST_ASSERT_EQUAL_UINT32(1300, delivery.flow_id);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(payload, delivery.payload.data(),
                               sizeof(payload));
}

void testRuntimeAlternatePathFloodDuplicateCancelsPendingRelay() {
  CprRuntime source(1);
  CprRuntime relay(2);
  source.setPacketAirtimeMs(10);
  relay.setPacketAirtimeMs(10);
  const std::uint8_t payload[] = {'d', 'u', 'p'};

  TEST_ASSERT_EQUAL_UINT32(
      1, source.sendApp(3, 1400, payload, sizeof(payload), 0, 10000, 1000,
                        2500));
  const CprRuntimeTx initial = startOldestTx(source, 100);
  receiveStartedTx(relay, initial, 120);
  TEST_ASSERT_NULL(relay.peekTx());

  CprWireFrame alternate = decodeStartedTx(initial);
  alternate.src = 4;
  alternate.path.length = 2;
  alternate.path.nodes[0] = 1;
  alternate.path.nodes[1] = 4;
  alternate.path_index = 1;
  --alternate.ttl;
  const CprEncodedFrame encoded = encodeCprFrame(alternate);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  TEST_ASSERT_EQUAL_UINT32(
      0, relay.receive(encoded.bytes.data(), encoded.size, 150));
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().rx_decode_errors);
  TEST_ASSERT_EQUAL_UINT32_MESSAGE(
      0, relay.poll(300),
      "A same-origin flood duplicate from another path must cancel pending work, not create another relay");
  TEST_ASSERT_NULL(relay.peekTx());
  TEST_ASSERT_EQUAL_UINT32(0, relay.stats().tx_started);
}

}  // namespace

void runCprRuntimeTests() {
  RUN_TEST(testRuntimeColdFloodAckLearnsNextRoutedFlow);
  RUN_TEST(testRuntimeRejectsSerializedAckFromWrongSender);
  RUN_TEST(testRuntimePreflightRejectsInfeasibleInitialFloodAndReleasesCapacity);
  RUN_TEST(testRuntimeDiscardUnstartedFloodReleasesCapacity);
  RUN_TEST(testRuntimeOverheardAckCancelsOffPathPendingFlood);
  RUN_TEST(testRuntimeBudgetCountsDownAcrossUnsynchronizedRelayClocks);
  RUN_TEST(testRuntimeRoutedRepeatRecoveryAckUsesPerFlowBudgetAndGeneration);
  RUN_TEST(testRuntimeSevenHopFloodAndRoutedDataReceiveReverseAck);
  RUN_TEST(testRuntimeFloodAckAcrossMillisWrapKeepsLocalDeadlineAndRelayDueTime);
  RUN_TEST(testRuntimeRejectsRoutedDataWithWrongPhysicalHopIdentity);
  RUN_TEST(testRuntimeRejectsFloodWhoseSenderDiffersFromPathTail);
  RUN_TEST(testRuntimeAlternatePathFloodDuplicateCancelsPendingRelay);
}
