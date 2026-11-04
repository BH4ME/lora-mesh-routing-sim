#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace meshecho_cpr {

using NodeId = std::uint16_t;

// Local intervals must be shorter than half the uint32_t clock range.
inline bool cprTimeBefore(std::uint32_t now, std::uint32_t future) {
  const std::uint32_t distance = future - now;
  return distance != 0U && distance < 0x80000000U;
}

constexpr std::size_t kMaxPathNodes = 8;
constexpr std::size_t kMaxRoutes = 8;
constexpr std::size_t kMaxCprFlows = 8;
constexpr std::size_t kMaxPendingRelays = 8;

constexpr std::uint8_t kInitialRepair = 0;
constexpr std::uint8_t kRepeatRepair = 1;
constexpr std::uint8_t kRecoveryRepair = 2;

struct Path {
  std::uint8_t length = 0;
  NodeId nodes[kMaxPathNodes] = {};

  bool valid() const {
    if (length < 2 || length > kMaxPathNodes) {
      return false;
    }
    for (std::size_t i = 0; i < length; ++i) {
      if (nodes[i] == 0 || nodes[i] == 0xFFFFU) {
        return false;
      }
      for (std::size_t j = 0; j < i; ++j) {
        if (nodes[i] == nodes[j]) {
          return false;
        }
      }
    }
    return true;
  }

  bool operator==(const Path& other) const {
    if (length != other.length) {
      return false;
    }
    for (std::size_t i = 0; i < length; ++i) {
      if (nodes[i] != other.nodes[i]) {
        return false;
      }
    }
    return true;
  }

  bool contains(NodeId node) const {
    for (std::size_t i = 0; i < length; ++i) {
      if (nodes[i] == node) {
        return true;
      }
    }
    return false;
  }
};

struct RouteEntry {
  bool active = false;
  NodeId destination = 0;
  Path path{};
  std::uint32_t generation = 0;
  // Four-argument installs may wrap the expiry to zero, so its presence is
  // separate from its timestamp. Legacy nonzero absolute expiries still work.
  std::uint32_t expires_at_ms = 0;
  bool has_expiry = false;

  bool hasExpiry() const { return has_expiry || expires_at_ms != 0U; }

  bool usableAt(std::uint32_t now_ms) const {
    return active && (!hasExpiry() || cprTimeBefore(now_ms, expires_at_ms));
  }
};

struct RouteInstallResult {
  bool accepted = false;
  std::uint32_t generation = 0;
  std::uint32_t expires_at_ms = 0;
};

class RouteTable {
 public:
  // Installs a route with an absolute expiry.  The two-argument overload is
  // retained for callers that deliberately use a non-expiring route.
  RouteInstallResult install(NodeId destination, const Path& path,
                             std::uint32_t expires_at_ms = 0U) {
    if (!path.valid() || path.nodes[path.length - 1U] != destination) {
      return {};
    }

    RouteEntry* slot = findMutable(destination);
    if (slot == nullptr) {
      for (auto& entry : entries_) {
        if (!entry.active) {
          slot = &entry;
          break;
        }
      }
    }
    if (slot == nullptr) {
      return {};
    }

    slot->active = true;
    slot->destination = destination;
    slot->path = path;
    slot->generation = nextGeneration();
    slot->expires_at_ms = expires_at_ms;
    slot->has_expiry = expires_at_ms != 0U;
    return {true, slot->generation, slot->expires_at_ms};
  }

  // Local lifetimes use modular millis() arithmetic, including expiry zero.
  RouteInstallResult install(NodeId destination, const Path& path,
                             std::uint32_t installed_at_ms,
                             std::uint32_t lifetime_ms) {
    if (lifetime_ms == 0U || lifetime_ms >= 0x80000000U) {
      return {};
    }
    expire(installed_at_ms);
    RouteInstallResult result = install(destination, path, installed_at_ms + lifetime_ms);
    if (result.accepted) {
      findMutable(destination)->has_expiry = true;
    }
    return result;
  }

  const RouteEntry* find(NodeId destination) const {
    for (const auto& entry : entries_) {
      if (entry.active && entry.destination == destination) {
        return &entry;
      }
    }
    return nullptr;
  }

