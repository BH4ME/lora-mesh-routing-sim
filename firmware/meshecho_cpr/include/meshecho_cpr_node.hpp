#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "meshecho_cpr_wire.hpp"

namespace meshecho_cpr {

constexpr NodeId kCprBroadcastId = 0xFFFFU;
constexpr std::size_t kMaxCprPendingApps = kMaxCprFlows;
constexpr std::size_t kMaxCprSeenFrames = 16;
constexpr std::size_t kMaxCprRelaySlots = kMaxPendingRelays;
constexpr std::size_t kMaxCprDeliveries = 8;
constexpr std::size_t kMaxCprDeliveredKeys = 16;
constexpr std::uint32_t kDefaultCprAckTimeoutMs = 500;
constexpr std::uint32_t kDefaultCprDiscoveryWaitMs = 750;
constexpr std::uint32_t kDefaultCprRelayJitterMs = 80;
constexpr std::uint32_t kDefaultCprRouteLifetimeMs = 600000;

struct CprOutboundFrame {
  CprWireFrame frame{};
  std::uint32_t due_at_ms = 0;
  bool relay_pending = false;
  PendingTxToken* pending = nullptr;
  std::uint32_t expires_at_ms = 0;
  std::uint32_t pending_lease = 0;
};

// A fixed-size application delivery record.  The source is taken from the
// route origin (path[0]), rather than from the immediate LoRa hop.
struct CprDelivery {
  NodeId source = 0;
  NodeId destination = 0;
  std::uint32_t flow_id = 0;
  std::uint32_t request_id = 0;
  std::uint32_t created_at_ms = 0;
  std::uint32_t delivered_at_ms = 0;
  std::uint8_t repair_index = kInitialRepair;
  std::uint8_t payload_len = 0;
  std::array<std::uint8_t, kCprAppPayloadSize> payload{};
};

class CprNode {
 public:
  explicit CprNode(NodeId node_id) : node_id_(node_id) {}

  NodeId nodeId() const { return node_id_; }

  void setAckTimeoutMs(std::uint32_t timeout_ms) {
    ack_timeout_ms_ = timeout_ms == 0 ? kDefaultCprAckTimeoutMs : timeout_ms;
  }

  void setDiscoveryWaitMs(std::uint32_t wait_ms) {
    discovery_wait_ms_ = wait_ms == 0 ? kDefaultCprDiscoveryWaitMs : wait_ms;
  }

  RouteInstallResult installRoute(NodeId destination, const Path& path) {
    if (!path.valid() || path.nodes[0] != node_id_) {
      return {};
    }
    return routes_.install(destination, path);
  }

  bool flowAcked(std::uint32_t flow_id) const { return controller_.isAcked(flow_id); }

  bool canTransmit(const CprOutboundFrame& outbound, std::uint32_t now_ms) const {
    const CprWireFrame& frame = outbound.frame;
    if (!cprFrameValid(frame) || frame.ttl == 0U ||
        (outbound.pending != nullptr &&
         (outbound.pending->lease != outbound.pending_lease ||
          outbound.pending->canceled || outbound.pending->committed))) {
      return false;
    }
    if ((frame.type != CprFrameType::Data && frame.type != CprFrameType::Flood) ||
        frame.path.nodes[0] != node_id_) {
      return true;
    }
    const AppRecord* app = findApp(frame.flow_id);
    const CprFlowRecord* flow = controller_.flow(frame.flow_id);
    if (app == nullptr || flow == nullptr || flow->acked ||
        !cprTimeBefore(now_ms, app->deadline_ms)) {
      return false;
    }
    const std::uint32_t bound = frame.type == CprFrameType::Flood
                                    ? app->flood_bound_ms : app->route_bound_ms;
    if (bound > app->deadline_ms - now_ms) {
      return false;
    }
    if (flow->initial_action == CprAction::R_INITIAL) {
      const RouteEntry* route = routes_.find(app->destination, now_ms);
      if (route == nullptr || route->generation != flow->initial_route_generation ||
          !(route->path == flow->initial_path)) {
        return false;
      }
    }
    if (frame.repair_index == kInitialRepair) {
      return !flow->initial_started;
    }
    if (frame.repair_index == kRepeatRepair) {
      return flow->initial_started && flow->repeat_requested && !flow->repeat_started;
    }
    return flow->repeat_started && flow->recovery_requested && !flow->recovery_started;
  }

