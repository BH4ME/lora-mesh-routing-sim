#pragma once

#include <cctype>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace smart_calm {

constexpr const char* kMeshEchoFirmwareVersion = "meshecho-firmware-v2.1.2";
constexpr const char* kMeshEchoConfigProtocol = "meshecho-config-v1";
constexpr std::size_t kMeshEchoCallsignSize = 17;

struct MeshEchoConfig {
  std::uint16_t node_id = 1;
  char callsign[kMeshEchoCallsignSize] = "BH4ME";
  char region[12] = "US915";
  float freq_mhz = 915.0f;
  float bw_khz = 125.0f;
  std::uint8_t sf = 9;
  std::uint8_t cr = 7;
  std::int8_t tx_power_dbm = 17;
  std::uint8_t max_hops = 6;
  std::uint16_t route_ttl_s = 600;
  std::uint8_t fallback_ttl = 2;
  std::uint16_t ack_timeout_ms = 1800;
  std::uint8_t max_timeout_retries = 2;
  bool retry_after_fallback = false;
  bool ble_enabled = true;
  bool wifi_enabled = false;
};

struct MeshEchoRuntimeInfo {
  const char* version = kMeshEchoFirmwareVersion;
  const char* protocol = kMeshEchoConfigProtocol;
  const char* target = "unknown";
  const char* chip = "unknown";
  const char* radio = "unknown";
  const char* active_profile = "balanced";
  std::uint32_t uptime_ms = 0;
  std::uint32_t tx_count = 0;
  std::uint32_t control_tx = 0;
  std::uint32_t rx_success = 0;
  std::uint32_t rx_fail = 0;
  std::uint32_t collision_fail = 0;
  std::uint32_t route_cache_hits = 0;
  std::uint32_t route_cache_misses = 0;
  std::uint32_t route_repair_count = 0;
  std::uint32_t route_expired_count = 0;
  std::uint32_t neighbor_updates = 0;
  std::uint32_t neighbor_expired_count = 0;
  std::uint32_t fallback_forward_count = 0;
  std::uint32_t fallback_delivery_count = 0;
  std::uint32_t unicast_deliveries = 0;
  std::uint32_t unicast_acks = 0;
  std::uint32_t unicast_failures = 0;
  float delivery_delay_total_s = 0.0f;
  std::uint32_t delivery_delay_samples = 0;
  std::uint32_t policy_switch_count = 0;
  std::uint32_t policy_update_count = 0;
  std::uint32_t active_routes = 0;
  std::uint32_t pending_flows = 0;
  std::uint32_t neighbors = 0;
};

struct MeshEchoConfigCommandResult {
  bool handled = false;
  bool ok = false;
  bool node_id_changed = false;
  bool radio_changed = false;
  bool save_requested = false;
  bool reboot_requested = false;
};

inline MeshEchoConfig makeDefaultMeshEchoConfig(std::uint16_t node_id,
                                                float freq_mhz,
                                                float bw_khz,
                                                std::uint8_t sf,
                                                std::uint8_t cr,
                                                std::int8_t tx_power_dbm,
                                                bool sx127x_radio) {
  MeshEchoConfig config{};
  config.node_id = node_id;
  config.freq_mhz = freq_mhz;
  config.bw_khz = bw_khz;
  config.sf = sf;
  config.cr = cr;
  config.tx_power_dbm = tx_power_dbm;
  std::snprintf(config.region, sizeof(config.region), "%s", freq_mhz < 900.0f ? "EU868" : "US915");
  if (sx127x_radio && config.sf < 6) {
    config.sf = 6;
  }
  return config;
}

inline const char* meshEchoBool(bool value) {
  return value ? "true" : "false";
}

inline char* meshEchoTrimLeft(char* text) {
  while (text != nullptr && *text != '\0' && std::isspace(static_cast<unsigned char>(*text))) {
    ++text;
  }
  return text;
}