  const RouteEntry* find(NodeId destination, std::uint32_t now_ms) const {
    for (const auto& entry : entries_) {
      if (entry.destination == destination && entry.usableAt(now_ms)) {
        return &entry;
      }
    }
    return nullptr;
  }

  RouteEntry* findMutable(NodeId destination) {
    for (auto& entry : entries_) {
      if (entry.active && entry.destination == destination) {
        return &entry;
      }
    }
    return nullptr;
  }

  std::uint32_t generation(NodeId destination) const {
    const RouteEntry* entry = find(destination);
    return entry == nullptr ? 0U : entry->generation;
  }

  std::uint32_t generation(NodeId destination, std::uint32_t now_ms) const {
    const RouteEntry* entry = find(destination, now_ms);
    return entry == nullptr ? 0U : entry->generation;
  }

  std::uint32_t expiry(NodeId destination) const {
    const RouteEntry* entry = find(destination);
    return entry == nullptr ? 0U : entry->expires_at_ms;
  }

  bool expire(std::uint32_t now_ms) {
    bool changed = false;
    for (auto& entry : entries_) {
      if (entry.active && entry.hasExpiry() &&
          !cprTimeBefore(now_ms, entry.expires_at_ms)) {
        entry.active = false;
        changed = true;
      }
    }
    return changed;
  }

  bool invalidate(NodeId destination) {
    RouteEntry* entry = findMutable(destination);
    if (entry == nullptr) {
      return false;
    }
    entry->active = false;
    return true;
  }

  bool invalidate(NodeId destination, std::uint32_t expected_generation) {
    RouteEntry* entry = findMutable(destination);
    if (entry == nullptr || expected_generation == 0U ||
        entry->generation != expected_generation) {
      return false;
    }
    entry->active = false;
    return true;
  }

  bool refresh(NodeId destination, std::uint32_t expected_generation,
               std::uint32_t now_ms, std::uint32_t lifetime_ms) {
    RouteEntry* entry = findMutable(destination);
    if (entry == nullptr || !entry->usableAt(now_ms) ||
        entry->generation != expected_generation || lifetime_ms == 0U ||
        lifetime_ms >= 0x80000000U) {
      return false;
    }
    entry->expires_at_ms = now_ms + lifetime_ms;
    entry->has_expiry = true;
    return true;
  }

 private:
  std::uint32_t nextGeneration() {
    ++next_generation_;
    if (next_generation_ == 0U) {
      ++next_generation_;
    }
    return next_generation_;
  }

  std::array<RouteEntry, kMaxRoutes> entries_{};
  std::uint32_t next_generation_ = 0;
};

enum class CprAction : std::uint8_t {
  R_INITIAL,
  F_INITIAL,
  R_REPEAT,
  F_RECOVERY,
  DROP,
};

struct CprDecision {
  CprAction action = CprAction::DROP;
  const char* reason = "unknown";
};

struct CprAckObservation {
  NodeId receiver = 0;
  NodeId sender = 0;
  std::uint32_t flow_id = 0;
  std::uint32_t request_id = 0;
  NodeId origin = 0;
  NodeId final_dst = 0;
  Path path{};
  std::uint8_t path_index = 0;
  std::uint8_t repair_index = 0;
  bool app_payload = false;
  // Zero is meaningful only for a genuinely route-free initial flood.
  std::uint32_t route_generation = 0;
};

struct CprAckResult {
  bool accepted = false;
  const char* reason = "unknown";
};

struct CprFlowRecord {
  bool active = false;
  std::uint32_t flow_id = 0;
  NodeId source = 0;
  NodeId destination = 0;
  std::uint32_t enqueue_at_ms = 0;
  std::uint32_t deadline_ms = 0;
  CprAction initial_action = CprAction::DROP;
  Path initial_path{};
  std::uint32_t initial_route_generation = 0;
  std::uint32_t initial_route_expiry_ms = 0;
  std::uint32_t recovery_route_generation = 0;
  std::uint32_t recovery_route_expiry_ms = 0;
  std::uint32_t initial_started_at_ms = 0;
  std::uint32_t repeat_started_at_ms = 0;
  std::uint32_t recovery_started_at_ms = 0;
  bool initial_started = false;
  bool repeat_requested = false;
  bool repeat_started = false;
  bool recovery_requested = false;
  bool recovery_started = false;
  bool acked = false;
  std::uint32_t acked_at_ms = 0;
  bool initial_route_has_expiry = false;
  bool recovery_route_has_expiry = false;
};

