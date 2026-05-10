#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "smart_calm_types.hpp"

namespace smart_calm {

struct EncodedFrame {
  std::array<std::uint8_t, kWireMaxFrameSize> bytes{};
  std::size_t size = 0;
};

inline std::uint16_t crc16Ccitt(const std::uint8_t* data, std::size_t len) {
  std::uint16_t crc = 0xFFFF;
  for (std::size_t i = 0; i < len; ++i) {
    crc ^= static_cast<std::uint16_t>(data[i]) << 8;
    for (std::uint8_t bit = 0; bit < 8; ++bit) {
      if ((crc & 0x8000U) != 0U) {
        crc = static_cast<std::uint16_t>((crc << 1U) ^ 0x1021U);
      } else {
        crc = static_cast<std::uint16_t>(crc << 1U);
      }
    }
  }
  return crc;
}

inline void putU8(EncodedFrame& encoded, std::uint8_t value) {
  encoded.bytes[encoded.size++] = value;
}

inline void putU16(EncodedFrame& encoded, std::uint16_t value) {
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>(value & 0xFFU);
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
}

inline void putU32(EncodedFrame& encoded, std::uint32_t value) {
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>(value & 0xFFU);
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>((value >> 8U) & 0xFFU);
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>((value >> 16U) & 0xFFU);
  encoded.bytes[encoded.size++] = static_cast<std::uint8_t>((value >> 24U) & 0xFFU);
}

inline bool getU8(const std::uint8_t* bytes, std::size_t len, std::size_t& offset, std::uint8_t* value) {
  if (value == nullptr || offset + 1U > len) {
    return false;
  }
  *value = bytes[offset++];
  return true;
}

inline bool getU16(const std::uint8_t* bytes, std::size_t len, std::size_t& offset, std::uint16_t* value) {
  if (value == nullptr || offset + 2U > len) {
    return false;
  }
  *value = static_cast<std::uint16_t>(bytes[offset]) |
           (static_cast<std::uint16_t>(bytes[offset + 1U]) << 8U);
  offset += 2U;
  return true;
}

inline bool getU32(const std::uint8_t* bytes, std::size_t len, std::size_t& offset, std::uint32_t* value) {
  if (value == nullptr || offset + 4U > len) {
    return false;
  }
  *value = static_cast<std::uint32_t>(bytes[offset]) |
           (static_cast<std::uint32_t>(bytes[offset + 1U]) << 8U) |
           (static_cast<std::uint32_t>(bytes[offset + 2U]) << 16U) |
           (static_cast<std::uint32_t>(bytes[offset + 3U]) << 24U);
  offset += 4U;
  return true;
}

inline EncodedFrame encodeWireFrame(const WireFrame& frame) {
  EncodedFrame encoded{};
  const std::uint8_t payload_len =
      frame.payload_len > kWirePayloadSize ? static_cast<std::uint8_t>(kWirePayloadSize) : frame.payload_len;

  putU16(encoded, kWireMagic);
  putU8(encoded, kWireVersion);
  putU8(encoded, static_cast<std::uint8_t>(frame.type));
  putU16(encoded, frame.src);
  putU16(encoded, frame.dst);
  putU16(encoded, frame.seq);
  putU32(encoded, frame.flow_id);
  putU32(encoded, frame.created_at_ms);
  putU8(encoded, frame.ttl);
  putU8(encoded, frame.state_index);
  putU8(encoded, frame.action_index);
  putU8(encoded, frame.flags);
  putU16(encoded, frame.confidence_milli);
  putU8(encoded, payload_len);
  for (std::uint8_t i = 0; i < payload_len; ++i) {
    putU8(encoded, static_cast<std::uint8_t>(frame.payload[i]));
  }
  const std::uint16_t crc = crc16Ccitt(encoded.bytes.data(), encoded.size);
  putU16(encoded, crc);
  return encoded;
}

inline bool decodeWireFrame(const std::uint8_t* bytes, std::size_t len, WireFrame* out) {
  if (bytes == nullptr || out == nullptr || len < kWireMinFrameSize || len > kWireMaxFrameSize) {
    return false;
  }
  std::size_t offset = 0;
  std::uint16_t magic = 0;
  std::uint8_t version = 0;
  std::uint8_t frame_type = 0;
  std::uint16_t received_crc = 0;
  if (!getU16(bytes, len, offset, &magic) || !getU8(bytes, len, offset, &version) ||
      !getU8(bytes, len, offset, &frame_type)) {
    return false;
  }
  if (magic != kWireMagic || version != kWireVersion || frame_type < static_cast<std::uint8_t>(FrameType::Hello) ||
      frame_type > static_cast<std::uint8_t>(FrameType::Ack)) {
    return false;
  }

  WireFrame frame{};
  frame.version = version;
  frame.type = static_cast<FrameType>(frame_type);
  if (!getU16(bytes, len, offset, &frame.src) || !getU16(bytes, len, offset, &frame.dst) ||
      !getU16(bytes, len, offset, &frame.seq) || !getU32(bytes, len, offset, &frame.flow_id) ||
      !getU32(bytes, len, offset, &frame.created_at_ms) || !getU8(bytes, len, offset, &frame.ttl) ||
      !getU8(bytes, len, offset, &frame.state_index) || !getU8(bytes, len, offset, &frame.action_index) ||
      !getU8(bytes, len, offset, &frame.flags) || !getU16(bytes, len, offset, &frame.confidence_milli) ||
      !getU8(bytes, len, offset, &frame.payload_len)) {
    return false;
  }
  if (frame.payload_len > kWirePayloadSize || offset + frame.payload_len + kWireCrcSize != len) {
    return false;
  }
  if (frame.payload_len > 0) {
    std::memcpy(frame.payload, bytes + offset, frame.payload_len);
    offset += frame.payload_len;
  }
  if (!getU16(bytes, len, offset, &received_crc)) {
    return false;
  }
  const std::uint16_t computed_crc = crc16Ccitt(bytes, len - kWireCrcSize);
  if (received_crc != computed_crc) {
    return false;
  }
  *out = frame;
  return true;
}

}  // namespace smart_calm