inline void meshEchoTrimRight(char* text) {
  if (text == nullptr) {
    return;
  }
  const std::size_t len = std::strlen(text);
  if (len == 0) {
    return;
  }
  char* end = text + len - 1;
  while (end >= text && std::isspace(static_cast<unsigned char>(*end))) {
    *end = '\0';
    if (end == text) {
      break;
    }
    --end;
  }
}

inline bool meshEchoEqualsIgnoreCase(const char* lhs, const char* rhs) {
  if (lhs == nullptr || rhs == nullptr) {
    return false;
  }
  while (*lhs != '\0' && *rhs != '\0') {
    const int a = std::tolower(static_cast<unsigned char>(*lhs));
    const int b = std::tolower(static_cast<unsigned char>(*rhs));
    if (a != b) {
      return false;
    }
    ++lhs;
    ++rhs;
  }
  return *lhs == '\0' && *rhs == '\0';
}

inline bool meshEchoStartsWithIgnoreCase(const char* text, const char* prefix) {
  if (text == nullptr || prefix == nullptr) {
    return false;
  }
  while (*prefix != '\0') {
    if (*text == '\0') {
      return false;
    }
    const int a = std::tolower(static_cast<unsigned char>(*text));
    const int b = std::tolower(static_cast<unsigned char>(*prefix));
    if (a != b) {
      return false;
    }
    ++text;
    ++prefix;
  }
  return true;
}

inline char* meshEchoTakeToken(char** cursor) {
  if (cursor == nullptr || *cursor == nullptr) {
    return nullptr;
  }
  char* token = meshEchoTrimLeft(*cursor);
  if (*token == '\0') {
    *cursor = token;
    return nullptr;
  }
  char* end = token;
  while (*end != '\0' && !std::isspace(static_cast<unsigned char>(*end))) {
    ++end;
  }
  if (*end != '\0') {
    *end = '\0';
    *cursor = end + 1;
  } else {
    *cursor = end;
  }
  return token;
}

inline bool meshEchoParseUnsigned(const char* value,
                                  unsigned long min_value,
                                  unsigned long max_value,
                                  unsigned long* out) {
  if (value == nullptr || *value == '\0' || out == nullptr) {
    return false;
  }
  char* end = nullptr;
  const unsigned long parsed = std::strtoul(value, &end, 10);
  end = meshEchoTrimLeft(end);
  if (end == nullptr || *end != '\0' || parsed < min_value || parsed > max_value) {
    return false;
  }
  *out = parsed;
  return true;
}

inline bool meshEchoParseSigned(const char* value, long min_value, long max_value, long* out) {
  if (value == nullptr || *value == '\0' || out == nullptr) {
    return false;
  }
  char* end = nullptr;
  const long parsed = std::strtol(value, &end, 10);
  end = meshEchoTrimLeft(end);
  if (end == nullptr || *end != '\0' || parsed < min_value || parsed > max_value) {
    return false;
  }
  *out = parsed;
  return true;
}

inline bool meshEchoParseFloat(const char* value, float min_value, float max_value, float* out) {
  if (value == nullptr || *value == '\0' || out == nullptr) {
    return false;
  }
  char* end = nullptr;
  const float parsed = std::strtof(value, &end);
  end = meshEchoTrimLeft(end);
  if (end == nullptr || *end != '\0' || parsed < min_value || parsed > max_value) {
    return false;
  }
  *out = parsed;
  return true;
}

inline bool meshEchoParseOnOff(const char* value, bool* out) {
  if (out == nullptr) {
    return false;
  }
  if (meshEchoEqualsIgnoreCase(value, "on") || meshEchoEqualsIgnoreCase(value, "true") ||
      meshEchoEqualsIgnoreCase(value, "1")) {
    *out = true;
    return true;
  }
  if (meshEchoEqualsIgnoreCase(value, "off") || meshEchoEqualsIgnoreCase(value, "false") ||
      meshEchoEqualsIgnoreCase(value, "0")) {
    *out = false;
    return true;
  }
  return false;
}