struct PendingTxToken {
  bool canceled = false;
  bool committed = false;
  std::uint32_t lease = 0;
};

struct CprPendingRelay {
  NodeId relay = 0;
  NodeId origin = 0;
  NodeId final_dst = 0;
  std::uint32_t flow_id = 0;
  std::uint32_t request_id = 0;
  std::uint32_t route_generation = 0;
  std::uint8_t repair_index = 0;
  Path path{};
  PendingTxToken* pending = nullptr;
};

class CprRelayLedger {
 public:
  bool enroll(const CprPendingRelay& record) {
    if (record.relay == 0 || record.flow_id == 0 || record.request_id == 0 ||
        record.pending == nullptr || !record.path.valid()) {
      return false;
    }
    if (record.repair_index > kRecoveryRepair) {
      return false;
    }

    for (auto& slot : records_) {
      if (slot.active && sameKey(slot.record, record)) {
        if (slot.record.pending != nullptr &&
            slot.record.pending != record.pending &&
            !slot.record.pending->committed) {
          slot.record.pending->canceled = true;
        }
        slot.record = record;
        return true;
      }
    }

    Slot* target = nullptr;
    for (auto& slot : records_) {
      if (!slot.active) {
        target = &slot;
        break;
      }
    }
    if (target == nullptr) {
      target = &records_[oldestIndex()];
      if (target->record.pending != nullptr && !target->record.pending->committed) {
        target->record.pending->canceled = true;
      }
    }

    target->active = true;
    target->serial = ++serial_;
    target->record = record;
    return true;
  }

  bool cancelForAck(NodeId relay, const CprAckObservation& ack) {
    if (ack.receiver != relay || ack.flow_id == 0 || ack.request_id != ack.flow_id ||
        ack.repair_index > kRecoveryRepair || !ack.path.valid() ||
        ack.path.nodes[0] != ack.final_dst ||
        ack.path.nodes[ack.path.length - 1U] != ack.origin ||
        ack.path_index >= ack.path.length - 1U ||
        ack.path.nodes[ack.path_index + 1U] != ack.sender || ack.app_payload ||
        ack.path.contains(relay)) {
      return false;
    }

    for (auto& slot : records_) {
      if (!slot.active || slot.record.relay != relay ||
          slot.record.origin != ack.final_dst ||
          slot.record.final_dst != ack.origin ||
          slot.record.flow_id != ack.flow_id ||
          slot.record.request_id != ack.request_id ||
          slot.record.route_generation != ack.route_generation ||
          slot.record.repair_index != ack.repair_index) {
        continue;
      }
      if (slot.record.pending == nullptr || slot.record.pending->canceled ||
          slot.record.pending->committed) {
        return false;
      }
      slot.record.pending->canceled = true;
      slot.active = false;
      return true;
    }
    return false;
  }

  void retire() {
    for (auto& slot : records_) {
      if (!slot.active || slot.record.pending == nullptr ||
          slot.record.pending->canceled || slot.record.pending->committed) {
        slot.active = false;
      }
    }
  }

  std::size_t activeCount() const {
    std::size_t count = 0;
    for (const auto& slot : records_) {
      if (slot.active) {
        ++count;
      }
    }
    return count;
  }

 private:
  struct Slot {
    bool active = false;
    std::uint32_t serial = 0;
    CprPendingRelay record{};
  };

  static bool sameKey(const CprPendingRelay& lhs, const CprPendingRelay& rhs) {
    return lhs.relay == rhs.relay && lhs.origin == rhs.origin &&
           lhs.final_dst == rhs.final_dst && lhs.flow_id == rhs.flow_id &&
           lhs.request_id == rhs.request_id &&
           lhs.repair_index == rhs.repair_index;
  }

  std::size_t oldestIndex() const {
    std::size_t oldest = 0;
    for (std::size_t i = 1; i < records_.size(); ++i) {
      if (records_[i].serial < records_[oldest].serial) {
        oldest = i;
      }
    }
    return oldest;
  }

