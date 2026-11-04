#include <cstdint>

#include <unity.h>

#include "meshecho_cpr_core.hpp"

using namespace meshecho_cpr;

namespace {

Path lifecyclePath() {
  Path path{};
  path.length = 3;
  path.nodes[0] = 1;
  path.nodes[1] = 2;
  path.nodes[2] = 3;
  return path;
}

void testRoutePathRejectsReservedNodeAtEveryPosition() {
  for (std::size_t i = 0; i < lifecyclePath().length; ++i) {
    Path path = lifecyclePath();
    path.nodes[i] = 0xFFFFU;
    TEST_ASSERT_FALSE(path.valid());
    RouteTable routes;
    TEST_ASSERT_FALSE(routes.install(path.nodes[path.length - 1U], path).accepted);
  }
}

void testRoutedFlowRejectsZeroGenerationAck() {
  RouteTable routes;
  const Path path = lifecyclePath();
  const RouteInstallResult installed = routes.install(3, path, 0, 60000);
  TEST_ASSERT_TRUE(installed.accepted);

  CprController controller;
  const CprDecision initial = controller.beginFlow(
      700, 1, 3, 0, 10000, routes.find(3, 0), installed.generation,
      1000, 2500);
  TEST_ASSERT_TRUE(initial.action == CprAction::R_INITIAL);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(700, 100));

  CprAckObservation ack{};
  ack.receiver = 1;
  ack.sender = 2;
  ack.flow_id = 700;
  ack.request_id = 700;
  ack.origin = 3;
  ack.final_dst = 1;
  ack.path = path;
  ack.path_index = 0;
  ack.repair_index = kInitialRepair;
  ack.route_generation = 0;
  TEST_ASSERT_FALSE(controller.acceptAck(ack, installed.generation, 200).accepted);
  TEST_ASSERT_FALSE(controller.isAcked(700));

  ack.route_generation = installed.generation;
  TEST_ASSERT_TRUE(controller.acceptAck(ack, installed.generation, 201).accepted);
  TEST_ASSERT_TRUE(controller.isAcked(700));
}

void testRecentlyRetiredFlowIdCannotBeReused() {
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      701, 1, 3, 0, 10000, nullptr, 0, 1000, 2500).action ==
      CprAction::F_INITIAL);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(701, 100));
  TEST_ASSERT_TRUE(controller.retire(701));
  TEST_ASSERT_TRUE(controller.wasRetired(701));

  TEST_ASSERT_TRUE(controller.beginFlow(
      701, 1, 3, 10001, 20000, nullptr, 0, 1000, 2500).action ==
      CprAction::DROP);
  TEST_ASSERT_NULL(controller.flow(701));
  TEST_ASSERT_TRUE(controller.beginFlow(
      702, 1, 3, 10001, 20000, nullptr, 0, 1000, 2500).action ==
      CprAction::F_INITIAL);
}

void testInitialRouteMustMatchBothFlowEndpoints() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(3, lifecyclePath(), 0, 60000);
  TEST_ASSERT_TRUE(installed.accepted);
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      703, 4, 3, 0, 10000, routes.find(3, 0), installed.generation,
      1000, 2500).action == CprAction::F_INITIAL);
  TEST_ASSERT_TRUE(controller.beginFlow(
      704, 1, 4, 0, 10000, routes.find(3, 0), installed.generation,
      1000, 2500).action == CprAction::F_INITIAL);
}

void testZeroGenerationRouteCannotSelectRoutedInitial() {
  RouteEntry route{};
  route.active = true;
  route.destination = 3;
  route.path = lifecyclePath();
  route.generation = 0;
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      706, 1, 3, 0, 10000, &route, 0, 1000, 2500).action ==
      CprAction::F_INITIAL);
}