inline bool meshEchoSafeToken(const char* value, std::size_t max_len) {
  if (value == nullptr) {
    return false;
  }
  const std::size_t len = std::strlen(value);
  if (len == 0 || len >= max_len) {
    return false;
  }
  for (std::size_t i = 0; i < len; ++i) {
    const unsigned char ch = static_cast<unsigned char>(value[i]);
    if (!(std::isalnum(ch) || ch == '_' || ch == '-' || ch == '.')) {
      return false;
    }
  }
  return true;
}

inline void formatMeshEchoErrorResponse(const char* error, char* out, std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(out, out_size, "{\"ok\":false,\"error\":\"%s\"}", error == nullptr ? "error" : error);
}

inline void formatMeshEchoConfigResponse(const MeshEchoConfig& config, char* out, std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(
      out,
      out_size,
      "{\"ok\":true,\"config\":{\"node_id\":%u,\"callsign\":\"%s\",\"region\":\"%s\","
      "\"freq_mhz\":%.3f,\"bw_khz\":%.1f,\"sf\":%u,\"cr\":%u,\"tx_power\":%d,"
      "\"max_hops\":%u,\"route_ttl_s\":%u,\"fallback_ttl\":%u,\"ack_timeout_ms\":%u,"
      "\"max_timeout_retries\":%u,\"retry_after_fallback\":%s,\"ble\":%s,\"wifi\":%s}}",
      static_cast<unsigned>(config.node_id),
      config.callsign,
      config.region,
      static_cast<double>(config.freq_mhz),
      static_cast<double>(config.bw_khz),
      static_cast<unsigned>(config.sf),
      static_cast<unsigned>(config.cr),
      static_cast<int>(config.tx_power_dbm),
      static_cast<unsigned>(config.max_hops),
      static_cast<unsigned>(config.route_ttl_s),
      static_cast<unsigned>(config.fallback_ttl),
      static_cast<unsigned>(config.ack_timeout_ms),
      static_cast<unsigned>(config.max_timeout_retries),
      meshEchoBool(config.retry_after_fallback),
      meshEchoBool(config.ble_enabled),
      meshEchoBool(config.wifi_enabled));
}

inline void formatMeshEchoVersionResponse(const MeshEchoRuntimeInfo& runtime, char* out, std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(
      out,
      out_size,
      "{\"ok\":true,\"version\":\"%s\",\"protocol\":\"%s\",\"target\":\"%s\","
      "\"chip\":\"%s\",\"radio\":\"%s\",\"transports\":[\"serial\"],\"uptime_ms\":%lu}",
      runtime.version,
      runtime.protocol,
      runtime.target,
      runtime.chip,
      runtime.radio,
      static_cast<unsigned long>(runtime.uptime_ms));
}