  std::array<Slot, kMaxPendingRelays> records_{};
  std::uint32_t serial_ = 0;
};

class CprController {
 public:
  CprDecision beginFlow(std::uint32_t flow_id,
                        NodeId source,
                        NodeId destination,
                        std::uint32_t enqueue_at_ms,
                        std::uint32_t deadline_ms,
                        const RouteEntry* route,
                        std::uint32_t route_generation,
                        std::uint32_t route_bound_ms,
                        std::uint32_t flood_bound_ms) {
    if (source == 0U || source == 0xFFFFU || destination == 0U ||
        destination == 0xFFFFU || source == destination) {
      return {CprAction::DROP, "invalid-endpoint"};
    }
    if (!cprTimeBefore(enqueue_at_ms, deadline_ms)) {
      return {CprAction::DROP, "invalid-deadline"};
    }
    CprFlowRecord* flow = acquire(flow_id);
    if (flow == nullptr) {
      return {CprAction::DROP, "flow-capacity"};
    }
    *flow = CprFlowRecord{};
    flow->active = true;
    flow->flow_id = flow_id;
    flow->source = source;
    flow->destination = destination;
    flow->enqueue_at_ms = enqueue_at_ms;
    flow->deadline_ms = deadline_ms;
    flow->initial_route_generation = route_generation;
    flow->initial_route_expiry_ms = route == nullptr ? 0U : route->expires_at_ms;
    flow->initial_route_has_expiry = route != nullptr && route->hasExpiry();

    const bool route_fits = route != nullptr && route->usableAt(enqueue_at_ms) &&
                            route_generation != 0U &&
                            route->generation == route_generation &&
                            route->path.valid() &&
                            route->destination == destination &&
                            route->path.nodes[0] == source &&
                            route->path.nodes[route->path.length - 1U] == destination &&
                            fits(enqueue_at_ms, route_bound_ms, deadline_ms);
    if (route_fits) {
      flow->initial_action = CprAction::R_INITIAL;
      flow->initial_path = route->path;
      return {CprAction::R_INITIAL, "confirmed-route"};
    }

    if (fits(enqueue_at_ms, flood_bound_ms, deadline_ms)) {
      flow->initial_action = CprAction::F_INITIAL;
      flow->initial_route_generation = 0U;
      flow->initial_route_expiry_ms = 0U;
      flow->initial_route_has_expiry = false;
      return {CprAction::F_INITIAL, "no-feasible-confirmed-route"};
    }
    flow->initial_action = CprAction::DROP;
    return {CprAction::DROP, "deadline-infeasible"};
  }

  bool markInitialTxStarted(std::uint32_t flow_id, std::uint32_t now_ms) {
    CprFlowRecord* flow = find(flow_id);
    if (flow == nullptr || flow->acked || flow->initial_action == CprAction::DROP ||
        flow->initial_started || !cprTimeBefore(now_ms, flow->deadline_ms) ||
        (flow->initial_action == CprAction::R_INITIAL &&
         !routeUsableAt(*flow, now_ms))) {
      return false;
    }
    flow->initial_started = true;
    flow->initial_started_at_ms = now_ms;
    return true;
  }