void testSourceAckRequiresActualSourceReceiver() {
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      705, 1, 3, 0, 10000, nullptr, 0, 1000, 2500).action ==
      CprAction::F_INITIAL);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(705, 100));
  CprAckObservation ack{};
  ack.sender = 2;
  ack.flow_id = 705;
  ack.request_id = 705;
  ack.origin = 3;
  ack.final_dst = 1;
  ack.path = lifecyclePath();
  for (const NodeId receiver : {NodeId{0}, NodeId{2}}) {
    ack.receiver = receiver;
    TEST_ASSERT_FALSE(controller.acceptAck(ack, 0, 200).accepted);
  }
  ack.receiver = 1;
  TEST_ASSERT_TRUE(controller.acceptAck(ack, 0, 201).accepted);
}

void testStartedInitialFloodAckIgnoresUnrelatedCurrentRouteGeneration() {
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      716, 1, 3, 0, 10000, nullptr, 0, 1000, 2500).action ==
      CprAction::F_INITIAL);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(716, 100));
  CprAckObservation ack{};
  ack.receiver = 1;
  ack.sender = 2;
  ack.flow_id = 716;
  ack.request_id = 716;
  ack.origin = 3;
  ack.final_dst = 1;
  ack.path = lifecyclePath();
  ack.route_generation = 9;
  TEST_ASSERT_FALSE(controller.acceptAck(ack, 9, 200).accepted);
  ack.route_generation = 0;
  ack.repair_index = kRepeatRepair;
  TEST_ASSERT_FALSE(controller.acceptAck(ack, 9, 201).accepted);
  ack.repair_index = kInitialRepair;
  TEST_ASSERT_TRUE(controller.acceptAck(ack, 9, 202).accepted);
  TEST_ASSERT_TRUE(controller.isAcked(716));
}

void testInitialFloodFallbackUsesZeroWireEpochAndNoRouteLease() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(3, lifecyclePath(), 0, 1000);
  TEST_ASSERT_TRUE(installed.accepted);
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      717, 1, 3, 0, 10000, routes.find(3, 0), installed.generation,
      11000, 2500).action == CprAction::F_INITIAL);
  const CprFlowRecord* flow = controller.flow(717);
  TEST_ASSERT_NOT_NULL(flow);
  TEST_ASSERT_EQUAL_UINT32(0, flow->initial_route_generation);
  TEST_ASSERT_EQUAL_UINT32(0, flow->initial_route_expiry_ms);
  TEST_ASSERT_FALSE(flow->initial_route_has_expiry);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(717, 100));
  CprAckObservation ack{};
  ack.receiver = 1;
  ack.sender = 2;
  ack.flow_id = 717;
  ack.request_id = 717;
  ack.origin = 3;
  ack.final_dst = 1;
  ack.path = lifecyclePath();
  ack.route_generation = installed.generation;
  TEST_ASSERT_FALSE(controller.acceptAck(ack, installed.generation, 200).accepted);
  ack.route_generation = 0;
  TEST_ASSERT_TRUE(controller.acceptAck(ack, installed.generation, 2000).accepted);
}

void testRouteLifetimeExpiresAtWrappedZero() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(
      3, lifecyclePath(), 0xFFFFFFF0U, 16U);
  TEST_ASSERT_TRUE(installed.accepted);
  TEST_ASSERT_EQUAL_UINT32(0, installed.expires_at_ms);
  TEST_ASSERT_NOT_NULL(routes.find(3, 0xFFFFFFF0U));
  TEST_ASSERT_NOT_NULL(routes.find(3, 0xFFFFFFFFU));
  TEST_ASSERT_NULL(routes.find(3, 0));
  TEST_ASSERT_TRUE(routes.expire(0));
  TEST_ASSERT_NULL(routes.find(3));
}