  void onTxDiscarded(const CprOutboundFrame& outbound) {
    if (outbound.pending != nullptr &&
        outbound.pending->lease == outbound.pending_lease &&
        !outbound.pending->committed) {
      outbound.pending->canceled = true;
    }
    const CprWireFrame& frame = outbound.frame;
    if ((frame.type == CprFrameType::Data || frame.type == CprFrameType::Flood) &&
        frame.path.length > 0 && frame.path.nodes[0] == node_id_) {
      if (AppRecord* app = findApp(frame.flow_id)) {
        app->active = false;
      }
      (void)controller_.retire(frame.flow_id);
    }
  }

  // Polls one application payload without allocating memory.  Delivery is
  // FIFO and remains bounded so a congested application cannot grow RAM use.
  bool pollDelivery(CprDelivery* out) {
    if (out == nullptr || delivery_count_ == 0) {
      return false;
    }
    *out = delivery_queue_[delivery_head_];
    delivery_head_ = (delivery_head_ + 1U) % kMaxCprDeliveries;
    --delivery_count_;
    return true;
  }

  std::size_t pendingDeliveryCount() const { return delivery_count_; }

  std::size_t sendApp(NodeId destination,
                      std::uint32_t flow_id,
                      const std::uint8_t* payload,
                      std::size_t payload_len,
                      std::uint32_t now_ms,
                      std::uint32_t deadline_ms,
                      std::uint32_t route_bound_ms,
                      std::uint32_t flood_bound_ms,
                      CprOutboundFrame* out,
                      std::size_t out_capacity) {
    if (node_id_ == 0 || destination == 0 || destination == kCprBroadcastId || flow_id == 0 ||
        out == nullptr || out_capacity == 0 || payload == nullptr || payload_len > kCprAppPayloadSize) {
      return 0;
    }
    AppRecord* app = acquireApp(flow_id);
    if (app == nullptr) {
      return 0;
    }
    *app = AppRecord{};
    app->active = true;
    app->flow_id = flow_id;
    app->destination = destination;
    app->enqueue_at_ms = now_ms;
    app->deadline_ms = deadline_ms;
    app->route_bound_ms = route_bound_ms;
    app->flood_bound_ms = flood_bound_ms;
    app->payload_len = static_cast<std::uint8_t>(payload_len);
    for (std::size_t i = 0; i < payload_len; ++i) {
      app->payload[i] = payload[i];
    }

    const RouteEntry* route = routes_.find(destination, now_ms);
    if (route != nullptr) {
      return beginWithRoute(*app, route, now_ms, out, out_capacity);
    }

    return beginWithoutRoute(*app, now_ms, out, out_capacity);
  }

  bool onTxStarted(const CprOutboundFrame& outbound, std::uint32_t now_ms) {
    if (outbound.pending != nullptr) {
      if (outbound.pending->lease != outbound.pending_lease ||
          outbound.pending->canceled || outbound.pending->committed) {
        return false;
      }
      outbound.pending->committed = true;
    }
    if (outbound.frame.type != CprFrameType::Data && outbound.frame.type != CprFrameType::Flood) {
      return true;
    }
    const bool source_generated =
        outbound.frame.path.length > 0 && outbound.frame.path.nodes[0] == node_id_;
    if (!source_generated) {
      return true;
    }
    bool marked = false;
    if (outbound.frame.repair_index == kInitialRepair) {
      marked = controller_.markInitialTxStarted(outbound.frame.flow_id, now_ms);
    } else if (outbound.frame.repair_index == kRepeatRepair) {
      marked = controller_.markRepeatTxStarted(outbound.frame.flow_id, now_ms);
    } else if (outbound.frame.repair_index == kRecoveryRepair) {
      marked = controller_.markRecoveryTxStarted(outbound.frame.flow_id, now_ms);
    }
    if (marked) {
      if (AppRecord* app = findApp(outbound.frame.flow_id)) {
        app->last_tx_started_ms = now_ms;
        app->has_started_tx = true;
      }
    }
    return marked;
  }

  std::size_t onFrame(const CprWireFrame& frame,
                      std::uint32_t now_ms,
                      CprOutboundFrame* out,
                      std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0 || frame.src == node_id_ || !cprFrameValid(frame)) {
      return 0;
    }
    switch (frame.type) {
      case CprFrameType::RouteRequest:
      case CprFrameType::RouteReply:
        // CPR learns paths from terminal ACKs, never discovery replies.
        return 0;
      case CprFrameType::Data:
        return handleData(frame, now_ms, out, out_capacity);
      case CprFrameType::Ack:
        return handleAck(frame, now_ms, out, out_capacity);
      case CprFrameType::Flood:
        return handleFlood(frame, now_ms, out, out_capacity);
    }
    return 0;
  }