  CprDecision requestRecovery(std::uint32_t flow_id,
                              std::uint32_t now_ms,
                              std::uint32_t route_bound_ms,
                              std::uint32_t flood_bound_ms,
                              std::uint32_t current_route_generation) {
    CprFlowRecord* flow = find(flow_id);
    if (flow == nullptr) {
      return {CprAction::DROP, "unknown-flow"};
    }
    if (flow->acked) {
      return {CprAction::DROP, "already-acked"};
    }
    if (!cprTimeBefore(now_ms, flow->deadline_ms)) {
      return {CprAction::DROP, "deadline-infeasible"};
    }
    if (flow->recovery_started) {
      return {CprAction::DROP, "recovery-started"};
    }
    if (flow->initial_action != CprAction::R_INITIAL) {
      return {CprAction::DROP, "no-routed-initial"};
    }
    if (!flow->initial_started) {
      return {CprAction::DROP, "initial-not-started"};
    }
    if (current_route_generation != flow->initial_route_generation) {
      return {CprAction::DROP, "stale-route-generation"};
    }
    if (!routeUsableAt(*flow, now_ms)) {
      return {CprAction::DROP, "stale-route-expiry"};
    }

    if (!flow->repeat_started) {
      if (flow->repeat_requested) {
        return {CprAction::DROP, "repeat-pending"};
      }
      if (!fits(now_ms, route_bound_ms, flow->deadline_ms)) {
        return {CprAction::DROP, "repeat-deadline-infeasible"};
      }
      flow->repeat_requested = true;
      return {CprAction::R_REPEAT, "repeat-after-initial-miss"};
    }

    if (flow->recovery_requested) {
      return {CprAction::DROP, "recovery-pending"};
    }
    if (!fits(now_ms, flood_bound_ms, flow->deadline_ms)) {
      return {CprAction::DROP, "recovery-deadline-infeasible"};
    }
    flow->recovery_requested = true;
    flow->recovery_route_generation = current_route_generation;
    flow->recovery_route_expiry_ms = flow->initial_route_expiry_ms;
    flow->recovery_route_has_expiry = flow->initial_route_has_expiry;
    return {CprAction::F_RECOVERY, "recovery-fits-after-repeat"};
  }

  bool markRepeatTxStarted(std::uint32_t flow_id, std::uint32_t now_ms) {
    CprFlowRecord* flow = find(flow_id);
    if (flow == nullptr || flow->acked || !flow->repeat_requested ||
        flow->repeat_started || !cprTimeBefore(now_ms, flow->deadline_ms) ||
        !routeUsableAt(*flow, now_ms)) {
      return false;
    }
    flow->repeat_started = true;
    flow->repeat_started_at_ms = now_ms;
    return true;
  }

  bool markRecoveryTxStarted(std::uint32_t flow_id, std::uint32_t now_ms) {
    CprFlowRecord* flow = find(flow_id);
    if (flow == nullptr || flow->acked || !flow->recovery_requested ||
        flow->recovery_started || !cprTimeBefore(now_ms, flow->deadline_ms) ||
        !routeUsableAt(*flow, now_ms)) {
      return false;
    }
    flow->recovery_started = true;
    flow->recovery_started_at_ms = now_ms;
    return true;
  }

  CprAckResult acceptAck(const CprAckObservation& ack,
                         std::uint32_t current_route_generation,
                         std::uint32_t now_ms) {
    CprFlowRecord* flow = find(ack.flow_id);
    if (flow == nullptr) {
      return {false, "unknown-flow"};
    }
    if (flow->acked) {
      return {false, "already-acked"};
    }
    if (ack.request_id != ack.flow_id) {
      return {false, "flow-request-mismatch"};
    }
    if (ack.receiver != flow->source || ack.origin != flow->destination ||
        ack.final_dst != flow->source) {
      return {false, "endpoint-mismatch"};
    }
    if (ack.app_payload) {
      return {false, "ack-has-payload"};
    }
    if (!cprTimeBefore(now_ms, flow->deadline_ms)) {
      return {false, "late"};
    }
    if (!ack.path.valid() || ack.path.nodes[0] != flow->source ||
        ack.path.nodes[ack.path.length - 1U] != flow->destination) {
      return {false, "path-endpoint-mismatch"};
    }
    if (ack.path_index != 0 || ack.sender != ack.path.nodes[1]) {
      return {false, "path-or-sender-mismatch"};
    }
    if (ack.repair_index > kRecoveryRepair) {
      return {false, "marker-mismatch"};
    }

    const std::uint32_t expected_generation =
        ack.repair_index == kRecoveryRepair &&
                flow->recovery_route_generation != 0U
            ? flow->recovery_route_generation
            : flow->initial_route_generation;
    const std::uint32_t expected_expiry =
        ack.repair_index == kRecoveryRepair
            ? flow->recovery_route_expiry_ms
            : flow->initial_route_expiry_ms;
    const bool expected_has_expiry =
        (ack.repair_index == kRecoveryRepair
             ? flow->recovery_route_has_expiry
             : flow->initial_route_has_expiry) || expected_expiry != 0U;
    if (flow->initial_action == CprAction::R_INITIAL && expected_has_expiry &&
        !cprTimeBefore(now_ms, expected_expiry)) {
      return {false, "stale-route-expiry"};
    }
    if (ack.route_generation != expected_generation) {
      return {false, "stale-route-generation"};
    }

    if (ack.repair_index == kInitialRepair) {
      if (!flow->initial_started) {
        return {false, "initial-not-started"};
      }
      if (flow->initial_action == CprAction::R_INITIAL &&
          !(ack.path == flow->initial_path)) {
        return {false, "initial-path-mismatch"};
      }
      if (flow->initial_action == CprAction::R_INITIAL &&
          current_route_generation != flow->initial_route_generation) {
        return {false, "stale-route-generation"};
      }
    } else if (ack.repair_index == kRepeatRepair) {
      if (!flow->repeat_started) {
        return {false, "repeat-not-started"};
      }
      if (!(ack.path == flow->initial_path)) {
        return {false, "repeat-path-mismatch"};
      }
      if (current_route_generation != flow->initial_route_generation) {
        return {false, "stale-route-generation"};
      }
    } else {
      if (!flow->recovery_started) {
        return {false, "recovery-not-started"};
      }
      const std::uint32_t expected = flow->recovery_route_generation == 0
                                         ? flow->initial_route_generation
                                         : flow->recovery_route_generation;
      if (current_route_generation != expected) {
        return {false, "stale-route-generation"};
      }
    }

    flow->acked = true;
    flow->acked_at_ms = now_ms;
    return {true, "accepted"};
  }