void testTimedRouteInstallReclaimsExpiredSlots() {
  RouteTable routes;
  for (std::size_t i = 0; i < kMaxRoutes; ++i) {
    Path path = lifecyclePath();
    const NodeId destination = static_cast<NodeId>(3U + i);
    path.nodes[2] = destination;
    TEST_ASSERT_TRUE(routes.install(destination, path, 0, 10).accepted);
  }
  Path next = lifecyclePath();
  next.nodes[2] = 20;
  TEST_ASSERT_TRUE(routes.install(20, next, 11, 10).accepted);
  TEST_ASSERT_NOT_NULL(routes.find(20, 11));
  TEST_ASSERT_NULL(routes.find(3));
}

void testRouteRefreshPreservesConfirmedGeneration() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(3, lifecyclePath(), 0, 1000);
  TEST_ASSERT_TRUE(installed.accepted);
  TEST_ASSERT_TRUE(routes.refresh(3, installed.generation, 900, 1000));
  TEST_ASSERT_EQUAL_UINT32(installed.generation, routes.generation(3, 1000));
  TEST_ASSERT_EQUAL_UINT32(1900, routes.expiry(3));
  TEST_ASSERT_FALSE(routes.refresh(3, installed.generation + 1U, 1000, 1000));
  TEST_ASSERT_EQUAL_UINT32(1900, routes.expiry(3));
  TEST_ASSERT_NULL(routes.find(3, 1900));
  TEST_ASSERT_FALSE(routes.refresh(3, installed.generation, 1900, 1000));
}

void testRouteInvalidationRequiresRecordedGeneration() {
  RouteTable routes;
  const RouteInstallResult original = routes.install(3, lifecyclePath(), 0, 1000);
  const RouteInstallResult replacement = routes.install(3, lifecyclePath(), 100, 1000);
  TEST_ASSERT_TRUE(original.accepted);
  TEST_ASSERT_TRUE(replacement.accepted);
  TEST_ASSERT_NOT_EQUAL(original.generation, replacement.generation);

  TEST_ASSERT_FALSE(routes.invalidate(3, original.generation));
  TEST_ASSERT_EQUAL_UINT32(replacement.generation, routes.generation(3, 200));
  TEST_ASSERT_FALSE(routes.invalidate(3, 0));
  TEST_ASSERT_TRUE(routes.invalidate(3, replacement.generation));
  TEST_ASSERT_NULL(routes.find(3));
  TEST_ASSERT_FALSE(routes.invalidate(3, replacement.generation));
}

void testTimedRouteInstallRejectsInvalidLifetimeWithoutReplacingRoute() {
  RouteTable routes;
  const RouteInstallResult original = routes.install(3, lifecyclePath(), 100, 1000);
  TEST_ASSERT_TRUE(original.accepted);
  for (const std::uint32_t lifetime : {0U, 0x80000000U, 0xFFFFFFFFU}) {
    TEST_ASSERT_FALSE(routes.install(3, lifecyclePath(), 200, lifetime).accepted);
    TEST_ASSERT_EQUAL_UINT32(original.generation, routes.generation(3, 200));
    TEST_ASSERT_EQUAL_UINT32(original.expires_at_ms, routes.expiry(3));
  }
}

void testControllerLifecycleCrossesClockRollover() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(3, lifecyclePath());
  CprController controller;
  TEST_ASSERT_TRUE(controller.beginFlow(
      706, 1, 3, 0xFFFFFFF0U, 1000, routes.find(3), installed.generation,
      10, 20).action == CprAction::R_INITIAL);
  TEST_ASSERT_TRUE(controller.markInitialTxStarted(706, 0xFFFFFFF5U));
  TEST_ASSERT_TRUE(controller.requestRecovery(
      706, 5, 10, 20, installed.generation).action == CprAction::R_REPEAT);
  TEST_ASSERT_TRUE(controller.markRepeatTxStarted(706, 6));
  TEST_ASSERT_TRUE(controller.requestRecovery(
      706, 20, 10, 20, installed.generation).action == CprAction::F_RECOVERY);
  TEST_ASSERT_TRUE(controller.markRecoveryTxStarted(706, 21));

  CprAckObservation ack{};
  ack.receiver = 1;
  ack.sender = 2;
  ack.flow_id = 706;
  ack.request_id = 706;
  ack.origin = 3;
  ack.final_dst = 1;
  ack.path = lifecyclePath();
  ack.repair_index = kRecoveryRepair;
  ack.route_generation = installed.generation;
  TEST_ASSERT_FALSE(controller.acceptAck(ack, installed.generation, 1000).accepted);
  TEST_ASSERT_TRUE(controller.acceptAck(ack, installed.generation, 999).accepted);
}