  std::size_t poll(std::uint32_t now_ms, CprOutboundFrame* out, std::size_t out_capacity) {
    if (out == nullptr || out_capacity == 0) {
      return 0;
    }
    std::size_t count = emitDueRelays(now_ms, out, out_capacity);
    if (count == out_capacity) {
      return count;
    }

    for (auto& app : apps_) {
      if (!app.active) {
        continue;
      }
      if (!cprTimeBefore(now_ms, app.deadline_ms)) {
        const CprFlowRecord* expired = controller_.flow(app.flow_id);
        if (expired != nullptr && !expired->acked &&
            expired->initial_action == CprAction::R_INITIAL) {
          (void)routes_.invalidate(app.destination, expired->initial_route_generation);
        }
        (void)controller_.retire(app.flow_id);
        app.active = false;
        continue;
      }
      if (app.discovery_pending && !cprTimeBefore(now_ms, app.discovery_deadline_ms)) {
        app.discovery_pending = false;
        const RouteEntry* route = routes_.find(app.destination, now_ms);
        if (route != nullptr) {
          count += beginWithRoute(app, route, now_ms, out + count, out_capacity - count);
        } else {
          count += beginWithoutRoute(app, now_ms, out + count, out_capacity - count);
        }
        if (count == out_capacity) {
          return count;
        }
      }

      const CprFlowRecord* flow = controller_.flow(app.flow_id);
      const std::uint32_t ack_wait_ms =
          app.route_bound_ms > ack_timeout_ms_ ? app.route_bound_ms : ack_timeout_ms_;
      if (flow == nullptr || flow->acked || !app.has_started_tx ||
          now_ms - app.last_tx_started_ms < ack_wait_ms) {
        continue;
      }
      const std::uint32_t generation = routes_.generation(app.destination, now_ms);
      const CprDecision decision = controller_.requestRecovery(
          app.flow_id, now_ms, app.route_bound_ms, app.flood_bound_ms, generation);
      if (decision.action == CprAction::R_REPEAT) {
        count += emitRepeat(app, now_ms, out + count, out_capacity - count);
      } else if (decision.action == CprAction::F_RECOVERY) {
        count += emitFlood(app, kRecoveryRepair, now_ms, out + count, out_capacity - count);
      } else if (!cprTimeBefore(now_ms, app.deadline_ms)) {
        app.active = false;
      }
      if (count == out_capacity) {
        return count;
      }
    }
    relays_.retire();
    retireRelaySlots();
    return count;
  }

 private:
  struct AppRecord {
    bool active = false;
    bool discovery_pending = false;
    bool has_started_tx = false;
    std::uint32_t flow_id = 0;
    NodeId destination = 0;
    std::uint32_t enqueue_at_ms = 0;
    std::uint32_t deadline_ms = 0;
    std::uint32_t route_bound_ms = 0;
    std::uint32_t flood_bound_ms = 0;
    std::uint32_t discovery_deadline_ms = 0;
    std::uint32_t last_tx_started_ms = 0;
    std::uint8_t payload_len = 0;
    std::array<std::uint8_t, kCprAppPayloadSize> payload{};
  };

  struct SeenRecord {
    bool active = false;
    CprFrameType type = CprFrameType::Data;
    std::uint32_t flow_id = 0;
    std::uint8_t repair_index = 0;
    NodeId source = 0;
    std::uint32_t seen_at_ms = 0;
  };

  struct RelaySlot {
    bool active = false;
    bool offered = false;
    std::uint32_t due_at_ms = 0;
    std::uint32_t expires_at_ms = 0;
    PendingTxToken token{};
    CprWireFrame frame{};
    CprPendingRelay ledger_record{};
  };

  struct DeliveredKey {
    bool active = false;
    NodeId source = 0;
    NodeId destination = 0;
    std::uint32_t flow_id = 0;
    std::uint32_t request_id = 0;
    std::uint32_t serial = 0;
  };

