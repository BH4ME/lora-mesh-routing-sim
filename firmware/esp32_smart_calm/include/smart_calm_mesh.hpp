#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include "smart_calm_controller.hpp"
#include "smart_calm_types.hpp"

namespace smart_calm {

constexpr std::size_t kMaxRouteCacheEntries = 8;
constexpr std::size_t kMaxPendingFlows = 4;
constexpr std::size_t kMaxSeenRequests = 12;
constexpr std::size_t kMaxNeighbors = 16;
constexpr std::size_t kMaxOutboundFrames = 3;
constexpr std::uint8_t kDefaultRreqTtl = 6;
constexpr std::uint8_t kDefaultDataTtl = 6;
constexpr std::uint8_t kDefaultAckTtl = 6;
constexpr std::uint32_t kSeenRequestTtlMs = 60000U;
constexpr std::uint32_t kNeighborTtlMs = 120000U;

struct RoutePayload {
  std::uint8_t path_len = 0;
  std::uint8_t path_index = 0;
  std::uint8_t app_len = 0;
  std::uint16_t path[kMaxRouteHops] = {};
  std::uint8_t app[kRouteAppPayloadSize] = {};
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

  std::size_t activeRouteCount() const {
    std::size_t count = 0;
    for (const auto& route : routes_) {
      count += route.active ? 1U : 0U;
    }
    return count;
  }

  std::size_t pendingFlowCount() const {
    std::size_t count = 0;
    for (const auto& pending : pending_) {
      count += pending.active ? 1U : 0U;
    }
    return count;
  }

  std::size_t neighborCount() const {
    std::size_t count = 0;
    for (const auto& neighbor : neighbors_) {
      count += neighbor.active ? 1U : 0U;
    }
    return count;
  }

  std::size_t sendApp(const MeshRuntimeLimits& limits,
                      std::uint16_t dst,
                      std::uint32_t flow_id,
                      const std::uint8_t* payload,
                      std::size_t payload_len,
                      std::uint32_t now_ms,
                      std::uint32_t entropy,
                      SmartCalmController& controller,
                      Snapshot& snapshot,
                      OutboundFrame* out,
                      std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0 || payload == nullptr || payload_len > kRouteAppPayloadSize) {
      return 0;
    }
    snapshot.unicast_flows++;
    controller.beginFlow(flow_id, snapshot, entropy, now_ms);

    PendingFlow& pending = acquirePending(flow_id);
    pending = PendingFlow{};
    pending.active = true;
    pending.dst = dst;
    pending.flow_id = flow_id;
    pending.created_at_ms = now_ms;
    pending.last_attempt_at_ms = now_ms;
    pending.state_index = controller.activeStateIndex();
    pending.action_index = controller.activeProfileIndex();
    pending.payload_len = static_cast<std::uint8_t>(payload_len);
    std::memcpy(pending.payload, payload, pending.payload_len);

    if (RouteEntry* route = findRoute(dst, now_ms, effectiveRouteTtl(limits, controller))) {
      snapshot.route_cache_hits++;
      return emitDataFromRoute(
          *route,
          limits,
          flow_id,
          payload,
          payload_len,
          pending.state_index,
          pending.action_index,
          now_ms,
          pending.created_at_ms,
          controller,
          snapshot,
          out,
          out_capacity);
    }

    snapshot.route_cache_misses++;
    controller.markRouteMiss(flow_id);
    ++snapshot.route_repair_count;
    return emitRreq(limits, dst, flow_id, now_ms, out, out_capacity);
  }