  bool isAcked(std::uint32_t flow_id) const {
    const CprFlowRecord* flow = find(flow_id);
    if (flow != nullptr) {
      return flow->acked;
    }
    for (const auto& completed : completed_) {
      if (completed.flow_id == flow_id && flow_id != 0U) {
        return completed.acked;
      }
    }
    return false;
  }

  bool wasRetired(std::uint32_t flow_id) const {
    for (const auto& completed : completed_) {
      if (completed.flow_id == flow_id && flow_id != 0U) {
        return true;
      }
    }
    return false;
  }

  bool retire(std::uint32_t flow_id) {
    CprFlowRecord* flow = find(flow_id);
    if (flow == nullptr) {
      return false;
    }
    completed_[next_completed_] = {flow_id, flow->acked};
    next_completed_ = (next_completed_ + 1U) % completed_.size();
    *flow = CprFlowRecord{};
    return true;
  }

  const CprFlowRecord* flow(std::uint32_t flow_id) const {
    return find(flow_id);
  }

 private:
  static bool routeUsableAt(const CprFlowRecord& flow, std::uint32_t now_ms) {
    return (!flow.initial_route_has_expiry && flow.initial_route_expiry_ms == 0U) ||
           cprTimeBefore(now_ms, flow.initial_route_expiry_ms);
  }

  static bool fits(std::uint32_t now_ms,
                   std::uint32_t duration_ms,
                   std::uint32_t deadline_ms) {
    return cprTimeBefore(now_ms, deadline_ms) && duration_ms <= deadline_ms - now_ms;
  }

  CprFlowRecord* find(std::uint32_t flow_id) {
    for (auto& flow : flows_) {
      if (flow.active && flow.flow_id == flow_id) {
        return &flow;
      }
    }
    return nullptr;
  }

  const CprFlowRecord* find(std::uint32_t flow_id) const {
    for (const auto& flow : flows_) {
      if (flow.active && flow.flow_id == flow_id) {
        return &flow;
      }
    }
    return nullptr;
  }

  CprFlowRecord* acquire(std::uint32_t flow_id) {
    if (flow_id == 0 || wasRetired(flow_id)) {
      return nullptr;
    }
    if (find(flow_id) != nullptr) {
      return nullptr;
    }
    for (auto& flow : flows_) {
      if (!flow.active) {
        return &flow;
      }
    }
    return nullptr;
  }

  struct CompletedFlow {
    std::uint32_t flow_id = 0;
    bool acked = false;
  };

  std::array<CprFlowRecord, kMaxCprFlows> flows_{};
  std::array<CompletedFlow, kMaxCprFlows> completed_{};
  std::size_t next_completed_ = 0;
};

}  // namespace meshecho_cpr

