#include <cstddef>
#include <cstdint>

#include <unity.h>

#include "meshecho_cpr_wire.hpp"

using namespace meshecho_cpr;

namespace {

CprWireFrame sampleDataFrame() {
  CprWireFrame frame{};
  frame.type = CprFrameType::Data;
  frame.src = 1;
  frame.dst = 2;
  frame.sequence = 0x4321U;
  frame.flow_id = 0x12345678U;
  frame.request_id = frame.flow_id;
  frame.created_at_ms = 1000;
  frame.remaining_budget_ms = 5000;
  frame.route_generation = 7;
  frame.ttl = 5;
  frame.path_index = 1;
  frame.repair_index = kRepeatRepair;
  frame.flags = 0xA5U;
  frame.path.length = 3;
  frame.path.nodes[0] = 1;
  frame.path.nodes[1] = 2;
  frame.path.nodes[2] = 3;
  frame.payload_len = 3;
  frame.payload[0] = 'o';
  frame.payload[1] = 'k';
  frame.payload[2] = '!';
  return frame;
}

void refreshCrc(CprEncodedFrame& encoded) {
  const std::uint16_t crc =
      cprCrc16(encoded.bytes.data(), encoded.size - kCprWireCrcSize);
  encoded.bytes[encoded.size - 2U] = static_cast<std::uint8_t>(crc);
  encoded.bytes[encoded.size - 1U] = static_cast<std::uint8_t>(crc >> 8U);
}

}  // namespace

void testCprWireRoundTripPreservesIdentity() {
  const CprWireFrame frame = sampleDataFrame();
  const CprEncodedFrame encoded = encodeCprFrame(frame);
  TEST_ASSERT_GREATER_THAN_UINT32(kCprWireHeaderSize, encoded.size);

  CprWireFrame decoded{};
  TEST_ASSERT_TRUE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  TEST_ASSERT_EQUAL_UINT8(static_cast<std::uint8_t>(frame.type),
                          static_cast<std::uint8_t>(decoded.type));
  TEST_ASSERT_EQUAL_UINT16(frame.src, decoded.src);
  TEST_ASSERT_EQUAL_UINT16(frame.dst, decoded.dst);
  TEST_ASSERT_EQUAL_UINT16(frame.sequence, decoded.sequence);
  TEST_ASSERT_EQUAL_UINT32(frame.flow_id, decoded.flow_id);
  TEST_ASSERT_EQUAL_UINT32(frame.request_id, decoded.request_id);
  TEST_ASSERT_EQUAL_UINT32(frame.created_at_ms, decoded.created_at_ms);
  TEST_ASSERT_EQUAL_UINT32(frame.remaining_budget_ms, decoded.remaining_budget_ms);
  TEST_ASSERT_EQUAL_UINT32(frame.route_generation, decoded.route_generation);
  TEST_ASSERT_EQUAL_UINT8(frame.ttl, decoded.ttl);
  TEST_ASSERT_EQUAL_UINT8(frame.path_index, decoded.path_index);
  TEST_ASSERT_EQUAL_UINT8(frame.repair_index, decoded.repair_index);
  TEST_ASSERT_EQUAL_UINT8(frame.flags, decoded.flags);
  TEST_ASSERT_TRUE(frame.path == decoded.path);
  TEST_ASSERT_EQUAL_UINT8(frame.payload_len, decoded.payload_len);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(frame.payload.data(), decoded.payload.data(),
                               frame.payload_len);
}

void testCprWireMaximumPathAndPayloadRoundTrip() {
  CprWireFrame frame = sampleDataFrame();
  frame.path.length = static_cast<std::uint8_t>(kMaxPathNodes);
  for (std::size_t i = 0; i < kMaxPathNodes; ++i) {
    frame.path.nodes[i] = static_cast<NodeId>(i + 1U);
  }
  frame.payload_len = static_cast<std::uint8_t>(kCprAppPayloadSize);
  for (std::size_t i = 0; i < kCprAppPayloadSize; ++i) {
    frame.payload[i] = static_cast<std::uint8_t>(i);
  }

  const CprEncodedFrame encoded = encodeCprFrame(frame);
  TEST_ASSERT_EQUAL_UINT32(kCprMaxFrameSize, encoded.size);
  CprWireFrame decoded{};
  TEST_ASSERT_TRUE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  TEST_ASSERT_TRUE(frame.path == decoded.path);
  TEST_ASSERT_EQUAL_UINT8_ARRAY(frame.payload.data(), decoded.payload.data(),
                               kCprAppPayloadSize);
}

void testCprWireCrcRejectsEverySingleByteMutation() {
  const CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  for (std::size_t i = 0; i < encoded.size; ++i) {
    CprEncodedFrame mutated = encoded;
    mutated.bytes[i] ^= 0x01U;
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(mutated.bytes.data(), mutated.size, &decoded));
  }
}

