#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "smart_calm_prior.hpp"
#include "smart_calm_types.hpp"

namespace smart_calm {

inline float clampFloat(float value, float lo, float hi) {
  return std::max(lo, std::min(hi, value));
}

class SmartCalmController {
 public:
  struct Settings {
    std::uint16_t node_count = 50;
    float update_interval_s = 30.0f;
    float learning_rate = 0.45f;
    float discount = 0.75f;
    float exploration = 0.02f;
    float flow_timeout_s = 35.0f;
  };

  SmartCalmController() : SmartCalmController(Settings{}, defaultProfiles()) {}

  explicit SmartCalmController(
      Settings settings,
      std::array<Profile, kProfileCount> profiles = defaultProfiles())
      : settings_(settings), profiles_(profiles) {
    reset();
  }

  void reset() {
    q_values_.fill(0.0f);
    decisions_.fill(FlowDecision{});
    active_profile_index_ = 1;
    active_state_index_ = 0;
    policy_switch_count_ = 0;
    policy_update_count_ = 0;
    policy_reward_total_ = 0.0f;
    applyProfile(active_profile_index_);
    last_snapshot_ = Snapshot{};
  }

  template <std::size_t N>
  void loadPrior(const std::array<PriorEntry, N>& prior) {
    q_values_.fill(0.0f);
    for (const auto& entry : prior) {
      if (entry.state >= kStateCount || entry.action >= kActionCount) {
        continue;
      }
      q_values_[index(entry.state, entry.action)] = entry.value;
    }
  }

  void loadPrior(const PriorEntry* prior, std::size_t count) {
    q_values_.fill(0.0f);
    if (prior == nullptr) {
      return;
    }
    for (std::size_t i = 0; i < count; ++i) {
      const auto& entry = prior[i];
      if (entry.state >= kStateCount || entry.action >= kActionCount) {
        continue;
      }
      q_values_[index(entry.state, entry.action)] = entry.value;
    }
  }

  const Profile& activeProfile() const {
    return profiles_[active_profile_index_];
  }

  std::uint8_t activeProfileIndex() const {
    return active_profile_index_;
  }

  std::uint8_t activeStateIndex() const {
    return active_state_index_;
  }

  const std::array<float, kStateCount * kActionCount>& qValues() const {
    return q_values_;
  }

  const Settings& settings() const {
    return settings_;
  }

  std::uint8_t stateIndexFromSnapshot(const Snapshot& snapshot) const {
    const float attempts = std::max(1.0f, static_cast<float>(snapshot.unicast_flows));
    const float pdr = static_cast<float>(snapshot.unicast_deliveries) / attempts;
    const float route_attempts = static_cast<float>(snapshot.route_cache_hits + snapshot.route_cache_misses);
    const float miss_ratio = static_cast<float>(snapshot.route_cache_misses) / std::max(1.0f, route_attempts);
    const float collision_per_tx = static_cast<float>(snapshot.collision_fail) /
                                   std::max(1.0f, static_cast<float>(snapshot.tx_count));

    std::uint8_t reliability_bucket = 0;
    if (pdr < 0.65f || miss_ratio > 0.45f) {
      reliability_bucket = 0;
    } else if (pdr < 0.85f || miss_ratio > 0.25f) {
      reliability_bucket = 1;
    } else {
      reliability_bucket = 2;
    }

    const std::uint8_t congestion_bucket = collision_per_tx > 18.0f ? 1 : 0;
    return static_cast<std::uint8_t>(reliability_bucket * 2 + congestion_bucket);
  }

  std::uint8_t selectAction(std::uint8_t state_index, std::uint32_t entropy) const {
    const std::uint32_t exploration_threshold = static_cast<std::uint32_t>(settings_.exploration * 1000.0f);
    if ((entropy % 1000U) < exploration_threshold) {
      return static_cast<std::uint8_t>(entropy % kActionCount);
    }

    float best_score = -1.0e9f;
    std::uint8_t best_action = 0;
    for (std::uint8_t action = 0; action < kActionCount; ++action) {
      const float bias = profileBias(action);
      const float score = q_values_[index(state_index, action)] + bias;
      if (score > best_score || (score == best_score && action < best_action)) {
        best_score = score;
        best_action = action;
      }
    }
    return best_action;
  }

