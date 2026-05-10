#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "smart_calm_controller.hpp"
#include "smart_calm_types.hpp"

namespace smart_calm {

constexpr std::size_t kMaxRouteHops = 6;
constexpr std::size_t kMaxRouteCacheEntries = 8;
constexpr std::size_t kMaxPendingFlows = 4;
constexpr std::size_t kMaxSeenRequests = 12;
constexpr std::size_t kMaxOutboundFrames = 3;
constexpr std::uint8_t kDefaultRreqTtl = 6;
constexpr std::uint8_t kDefaultDataTtl = 6;
constexpr std::uint8_t kDefaultAckTtl = 6;

struct RoutePayload {
  std::uint8_t path_len = 0;
  std::uint8_t path_index = 0;
  std::uint8_t app_len = 0;
  std::uint16_t path[kMaxRouteHops] = {};
  std::uint8_t app[kWirePayloadSize - 2 - 2 * kMaxRouteHops] = {};
};

struct OutboundFrame {
  WireFrame frame{};
  bool broadcast = false;
};

inline float confidenceFromSnr(float snr) {
  if (snr <= -8.0f) {
    return 0.15f;
  }
  if (snr >= 10.0f) {
    return 0.98f;
  }
  return clampFloat((snr + 8.0f) / 18.0f, 0.15f, 0.98f);
}

inline std::uint16_t confidenceMilli(float confidence) {
  return static_cast<std::uint16_t>(clampFloat(confidence, 0.0f, 1.0f) * 1000.0f);
}

inline bool encodeRoutePayload(WireFrame& frame, const RoutePayload& route) {
  if (route.path_len == 0 || route.path_len > kMaxRouteHops || route.path_index >= route.path_len ||
      route.app_len > sizeof(route.app)) {
    return false;
  }
  const std::size_t len = 2U + static_cast<std::size_t>(route.path_len) * 2U + route.app_len;
  if (len > kWirePayloadSize) {
    return false;
  }

  frame.payload[0] = static_cast<char>(route.path_len);
  frame.payload[1] = static_cast<char>(route.path_index);
  std::size_t offset = 2;
  for (std::uint8_t i = 0; i < route.path_len; ++i) {
    const std::uint16_t node = route.path[i];
    frame.payload[offset++] = static_cast<char>(node & 0xFFU);
    frame.payload[offset++] = static_cast<char>((node >> 8U) & 0xFFU);
  }
  for (std::uint8_t i = 0; i < route.app_len; ++i) {
    frame.payload[offset++] = static_cast<char>(route.app[i]);
  }
  frame.payload_len = static_cast<std::uint8_t>(len);
  return true;
}

inline bool decodeRoutePayload(const WireFrame& frame, RoutePayload* out) {
  if (out == nullptr || frame.payload_len < 2) {
    return false;
  }

  RoutePayload route{};
  route.path_len = static_cast<std::uint8_t>(frame.payload[0]);
  route.path_index = static_cast<std::uint8_t>(frame.payload[1]);
  if (route.path_len == 0 || route.path_len > kMaxRouteHops || route.path_index >= route.path_len) {
    return false;
  }
  const std::size_t route_bytes = 2U + static_cast<std::size_t>(route.path_len) * 2U;
  if (route_bytes > frame.payload_len) {
    return false;
  }
  std::size_t offset = 2;
  for (std::uint8_t i = 0; i < route.path_len; ++i) {
    const std::uint8_t lo = static_cast<std::uint8_t>(frame.payload[offset++]);
    const std::uint8_t hi = static_cast<std::uint8_t>(frame.payload[offset++]);
    route.path[i] = static_cast<std::uint16_t>(lo) | (static_cast<std::uint16_t>(hi) << 8U);
  }
  route.app_len = static_cast<std::uint8_t>(frame.payload_len - route_bytes);
  if (route.app_len > sizeof(route.app)) {
    return false;
  }
  for (std::uint8_t i = 0; i < route.app_len; ++i) {
    route.app[i] = static_cast<std::uint8_t>(frame.payload[offset++]);
  }
  *out = route;
  return true;
}

class SmartCalmMesh {
 public:
  explicit SmartCalmMesh(std::uint16_t node_id) : node_id_(node_id) {}