void testCprWireRejectsUnknownVersionWithValidCrc() {
  CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  encoded.bytes[2] = static_cast<std::uint8_t>(kCprWireVersion + 1U);
  refreshCrc(encoded);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
}

void testCprWireBudgetRoundTripRejectsLegacyVersionWithValidCrc() {
  CprWireFrame frame = sampleDataFrame();
  frame.created_at_ms = 0xFFFFFFF0U;
  frame.remaining_budget_ms = 1234U;
  CprEncodedFrame encoded = encodeCprFrame(frame);
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);

  CprWireFrame decoded{};
  TEST_ASSERT_TRUE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  TEST_ASSERT_EQUAL_UINT32(frame.created_at_ms, decoded.created_at_ms);
  TEST_ASSERT_EQUAL_UINT32(1234U, decoded.remaining_budget_ms);

  encoded.bytes[2] = 1U;
  refreshCrc(encoded);
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
}

void testCprWireRejectsTruncationAndTrailingBytes() {
  const CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  TEST_ASSERT_GREATER_THAN_UINT32(0, encoded.size);
  for (std::size_t length = 0; length < encoded.size; ++length) {
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), length, &decoded));
  }

  CprEncodedFrame extended = encoded;
  ++extended.size;
  refreshCrc(extended);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(extended.bytes.data(), extended.size, &decoded));
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), kCprMaxFrameSize + 1U,
                                  &decoded));
}

void testCprWireRejectsNullDecodeArguments() {
  const CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(nullptr, encoded.size, &decoded));
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, nullptr));
}

void testCprWireRejectsReservedSourceAddresses() {
  for (const NodeId source : {NodeId{0}, NodeId{0xFFFFU}}) {
    CprWireFrame frame = sampleDataFrame();
    frame.src = source;
    TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);

    CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
    encoded.bytes[4] = static_cast<std::uint8_t>(source);
    encoded.bytes[5] = static_cast<std::uint8_t>(source >> 8U);
    refreshCrc(encoded);
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  }
}

void testCprWireRejectsReservedPathNodes() {
  for (const NodeId node : {NodeId{0}, NodeId{0xFFFFU}}) {
    CprWireFrame frame = sampleDataFrame();
    frame.path.nodes[1] = node;
    TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);

    CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
    encoded.bytes[37] = static_cast<std::uint8_t>(node);
    encoded.bytes[38] = static_cast<std::uint8_t>(node >> 8U);
    refreshCrc(encoded);
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  }
}

void testCprWireRejectsInvalidEnvelopeFields() {
  for (const auto type : {std::uint8_t{0}, std::uint8_t{6}}) {
    CprWireFrame frame = sampleDataFrame();
    frame.type = static_cast<CprFrameType>(type);
    TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);
    CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
    encoded.bytes[3] = type;
    refreshCrc(encoded);
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  }

  for (const NodeId destination : {NodeId{0}, NodeId{0xFFFFU}}) {
    CprWireFrame frame = sampleDataFrame();
    frame.dst = destination;
    TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);
    CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
    encoded.bytes[6] = static_cast<std::uint8_t>(destination);
    encoded.bytes[7] = static_cast<std::uint8_t>(destination >> 8U);
    refreshCrc(encoded);
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  }

  CprWireFrame frame = sampleDataFrame();
  frame.flow_id = 0;
  frame.request_id = 0;
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);
  frame = sampleDataFrame();
  ++frame.request_id;
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);
  frame = sampleDataFrame();
  frame.repair_index = static_cast<std::uint8_t>(kRecoveryRepair + 1U);
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);

  CprEncodedFrame request_mismatch = encodeCprFrame(sampleDataFrame());
  request_mismatch.bytes[14] ^= 0x01U;
  refreshCrc(request_mismatch);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(request_mismatch.bytes.data(),
                                  request_mismatch.size, &decoded));
  CprEncodedFrame invalid_marker = encodeCprFrame(sampleDataFrame());
  invalid_marker.bytes[32] = static_cast<std::uint8_t>(kRecoveryRepair + 1U);
  refreshCrc(invalid_marker);
  TEST_ASSERT_FALSE(decodeCprFrame(invalid_marker.bytes.data(), invalid_marker.size,
                                  &decoded));
}