void testWrappedRouteExpiryGuardsEverySourceStage() {
  RouteTable routes;
  const RouteInstallResult installed = routes.install(
      3, lifecyclePath(), 0xFFFFFFF0U, 16);
  const RouteEntry* route = routes.find(3, 0xFFFFFFF0U);
  TEST_ASSERT_NOT_NULL(route);
  CprController initial;
  TEST_ASSERT_TRUE(initial.beginFlow(
      708, 1, 3, 0xFFFFFFF0U, 100, route, installed.generation,
      1, 2).action == CprAction::R_INITIAL);
  TEST_ASSERT_FALSE(initial.markInitialTxStarted(708, 0));

  CprController repeat;
  TEST_ASSERT_TRUE(repeat.beginFlow(
      709, 1, 3, 0xFFFFFFF0U, 100, route, installed.generation,
      1, 2).action == CprAction::R_INITIAL);
  TEST_ASSERT_TRUE(repeat.markInitialTxStarted(709, 0xFFFFFFF1U));
  TEST_ASSERT_TRUE(repeat.requestRecovery(
      709, 0xFFFFFFF2U, 1, 2, installed.generation).action == CprAction::R_REPEAT);
  TEST_ASSERT_FALSE(repeat.markRepeatTxStarted(709, 0));

  CprController recovery;
  TEST_ASSERT_TRUE(recovery.beginFlow(
      710, 1, 3, 0xFFFFFFF0U, 100, route, installed.generation,
      1, 2).action == CprAction::R_INITIAL);
  TEST_ASSERT_TRUE(recovery.markInitialTxStarted(710, 0xFFFFFFF1U));
  TEST_ASSERT_TRUE(recovery.requestRecovery(
      710, 0xFFFFFFF2U, 1, 2, installed.generation).action == CprAction::R_REPEAT);
  TEST_ASSERT_TRUE(recovery.markRepeatTxStarted(710, 0xFFFFFFF3U));
  TEST_ASSERT_TRUE(recovery.requestRecovery(
      710, 0xFFFFFFF4U, 1, 2, installed.generation).action == CprAction::F_RECOVERY);
  TEST_ASSERT_FALSE(recovery.markRecoveryTxStarted(710, 0));

  CprController expired;
  TEST_ASSERT_TRUE(expired.beginFlow(
      711, 1, 3, 0, 100, route, installed.generation,
      1, 2).action == CprAction::F_INITIAL);
}

