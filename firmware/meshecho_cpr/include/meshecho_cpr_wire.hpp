#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "meshecho_cpr_core.hpp"

namespace meshecho_cpr {

constexpr std::uint16_t kCprWireMagic = 0x4D45;  // "ME" in little endian.
constexpr std::uint8_t kCprWireVersion = 2;
constexpr std::size_t kCprAppPayloadSize = 32;
// Fixed fields include both path.length and payload_len, but exclude the
// variable path, payload, and CRC bytes.
constexpr std::size_t kCprWireHeaderSize = 36;
constexpr std::size_t kCprWireCrcSize = 2;
constexpr std::size_t kCprMaxFrameSize =
    kCprWireHeaderSize + (kMaxPathNodes * sizeof(NodeId)) + kCprAppPayloadSize + kCprWireCrcSize;

enum class CprFrameType : std::uint8_t {
  RouteRequest = 1,
  RouteReply = 2,
  Data = 3,
  Ack = 4,
  Flood = 5,
};

struct CprWireFrame {
  CprFrameType type = CprFrameType::Data;
  NodeId src = 0;
  NodeId dst = 0;
  std::uint16_t sequence = 0;
  std::uint32_t flow_id = 0;
  std::uint32_t request_id = 0;
  // Source-clock metadata; receivers must not compare it with local millis().
  std::uint32_t created_at_ms = 0;
  // Duration remaining at this hop's physical TX start, not an absolute time.
  std::uint32_t remaining_budget_ms = 0;
  std::uint32_t route_generation = 0;
  std::uint8_t ttl = 0;
  std::uint8_t path_index = 0;
  std::uint8_t repair_index = kInitialRepair;
  std::uint8_t flags = 0;
  Path path{};
  std::uint8_t payload_len = 0;
  std::array<std::uint8_t, kCprAppPayloadSize> payload{};
};

struct CprEncodedFrame {
  std::array<std::uint8_t, kCprMaxFrameSize> bytes{};
  std::size_t size = 0;
};

inline std::uint16_t cprCrc16(const std::uint8_t* data, std::size_t length) {
  std::uint16_t crc = 0xFFFFU;
  for (std::size_t i = 0; i < length; ++i) {
    crc ^= static_cast<std::uint16_t>(data[i]) << 8U;
    for (std::uint8_t bit = 0; bit < 8; ++bit) {
      crc = (crc & 0x8000U) != 0U
                ? static_cast<std::uint16_t>((crc << 1U) ^ 0x1021U)
                : static_cast<std::uint16_t>(crc << 1U);
    }
  }
  return crc;
}

inline bool cprFrameTypeValid(CprFrameType type) {
  const auto value = static_cast<std::uint8_t>(type);
  return value >= static_cast<std::uint8_t>(CprFrameType::RouteRequest) &&
         value <= static_cast<std::uint8_t>(CprFrameType::Flood);
}

inline bool cprWirePathValid(const Path& path) {
  if (path.length == 0 || path.length > kMaxPathNodes) {
    return false;
  }
  for (std::size_t i = 0; i < path.length; ++i) {
    if (path.nodes[i] == 0 || path.nodes[i] == 0xFFFFU) {
      return false;
    }
    for (std::size_t j = 0; j < i; ++j) {
      if (path.nodes[i] == path.nodes[j]) {
        return false;
      }
    }
  }
  return true;
}

inline bool cprFrameValid(const CprWireFrame& frame) {
  if (!cprFrameTypeValid(frame.type) || frame.src == 0 || frame.src == 0xFFFFU ||
      frame.dst == 0 || frame.dst == 0xFFFFU || frame.flow_id == 0 ||
      frame.request_id != frame.flow_id || frame.repair_index > kRecoveryRepair ||
      !cprWirePathValid(frame.path) || frame.path_index >= frame.path.length ||
      frame.payload_len > kCprAppPayloadSize) {
    return false;
  }
  switch (frame.type) {
    case CprFrameType::RouteRequest:
      return frame.path.length >= 1U;
    case CprFrameType::RouteReply:
      return frame.path.length >= 2U;
    case CprFrameType::Data:
      return frame.path.length >= 2U;
    case CprFrameType::Ack:
      // Direct node ingress may inspect an ACK before serialization.  The
      // encode/decode paths below additionally enforce the zero-payload ACK
      // rule on the wire.
      return frame.path.length >= 2U;
    case CprFrameType::Flood:
      return frame.path.length >= 1U;
  }
  return false;
}

namespace detail {

inline bool putU8(CprEncodedFrame& encoded, std::uint8_t value) {
  if (encoded.size >= encoded.bytes.size()) {
    return false;
  }
  encoded.bytes[encoded.size++] = value;
  return true;
}

inline bool putU16(CprEncodedFrame& encoded, std::uint16_t value) {
  return putU8(encoded, static_cast<std::uint8_t>(value & 0xFFU)) &&
         putU8(encoded, static_cast<std::uint8_t>((value >> 8U) & 0xFFU));
}

inline bool putU32(CprEncodedFrame& encoded, std::uint32_t value) {
  return putU8(encoded, static_cast<std::uint8_t>(value & 0xFFU)) &&
         putU8(encoded, static_cast<std::uint8_t>((value >> 8U) & 0xFFU)) &&
         putU8(encoded, static_cast<std::uint8_t>((value >> 16U) & 0xFFU)) &&
         putU8(encoded, static_cast<std::uint8_t>((value >> 24U) & 0xFFU));
}

inline bool getU8(const std::uint8_t* bytes,
                  std::size_t length,
                  std::size_t& offset,
                  std::uint8_t* value) {
  if (bytes == nullptr || value == nullptr || offset >= length) {
    return false;
  }
  *value = bytes[offset++];
  return true;
}

inline bool getU16(const std::uint8_t* bytes,
                   std::size_t length,
                   std::size_t& offset,
                   std::uint16_t* value) {
  std::uint8_t lo = 0;
  std::uint8_t hi = 0;
  if (!getU8(bytes, length, offset, &lo) || !getU8(bytes, length, offset, &hi) || value == nullptr) {
    return false;
  }
  *value = static_cast<std::uint16_t>(lo) | (static_cast<std::uint16_t>(hi) << 8U);
  return true;
}

inline bool getU32(const std::uint8_t* bytes,
                   std::size_t length,
                   std::size_t& offset,
                   std::uint32_t* value) {
  std::uint16_t lo = 0;
  std::uint16_t hi = 0;
  if (!getU16(bytes, length, offset, &lo) || !getU16(bytes, length, offset, &hi) || value == nullptr) {
    return false;
  }
  *value = static_cast<std::uint32_t>(lo) | (static_cast<std::uint32_t>(hi) << 16U);
  return true;
}

}  // namespace detail

inline CprEncodedFrame encodeCprFrame(const CprWireFrame& frame) {
  CprEncodedFrame encoded{};
  if (!cprFrameValid(frame) ||
      (frame.type == CprFrameType::Ack && frame.payload_len != 0U)) {
    return encoded;
  }

  const auto putPath = [&]() {
    if (!detail::putU8(encoded, frame.path.length)) {
      return false;
    }
    for (std::uint8_t i = 0; i < frame.path.length; ++i) {
      if (!detail::putU16(encoded, frame.path.nodes[i])) {
        return false;
      }
    }
    return true;
  };

  if (!detail::putU16(encoded, kCprWireMagic) || !detail::putU8(encoded, kCprWireVersion) ||
      !detail::putU8(encoded, static_cast<std::uint8_t>(frame.type)) || !detail::putU16(encoded, frame.src) ||
      !detail::putU16(encoded, frame.dst) || !detail::putU16(encoded, frame.sequence) ||
      !detail::putU32(encoded, frame.flow_id) || !detail::putU32(encoded, frame.request_id) ||
      !detail::putU32(encoded, frame.created_at_ms) || !detail::putU32(encoded, frame.remaining_budget_ms) ||
      !detail::putU32(encoded, frame.route_generation) || !detail::putU8(encoded, frame.ttl) ||
      !detail::putU8(encoded, frame.path_index) || !detail::putU8(encoded, frame.repair_index) ||
      !detail::putU8(encoded, frame.flags) || !putPath() || !detail::putU8(encoded, frame.payload_len)) {
    encoded.size = 0;
    return encoded;
  }
  for (std::uint8_t i = 0; i < frame.payload_len; ++i) {
    if (!detail::putU8(encoded, frame.payload[i])) {
      encoded.size = 0;
      return encoded;
    }
  }
  if (!detail::putU16(encoded, cprCrc16(encoded.bytes.data(), encoded.size))) {
    encoded.size = 0;
  }
  return encoded;
}

inline bool decodeCprFrame(const std::uint8_t* bytes, std::size_t length, CprWireFrame* out) {
  if (bytes == nullptr || out == nullptr ||
      length < kCprWireHeaderSize + 1U + kCprWireCrcSize ||
      length > kCprMaxFrameSize) {
    return false;
  }
  std::uint16_t magic = 0;
  std::uint8_t version = 0;
  std::uint8_t type = 0;
  std::size_t offset = 0;
  if (!detail::getU16(bytes, length, offset, &magic) || !detail::getU8(bytes, length, offset, &version) ||
      !detail::getU8(bytes, length, offset, &type) || magic != kCprWireMagic || version != kCprWireVersion) {
    return false;
  }

  CprWireFrame frame{};
  frame.type = static_cast<CprFrameType>(type);
  if (!detail::getU16(bytes, length, offset, &frame.src) || !detail::getU16(bytes, length, offset, &frame.dst) ||
      !detail::getU16(bytes, length, offset, &frame.sequence) || !detail::getU32(bytes, length, offset, &frame.flow_id) ||
      !detail::getU32(bytes, length, offset, &frame.request_id) || !detail::getU32(bytes, length, offset, &frame.created_at_ms) ||
      !detail::getU32(bytes, length, offset, &frame.remaining_budget_ms) || !detail::getU32(bytes, length, offset, &frame.route_generation) ||
      !detail::getU8(bytes, length, offset, &frame.ttl) || !detail::getU8(bytes, length, offset, &frame.path_index) ||
      !detail::getU8(bytes, length, offset, &frame.repair_index) || !detail::getU8(bytes, length, offset, &frame.flags)) {
    return false;
  }
  if (!detail::getU8(bytes, length, offset, &frame.path.length) || frame.path.length == 0 ||
      frame.path.length > kMaxPathNodes) {
    return false;
  }
  for (std::uint8_t i = 0; i < frame.path.length; ++i) {
    if (!detail::getU16(bytes, length, offset, &frame.path.nodes[i])) {
      return false;
    }
  }
  if (!detail::getU8(bytes, length, offset, &frame.payload_len) || frame.payload_len > kCprAppPayloadSize ||
      offset + frame.payload_len + kCprWireCrcSize != length) {
    return false;
  }
  for (std::uint8_t i = 0; i < frame.payload_len; ++i) {
    if (!detail::getU8(bytes, length, offset, &frame.payload[i])) {
      return false;
    }
  }
  std::uint16_t received_crc = 0;
  if (!detail::getU16(bytes, length, offset, &received_crc) ||
      received_crc != cprCrc16(bytes, length - kCprWireCrcSize) ||
      !cprFrameValid(frame) ||
      (frame.type == CprFrameType::Ack && frame.payload_len != 0U)) {
    return false;
  }
  *out = frame;
  return true;
}

}  // namespace meshecho_cpr