  NodeId node_id_ = 0;
  std::uint16_t next_sequence_ = 1;
  std::uint32_t next_relay_lease_ = 0;
  std::uint32_t ack_timeout_ms_ = kDefaultCprAckTimeoutMs;
  std::uint32_t discovery_wait_ms_ = kDefaultCprDiscoveryWaitMs;
  RouteTable routes_{};
  CprController controller_{};
  CprRelayLedger relays_{};
  std::array<AppRecord, kMaxCprPendingApps> apps_{};
  std::array<SeenRecord, kMaxCprSeenFrames> seen_{};
  std::array<RelaySlot, kMaxCprRelaySlots> relay_slots_{};
  std::array<CprDelivery, kMaxCprDeliveries> delivery_queue_{};
  std::size_t delivery_head_ = 0;
  std::size_t delivery_count_ = 0;
  std::array<DeliveredKey, kMaxCprDeliveredKeys> delivered_keys_{};
  std::uint32_t delivered_serial_ = 0;

  std::uint16_t nextSequence() {
    const std::uint16_t current = next_sequence_++;
    if (next_sequence_ == 0) {
      next_sequence_ = 1;
    }
    return current;
  }

  AppRecord* findApp(std::uint32_t flow_id) {
    for (auto& app : apps_) {
      if (app.active && app.flow_id == flow_id) {
        return &app;
      }
    }
    return nullptr;
  }

  const AppRecord* findApp(std::uint32_t flow_id) const {
    for (const auto& app : apps_) {
      if (app.active && app.flow_id == flow_id) {
        return &app;
      }
    }
    return nullptr;
  }

  AppRecord* acquireApp(std::uint32_t flow_id) {
    if (findApp(flow_id) != nullptr) {
      return nullptr;
    }
    for (auto& app : apps_) {
      if (!app.active) {
        return &app;
      }
    }
    return nullptr;
  }

  CprWireFrame baseFrame(CprFrameType type,
                         NodeId destination,
                         std::uint32_t flow_id,
                         std::uint32_t now_ms) {
    CprWireFrame frame{};
    frame.type = type;
    frame.src = node_id_;
    frame.dst = destination;
    frame.sequence = nextSequence();
    frame.flow_id = flow_id;
    frame.request_id = flow_id;
    frame.created_at_ms = now_ms;
    frame.ttl = static_cast<std::uint8_t>(kMaxPathNodes);
    return frame;
  }

  std::size_t pushImmediate(const CprWireFrame& frame,
                            CprOutboundFrame* out,
                            std::size_t out_capacity,
                            std::uint32_t now_ms) const {
    if (out == nullptr || out_capacity == 0) {
      return 0;
    }
    out[0] = CprOutboundFrame{};
    out[0].frame = frame;
    out[0].due_at_ms = now_ms;
    out[0].expires_at_ms = now_ms + frame.remaining_budget_ms;
    return 1;
  }

  std::size_t beginWithRoute(AppRecord& app,
                             const RouteEntry* route,
                             std::uint32_t now_ms,
                             CprOutboundFrame* out,
                             std::size_t out_capacity) {
    if (route == nullptr) {
      return beginWithoutRoute(app, now_ms, out, out_capacity);
    }
    const CprDecision decision = controller_.beginFlow(
        app.flow_id, node_id_, app.destination, app.enqueue_at_ms, app.deadline_ms,
        route, route->generation, app.route_bound_ms, app.flood_bound_ms);
    if (decision.action == CprAction::R_INITIAL) {
      return emitData(app, route->path, route->generation, kInitialRepair, now_ms, out, out_capacity);
    }
    if (decision.action == CprAction::F_INITIAL) {
      return emitFlood(app, kInitialRepair, now_ms, out, out_capacity);
    }
    (void)controller_.retire(app.flow_id);
    app.active = false;
    return 0;
  }

  std::size_t beginWithoutRoute(AppRecord& app,
                                std::uint32_t now_ms,
                                CprOutboundFrame* out,
                                std::size_t out_capacity) {
    const CprDecision decision = controller_.beginFlow(
        app.flow_id, node_id_, app.destination, app.enqueue_at_ms, app.deadline_ms,
        nullptr, 0, app.route_bound_ms, app.flood_bound_ms);
    if (decision.action == CprAction::F_INITIAL) {
      return emitFlood(app, kInitialRepair, now_ms, out, out_capacity);
    }
    (void)controller_.retire(app.flow_id);
    app.active = false;
    return 0;
  }

