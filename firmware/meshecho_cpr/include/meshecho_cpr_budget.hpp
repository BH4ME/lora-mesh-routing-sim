#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>

#include "meshecho_cpr_wire.hpp"

namespace meshecho_cpr {

enum class CprLoRaLdro : std::uint8_t { Auto, Disabled, Enabled };

struct CprLoRaBudgetConfig {
  double bandwidth_khz = 125.0;
  std::uint8_t spreading_factor = 9;
  std::uint8_t coding_rate = 7;
  std::uint16_t preamble_length = 8;
  bool crc_enabled = true;
  bool implicit_header = false;
  CprLoRaLdro low_data_rate_optimize = CprLoRaLdro::Auto;
  std::uint32_t per_hop_guard_ms = 200;
};

// SF7--12 share this LoRa formula across both supported radio families.
// CRC here is the PHY CRC, in addition to the CPR CRC already in wire_bytes.
inline std::uint32_t cprFrameAirtimeMs(const CprLoRaBudgetConfig& config,
                                      std::size_t wire_bytes) {
  if (!(config.bandwidth_khz >= 7.8 && config.bandwidth_khz <= 500.0) ||
      config.spreading_factor < 7U || config.spreading_factor > 12U ||
      config.coding_rate < 5U || config.coding_rate > 8U ||
      config.preamble_length < 6U || wire_bytes == 0U ||
      wire_bytes > kCprMaxFrameSize ||
      (config.low_data_rate_optimize != CprLoRaLdro::Auto &&
       config.low_data_rate_optimize != CprLoRaLdro::Disabled &&
       config.low_data_rate_optimize != CprLoRaLdro::Enabled)) {
    return 0;
  }
  const double symbol_ms =
      static_cast<double>(1UL << config.spreading_factor) / config.bandwidth_khz;
  const bool ldro = config.low_data_rate_optimize == CprLoRaLdro::Enabled ||
                    (config.low_data_rate_optimize == CprLoRaLdro::Auto &&
                     symbol_ms >= 16.0);
  const int numerator = static_cast<int>(wire_bytes * 8U) -
                        4 * config.spreading_factor + 28 +
                        (config.crc_enabled ? 16 : 0) -
                        (config.implicit_header ? 20 : 0);
  const int denominator = 4 * (config.spreading_factor - (ldro ? 2 : 0));
  const int payload_blocks =
      numerator > 0 ? (numerator + denominator - 1) / denominator : 0;
  const double symbols = config.preamble_length + 4.25 + 8.0 +
                         payload_blocks * config.coding_rate;
  return static_cast<std::uint32_t>(std::ceil(symbols * symbol_ms));
}

struct CprExchangeBudget {
  bool valid = false;
  std::uint32_t route_bound_ms = 0;
  std::uint32_t flood_bound_ms = 0;
  std::uint32_t data_airtime_ms = 0;
  std::uint32_t ack_airtime_ms = 0;
  std::uint32_t max_data_airtime_ms = 0;
  std::uint32_t max_ack_airtime_ms = 0;
};

// These are corridor exchange bounds under the configured per-hop scheduler
// guard, not deterministic latency guarantees under arbitrary RF contention.
inline CprExchangeBudget cprExchangeBudgets(const CprLoRaBudgetConfig& config,
                                           std::size_t payload_bytes,
                                           std::size_t routed_path_nodes) {
  if (payload_bytes > kCprAppPayloadSize || routed_path_nodes < 2U ||
      routed_path_nodes > kMaxPathNodes) {
    return {};
  }
  const auto wireSize = [](std::size_t nodes, std::size_t payload) {
    return kCprWireHeaderSize + kCprWireCrcSize + nodes * sizeof(NodeId) + payload;
  };
  const std::uint32_t data_ms =
      cprFrameAirtimeMs(config, wireSize(routed_path_nodes, payload_bytes));
  const std::uint32_t ack_ms =
      cprFrameAirtimeMs(config, wireSize(routed_path_nodes, 0U));
  const std::uint32_t flood_data_ms =
      cprFrameAirtimeMs(config, wireSize(kMaxPathNodes, payload_bytes));
  const std::uint32_t flood_ack_ms =
      cprFrameAirtimeMs(config, wireSize(kMaxPathNodes, 0U));
  if (data_ms == 0U || ack_ms == 0U || flood_data_ms == 0U || flood_ack_ms == 0U) {
    return {};
  }
  const std::uint64_t guard_pair_ms = 2ULL * config.per_hop_guard_ms;
  const std::uint64_t route_ms =
      (routed_path_nodes - 1U) * (data_ms + static_cast<std::uint64_t>(ack_ms) +
                                guard_pair_ms);
  const std::uint64_t flood_ms =
      (kMaxPathNodes - 1U) *
      (flood_data_ms + static_cast<std::uint64_t>(flood_ack_ms) + guard_pair_ms);
  if (route_ms > 0x7FFFFFFFULL || flood_ms > 0x7FFFFFFFULL) {
    return {};
  }
  return {true, static_cast<std::uint32_t>(route_ms),
          static_cast<std::uint32_t>(flood_ms), data_ms, ack_ms,
          flood_data_ms, flood_ack_ms};
}

}  // namespace meshecho_cpr