void testAckLeaseExpiryIsWrapSafeForEveryMarker() {
  for (const std::uint32_t lifetime : {16U, 48U}) {
    RouteTable routes;
    const RouteInstallResult installed = routes.install(
        3, lifecyclePath(), 0xFFFFFFF0U, lifetime);
    for (std::uint8_t marker = kInitialRepair; marker <= kRecoveryRepair; ++marker) {
      CprController controller;
      const std::uint32_t flow_id = 712U + marker;
      TEST_ASSERT_TRUE(controller.beginFlow(
          flow_id, 1, 3, 0xFFFFFFF0U, 100, routes.find(3), installed.generation,
          1, 2).action == CprAction::R_INITIAL);
      TEST_ASSERT_TRUE(controller.markInitialTxStarted(flow_id, 0xFFFFFFF1U));
      if (marker >= kRepeatRepair) {
        TEST_ASSERT_TRUE(controller.requestRecovery(
            flow_id, 0xFFFFFFF2U, 1, 2, installed.generation).action == CprAction::R_REPEAT);
        TEST_ASSERT_TRUE(controller.markRepeatTxStarted(flow_id, 0xFFFFFFF3U));
      }
      if (marker == kRecoveryRepair) {
        TEST_ASSERT_TRUE(controller.requestRecovery(
            flow_id, 0xFFFFFFF4U, 1, 2, installed.generation).action == CprAction::F_RECOVERY);
        TEST_ASSERT_TRUE(controller.markRecoveryTxStarted(flow_id, 0xFFFFFFF5U));
      }
      CprAckObservation ack{};
      ack.receiver = 1;
      ack.sender = 2;
      ack.flow_id = flow_id;
      ack.request_id = flow_id;
      ack.origin = 3;
      ack.final_dst = 1;
      ack.path = lifecyclePath();
      ack.repair_index = marker;
      ack.route_generation = installed.generation;
      TEST_ASSERT_FALSE(controller.acceptAck(
          ack, installed.generation, installed.expires_at_ms).accepted);
      TEST_ASSERT_TRUE(controller.acceptAck(
          ack, installed.generation, installed.expires_at_ms - 1U).accepted);
    }
  }
}

void testInvalidFlowRegistrationDoesNotConsumeCapacity() {
  struct InvalidFlow {
    NodeId source;
    NodeId destination;
    std::uint32_t deadline;
  };
  const InvalidFlow invalid[] = {
      {0, 3, 1000}, {0xFFFFU, 3, 1000}, {1, 0, 1000},
      {1, 0xFFFFU, 1000}, {1, 1, 1000}, {1, 3, 100},
      {1, 3, 99}, {1, 3, 100U + 0x80000000U},
      {1, 3, 100U + 0x80000001U},
  };
  CprController controller;
  std::uint32_t flow_id = 800;
  for (const auto& item : invalid) {
    TEST_ASSERT_TRUE(controller.beginFlow(
        flow_id, item.source, item.destination, 100, item.deadline,
        nullptr, 0, 10, 20).action == CprAction::DROP);
    TEST_ASSERT_NULL(controller.flow(flow_id));
    ++flow_id;
  }
  for (std::uint32_t i = 0; i < kMaxCprFlows; ++i) {
    TEST_ASSERT_TRUE(controller.beginFlow(
        900U + i, 1, 3, 100, 1000, nullptr, 0, 10, 20).action ==
        CprAction::F_INITIAL);
  }
}

}  // namespace

void runCprLifecycleTests() {
  RUN_TEST(testRoutePathRejectsReservedNodeAtEveryPosition);
  RUN_TEST(testRoutedFlowRejectsZeroGenerationAck);
  RUN_TEST(testRecentlyRetiredFlowIdCannotBeReused);
  RUN_TEST(testInitialRouteMustMatchBothFlowEndpoints);
  RUN_TEST(testZeroGenerationRouteCannotSelectRoutedInitial);
  RUN_TEST(testSourceAckRequiresActualSourceReceiver);
  RUN_TEST(testStartedInitialFloodAckIgnoresUnrelatedCurrentRouteGeneration);
  RUN_TEST(testInitialFloodFallbackUsesZeroWireEpochAndNoRouteLease);
  RUN_TEST(testRouteLifetimeExpiresAtWrappedZero);
  RUN_TEST(testTimedRouteInstallReclaimsExpiredSlots);
  RUN_TEST(testRouteRefreshPreservesConfirmedGeneration);
  RUN_TEST(testRouteInvalidationRequiresRecordedGeneration);
  RUN_TEST(testTimedRouteInstallRejectsInvalidLifetimeWithoutReplacingRoute);
  RUN_TEST(testControllerLifecycleCrossesClockRollover);
  RUN_TEST(testWrappedRouteExpiryGuardsEverySourceStage);
  RUN_TEST(testAckLeaseExpiryIsWrapSafeForEveryMarker);
  RUN_TEST(testInvalidFlowRegistrationDoesNotConsumeCapacity);
}