  std::size_t emitRouteRequest(const AppRecord& app,
                               std::uint32_t now_ms,
                               CprOutboundFrame* out,
                               std::size_t out_capacity) {
    CprWireFrame frame = baseFrame(CprFrameType::RouteRequest, app.destination, app.flow_id, now_ms);
    frame.remaining_budget_ms = app.deadline_ms - now_ms;
    frame.path.length = 1;
    frame.path.nodes[0] = node_id_;
    frame.path_index = 0;
    frame.ttl = static_cast<std::uint8_t>(kMaxPathNodes);
    return pushImmediate(frame, out, out_capacity, now_ms);
  }

  std::size_t emitData(const AppRecord& app,
                       const Path& path,
                       std::uint32_t generation,
                       std::uint8_t repair_index,
                       std::uint32_t now_ms,
                       CprOutboundFrame* out,
                       std::size_t out_capacity) {
    if (!path.valid() || path.nodes[0] != node_id_ || path.length < 2 || app.payload_len > kCprAppPayloadSize) {
      return 0;
    }
    CprWireFrame frame = baseFrame(CprFrameType::Data, path.nodes[1], app.flow_id, now_ms);
    frame.remaining_budget_ms = app.deadline_ms - now_ms;
    frame.route_generation = generation;
    frame.repair_index = repair_index;
    frame.path = path;
    frame.path_index = 1;
    frame.payload_len = app.payload_len;
    for (std::uint8_t i = 0; i < app.payload_len; ++i) {
      frame.payload[i] = app.payload[i];
    }
    return pushImmediate(frame, out, out_capacity, now_ms);
  }

  std::size_t emitRepeat(const AppRecord& app,
                         std::uint32_t now_ms,
                         CprOutboundFrame* out,
                         std::size_t out_capacity) {
    const CprFlowRecord* flow = controller_.flow(app.flow_id);
    if (flow == nullptr) {
      return 0;
    }
    return emitData(app, flow->initial_path, flow->initial_route_generation,
                    kRepeatRepair, now_ms, out, out_capacity);
  }

  std::size_t emitFlood(const AppRecord& app,
                        std::uint8_t repair_index,
                        std::uint32_t now_ms,
                        CprOutboundFrame* out,
                        std::size_t out_capacity) {
    CprWireFrame frame = baseFrame(CprFrameType::Flood, app.destination, app.flow_id, now_ms);
    frame.remaining_budget_ms = app.deadline_ms - now_ms;
    frame.repair_index = repair_index;
    if (repair_index == kRecoveryRepair) {
      const CprFlowRecord* flow = controller_.flow(app.flow_id);
      if (flow == nullptr) {
        return 0;
      }
      frame.route_generation = flow->recovery_route_generation;
    }
    frame.path.length = 1;
    frame.path.nodes[0] = node_id_;
    frame.path_index = 0;
    frame.payload_len = app.payload_len;
    for (std::uint8_t i = 0; i < app.payload_len; ++i) {
      frame.payload[i] = app.payload[i];
    }
    return pushImmediate(frame, out, out_capacity, now_ms);
  }

  bool markSeen(const CprWireFrame& frame, std::uint32_t now_ms) {
    for (const auto& item : seen_) {
      if (item.active && item.type == frame.type && item.source == frame.src &&
          item.flow_id == frame.flow_id && item.repair_index == frame.repair_index) {
        return false;
      }
    }
    SeenRecord* target = nullptr;
    for (auto& item : seen_) {
      if (!item.active || now_ms - item.seen_at_ms > 60000U) {
        target = &item;
        break;
      }
    }
    if (target == nullptr) {
      target = &seen_[0];
    }
    *target = SeenRecord{true, frame.type, frame.flow_id, frame.repair_index, frame.src, now_ms};
    return true;
  }

  bool deliveryWasSeen(const CprWireFrame& frame, NodeId source) const {
    for (const auto& key : delivered_keys_) {
      if (key.active && key.source == source && key.destination == node_id_ &&
          key.flow_id == frame.flow_id && key.request_id == frame.request_id) {
        return true;
      }
    }
    return false;
  }

  void rememberDelivery(const CprWireFrame& frame, NodeId source) {
    DeliveredKey* target = nullptr;
    for (auto& key : delivered_keys_) {
      if (!key.active) {
        target = &key;
        break;
      }
    }
    if (target == nullptr) {
      target = &delivered_keys_[0];
      for (auto& key : delivered_keys_) {
        if (key.serial < target->serial) {
          target = &key;
        }
      }
    }
    *target = DeliveredKey{true, source, node_id_, frame.flow_id, frame.request_id,
                           ++delivered_serial_};
  }