  std::uint8_t beginFlow(std::uint32_t flow_id,
                         const Snapshot& snapshot,
                         std::uint32_t entropy,
                         std::uint32_t now_ms) {
    const std::uint8_t state_index = stateIndexFromSnapshot(snapshot);
    const std::uint8_t action_index = selectAction(state_index, entropy);
    if (action_index != active_profile_index_) {
      ++policy_switch_count_;
    }
    active_state_index_ = state_index;
    active_profile_index_ = action_index;
    applyProfile(action_index);
    FlowDecision& decision = acquireDecision(flow_id);
    decision.active = true;
    decision.flow_id = flow_id;
    decision.state_index = state_index;
    decision.action_index = action_index;
    decision.confidence = 0.0f;
    decision.route_miss = 0;
    decision.fallback_count = 0;
    decision.timeout_retries = 0;
    decision.created_at_ms = now_ms;
    return action_index;
  }

  void markRouteMiss(std::uint32_t flow_id) {
    if (FlowDecision* decision = findDecision(flow_id)) {
      ++decision->route_miss;
    }
  }

  void markFallback(std::uint32_t flow_id) {
    if (FlowDecision* decision = findDecision(flow_id)) {
      ++decision->fallback_count;
    }
  }

  void markConfidence(std::uint32_t flow_id, float confidence) {
    if (FlowDecision* decision = findDecision(flow_id)) {
      decision->confidence = std::max(decision->confidence, clampFloat(confidence, 0.0f, 1.0f));
    }
  }

  void completeFlow(std::uint32_t flow_id,
                    bool delivered,
                    const Snapshot& snapshot,
                    std::uint32_t now_ms) {
    FlowDecision* decision = findDecision(flow_id);
    if (decision == nullptr || !decision->active) {
      return;
    }
    const float latency_s = static_cast<float>(now_ms - decision->created_at_ms) / 1000.0f;
    const float reward =
        (delivered ? 1.0f : -0.8f) - 0.02f * latency_s - 0.08f * decision->route_miss -
        0.035f * decision->fallback_count + 0.08f * decision->confidence;
    updateFromReward(*decision, reward, snapshot);
    decision->active = false;
  }

  void learningTick(const Snapshot& current, std::uint32_t entropy) {
    const Snapshot previous = last_snapshot_;
    const float reward = windowReward(previous, current);
    const std::uint8_t new_state = stateIndexFromSnapshot(current);
    const std::uint8_t old_action = active_profile_index_;
    const std::uint8_t old_state = active_state_index_;
    const std::size_t old_key = index(old_state, old_action);
    const float old_value = q_values_[old_key];
    const float best_next = bestNextValue(new_state);
    q_values_[old_key] =
        old_value + settings_.learning_rate * (reward + settings_.discount * best_next - old_value);
    ++policy_update_count_;
    policy_reward_total_ += reward;
    active_state_index_ = new_state;
    const std::uint8_t next_action = selectAction(new_state, entropy);
    if (next_action != active_profile_index_) {
      ++policy_switch_count_;
    }
    active_profile_index_ = next_action;
    applyProfile(next_action);
    last_snapshot_ = current;
  }

  std::size_t flowCapacity() const {
    return kMaxTrackedFlows;
  }

  void formatStatus(char* out, std::size_t out_size) const {
    if (out == nullptr || out_size == 0) {
      return;
    }
    const float pdr = last_snapshot_.unicast_flows
                          ? static_cast<float>(last_snapshot_.unicast_deliveries) /
                                static_cast<float>(last_snapshot_.unicast_flows)
                          : 0.0f;
    std::snprintf(
        out,
        out_size,
        "profile=%s state=%u q=%.3f reward=%.3f pdr=%.3f switch=%lu update=%lu",
        activeProfile().name,
        static_cast<unsigned>(active_profile_index_),
        q_values_[index(active_state_index_, active_profile_index_)],
        policy_reward_total_,
        pdr,
        static_cast<unsigned long>(policy_switch_count_),
        static_cast<unsigned long>(policy_update_count_));
  }

 private:
  Settings settings_;
  std::array<Profile, kProfileCount> profiles_;
  std::array<float, kStateCount * kActionCount> q_values_{};
  std::array<FlowDecision, kMaxTrackedFlows> decisions_{};
  Snapshot last_snapshot_{};
  std::uint8_t active_profile_index_ = 1;
  std::uint8_t active_state_index_ = 0;
  std::uint32_t policy_switch_count_ = 0;
  std::uint32_t policy_update_count_ = 0;
  float policy_reward_total_ = 0.0f;

  static constexpr std::size_t index(std::uint8_t state, std::uint8_t action) {
    return static_cast<std::size_t>(state) * kActionCount + action;
  }

