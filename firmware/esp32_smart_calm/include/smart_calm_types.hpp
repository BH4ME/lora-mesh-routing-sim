#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace smart_calm {

constexpr std::size_t kProfileCount = 3;
constexpr std::size_t kStateCount = 6;
constexpr std::size_t kActionCount = 3;
constexpr std::size_t kMaxTrackedFlows = 8;
constexpr std::size_t kWirePayloadSize = 32;
constexpr std::uint16_t kWireMagic = 0x5343;
constexpr std::uint8_t kWireVersion = 1;
constexpr std::size_t kWirePrefixSize = 2 + 1 + 1 + 2 + 2 + 2 + 4 + 4 + 1 + 1 + 1 + 1 + 2 + 1;
constexpr std::size_t kWireCrcSize = 2;
constexpr std::size_t kWireMinFrameSize = kWirePrefixSize + kWireCrcSize;
constexpr std::size_t kWireMaxFrameSize = kWirePrefixSize + kWirePayloadSize + kWireCrcSize;
constexpr std::uint16_t kBroadcastAddress = 0xFFFF;

struct Profile {
  const char* name;
  float route_ttl_s;
  float discovery_window_s;
  float fallback_confidence_threshold;
  std::uint8_t fallback_ttl;
  float fallback_delay_margin_s;
  float hop_penalty_per_hop;
  float route_age_penalty;
};

struct Snapshot {
  std::uint32_t tx_count = 0;
  std::uint32_t control_tx = 0;
  std::uint32_t collision_fail = 0;
  std::uint32_t route_cache_hits = 0;
  std::uint32_t route_cache_misses = 0;
  std::uint32_t route_repair_count = 0;
  std::uint32_t fallback_forward_count = 0;
  float path_confidence_total = 0.0f;
  std::uint32_t path_confidence_samples = 0;
  std::uint32_t unicast_flows = 0;
  std::uint32_t broadcast_flows = 0;
  std::uint32_t unicast_deliveries = 0;
  std::uint32_t unicast_acks = 0;
  std::uint32_t broadcast_deliveries = 0;
  float delivery_delay_total_s = 0.0f;
  std::uint32_t delivery_delay_samples = 0;
};

inline void saturatingIncrement(std::uint32_t& value) {
  if (value < std::numeric_limits<std::uint32_t>::max()) {
    ++value;
  }
}

inline void saturatingAdd(std::uint32_t& value, std::uint32_t delta) {
  const std::uint32_t cap = std::numeric_limits<std::uint32_t>::max();
  const std::uint32_t room = cap - value;
  value += delta > room ? room : delta;
}

inline void saturatingAddFloat(float& value, float delta, float abs_bound) {
  value += delta;
  if (value > abs_bound) {
    value = abs_bound;
  } else if (value < -abs_bound) {
    value = -abs_bound;
  }
}

struct PriorEntry {
  std::uint8_t state;
  std::uint8_t action;
  float value;
};

enum class FrameType : std::uint8_t {
  Hello = 1,
  Data = 2,
  Rreq = 3,
  Rrep = 4,
  Fallback = 5,
  Status = 6,
  Ack = 7,
};

#pragma pack(push, 1)
struct WireFrame {
  std::uint8_t version = kWireVersion;
  FrameType type = FrameType::Status;
  std::uint16_t src = 0;
  std::uint16_t dst = 0;
  std::uint16_t seq = 0;
  std::uint32_t flow_id = 0;
  std::uint32_t created_at_ms = 0;
  std::uint8_t ttl = 0;
  std::uint8_t state_index = 0;
  std::uint8_t action_index = 0;
  std::uint8_t flags = 0;
  std::uint16_t confidence_milli = 0;
  std::uint8_t payload_len = 0;
  char payload[kWirePayloadSize] = {0};
};
#pragma pack(pop)

static_assert(kWireMaxFrameSize <= 255, "WireFrame should fit into one LoRa packet");

struct FlowDecision {
  bool active = false;
  std::uint32_t flow_id = 0;
  std::uint8_t state_index = 0;
  std::uint8_t action_index = 0;
  float confidence = 0.0f;
  std::uint8_t route_miss = 0;
  std::uint8_t fallback_count = 0;
  std::uint8_t timeout_retries = 0;
  std::uint32_t created_at_ms = 0;
};

inline constexpr std::array<Profile, kProfileCount> defaultProfiles() {
  return {{
      {"lean", 900.0f, 2.0f, 0.0f, 1, 0.6f, 0.02f, 0.08f},
      {"balanced", 600.0f, 2.0f, 0.0f, 2, 0.6f, 0.025f, 0.10f},
      {"rescue", 360.0f, 2.8f, 0.9f, 3, 0.9f, 0.04f, 0.18f},
  }};
}

}  // namespace smart_calm