  // Returns true for an already delivered flow (so a retransmission can be
  // ACKed), and only returns false for a new payload when the queue is full.
  bool enqueueDelivery(const CprWireFrame& frame, std::uint32_t now_ms) {
    if (frame.path.length == 0 || frame.dst != node_id_) {
      return false;
    }
    const NodeId source = frame.path.nodes[0];
    if (deliveryWasSeen(frame, source)) {
      return true;
    }
    if (delivery_count_ >= kMaxCprDeliveries) {
      return false;
    }
    CprDelivery& delivery =
        delivery_queue_[(delivery_head_ + delivery_count_) % kMaxCprDeliveries];
    delivery = CprDelivery{};
    delivery.source = source;
    delivery.destination = node_id_;
    delivery.flow_id = frame.flow_id;
    delivery.request_id = frame.request_id;
    delivery.created_at_ms = frame.created_at_ms;
    delivery.delivered_at_ms = now_ms;
    delivery.repair_index = frame.repair_index;
    delivery.payload_len = frame.payload_len;
    for (std::uint8_t i = 0; i < frame.payload_len; ++i) {
      delivery.payload[i] = frame.payload[i];
    }
    ++delivery_count_;
    rememberDelivery(frame, source);
    return true;
  }

  std::size_t handleRouteRequest(const CprWireFrame& incoming,
                                 std::uint32_t now_ms,
                                 CprOutboundFrame* out,
                                 std::size_t out_capacity) {
    if (!cprWirePathValid(incoming.path) || incoming.path_index + 1U != incoming.path.length ||
        incoming.path.contains(node_id_) || !markSeen(incoming, now_ms)) {
      return 0;
    }
    Path path = incoming.path;
    if (path.length >= kMaxPathNodes) {
      return 0;
    }
    path.nodes[path.length++] = node_id_;
    if (incoming.dst == node_id_) {
      CprWireFrame reply = baseFrame(CprFrameType::RouteReply, path.nodes[path.length - 2U], incoming.flow_id, now_ms);
      reply.request_id = incoming.request_id;
      reply.created_at_ms = incoming.created_at_ms;
      reply.remaining_budget_ms = incoming.remaining_budget_ms;
      reply.ttl = incoming.ttl;
      reply.path = path;
      reply.path_index = static_cast<std::uint8_t>(path.length - 2U);
      return pushImmediate(reply, out, out_capacity, now_ms);
    }
    if (incoming.ttl <= 1) {
      return 0;
    }
    CprWireFrame forward = incoming;
    forward.src = node_id_;
    forward.sequence = nextSequence();
    forward.ttl = static_cast<std::uint8_t>(incoming.ttl - 1U);
    forward.path = path;
    forward.path_index = static_cast<std::uint8_t>(path.length - 1U);
    return pushImmediate(forward, out, out_capacity, now_ms);
  }

  std::size_t handleRouteReply(const CprWireFrame& incoming,
                               std::uint32_t now_ms,
                               CprOutboundFrame* out,
                               std::size_t out_capacity) {
    if (!cprWirePathValid(incoming.path) || incoming.path_index >= incoming.path.length ||
        incoming.path.nodes[incoming.path_index] != node_id_) {
      return 0;
    }
    Path path = incoming.path;
    if (incoming.path_index == 0) {
      const NodeId destination = path.nodes[path.length - 1U];
      const RouteInstallResult installed = routes_.install(destination, path);
      if (!installed.accepted) {
        return 0;
      }
      AppRecord* app = findApp(incoming.flow_id);
      if (app == nullptr) {
        return 0;
      }
      app->discovery_pending = false;
      return beginWithRoute(*app, routes_.find(destination, now_ms), now_ms, out, out_capacity);
    }
    const std::uint8_t previous_index = static_cast<std::uint8_t>(incoming.path_index - 1U);
    CprWireFrame forward = incoming;
    forward.src = node_id_;
    forward.dst = path.nodes[previous_index];
    forward.sequence = nextSequence();
    forward.path_index = previous_index;
    forward.ttl = incoming.ttl > 1 ? static_cast<std::uint8_t>(incoming.ttl - 1U) : 0;
    return pushImmediate(forward, out, out_capacity, now_ms);
  }