  static float profileBias(std::uint8_t action) {
    switch (action) {
      case 0:
        return 0.015f;
      case 1:
        return 0.0f;
      case 2:
        return -0.015f;
      default:
        return 0.0f;
    }
  }

  float bestNextValue(std::uint8_t state) const {
    float best = q_values_[index(state, 0)];
    for (std::uint8_t action = 1; action < kActionCount; ++action) {
      best = std::max(best, q_values_[index(state, action)]);
    }
    return best;
  }

  float windowReward(const Snapshot& previous, const Snapshot& current) const {
    const float new_unicast = static_cast<float>(current.unicast_flows - previous.unicast_flows);
    const float new_broadcast = static_cast<float>(current.broadcast_flows - previous.broadcast_flows);
    const float new_unicast_deliveries =
        static_cast<float>(current.unicast_deliveries - previous.unicast_deliveries);
    const float new_broadcast_deliveries =
        static_cast<float>(current.broadcast_deliveries - previous.broadcast_deliveries);
    const float new_tx = static_cast<float>(current.tx_count - previous.tx_count);
    const float new_control = static_cast<float>(current.control_tx - previous.control_tx);
    const float new_collisions = static_cast<float>(current.collision_fail - previous.collision_fail);
    const float new_repairs =
        static_cast<float>(current.route_repair_count - previous.route_repair_count);
    const float new_fallback =
        static_cast<float>(current.fallback_forward_count - previous.fallback_forward_count);
    const float new_delay_total =
        current.delivery_delay_total_s - previous.delivery_delay_total_s;
    const float new_delay_samples =
        static_cast<float>(current.delivery_delay_samples - previous.delivery_delay_samples);

    const float unicast_pdr = new_unicast_deliveries / std::max(1.0f, new_unicast);
    const float broadcast_gain = new_broadcast_deliveries /
                                 std::max(1.0f, new_broadcast *
                                                         std::max(1.0f, static_cast<float>(settings_.node_count - 1)));
    const float avg_delay = new_delay_total / std::max(1.0f, new_delay_samples);
    const float control_ratio = new_control / std::max(1.0f, new_tx);
    const float collision_pressure = new_collisions / std::max(1.0f, new_tx);

    return 1.6f * unicast_pdr + 0.4f * broadcast_gain - 0.03f * avg_delay - 0.35f * control_ratio -
           0.012f * collision_pressure - 0.05f * new_repairs - 0.004f * new_fallback;
  }

  void updateFromReward(const FlowDecision& decision, float reward, const Snapshot& snapshot) {
    const std::uint8_t state = stateIndexFromSnapshot(snapshot);
    const std::size_t key = index(decision.state_index, decision.action_index);
    const float old_value = q_values_[key];
    const float best_next = bestNextValue(state);
    q_values_[key] =
        old_value + settings_.learning_rate * (reward + settings_.discount * best_next - old_value);
    ++policy_update_count_;
    policy_reward_total_ += reward;
  }

  void applyProfile(std::uint8_t index) {
    const Profile& profile = profiles_[index];
    route_ttl_s_ = profile.route_ttl_s;
    discovery_window_s_ = profile.discovery_window_s;
    fallback_confidence_threshold_ = profile.fallback_confidence_threshold;
    fallback_ttl_ = profile.fallback_ttl;
    fallback_delay_margin_s_ = profile.fallback_delay_margin_s;
    hop_penalty_per_hop_ = profile.hop_penalty_per_hop;
    route_age_penalty_ = profile.route_age_penalty;
  }

  FlowDecision* findDecision(std::uint32_t flow_id) {
    for (auto& decision : decisions_) {
      if (decision.active && decision.flow_id == flow_id) {
        return &decision;
      }
    }
    return nullptr;
  }

  FlowDecision& acquireDecision(std::uint32_t flow_id) {
    if (FlowDecision* existing = findDecision(flow_id)) {
      return *existing;
    }
    for (auto& decision : decisions_) {
      if (!decision.active) {
        return decision;
      }
    }
    return decisions_[0];
  }

  float route_ttl_s_ = 600.0f;
  float discovery_window_s_ = 2.0f;
  float fallback_confidence_threshold_ = 0.0f;
  std::uint8_t fallback_ttl_ = 2;
  float fallback_delay_margin_s_ = 0.6f;
  float hop_penalty_per_hop_ = 0.025f;
  float route_age_penalty_ = 0.1f;
};

}  // namespace smart_calm
