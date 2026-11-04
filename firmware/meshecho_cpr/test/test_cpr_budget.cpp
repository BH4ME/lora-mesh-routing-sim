#include <unity.h>

#include <limits>

#include "meshecho_cpr_budget.hpp"

using namespace meshecho_cpr;

void testCprBudgetDefaultMaximumFrameAirtime() {
  const CprLoRaBudgetConfig config{};
  // SF9, 125 kHz, CR4/7, eight preamble symbols, explicit header and CRC:
  // (8 + 4.25 + 8 + ceil(696/36) * 7) * 4.096 = 656.384 ms.
  TEST_ASSERT_EQUAL_UINT32(657U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
}

void testCprBudgetExchangeIncludesEveryHopAndAck() {
  const CprExchangeBudget budget =
      cprExchangeBudgets(CprLoRaBudgetConfig{}, kCprAppPayloadSize, kMaxPathNodes);
  TEST_ASSERT_TRUE(budget.valid);
  TEST_ASSERT_EQUAL_UINT32(657U, budget.data_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(456U, budget.ack_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(10591U, budget.route_bound_ms);
  TEST_ASSERT_EQUAL_UINT32(budget.route_bound_ms, budget.flood_bound_ms);
}

void testCprBudgetRejectsUnknownLdroMode() {
  CprLoRaBudgetConfig config{};
  config.low_data_rate_optimize = static_cast<CprLoRaLdro>(255U);
  TEST_ASSERT_EQUAL_UINT32(0U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  TEST_ASSERT_FALSE(
      cprExchangeBudgets(config, kCprAppPayloadSize, kMaxPathNodes).valid);
}

void testCprBudgetRejectsExchangeOutsideModularClockHorizon() {
  CprLoRaBudgetConfig config{};
  config.per_hop_guard_ms = 200000000U;
  TEST_ASSERT_FALSE(
      cprExchangeBudgets(config, kCprAppPayloadSize, kMaxPathNodes).valid);
}

void testCprBudgetShortRouteKeepsWorstCaseFloodAndReceiveAirtime() {
  const CprExchangeBudget budget =
      cprExchangeBudgets(CprLoRaBudgetConfig{}, kCprAppPayloadSize, 2U);
  TEST_ASSERT_TRUE(budget.valid);
  TEST_ASSERT_LESS_THAN_UINT32(budget.flood_bound_ms, budget.route_bound_ms);
  TEST_ASSERT_LESS_THAN_UINT32(budget.max_data_airtime_ms, budget.data_airtime_ms);
  TEST_ASSERT_LESS_THAN_UINT32(budget.max_ack_airtime_ms, budget.ack_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(657U, budget.max_data_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(456U, budget.max_ack_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(10591U, budget.flood_bound_ms);
}

void testCprBudgetSf12EnablesLdroAndExceedsThirtySecondDeadline() {
  CprLoRaBudgetConfig config{};
  config.spreading_factor = 12U;
  const CprExchangeBudget budget =
      cprExchangeBudgets(config, kCprAppPayloadSize, kMaxPathNodes);
  TEST_ASSERT_TRUE(budget.valid);
  TEST_ASSERT_EQUAL_UINT32(4793U, budget.data_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(3187U, budget.ack_airtime_ms);
  TEST_ASSERT_EQUAL_UINT32(58660U, budget.route_bound_ms);
  TEST_ASSERT_GREATER_THAN_UINT32(30000U, budget.flood_bound_ms);
  config.low_data_rate_optimize = CprLoRaLdro::Disabled;
  TEST_ASSERT_EQUAL_UINT32(4105U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
}

void testCprBudgetAccountsForPhyHeaderCrcCodingRateAndPreamble() {
  CprLoRaBudgetConfig config{};
  config.crc_enabled = false;
  TEST_ASSERT_EQUAL_UINT32(628U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  config = CprLoRaBudgetConfig{};
  config.implicit_header = true;
  TEST_ASSERT_EQUAL_UINT32(628U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  config = CprLoRaBudgetConfig{};
  config.coding_rate = 5U;
  TEST_ASSERT_EQUAL_UINT32(493U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  config = CprLoRaBudgetConfig{};
  config.preamble_length = 16U;
  TEST_ASSERT_EQUAL_UINT32(690U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  config = CprLoRaBudgetConfig{};
  config.bandwidth_khz = 250.0;
  TEST_ASSERT_EQUAL_UINT32(329U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
  config = CprLoRaBudgetConfig{};
  config.low_data_rate_optimize = CprLoRaLdro::Enabled;
  TEST_ASSERT_EQUAL_UINT32(800U, cprFrameAirtimeMs(config, kCprMaxFrameSize));
}

void testCprBudgetMatchesRealEncodedDataAndAckBytes() {
  CprWireFrame frame{};
  frame.type = CprFrameType::Data;
  frame.src = 1U;
  frame.dst = 2U;
  frame.flow_id = 1U;
  frame.request_id = 1U;
  frame.path_index = 1U;
  for (std::size_t nodes = 2U; nodes <= kMaxPathNodes; ++nodes) {
    frame.path.length = static_cast<std::uint8_t>(nodes);
    for (std::size_t i = 0U; i < nodes; ++i) {
      frame.path.nodes[i] = static_cast<NodeId>(i + 1U);
    }
    for (std::size_t payload = 0U; payload <= kCprAppPayloadSize; ++payload) {
      frame.type = CprFrameType::Data;
      frame.payload_len = static_cast<std::uint8_t>(payload);
      const CprEncodedFrame data = encodeCprFrame(frame);
      TEST_ASSERT_EQUAL_UINT32(38U + 2U * nodes + payload, data.size);
      const CprExchangeBudget budget =
          cprExchangeBudgets(CprLoRaBudgetConfig{}, payload, nodes);
      TEST_ASSERT_TRUE(budget.valid);
      TEST_ASSERT_EQUAL_UINT32(
          cprFrameAirtimeMs(CprLoRaBudgetConfig{}, data.size), budget.data_airtime_ms);
      frame.type = CprFrameType::Ack;
      frame.payload_len = 0U;
      const CprEncodedFrame ack = encodeCprFrame(frame);
      TEST_ASSERT_EQUAL_UINT32(38U + 2U * nodes, ack.size);
      TEST_ASSERT_EQUAL_UINT32(
          cprFrameAirtimeMs(CprLoRaBudgetConfig{}, ack.size), budget.ack_airtime_ms);
    }
  }
}

void testCprBudgetInvalidConfigurationCannotAdmitAnExchange() {
  const CprLoRaBudgetConfig normal{};
  TEST_ASSERT_EQUAL_UINT32(0U, cprFrameAirtimeMs(normal, 0U));
  TEST_ASSERT_EQUAL_UINT32(0U, cprFrameAirtimeMs(normal, kCprMaxFrameSize + 1U));
  TEST_ASSERT_FALSE(cprExchangeBudgets(normal, kCprAppPayloadSize + 1U, 2U).valid);
  TEST_ASSERT_FALSE(cprExchangeBudgets(normal, 1U, 1U).valid);
  TEST_ASSERT_FALSE(cprExchangeBudgets(normal, 1U, kMaxPathNodes + 1U).valid);
  const double invalid_bandwidths[]{0.0, 7.0, 501.0,
                                  std::numeric_limits<double>::quiet_NaN(),
                                  std::numeric_limits<double>::infinity()};
  for (const double bandwidth : invalid_bandwidths) {
    CprLoRaBudgetConfig config{};
    config.bandwidth_khz = bandwidth;
    TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  }
  CprLoRaBudgetConfig config{};
  config.spreading_factor = 6U;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  config.spreading_factor = 13U;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  config = CprLoRaBudgetConfig{};
  config.coding_rate = 4U;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  config.coding_rate = 9U;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  config = CprLoRaBudgetConfig{};
  config.preamble_length = 5U;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
  config = CprLoRaBudgetConfig{};
  config.per_hop_guard_ms = 0xFFFFFFFFU;
  TEST_ASSERT_FALSE(cprExchangeBudgets(config, 1U, 2U).valid);
}

void runCprBudgetTests() {
  RUN_TEST(testCprBudgetDefaultMaximumFrameAirtime);
  RUN_TEST(testCprBudgetExchangeIncludesEveryHopAndAck);
  RUN_TEST(testCprBudgetRejectsUnknownLdroMode);
  RUN_TEST(testCprBudgetRejectsExchangeOutsideModularClockHorizon);
  RUN_TEST(testCprBudgetShortRouteKeepsWorstCaseFloodAndReceiveAirtime);
  RUN_TEST(testCprBudgetSf12EnablesLdroAndExceedsThirtySecondDeadline);
  RUN_TEST(testCprBudgetAccountsForPhyHeaderCrcCodingRateAndPreamble);
  RUN_TEST(testCprBudgetMatchesRealEncodedDataAndAckBytes);
  RUN_TEST(testCprBudgetInvalidConfigurationCannotAdmitAnExchange);
}