  std::size_t handleData(const CprWireFrame& incoming,
                         std::uint32_t now_ms,
                         CprOutboundFrame* out,
                         std::size_t out_capacity) {
    if (!cprWirePathValid(incoming.path) || incoming.path_index == 0U ||
        incoming.path_index >= incoming.path.length || incoming.ttl == 0U ||
        incoming.dst != node_id_ ||
        incoming.src != incoming.path.nodes[incoming.path_index - 1U] ||
        incoming.path.nodes[incoming.path_index] != node_id_) {
      return 0;
    }
    if (incoming.path_index + 1U == incoming.path.length) {
      if (incoming.path.length < 2) {
        return 0;
      }
      if (!enqueueDelivery(incoming, now_ms)) {
        return 0;
      }
      CprWireFrame ack = baseFrame(CprFrameType::Ack, incoming.path.nodes[incoming.path.length - 2U],
                                   incoming.flow_id, now_ms);
      ack.request_id = incoming.request_id;
      ack.created_at_ms = incoming.created_at_ms;
      ack.remaining_budget_ms = incoming.remaining_budget_ms;
      ack.route_generation = incoming.route_generation;
      ack.repair_index = incoming.repair_index;
      ack.path = incoming.path;
      ack.path_index = static_cast<std::uint8_t>(incoming.path.length - 2U);
      ack.ttl = static_cast<std::uint8_t>(incoming.path.length - 1U);
      return pushImmediate(ack, out, out_capacity, now_ms);
    }
    if (incoming.ttl <= 1) {
      return 0;
    }
    CprWireFrame forward = incoming;
    forward.src = node_id_;
    forward.dst = incoming.path.nodes[incoming.path_index + 1U];
    forward.sequence = nextSequence();
    forward.path_index = static_cast<std::uint8_t>(incoming.path_index + 1U);
    forward.ttl = static_cast<std::uint8_t>(incoming.ttl - 1U);
    return pushImmediate(forward, out, out_capacity, now_ms);
  }

  std::size_t handleAck(const CprWireFrame& incoming,
                        std::uint32_t now_ms,
                        CprOutboundFrame* out,
                        std::size_t out_capacity) {
    if (!cprWirePathValid(incoming.path) || incoming.path.length < 2 ||
        incoming.path_index + 1U >= incoming.path.length ||
        incoming.dst != incoming.path.nodes[incoming.path_index] ||
        incoming.payload_len != 0U ||
        incoming.src != incoming.path.nodes[incoming.path_index + 1U]) {
      return 0;
    }
    CprAckObservation observation{};
    observation.receiver = node_id_;
    observation.sender = incoming.src;
    observation.flow_id = incoming.flow_id;
    observation.request_id = incoming.request_id;
    observation.origin = incoming.path.nodes[incoming.path.length - 1U];
    observation.final_dst = incoming.path.nodes[0];
    observation.path = incoming.path;
    observation.path_index = incoming.path_index;
    observation.repair_index = incoming.repair_index;
    observation.route_generation = incoming.route_generation;
    observation.app_payload = incoming.payload_len != 0U;

    // All radios can overhear a decoded unicast ACK. Only off-path pending
    // floods may be canceled; intended reverse-path hops must still relay it.
    relays_.cancelForAck(node_id_, observation);
    if (incoming.dst != node_id_) {
      return 0;
    }

    if (incoming.path_index > 0) {
      if (incoming.ttl <= 1U) {
        return 0;
      }
      CprWireFrame forward = incoming;
      forward.src = node_id_;
      forward.dst = incoming.path.nodes[incoming.path_index - 1U];
      forward.sequence = nextSequence();
      forward.path_index = static_cast<std::uint8_t>(incoming.path_index - 1U);
      forward.ttl = incoming.ttl > 1 ? static_cast<std::uint8_t>(incoming.ttl - 1U) : 0;
      return pushImmediate(forward, out, out_capacity, now_ms);
    }

    const std::uint32_t generation = routes_.generation(observation.origin, now_ms);
    const CprAckResult result = controller_.acceptAck(incomingToAck(observation), generation, now_ms);
    if (result.accepted) {
      const RouteEntry* current = routes_.find(observation.origin, now_ms);
      if (current != nullptr && current->path == observation.path) {
        (void)routes_.refresh(observation.origin, current->generation, now_ms,
                              kDefaultCprRouteLifetimeMs);
      } else {
        (void)routes_.install(observation.origin, observation.path, now_ms,
                              kDefaultCprRouteLifetimeMs);
      }
      if (AppRecord* app = findApp(incoming.flow_id)) {
        app->active = false;
      }
      controller_.retire(incoming.flow_id);
    }
    return 0;
  }