inline void formatMeshEchoShowResponse(const MeshEchoConfig& config,
                                       const MeshEchoRuntimeInfo& runtime,
                                       char* out,
                                       std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(
      out,
      out_size,
      "{\"ok\":true,\"version\":\"%s\",\"target\":\"%s\",\"chip\":\"%s\",\"radio\":\"%s\","
      "\"uptime_ms\":%lu,\"active_profile\":\"%s\",\"stats\":{\"tx_count\":%lu,\"control_tx\":%lu,"
      "\"rx_success\":%lu,\"rx_fail\":%lu,\"collision_fail\":%lu,\"route_cache_hits\":%lu,"
      "\"route_cache_misses\":%lu,\"route_repair_count\":%lu,\"route_expired_count\":%lu,"
      "\"fallback_forward_count\":%lu,\"fallback_delivery_count\":%lu,\"active_routes\":%lu,"
      "\"pending_flows\":%lu,\"neighbors\":%lu,\"neighbor_updates\":%lu,\"neighbor_expired_count\":%lu,"
      "\"unicast_deliveries\":%lu,\"unicast_acks\":%lu,\"unicast_failures\":%lu,"
      "\"avg_ack_delay_s\":%.3f,\"policy_switch_count\":%lu,\"policy_update_count\":%lu},"
      "\"config\":{\"node_id\":%u,\"callsign\":\"%s\",\"region\":\"%s\",\"freq_mhz\":%.3f,"
      "\"bw_khz\":%.1f,\"sf\":%u,\"cr\":%u,\"tx_power\":%d,\"max_hops\":%u,"
      "\"route_ttl_s\":%u,\"fallback_ttl\":%u,\"ack_timeout_ms\":%u,"
      "\"max_timeout_retries\":%u,\"retry_after_fallback\":%s,\"ble\":%s,\"wifi\":%s}}",
      runtime.version,
      runtime.target,
      runtime.chip,
      runtime.radio,
      static_cast<unsigned long>(runtime.uptime_ms),
      runtime.active_profile,
      static_cast<unsigned long>(runtime.tx_count),
      static_cast<unsigned long>(runtime.control_tx),
      static_cast<unsigned long>(runtime.rx_success),
      static_cast<unsigned long>(runtime.rx_fail),
      static_cast<unsigned long>(runtime.collision_fail),
      static_cast<unsigned long>(runtime.route_cache_hits),
      static_cast<unsigned long>(runtime.route_cache_misses),
      static_cast<unsigned long>(runtime.route_repair_count),
      static_cast<unsigned long>(runtime.route_expired_count),
      static_cast<unsigned long>(runtime.fallback_forward_count),
      static_cast<unsigned long>(runtime.fallback_delivery_count),
      static_cast<unsigned long>(runtime.active_routes),
      static_cast<unsigned long>(runtime.pending_flows),
      static_cast<unsigned long>(runtime.neighbors),
      static_cast<unsigned long>(runtime.neighbor_updates),
      static_cast<unsigned long>(runtime.neighbor_expired_count),
      static_cast<unsigned long>(runtime.unicast_deliveries),
      static_cast<unsigned long>(runtime.unicast_acks),
      static_cast<unsigned long>(runtime.unicast_failures),
      static_cast<double>(runtime.delivery_delay_samples
                              ? runtime.delivery_delay_total_s /
                                    static_cast<float>(runtime.delivery_delay_samples)
                              : 0.0f),
      static_cast<unsigned long>(runtime.policy_switch_count),
      static_cast<unsigned long>(runtime.policy_update_count),
      static_cast<unsigned>(config.node_id),
      config.callsign,
      config.region,
      static_cast<double>(config.freq_mhz),
      static_cast<double>(config.bw_khz),
      static_cast<unsigned>(config.sf),
      static_cast<unsigned>(config.cr),
      static_cast<int>(config.tx_power_dbm),
      static_cast<unsigned>(config.max_hops),
      static_cast<unsigned>(config.route_ttl_s),
      static_cast<unsigned>(config.fallback_ttl),
      static_cast<unsigned>(config.ack_timeout_ms),
      static_cast<unsigned>(config.max_timeout_retries),
      meshEchoBool(config.retry_after_fallback),
      meshEchoBool(config.ble_enabled),
      meshEchoBool(config.wifi_enabled));
}

inline void formatMeshEchoSetResponse(const char* field, const char* value, char* out, std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(
      out,
      out_size,
      "{\"ok\":true,\"field\":\"%s\",\"value\":\"%s\",\"needs_save\":true}",
      field == nullptr ? "" : field,
      value == nullptr ? "" : value);
}

inline void formatMeshEchoSaveResponse(bool saved, char* out, std::size_t out_size) {
  if (out == nullptr || out_size == 0) {
    return;
  }
  std::snprintf(
      out,
      out_size,
      "{\"ok\":%s,\"saved\":%s,\"message\":\"%s\"}",
      meshEchoBool(saved),
      meshEchoBool(saved),
      saved ? "config persisted" : "config save failed");
}