  std::size_t handleFrame(const MeshRuntimeLimits& limits,
                          const WireFrame& frame,
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
    observeNeighbor(frame.src, now_ms, rssi, snr);
    switch (frame.type) {
      case FrameType::Rreq:
        return handleRreq(limits, frame, now_ms, rssi, snr, out, out_capacity);
      case FrameType::Rrep:
        return handleRrep(limits, frame, now_ms, rssi, snr, controller, snapshot, out, out_capacity);
      case FrameType::Data:
        return handleData(limits, frame, now_ms, rssi, snr, controller, snapshot, out, out_capacity);
      case FrameType::Fallback:
        return handleFallback(limits, frame, now_ms, rssi, snr, controller, snapshot, out, out_capacity);
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

  std::size_t tick(const MeshRuntimeLimits& limits,
                   std::uint32_t now_ms,
                   SmartCalmController& controller,
                   Snapshot& snapshot,
                   OutboundFrame* out,
                   std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0) {
      return 0;
    }

    purgeExpiredRoutes(now_ms, effectiveRouteTtl(limits, controller));
    purgeExpiredNeighbors(now_ms);
    purgeExpiredSeen(now_ms);
    snapshot.route_expired_count = route_expired_count_;
    snapshot.neighbor_updates = neighbor_update_count_;
    snapshot.neighbor_expired_count = neighbor_expired_count_;

    for (auto& pending : pending_) {
      if (!pending.active || now_ms - pending.last_attempt_at_ms < std::max<std::uint16_t>(1, limits.ack_timeout_ms)) {
        continue;
      }

      const bool can_retry =
          pending.timeout_retries < limits.max_timeout_retries &&
          (limits.retry_after_fallback || !pending.used_fallback);
      if (!can_retry) {
        ++snapshot.unicast_failures;
        controller.completeFlow(pending.flow_id, false, snapshot, now_ms);
        pending.active = false;
        continue;
      }

      ++pending.timeout_retries;
      controller.markTimeoutRetry(pending.flow_id);
      ++snapshot.route_repair_count;

      if (RouteEntry* route = findRoute(pending.dst, now_ms, effectiveRouteTtl(limits, controller))) {
        const std::size_t count = emitDataFromRoute(
            *route,
            limits,
            pending.flow_id,
            pending.payload,
            pending.payload_len,
            pending.state_index,
            pending.action_index,
            now_ms,
            pending.created_at_ms,
            controller,
            snapshot,
            out,
            out_capacity);
        if (count > 0) {
          pending.last_attempt_at_ms = now_ms;
          return count;
        }
      }

      const std::size_t count =
          emitFallbackFromPending(limits, pending, now_ms, controller, snapshot, out, out_capacity);
      if (count > 0) {
        pending.last_attempt_at_ms = now_ms;
        pending.used_fallback = true;
        return count;
      }
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
    std::uint32_t last_attempt_at_ms = 0;
    std::uint8_t state_index = 0;
    std::uint8_t action_index = 1;
    std::uint8_t timeout_retries = 0;
    bool used_fallback = false;
    std::uint8_t payload_len = 0;
    std::uint8_t payload[kRouteAppPayloadSize] = {};
  };

  struct SeenRequest {
    bool active = false;
    FrameType type = FrameType::Rreq;
    std::uint16_t src = 0;
    std::uint16_t dst = 0;
    std::uint32_t flow_id = 0;
    std::uint32_t seen_at_ms = 0;
  };

  struct NeighborEntry {
    bool active = false;
    std::uint16_t node = 0;
    std::uint32_t updated_at_ms = 0;
    float rssi = 0.0f;
    float snr = 0.0f;
    float confidence = 0.0f;
  };

  std::uint16_t node_id_;
  std::uint16_t next_seq_ = 1;
  std::array<RouteEntry, kMaxRouteCacheEntries> routes_{};
  std::array<PendingFlow, kMaxPendingFlows> pending_{};
  std::array<SeenRequest, kMaxSeenRequests> seen_{};
  std::array<NeighborEntry, kMaxNeighbors> neighbors_{};
  std::uint32_t route_expired_count_ = 0;
  std::uint32_t neighbor_update_count_ = 0;
  std::uint32_t neighbor_expired_count_ = 0;

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

  float effectiveRouteTtl(const MeshRuntimeLimits& limits, const SmartCalmController& controller) const {
    const float profile_ttl_s = controller.activeProfile().route_ttl_s;
    const float configured_ttl_s = static_cast<float>(std::max<std::uint16_t>(1, limits.route_ttl_s));
    return std::min(profile_ttl_s, configured_ttl_s);
  }

  std::uint8_t boundedTtl(std::uint8_t requested, const MeshRuntimeLimits& limits) const {
    const std::uint8_t max_hops = std::max<std::uint8_t>(1, limits.max_hops);
    return static_cast<std::uint8_t>(std::min<std::uint8_t>(std::max<std::uint8_t>(1, requested), max_hops));
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
    return markSeenKey(frame.type, frame.src, frame.dst, frame.flow_id, now_ms);
  }

  bool markSeenKey(FrameType type,
                   std::uint16_t src,
                   std::uint16_t dst,
                   std::uint32_t flow_id,
                   std::uint32_t now_ms) {
    for (auto& seen : seen_) {
      if (seen.active && seen.type == type && seen.src == src && seen.dst == dst &&
          seen.flow_id == flow_id) {
        return false;
      }
    }
    for (auto& seen : seen_) {
      if (!seen.active || now_ms - seen.seen_at_ms > kSeenRequestTtlMs) {
        seen.active = true;
        seen.type = type;
        seen.src = src;
        seen.dst = dst;
        seen.flow_id = flow_id;
        seen.seen_at_ms = now_ms;
        return true;
      }
    }
    seen_[0] = SeenRequest{true, type, src, dst, flow_id, now_ms};
    return true;
  }

  void observeNeighbor(std::uint16_t node, std::uint32_t now_ms, float rssi, float snr) {
    NeighborEntry* oldest = &neighbors_[0];
    for (auto& neighbor : neighbors_) {
      if (neighbor.active && neighbor.node == node) {
        neighbor.updated_at_ms = now_ms;
        neighbor.rssi = rssi;
        neighbor.snr = snr;
        neighbor.confidence = confidenceFromSnr(snr);
        ++neighbor_update_count_;
        return;
      }
      if (!neighbor.active) {
        oldest = &neighbor;
        break;
      }
      if (neighbor.updated_at_ms < oldest->updated_at_ms) {
        oldest = &neighbor;
      }
    }
    *oldest = NeighborEntry{true, node, now_ms, rssi, snr, confidenceFromSnr(snr)};
    ++neighbor_update_count_;
  }

  void purgeExpiredRoutes(std::uint32_t now_ms, float route_ttl_s) {
    for (auto& route : routes_) {
      if (!route.active) {
        continue;
      }
      const float age_s = static_cast<float>(now_ms - route.updated_at_ms) / 1000.0f;
      if (age_s > route_ttl_s) {
        route.active = false;
        ++route_expired_count_;
      }
    }
  }

  void purgeExpiredNeighbors(std::uint32_t now_ms) {
    for (auto& neighbor : neighbors_) {
      if (neighbor.active && now_ms - neighbor.updated_at_ms > kNeighborTtlMs) {
        neighbor.active = false;
        ++neighbor_expired_count_;
      }
    }
  }

  void purgeExpiredSeen(std::uint32_t now_ms) {
    for (auto& seen : seen_) {
      if (seen.active && now_ms - seen.seen_at_ms > kSeenRequestTtlMs) {
        seen.active = false;
      }
    }
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

  std::size_t emitRreq(const MeshRuntimeLimits& limits,
                       std::uint16_t dst,
                       std::uint32_t flow_id,
                       std::uint32_t now_ms,
                       OutboundFrame* out,
                       std::size_t out_capacity) {
    RoutePayload route{};
    route.path_len = 1;
    route.path_index = 0;
    route.path[0] = node_id_;

    WireFrame frame = baseFrame(FrameType::Rreq, dst, flow_id, now_ms);
    frame.ttl = boundedTtl(kDefaultRreqTtl, limits);
    frame.flags = 0;
    frame.confidence_milli = 1000;
    if (!encodeRoutePayload(frame, route)) {
      return 0;
    }
    return pushOutbound(frame, true, out, out_capacity);
  }

  std::size_t emitDataFromRoute(const RouteEntry& route,
                                const MeshRuntimeLimits& limits,
                                std::uint32_t flow_id,
                                const std::uint8_t* payload,
                                std::size_t payload_len,
                                std::uint8_t state_index,
                                std::uint8_t action_index,
                                std::uint32_t now_ms,
                                std::uint32_t created_at_ms,
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
    frame.created_at_ms = created_at_ms;
    frame.ttl = boundedTtl(kDefaultDataTtl, limits);
    frame.state_index = state_index;
    frame.action_index = action_index;
    frame.confidence_milli = confidenceMilli(route.confidence);
    if (!encodeRoutePayload(frame, route_payload)) {
      return 0;
    }
    snapshot.path_confidence_total += route.confidence;
    snapshot.path_confidence_samples++;
    controller.markConfidence(flow_id, route.confidence);
    return pushOutbound(frame, false, out, out_capacity);
  }

  std::size_t emitFallbackFromPending(const MeshRuntimeLimits& limits,
                                      PendingFlow& pending,
                                      std::uint32_t now_ms,
                                      SmartCalmController& controller,
                                      Snapshot& snapshot,
                                      OutboundFrame* out,
                                      std::size_t out_capacity) {
    RoutePayload route{};
    route.path_len = 1;
    route.path_index = 0;
    route.app_len = pending.payload_len;
    route.path[0] = node_id_;
    std::memcpy(route.app, pending.payload, pending.payload_len);

    WireFrame frame = baseFrame(FrameType::Fallback, pending.dst, pending.flow_id, now_ms);
    frame.created_at_ms = pending.created_at_ms;
    frame.ttl = boundedTtl(std::max<std::uint8_t>(1, limits.fallback_ttl), limits);
    frame.state_index = pending.state_index;
    frame.action_index = pending.action_index;
    frame.confidence_milli = 1000;
    if (!encodeRoutePayload(frame, route)) {
      return 0;
    }
    controller.markFallback(pending.flow_id);
    ++snapshot.fallback_forward_count;
    return pushOutbound(frame, true, out, out_capacity);
  }

  std::size_t handleRreq(const MeshRuntimeLimits& limits,
                         const WireFrame& frame,
                         std::uint32_t now_ms,
                         float rssi,
                         float snr,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    (void)rssi;
    if (!markSeen(frame, now_ms)) {
      return 0;
    }
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path_len >= kMaxRouteHops) {
      return 0;
    }
    const std::uint16_t wanted_dst = frame.dst;
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
      reply.ttl = boundedTtl(kDefaultDataTtl, limits);
      reply.confidence_milli = confidenceMilli(confidenceFromSnr(snr));
      route.path_index = static_cast<std::uint8_t>(route.path_len - 2U);
      if (!encodeRoutePayload(reply, route)) {
        return 0;
      }
      return pushOutbound(reply, false, out, out_capacity);
    }

    if (frame.ttl <= 1) {
      return 0;
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

  std::size_t handleRrep(const MeshRuntimeLimits& limits,
                         const WireFrame& frame,
                         std::uint32_t now_ms,
                         float rssi,
                         float snr,
                         SmartCalmController& controller,
                         Snapshot& snapshot,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    (void)rssi;
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
        RouteEntry* cached = findRoute(final_dst, now_ms, effectiveRouteTtl(limits, controller));
        if (cached == nullptr) {
          pending->last_attempt_at_ms = now_ms;
          return 0;
        }
        const std::size_t count = emitDataFromRoute(*cached,
                                                   limits,
                                                   pending->flow_id,
                                                   pending->payload,
                                                   pending->payload_len,
                                                   pending->state_index,
                                                   pending->action_index,
                                                   now_ms,
                                                   pending->created_at_ms,
                                                   controller,
                                                   snapshot,
                                                   out,
                                                   out_capacity);
        if (count > 0) {
          pending->last_attempt_at_ms = now_ms;
        }
        return count;
      }
      return 0;
    }

    if (frame.ttl <= 1) {
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

  std::size_t handleData(const MeshRuntimeLimits& limits,
                         const WireFrame& frame,
                         std::uint32_t now_ms,
                         float rssi,
                         float snr,
                         SmartCalmController& controller,
                         Snapshot& snapshot,
                         OutboundFrame* out,
                         std::size_t out_capacity) {
    (void)rssi;
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path[route.path_index] != node_id_) {
      return 0;
    }
    const float confidence =
        std::min<float>(static_cast<float>(frame.confidence_milli) / 1000.0f, confidenceFromSnr(snr));
    if (route.path_index + 1U >= route.path_len) {
      snapshot.unicast_deliveries++;
      snapshot.path_confidence_total += confidence;
      snapshot.path_confidence_samples++;

      route.path_index--;
      WireFrame ack = baseFrame(FrameType::Ack, route.path[route.path_index], frame.flow_id, now_ms);
      ack.created_at_ms = frame.created_at_ms;
      ack.ttl = boundedTtl(kDefaultAckTtl, limits);
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
      snapshot.unicast_acks++;
      snapshot.delivery_delay_total_s += static_cast<float>(now_ms - frame.created_at_ms) / 1000.0f;
      snapshot.delivery_delay_samples++;
      if (PendingFlow* pending = findPending(frame.flow_id)) {
        pending->active = false;
      }
      controller.completeFlow(frame.flow_id, true, snapshot, now_ms);
      return 0;
    }
    if (frame.ttl <= 1) {
      return 0;
    }
    route.path_index--;
    WireFrame forward = baseFrame(FrameType::Ack, route.path[route.path_index], frame.flow_id, frame.created_at_ms);
    forward.ttl = static_cast<std::uint8_t>(frame.ttl - 1U);
    forward.confidence_milli = frame.confidence_milli;
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    return pushOutbound(forward, false, out, out_capacity);
  }

  std::size_t handleFallback(const MeshRuntimeLimits& limits,
                             const WireFrame& frame,
                             std::uint32_t now_ms,
                             float rssi,
                             float snr,
                             SmartCalmController& controller,
                             Snapshot& snapshot,
                             OutboundFrame* out,
                             std::size_t out_capacity) {
    (void)rssi;
    RoutePayload route{};
    if (!decodeRoutePayload(frame, &route) || route.path_len >= kMaxRouteHops) {
      return 0;
    }

    const std::uint16_t origin = route.path[0];
    if (!markSeenKey(FrameType::Fallback, origin, frame.dst, frame.flow_id, now_ms)) {
      return 0;
    }
    for (std::uint8_t i = 0; i < route.path_len; ++i) {
      if (route.path[i] == node_id_) {
        return 0;
      }
    }
    route.path[route.path_len++] = node_id_;
    route.path_index = static_cast<std::uint8_t>(route.path_len - 1U);
    const float confidence =
        std::min<float>(static_cast<float>(frame.confidence_milli) / 1000.0f, confidenceFromSnr(snr));

    if (frame.dst == node_id_) {
      snapshot.unicast_deliveries++;
      snapshot.fallback_delivery_count++;
      snapshot.path_confidence_total += confidence;
      snapshot.path_confidence_samples++;
      controller.markConfidence(frame.flow_id, confidence);

      route.path_index--;
      WireFrame ack = baseFrame(FrameType::Ack, route.path[route.path_index], frame.flow_id, now_ms);
      ack.created_at_ms = frame.created_at_ms;
      ack.ttl = boundedTtl(kDefaultAckTtl, limits);
      ack.state_index = frame.state_index;
      ack.action_index = frame.action_index;
      ack.confidence_milli = confidenceMilli(confidence);
      if (!encodeRoutePayload(ack, route)) {
        return 0;
      }
      return pushOutbound(ack, false, out, out_capacity);
    }

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
        static_cast<std::uint16_t>(std::min<std::uint16_t>(frame.confidence_milli, confidenceMilli(confidence)));
    if (!encodeRoutePayload(forward, route)) {
      return 0;
    }
    return pushOutbound(forward, true, out, out_capacity);
  }
};

}  // namespace smart_calm