void testCprWireRejectsInvalidPathShape() {
  for (const std::uint8_t length : {std::uint8_t{0},
                                  static_cast<std::uint8_t>(kMaxPathNodes + 1U)}) {
    CprWireFrame frame = sampleDataFrame();
    frame.path.length = length;
    TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);
    CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
    encoded.bytes[34] = length;
    refreshCrc(encoded);
    CprWireFrame decoded{};
    TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
  }

  CprWireFrame loop = sampleDataFrame();
  loop.path.nodes[2] = loop.path.nodes[0];
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(loop).size);
  CprEncodedFrame encoded_loop = encodeCprFrame(sampleDataFrame());
  encoded_loop.bytes[39] = 1;
  encoded_loop.bytes[40] = 0;
  refreshCrc(encoded_loop);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(encoded_loop.bytes.data(), encoded_loop.size,
                                  &decoded));

  CprWireFrame invalid_index = sampleDataFrame();
  invalid_index.path_index = invalid_index.path.length;
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(invalid_index).size);
  CprEncodedFrame encoded_index = encodeCprFrame(sampleDataFrame());
  encoded_index.bytes[31] = invalid_index.path_index;
  refreshCrc(encoded_index);
  TEST_ASSERT_FALSE(decodeCprFrame(encoded_index.bytes.data(), encoded_index.size,
                                  &decoded));

  CprWireFrame too_short = sampleDataFrame();
  too_short.path.length = 1;
  too_short.path_index = 0;
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(too_short).size);
}

void testCprWireRejectsOversizedPayload() {
  CprWireFrame frame = sampleDataFrame();
  frame.payload_len = static_cast<std::uint8_t>(kCprAppPayloadSize + 1U);
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(frame).size);

  CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  encoded.bytes[41] = frame.payload_len;
  refreshCrc(encoded);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
}

void testCprWireRejectsAckPayload() {
  CprWireFrame ack = sampleDataFrame();
  ack.type = CprFrameType::Ack;
  ack.src = 3;
  ack.dst = 2;
  ack.payload_len = 0;
  const CprEncodedFrame valid = encodeCprFrame(ack);
  TEST_ASSERT_GREATER_THAN_UINT32(0, valid.size);
  CprWireFrame decoded{};
  TEST_ASSERT_TRUE(decodeCprFrame(valid.bytes.data(), valid.size, &decoded));

  ack.payload_len = 1;
  TEST_ASSERT_EQUAL_UINT32(0, encodeCprFrame(ack).size);
  CprEncodedFrame encoded_payload = encodeCprFrame(sampleDataFrame());
  encoded_payload.bytes[3] = static_cast<std::uint8_t>(CprFrameType::Ack);
  refreshCrc(encoded_payload);
  TEST_ASSERT_FALSE(decodeCprFrame(encoded_payload.bytes.data(),
                                  encoded_payload.size, &decoded));
}

void testCprWireRoundTripsMinimumFloodAndRouteRequest() {
  for (const CprFrameType type : {CprFrameType::Flood, CprFrameType::RouteRequest}) {
    CprWireFrame frame = sampleDataFrame();
    frame.type = type;
    frame.dst = 3;
    frame.path.length = 1;
    frame.path_index = 0;
    frame.payload_len = 0;
    const CprEncodedFrame encoded = encodeCprFrame(frame);
    TEST_ASSERT_EQUAL_UINT32(kCprWireHeaderSize + sizeof(NodeId) + kCprWireCrcSize,
                             encoded.size);
    CprWireFrame decoded{};
    TEST_ASSERT_TRUE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
    TEST_ASSERT_TRUE(frame.path == decoded.path);
    TEST_ASSERT_EQUAL_UINT8(0, decoded.payload_len);
  }
}

void testCprWireRejectsInvalidMagicWithValidCrc() {
  CprEncodedFrame encoded = encodeCprFrame(sampleDataFrame());
  encoded.bytes[0] ^= 0x01U;
  refreshCrc(encoded);
  CprWireFrame decoded{};
  TEST_ASSERT_FALSE(decodeCprFrame(encoded.bytes.data(), encoded.size, &decoded));
}

void runCprWireTests() {
  RUN_TEST(testCprWireRoundTripPreservesIdentity);
  RUN_TEST(testCprWireMaximumPathAndPayloadRoundTrip);
  RUN_TEST(testCprWireCrcRejectsEverySingleByteMutation);
  RUN_TEST(testCprWireRejectsUnknownVersionWithValidCrc);
  RUN_TEST(testCprWireBudgetRoundTripRejectsLegacyVersionWithValidCrc);
  RUN_TEST(testCprWireRejectsTruncationAndTrailingBytes);
  RUN_TEST(testCprWireRejectsNullDecodeArguments);
  RUN_TEST(testCprWireRejectsReservedSourceAddresses);
  RUN_TEST(testCprWireRejectsReservedPathNodes);
  RUN_TEST(testCprWireRejectsInvalidEnvelopeFields);
  RUN_TEST(testCprWireRejectsInvalidPathShape);
  RUN_TEST(testCprWireRejectsOversizedPayload);
  RUN_TEST(testCprWireRejectsAckPayload);
  RUN_TEST(testCprWireRoundTripsMinimumFloodAndRouteRequest);
  RUN_TEST(testCprWireRejectsInvalidMagicWithValidCrc);
}