inline MeshEchoConfigCommandResult handleMeshEchoConfigCommand(const char* raw_line,
                                                               MeshEchoConfig& config,
                                                               const MeshEchoRuntimeInfo& runtime,
                                                               char* response,
                                                               std::size_t response_size) {
  MeshEchoConfigCommandResult result{};
  char line[192]{};
  if (raw_line == nullptr) {
    result.handled = true;
    formatMeshEchoErrorResponse("empty command", response, response_size);
    return result;
  }
  std::snprintf(line, sizeof(line), "%s", raw_line);
  char* trimmed = meshEchoTrimLeft(line);
  meshEchoTrimRight(trimmed);
  if (*trimmed == '\0') {
    result.handled = true;
    formatMeshEchoErrorResponse("empty command", response, response_size);
    return result;
  }
  if (meshEchoStartsWithIgnoreCase(trimmed, "send ")) {
    return result;
  }

  result.handled = true;
  char* cursor = trimmed;
  char* command = meshEchoTakeToken(&cursor);
  if (meshEchoEqualsIgnoreCase(command, "version")) {
    result.ok = true;
    formatMeshEchoVersionResponse(runtime, response, response_size);
    return result;
  }
  if (meshEchoEqualsIgnoreCase(command, "show")) {
    result.ok = true;
    formatMeshEchoShowResponse(config, runtime, response, response_size);
    return result;
  }
  if (meshEchoEqualsIgnoreCase(command, "get")) {
    char* subject = meshEchoTakeToken(&cursor);
    if (!meshEchoEqualsIgnoreCase(subject, "config")) {
      formatMeshEchoErrorResponse("expected: get config", response, response_size);
      return result;
    }
    result.ok = true;
    formatMeshEchoConfigResponse(config, response, response_size);
    return result;
  }
  if (meshEchoEqualsIgnoreCase(command, "save")) {
    result.ok = true;
    result.save_requested = true;
    formatMeshEchoSaveResponse(true, response, response_size);
    return result;
  }
  if (meshEchoEqualsIgnoreCase(command, "reboot")) {
    result.ok = true;
    result.reboot_requested = true;
    std::snprintf(response, response_size, "{\"ok\":true,\"reboot\":true}");
    return result;
  }
  if (!meshEchoEqualsIgnoreCase(command, "set")) {
    formatMeshEchoErrorResponse("unknown command", response, response_size);
    return result;
  }

  char* field = meshEchoTakeToken(&cursor);
  char* value = meshEchoTrimLeft(cursor);
  meshEchoTrimRight(value);
  if (field == nullptr || value == nullptr || *value == '\0') {
    formatMeshEchoErrorResponse("expected: set <field> <value>", response, response_size);
    return result;
  }

  unsigned long parsed_unsigned = 0;
  long parsed_signed = 0;
  float parsed_float = 0.0f;
  bool parsed_bool = false;

  if (meshEchoEqualsIgnoreCase(field, "node_id")) {
    if (!meshEchoParseUnsigned(value, 1, 65534, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid node_id (expected 1..65534)", response, response_size);
      return result;
    }
    config.node_id = static_cast<std::uint16_t>(parsed_unsigned);
    result.node_id_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "callsign")) {
    if (!meshEchoSafeToken(value, sizeof(config.callsign))) {
      formatMeshEchoErrorResponse("invalid callsign (use 1..16 letters, digits, _, -, .)", response, response_size);
      return result;
    }
    std::snprintf(config.callsign, sizeof(config.callsign), "%s", value);
  } else if (meshEchoEqualsIgnoreCase(field, "region")) {
    if (!meshEchoSafeToken(value, sizeof(config.region))) {
      formatMeshEchoErrorResponse("invalid region", response, response_size);
      return result;
    }
    std::snprintf(config.region, sizeof(config.region), "%s", value);
  } else if (meshEchoEqualsIgnoreCase(field, "freq_mhz")) {
    if (!meshEchoParseFloat(value, 410.0f, 930.0f, &parsed_float)) {
      formatMeshEchoErrorResponse("invalid freq_mhz (expected 410..930)", response, response_size);
      return result;
    }
    config.freq_mhz = parsed_float;
    result.radio_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "bw_khz")) {
    if (!meshEchoParseFloat(value, 7.0f, 500.0f, &parsed_float)) {
      formatMeshEchoErrorResponse("invalid bw_khz (expected 7..500)", response, response_size);
      return result;
    }
    config.bw_khz = parsed_float;
    result.radio_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "sf")) {
    if (!meshEchoParseUnsigned(value, 6, 12, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid sf (expected 6..12)", response, response_size);
      return result;
    }
    config.sf = static_cast<std::uint8_t>(parsed_unsigned);
    result.radio_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "cr")) {
    if (!meshEchoParseUnsigned(value, 5, 8, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid cr (expected 5..8)", response, response_size);
      return result;
    }
    config.cr = static_cast<std::uint8_t>(parsed_unsigned);
    result.radio_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "tx_power")) {
    if (!meshEchoParseSigned(value, 2, 22, &parsed_signed)) {
      formatMeshEchoErrorResponse("invalid tx_power (expected 2..22)", response, response_size);
      return result;
    }
    config.tx_power_dbm = static_cast<std::int8_t>(parsed_signed);
    result.radio_changed = true;
  } else if (meshEchoEqualsIgnoreCase(field, "max_hops")) {
    if (!meshEchoParseUnsigned(value, 1, 6, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid max_hops (expected 1..6)", response, response_size);
      return result;
    }
    config.max_hops = static_cast<std::uint8_t>(parsed_unsigned);
  } else if (meshEchoEqualsIgnoreCase(field, "route_ttl_s")) {
    if (!meshEchoParseUnsigned(value, 10, 3600, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid route_ttl_s (expected 10..3600)", response, response_size);
      return result;
    }
    config.route_ttl_s = static_cast<std::uint16_t>(parsed_unsigned);
  } else if (meshEchoEqualsIgnoreCase(field, "fallback_ttl")) {
    if (!meshEchoParseUnsigned(value, 1, 6, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid fallback_ttl (expected 1..6)", response, response_size);
      return result;
    }
    config.fallback_ttl = static_cast<std::uint8_t>(parsed_unsigned);
  } else if (meshEchoEqualsIgnoreCase(field, "ack_timeout_ms")) {
    if (!meshEchoParseUnsigned(value, 200, 10000, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid ack_timeout_ms (expected 200..10000)", response, response_size);
      return result;
    }
    config.ack_timeout_ms = static_cast<std::uint16_t>(parsed_unsigned);
  } else if (meshEchoEqualsIgnoreCase(field, "max_timeout_retries")) {
    if (!meshEchoParseUnsigned(value, 0, 6, &parsed_unsigned)) {
      formatMeshEchoErrorResponse("invalid max_timeout_retries (expected 0..6)", response, response_size);
      return result;
    }
    config.max_timeout_retries = static_cast<std::uint8_t>(parsed_unsigned);
  } else if (meshEchoEqualsIgnoreCase(field, "retry_after_fallback")) {
    if (!meshEchoParseOnOff(value, &parsed_bool)) {
      formatMeshEchoErrorResponse("invalid retry_after_fallback (expected on/off)", response, response_size);
      return result;
    }
    config.retry_after_fallback = parsed_bool;
  } else if (meshEchoEqualsIgnoreCase(field, "ble")) {
    if (!meshEchoParseOnOff(value, &parsed_bool)) {
      formatMeshEchoErrorResponse("invalid ble (expected on/off)", response, response_size);
      return result;
    }
    config.ble_enabled = parsed_bool;
  } else if (meshEchoEqualsIgnoreCase(field, "wifi")) {
    if (!meshEchoParseOnOff(value, &parsed_bool)) {
      formatMeshEchoErrorResponse("invalid wifi (expected on/off)", response, response_size);
      return result;
    }
    config.wifi_enabled = parsed_bool;
  } else {
    formatMeshEchoErrorResponse("unknown field", response, response_size);
    return result;
  }

  result.ok = true;
  formatMeshEchoSetResponse(field, value, response, response_size);
  return result;
}

}  // namespace smart_calm