// Compatibility facade for the compact CprCore API used by the first native
// scaffold. The production firmware uses CprNode/CprRuntime above; this
// facade keeps the public test contract while retaining physical-start gates.
namespace meshecho_cpr {

enum class Action : std::uint8_t { R_INITIAL, F_INITIAL, R_REPEAT, F_RECOVERY, DROP };
struct Decision { Action action = Action::DROP; const char* reason = "unknown"; };
struct FlowRequest {
  std::uint32_t flow_id = 0; NodeId source = 0; NodeId destination = 0;
  std::uint32_t enqueue_ms = 0; std::uint32_t deadline_ms = 0;
  std::uint32_t route_bound_ms = 0; std::uint32_t flood_bound_ms = 0;
};
struct AckInfo {
  std::uint32_t flow_id = 0, request_id = 0; NodeId source = 0, destination = 0;
  std::uint32_t generation = 0; std::uint8_t marker = 0; NodeId sender = 0;
  std::uint8_t path_index = 0, path_len = 0; NodeId path[kMaxPathNodes] = {};
};
struct PendingRelay {
  NodeId relay = 0, origin = 0, destination = 0; std::uint32_t flow_id = 0, request_id = 0, generation = 0;
  std::uint8_t marker = 0; NodeId sender = 0; std::uint8_t path_len = 0;
  NodeId path[kMaxPathNodes] = {}; bool committed = false; bool canceled = false;
};

class CprCore {
 public:
  explicit CprCore(NodeId node_id) : node_id_(node_id) {}

  bool confirmRoute(NodeId source, NodeId destination, const NodeId* path,
                   std::size_t length, std::uint32_t generation,
                   std::uint32_t now_ms, std::uint32_t lifetime_ms) {
    if (source == 0 || destination == 0 || path == nullptr || generation == 0 ||
        length < 2 || length > kMaxPathNodes || path[0] != source ||
        path[length - 1U] != destination || !validPath(path, length)) return false;
    route_.active = true; route_.source = source; route_.destination = destination;
    route_.generation = generation; route_.expires_at_ms = now_ms + lifetime_ms;
    route_.length = static_cast<std::uint8_t>(length); copy(route_.path, path, length);
    return true;
  }

  Decision beginFlow(const FlowRequest& request) {
    Flow* flow = slot(request.flow_id);
    if (flow == nullptr || request.flow_id == 0 || request.source == 0 ||
        request.destination == 0 || request.deadline_ms <= request.enqueue_ms) return {Action::DROP, "invalid-flow"};
    *flow = Flow{}; flow->active = true; flow->request = request;
    const bool routed = route_.active && route_.source == request.source &&
                        route_.destination == request.destination && route_.expires_at_ms > request.enqueue_ms;
    flow->generation = routed ? route_.generation : 0; flow->length = routed ? route_.length : 0;
    if (routed) { copy(flow->path, route_.path, route_.length); flow->pending = Action::R_INITIAL; return {Action::R_INITIAL, "confirmed-route"}; }
    flow->pending = Action::F_INITIAL; return {Action::F_INITIAL, "route-missing"};
  }

  bool onTxStarted(std::uint32_t flow_id, Action action, std::uint32_t at_ms) {
    Flow* flow = find(flow_id);
    if (flow == nullptr || !flow->active || flow->pending != action || at_ms >= flow->request.deadline_ms) return false;
    if (action == Action::R_INITIAL || action == Action::F_INITIAL) flow->initial_started = true;
    else if (action == Action::R_REPEAT) flow->repeat_started = true;
    else if (action == Action::F_RECOVERY) flow->recovery_started = true;
    else return false;
    flow->pending = Action::DROP; return true;
  }

  Decision onAttemptTimeout(std::uint32_t flow_id, std::uint32_t now_ms) {
    Flow* flow = find(flow_id);
    if (flow == nullptr || !flow->active || flow->acked || now_ms >= flow->request.deadline_ms) return {Action::DROP, "deadline"};
    if (flow->pending != Action::DROP) return {Action::DROP, "tx-not-started"};
    if (!flow->initial_started && !flow->repeat_started && !flow->recovery_started) return {Action::DROP, "initial-not-started"};
    if (!flow->repeat_started) { flow->pending = Action::R_REPEAT; return {Action::R_REPEAT, "repeat-after-initial"}; }
    if (!flow->recovery_started) { flow->pending = Action::F_RECOVERY; return {Action::F_RECOVERY, "recovery-after-repeat"}; }
    flow->active = false; return {Action::DROP, "recovery-started"};
  }