  CprAckObservation incomingToAck(const CprAckObservation& observation) const { return observation; }

  std::size_t handleFlood(const CprWireFrame& incoming,
                          std::uint32_t now_ms,
                          CprOutboundFrame* out,
                          std::size_t out_capacity) {
    if (!cprWirePathValid(incoming.path) || incoming.path_index + 1U != incoming.path.length ||
        incoming.src != incoming.path.nodes[incoming.path.length - 1U] ||
        incoming.path.contains(node_id_)) {
      return 0;
    }
    Path path = incoming.path;
    if (path.length >= kMaxPathNodes) {
      return 0;
    }
    path.nodes[path.length++] = node_id_;
    if (incoming.dst == node_id_) {
      if (!enqueueDelivery(incoming, now_ms)) {
        return 0;
      }
      CprWireFrame ack = baseFrame(CprFrameType::Ack, path.nodes[path.length - 2U], incoming.flow_id, now_ms);
      ack.request_id = incoming.request_id;
      ack.created_at_ms = incoming.created_at_ms;
      ack.remaining_budget_ms = incoming.remaining_budget_ms;
      ack.route_generation = incoming.route_generation;
      ack.repair_index = incoming.repair_index;
      ack.path = path;
      ack.path_index = static_cast<std::uint8_t>(path.length - 2U);
      ack.ttl = static_cast<std::uint8_t>(path.length - 1U);
      return pushImmediate(ack, out, out_capacity, now_ms);
    }
    if (!markSeen(incoming, now_ms)) {
      return 0;
    }
    if (incoming.ttl <= 1) {
      return 0;
    }
    RelaySlot* slot = acquireRelaySlot();
    if (slot == nullptr) {
      return 0;
    }
    slot->active = true;
    slot->offered = false;
    slot->due_at_ms = now_ms + kDefaultCprRelayJitterMs + (node_id_ % 7U) * 10U;
    slot->expires_at_ms = now_ms + incoming.remaining_budget_ms;
    slot->token = PendingTxToken{};
    if (++next_relay_lease_ == 0U) {
      ++next_relay_lease_;
    }
    slot->token.lease = next_relay_lease_;
    slot->frame = incoming;
    slot->frame.src = node_id_;
    slot->frame.sequence = nextSequence();
    slot->frame.ttl = static_cast<std::uint8_t>(incoming.ttl - 1U);
    slot->frame.path = path;
    slot->frame.path_index = static_cast<std::uint8_t>(path.length - 1U);
    slot->ledger_record = CprPendingRelay{
        node_id_, path.nodes[0], incoming.dst, incoming.flow_id, incoming.request_id,
        incoming.route_generation, incoming.repair_index, path, &slot->token};
    if (!relays_.enroll(slot->ledger_record)) {
      slot->active = false;
    }
    return 0;
  }

  RelaySlot* acquireRelaySlot() {
    for (auto& slot : relay_slots_) {
      if (!slot.active) {
        return &slot;
      }
    }
    return nullptr;
  }

  std::size_t emitDueRelays(std::uint32_t now_ms,
                            CprOutboundFrame* out,
                            std::size_t out_capacity) {
    std::size_t count = 0;
    for (auto& slot : relay_slots_) {
      if (!slot.active || slot.offered) {
        continue;
      }
      if (slot.token.canceled || !cprTimeBefore(now_ms, slot.expires_at_ms)) {
        slot.token.canceled = true;
        slot.active = false;
        continue;
      }
      if (cprTimeBefore(now_ms, slot.due_at_ms) || count >= out_capacity) {
        continue;
      }
      out[count] = CprOutboundFrame{};
      out[count].frame = slot.frame;
      out[count].due_at_ms = slot.due_at_ms;
      out[count].relay_pending = true;
      out[count].pending = &slot.token;
      out[count].pending_lease = slot.token.lease;
      out[count].expires_at_ms = slot.expires_at_ms;
      slot.offered = true;
      ++count;
    }
    return count;
  }

  void retireRelaySlots() {
    for (auto& slot : relay_slots_) {
      if (slot.active && (slot.token.canceled || slot.token.committed)) {
        slot.active = false;
      }
    }
  }
};

}  // namespace meshecho_cpr