  std::uint16_t nodeId() const {
    return node_id_;
  }

  std::size_t sendApp(std::uint16_t dst,
                      std::uint32_t flow_id,
                      const std::uint8_t* payload,
                      std::size_t payload_len,
                      std::uint32_t now_ms,
                      std::uint32_t entropy,
                      SmartCalmController& controller,
                      Snapshot& snapshot,
                      OutboundFrame* out,
                      std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0 || payload == nullptr || payload_len > kWirePayloadSize) {
      return 0;
    }
    snapshot.unicast_flows++;
    controller.beginFlow(flow_id, snapshot, entropy, now_ms);

    if (RouteEntry* route = findRoute(dst, now_ms, controller.activeProfile().route_ttl_s)) {
      snapshot.route_cache_hits++;
      return emitDataFromRoute(*route, flow_id, payload, payload_len, now_ms, controller, snapshot, out, out_capacity);
    }

    snapshot.route_cache_misses++;
    controller.markRouteMiss(flow_id);
    PendingFlow& pending = acquirePending(flow_id);
    pending.active = true;
    pending.dst = dst;
    pending.flow_id = flow_id;
    pending.created_at_ms = now_ms;
    pending.payload_len = static_cast<std::uint8_t>(std::min<std::size_t>(payload_len, sizeof(pending.payload)));
    std::memcpy(pending.payload, payload, pending.payload_len);
    return emitRreq(dst, flow_id, now_ms, out, out_capacity);
  }