  bool acceptAck(const AckInfo& ack, std::uint32_t now_ms) {
    Flow* flow = find(ack.flow_id);
    if (flow == nullptr || !flow->active || flow->acked || ack.request_id != ack.flow_id ||
        ack.source != flow->request.source || ack.destination != flow->request.destination ||
        ack.generation != flow->generation || ack.marker > 2 || ack.path_index != 0 ||
        ack.path_len != flow->length || !validPath(ack.path, ack.path_len) ||
        !same(ack.path, flow->path, flow->length) || ack.sender != ack.path[ack.path_len - 1U] ||
        now_ms > flow->request.deadline_ms) return false;
    const bool started = ack.marker == 0 ? flow->initial_started : ack.marker == 1 ? flow->repeat_started : flow->recovery_started;
    if (!started) return false;
    flow->acked = true;
    flow->active = false;
    return true;
  }

  bool enrollRelay(const PendingRelay& relay) {
    if (relay.relay == 0 || relay.flow_id == 0 || relay.request_id == 0 || relay.generation == 0 ||
        !validPath(relay.path, relay.path_len)) return false;
    for (auto& slot : relays_) if (slot.active && slot.value.relay == relay.relay && slot.value.flow_id == relay.flow_id && slot.value.request_id == relay.request_id) {
      if (!slot.value.committed) slot.value.canceled = true;
      slot.value = relay;
      return true;
    }
    for (auto& slot : relays_) if (!slot.active) { slot.active = true; slot.value = relay; return true; }
    return false;
  }

  bool cancelRelayForAck(NodeId relay, const AckInfo& ack) {
    for (auto& slot : relays_) {
      PendingRelay& value = slot.value;
      if (!slot.active || value.relay != relay || value.committed || value.canceled ||
          value.flow_id != ack.flow_id || value.request_id != ack.request_id || value.generation != ack.generation ||
          value.marker != ack.marker || value.path_len != ack.path_len || ack.path_index != 0 ||
          ack.sender != ack.path[0] || !same(value.path, ack.path, value.path_len)) continue;
      value.canceled = true; slot.active = false; return true;
    }
    return false;
  }

 private:
  struct Route { bool active = false; NodeId source = 0, destination = 0; std::uint32_t generation = 0, expires_at_ms = 0; std::uint8_t length = 0; NodeId path[kMaxPathNodes] = {}; };
  struct Flow { bool active = false, acked = false; FlowRequest request{}; std::uint32_t generation = 0; std::uint8_t length = 0; NodeId path[kMaxPathNodes] = {}; Action pending = Action::DROP; bool initial_started = false, repeat_started = false, recovery_started = false; };
  struct RelaySlot { bool active = false; PendingRelay value{}; };
  static bool validPath(const NodeId* path, std::size_t length) { if (path == nullptr || length < 2 || length > kMaxPathNodes) return false; for (std::size_t i = 0; i < length; ++i) { if (path[i] == 0) return false; for (std::size_t j = 0; j < i; ++j) if (path[i] == path[j]) return false; } return true; }
  static void copy(NodeId* dst, const NodeId* src, std::size_t length) { for (std::size_t i = 0; i < length; ++i) dst[i] = src[i]; }
  static bool same(const NodeId* a, const NodeId* b, std::size_t length) { for (std::size_t i = 0; i < length; ++i) if (a[i] != b[i]) return false; return true; }
  Flow* slot(std::uint32_t id) { for (auto& f : flows_) if (f.active && f.request.flow_id == id) return &f; for (auto& f : flows_) if (!f.active) return &f; return nullptr; }
  Flow* find(std::uint32_t id) { for (auto& f : flows_) if (f.active && f.request.flow_id == id) return &f; return nullptr; }
  NodeId node_id_ = 0; Route route_{}; Flow flows_[kMaxCprFlows]{}; RelaySlot relays_[kMaxPendingRelays]{};
};

}  // namespace meshecho_cpr