  std::size_t handleFrame(const WireFrame& frame,
                          std::uint32_t now_ms,
                          float rssi,
                          float snr,
                          SmartCalmController& controller,
                          Snapshot& snapshot,
                          OutboundFrame* out,
                          std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0 || frame.src == node_id_) {
      return 0;
    }
    switch (frame.type) {
      case FrameType::Rreq:
        return handleRreq(frame, now_ms, snr, out, out_capacity);
      case FrameType::Rrep:
        return handleRrep(frame, now_ms, snr, controller, snapshot, out, out_capacity);
      case FrameType::Data:
        return handleData(frame, now_ms, snr, controller, snapshot, out, out_capacity);
      case FrameType::Fallback:
        return handleFallback(frame, now_ms, snr, controller, snapshot, out, out_capacity);
      case FrameType::Ack:
        return handleAck(frame, now_ms, controller, snapshot, out, out_capacity);
      case FrameType::Hello:
      case FrameType::Status:
        snapshot.broadcast_flows++;
        snapshot.broadcast_deliveries++;
        return 0;
    }
    return 0;
  }

 private:
  struct RouteEntry {
    bool active = false;
    std::uint16_t dst = 0;
    std::uint8_t path_len = 0;
    std::uint16_t path[kMaxRouteHops] = {};
    float confidence = 0.0f;
    std::uint32_t updated_at_ms = 0;
  };

  struct PendingFlow {
    bool active = false;
    std::uint16_t dst = 0;
    std::uint32_t flow_id = 0;
    std::uint32_t created_at_ms = 0;
    std::uint8_t payload_len = 0;
    std::uint8_t payload[kWirePayloadSize] = {};
  };

  struct SeenRequest {
    bool active = false;
    std::uint16_t src = 0;
    std::uint16_t dst = 0;
    std::uint32_t flow_id = 0;
    std::uint32_t seen_at_ms = 0;
  };

  std::uint16_t node_id_;
  std::uint16_t next_seq_ = 1;
  std::array<RouteEntry, kMaxRouteCacheEntries> routes_{};
  std::array<PendingFlow, kMaxPendingFlows> pending_{};
  std::array<SeenRequest, kMaxSeenRequests> seen_{};

  WireFrame baseFrame(FrameType type, std::uint16_t dst, std::uint32_t flow_id, std::uint32_t now_ms) {
    WireFrame frame{};
    frame.type = type;
    frame.src = node_id_;
    frame.dst = dst;
    frame.seq = next_seq_++;
    frame.flow_id = flow_id;
    frame.created_at_ms = now_ms;
    frame.version = kWireVersion;
    return frame;
  }

  RouteEntry* findRoute(std::uint16_t dst, std::uint32_t now_ms, float route_ttl_s) {
    for (auto& route : routes_) {
      if (!route.active || route.dst != dst) {
        continue;
      }
      const float age_s = static_cast<float>(now_ms - route.updated_at_ms) / 1000.0f;
      if (age_s <= route_ttl_s) {
        return &route;
      }
      route.active = false;
    }
    return nullptr;
  }

  RouteEntry& acquireRoute(std::uint16_t dst) {
    for (auto& route : routes_) {
      if (route.active && route.dst == dst) {
        return route;
      }
    }
    for (auto& route : routes_) {
      if (!route.active) {
        return route;
      }
    }
    return routes_[0];
  }

  PendingFlow& acquirePending(std::uint32_t flow_id) {
    for (auto& pending : pending_) {
      if (pending.active && pending.flow_id == flow_id) {
        return pending;
      }
    }
    for (auto& pending : pending_) {
      if (!pending.active) {
        return pending;
      }
    }
    return pending_[0];
  }

  PendingFlow* findPending(std::uint32_t flow_id) {
    for (auto& pending : pending_) {
      if (pending.active && pending.flow_id == flow_id) {
        return &pending;
      }
    }
    return nullptr;
  }

  bool markSeen(const WireFrame& frame, std::uint32_t now_ms) {
    for (auto& seen : seen_) {
      if (seen.active && seen.src == frame.src && seen.dst == frame.dst && seen.flow_id == frame.flow_id) {
        return false;
      }
    }
    for (auto& seen : seen_) {
      if (!seen.active || now_ms - seen.seen_at_ms > 60000U) {
        seen.active = true;
        seen.src = frame.src;
        seen.dst = frame.dst;
        seen.flow_id = frame.flow_id;
        seen.seen_at_ms = now_ms;
        return true;
      }
    }
    seen_[0] = SeenRequest{true, frame.src, frame.dst, frame.flow_id, now_ms};
    return true;
  }

  void cacheRouteFromPath(std::uint16_t dst,
                          const RoutePayload& route_payload,
                          std::uint32_t now_ms,
                          float confidence) {
    RouteEntry& route = acquireRoute(dst);
    route.active = true;
    route.dst = dst;
    route.path_len = route_payload.path_len;
    for (std::uint8_t i = 0; i < route_payload.path_len; ++i) {
      route.path[i] = route_payload.path[i];
    }
    route.confidence = confidence;
    route.updated_at_ms = now_ms;
  }

  std::size_t pushOutbound(const WireFrame& frame,
                           bool broadcast,
                           OutboundFrame* out,
                           std::size_t out_capacity) const {
    if (out_capacity == 0) {
      return 0;
    }
    out[0].frame = frame;
    out[0].broadcast = broadcast;
    return 1;
  }

  std::size_t emitRreq(std::uint16_t dst,
                       std::uint32_t flow_id,
                       std::uint32_t now_ms,
                       OutboundFrame* out,
                       std::size_t out_capacity) {
    RoutePayload route{};
    route.path_len = 1;
    route.path_index = 0;
    route.path[0] = node_id_;

    WireFrame frame = baseFrame(FrameType::Rreq, kBroadcastAddress, flow_id, now_ms);
    frame.ttl = kDefaultRreqTtl;
    frame.flags = 0;
    frame.confidence_milli = 1000;
    if (!encodeRoutePayload(frame, route)) {
      return 0;
    }
    frame.dst = kBroadcastAddress;
    frame.flags = static_cast<std::uint8_t>(dst & 0xFFU);
    return pushOutbound(frame, true, out, out_capacity);
  }

  std::size_t emitDataFromRoute(const RouteEntry& route,
                                std::uint32_t flow_id,
                                const std::uint8_t* payload,
                                std::size_t payload_len,
                                std::uint32_t now_ms,
                                SmartCalmController& controller,
                                Snapshot& snapshot,
                                OutboundFrame* out,
                                std::size_t out_capacity) {
    if (route.path_len < 2 || route.path[0] != node_id_ || payload_len > sizeof(RoutePayload::app)) {
      return 0;
    }
    RoutePayload route_payload{};
    route_payload.path_len = route.path_len;
    route_payload.path_index = 1;
    route_payload.app_len = static_cast<std::uint8_t>(payload_len);
    for (std::uint8_t i = 0; i < route.path_len; ++i) {
      route_payload.path[i] = route.path[i];
    }
    std::memcpy(route_payload.app, payload, payload_len);

    WireFrame frame = baseFrame(FrameType::Data, route.path[1], flow_id, now_ms);
    frame.ttl = kDefaultDataTtl;
    frame.state_index = controller.activeStateIndex();
    frame.action_index = controller.activeProfileIndex();
    frame.confidence_milli = confidenceMilli(route.confidence);
    if (!encodeRoutePayload(frame, route_payload)) {
      return 0;
    }
    snapshot.path_confidence_total += route.confidence;
    snapshot.path_confidence_samples++;
    controller.markConfidence(flow_id, route.confidence);
    return pushOutbound(frame, false, out, out_capacity);
  }

  std::size_t handleRreq(const WireFrame& frame,
                         std::uint32_t now_ms,
                         float snr,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    if (frame.ttl <= 1 || !markSeen(frame, now_ms)) {
      return 0;
    }
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path_len >= kMaxRouteHops) {
      return 0;
    }
    const std::uint16_t wanted_dst = frame.flags;
    for (std::uint8_t i = 0; i < route.path_len; ++i) {
      if (route.path[i] == node_id_) {
        return 0;
      }
    }
    route.path[route.path_len++] = node_id_;
    route.path_index = static_cast<std::uint8_t>(route.path_len - 1U);

    if (wanted_dst == node_id_) {
      if (route.path_len < 2) {
        return 0;
      }
      WireFrame reply = baseFrame(FrameType::Rrep, route.path[route.path_len - 2U], frame.flow_id, now_ms);
      reply.ttl = kDefaultDataTtl;
      reply.confidence_milli = confidenceMilli(confidenceFromSnr(snr));
      route.path_index = static_cast<std::uint8_t>(route.path_len - 2U);
      if (!encodeRoutePayload(reply, route)) {
        return 0;
      }
      return pushOutbound(reply, false, out, out_capacity);
    }

    WireFrame forward = frame;
    forward.src = node_id_;
    forward.seq = next_seq_++;
    forward.ttl = static_cast<std::uint8_t>(frame.ttl - 1U);
    forward.confidence_milli =
        static_cast<std::uint16_t>(std::min<std::uint16_t>(frame.confidence_milli, confidenceMilli(confidenceFromSnr(snr))));
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    return pushOutbound(forward, true, out, out_capacity);
  }

  std::size_t handleRrep(const WireFrame& frame,
                         std::uint32_t now_ms,
                         float snr,
                         SmartCalmController& controller,
                         Snapshot& snapshot,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path[route.path_index] != node_id_) {
      return 0;
    }
    const float confidence =
        std::min<float>(static_cast<float>(frame.confidence_milli) / 1000.0f, confidenceFromSnr(snr));
    const std::uint16_t final_dst = route.path[route.path_len - 1U];
    cacheRouteFromPath(final_dst, route, now_ms, confidence);

    if (route.path_index == 0) {
      if (PendingFlow* pending = findPending(frame.flow_id)) {
        pending->active = false;
        return emitDataFromRoute(*findRoute(final_dst, now_ms, controller.activeProfile().route_ttl_s),
                                 pending->flow_id,
                                 pending->payload,
                                 pending->payload_len,
                                 now_ms,
                                 controller,
                                 snapshot,
                                 out,
                                 out_capacity);
      }
      return 0;
    }

    route.path_index--;
    WireFrame forward = baseFrame(FrameType::Rrep, route.path[route.path_index], frame.flow_id, now_ms);
    forward.ttl = static_cast<std::uint8_t>(std::max<int>(1, frame.ttl - 1));
    forward.confidence_milli = confidenceMilli(confidence);
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    return pushOutbound(forward, false, out, out_capacity);
  }

  std::size_t handleData(const WireFrame& frame,
                         std::uint32_t now_ms,
                         float snr,
                         SmartCalmController& controller,
                         Snapshot& snapshot,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path[route.path_index] != node_id_) {
      return 0;
    }
    const float confidence =
        std::min<float>(static_cast<float>(frame.confidence_milli) / 1000.0f, confidenceFromSnr(snr));
    if (route.path_index + 1U >= route.path_len) {
      snapshot.unicast_deliveries++;
      snapshot.delivery_delay_total_s += static_cast<float>(now_ms - frame.created_at_ms) / 1000.0f;
      snapshot.delivery_delay_samples++;
      snapshot.path_confidence_total += confidence;
      snapshot.path_confidence_samples++;

      route.path_index--;
      WireFrame ack = baseFrame(FrameType::Ack, route.path[route.path_index], frame.flow_id, now_ms);
      ack.ttl = kDefaultAckTtl;
      ack.confidence_milli = confidenceMilli(confidence);
      if (!encodeRoutePayload(ack, route)) {
        return 0;
      }
      return pushOutbound(ack, false, out, out_capacity);
    }

    if (frame.ttl <= 1) {
      return 0;
    }
    route.path_index++;
    WireFrame forward = baseFrame(FrameType::Data, route.path[route.path_index], frame.flow_id, frame.created_at_ms);
    forward.ttl = static_cast<std::uint8_t>(frame.ttl - 1U);
    forward.state_index = frame.state_index;
    forward.action_index = frame.action_index;
    forward.confidence_milli = confidenceMilli(confidence);
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    controller.markConfidence(frame.flow_id, confidence);
    return pushOutbound(forward, false, out, out_capacity);
  }

  std::size_t handleAck(const WireFrame& frame,
                        std::uint32_t now_ms,
                        SmartCalmController& controller,
                        Snapshot& snapshot,
                        OutboundFrame* out,
                        std::size_t out_capacity) {
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path[route.path_index] != node_id_) {
      return 0;
    }
    if (route.path_index == 0) {
      controller.completeFlow(frame.flow_id, true, snapshot, now_ms);
      return 0;
    }
    if (frame.ttl <= 1) {
      return 0;
    }
    route.path_index--;
    WireFrame forward = baseFrame(FrameType::Ack, route.path[route.path_index], frame.flow_id, now_ms);
    forward.ttl = static_cast<std::uint8_t>(frame.ttl - 1U);
    forward.confidence_milli = frame.confidence_milli;
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    return pushOutbound(forward, false, out, out_capacity);
  }

  std::size_t handleFallback(const WireFrame& frame,
                             std::uint32_t now_ms,
                             float snr,
                             SmartCalmController& controller,
                             Snapshot& snapshot,
                             OutboundFrame* out,
                             std::size_t out_capacity) {
    if (frame.ttl <= 1) {
      return 0;
    }
    snapshot.fallback_forward_count++;
    controller.markFallback(frame.flow_id);
    WireFrame forward = frame;
    forward.src = node_id_;
    forward.seq = next_seq_++;
    forward.ttl = static_cast<std::uint8_t>(frame.ttl - 1U);
    forward.confidence_milli =
        static_cast<std::uint16_t>(std::min<std::uint16_t>(frame.confidence_milli, confidenceMilli(confidenceFromSnr(snr))));
    return pushOutbound(forward, true, out, out_capacity);
  }
};

}  // namespace smart_calm
