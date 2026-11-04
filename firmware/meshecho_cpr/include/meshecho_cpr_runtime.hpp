#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "meshecho_cpr_node.hpp"
#include "meshecho_cpr_budget.hpp"

namespace meshecho_cpr {

// The queue is deliberately larger than the number of application flows so a
// recovery burst and a few control frames can coexist without heap storage.
constexpr std::size_t kMaxCprRuntimeTx =
    kMaxCprPendingApps + kMaxCprRelaySlots + 8U;
constexpr std::size_t kMaxCprRuntimeBatch = kMaxCprPendingApps + kMaxCprRelaySlots;

struct CprRuntimeTx {
  CprOutboundFrame outbound{};
  CprEncodedFrame encoded{};
};

struct CprRuntimeStats {
  std::uint32_t rx_frames = 0;
  std::uint32_t rx_decode_errors = 0;
  std::uint32_t rx_budget_drops = 0;
  std::uint32_t tx_enqueued = 0;
  std::uint32_t tx_queue_drops = 0;
  std::uint32_t tx_encode_errors = 0;
  std::uint32_t tx_started = 0;
  std::uint32_t tx_marker_rejections = 0;
  std::uint32_t tx_discarded = 0;
  std::uint32_t tx_completion_failures = 0;
  std::uint32_t tx_canceled = 0;
  std::uint32_t deliveries_polled = 0;
};

// Board-neutral adapter between CprNode and a byte-oriented radio. The
// physical driver owns timing and interrupts; this class owns serialization,
// bounded queueing, and the point at which a TX is considered started.
class CprRuntime {
 public:
  explicit CprRuntime(NodeId node_id) : node_(node_id) {}

  CprRuntime(const CprRuntime&) = delete;
  CprRuntime& operator=(const CprRuntime&) = delete;
  CprRuntime(CprRuntime&&) = delete;
  CprRuntime& operator=(CprRuntime&&) = delete;

  CprNode& node() { return node_; }
  const CprNode& node() const { return node_; }
  const CprRuntimeStats& stats() const { return stats_; }
  std::size_t txCount() const { return tx_count_; }
  void setPacketAirtimeMs(std::uint32_t duration_ms) {
    packet_airtime_ms_ = duration_ms;
    airtime_configured_ = false;
  }

  bool setAirtimeConfig(const CprLoRaBudgetConfig& config) {
    if (cprFrameAirtimeMs(config, kCprMaxFrameSize) == 0U) {
      return false;
    }
    airtime_config_ = config;
    airtime_configured_ = true;
    return true;
  }

  std::size_t sendApp(NodeId destination,
                      std::uint32_t flow_id,
                      const std::uint8_t* payload,
                      std::size_t payload_len,
                      std::uint32_t now_ms,
                      std::uint32_t deadline_ms,
                      std::uint32_t route_bound_ms,
                      std::uint32_t flood_bound_ms) {
    CprOutboundFrame batch[kMaxCprRuntimeBatch]{};
    const std::size_t produced = node_.sendApp(
        destination, flow_id, payload, payload_len, now_ms, deadline_ms,
        route_bound_ms, flood_bound_ms, batch, kMaxCprRuntimeBatch);
    return enqueueBatch(batch, produced);
  }

  // Decodes one complete radio packet and queues all resulting control/data
  // frames. Invalid CRC, version, or frame fields are rejected before the
  // state machine sees them.
  std::size_t receive(const std::uint8_t* bytes,
                      std::size_t length,
                      std::uint32_t now_ms) {
    purgeCanceled();
    ++stats_.rx_frames;
    CprWireFrame frame{};
    if (!decodeCprFrame(bytes, length, &frame)) {
      ++stats_.rx_decode_errors;
      return 0;
    }
    const std::uint32_t rx_airtime_ms = packetAirtimeMs(length);
    if (frame.remaining_budget_ms <= rx_airtime_ms ||
        frame.remaining_budget_ms >= 0x80000000U) {
      ++stats_.rx_budget_drops;
      return 0;
    }
    frame.remaining_budget_ms -= rx_airtime_ms;
    CprOutboundFrame batch[kMaxCprRuntimeBatch]{};
    const std::size_t produced = node_.onFrame(
        frame, now_ms, batch, kMaxCprRuntimeBatch);
    return enqueueBatch(batch, produced);
  }

  // Advances discovery, deadline admission, recovery, and delayed relay
  // offers. The caller should invoke this from its main loop or scheduler.
  std::size_t poll(std::uint32_t now_ms) {
    purgeCanceled();
    CprOutboundFrame batch[kMaxCprRuntimeBatch]{};
    const std::size_t produced =
        node_.poll(now_ms, batch, kMaxCprRuntimeBatch);
    return enqueueBatch(batch, produced);
  }

  // Returns the oldest non-canceled TX. The returned object remains owned by
  // this runtime and is valid until onTxStarted() or discardTx().
  CprRuntimeTx* peekTx() {
    purgeCanceled();
    return tx_count_ == 0 ? nullptr : &tx_queue_[0];
  }

  const CprRuntimeTx* peekTx() const {
    return tx_count_ == 0 ? nullptr : &tx_queue_[0];
  }

  bool txDue(std::uint32_t now_ms) {
    CprRuntimeTx* tx = peekTx();
    return tx != nullptr && !cprTimeBefore(now_ms, tx->outbound.due_at_ms);
  }

  // Preflight immediately before the physical driver's startTransmit call.
  // Enqueueing a frame does not reserve its deadline budget or route epoch.
  bool prepareTx(std::uint32_t now_ms) {
    CprRuntimeTx* tx = peekTx();
    if (tx == nullptr || !txDue(now_ms)) {
      return false;
    }
    if (!cprTimeBefore(now_ms, tx->outbound.expires_at_ms) ||
        tx->outbound.expires_at_ms - now_ms <= packetAirtimeMs(tx->encoded.size) ||
        !node_.canTransmit(tx->outbound, now_ms)) {
      (void)discardTx();
      return false;
    }
    tx->outbound.frame.remaining_budget_ms = tx->outbound.expires_at_ms - now_ms;
    tx->encoded = encodeCprFrame(tx->outbound.frame);
    if (tx->encoded.size == 0U) {
      ++stats_.tx_encode_errors;
      (void)discardTx();
      return false;
    }
    return true;
  }

  // Call immediately after the radio accepts the physical TX start. This is
  // the commit point for CPR's initial/repeat/recovery markers; completion is
  // reported separately because the bytes may already be on air if the
  // asynchronous finish wait fails.
  bool onTxStarted(std::uint32_t now_ms) {
    CprRuntimeTx* tx = peekTx();
    if (tx == nullptr) {
      return false;
    }
    const bool accepted = node_.onTxStarted(tx->outbound, now_ms);
    ++stats_.tx_started;
    if (!accepted) {
      ++stats_.tx_marker_rejections;
    }
    removeFront();
    return accepted;
  }

  void noteTxCompletionFailure() { ++stats_.tx_completion_failures; }

  // Drops a queued TX without marking it as physically started. Pending
  // relay offers are canceled so a later ACK cannot race with a failed send.
  bool discardTx() {
    CprRuntimeTx* tx = peekTx();
    if (tx == nullptr) {
      return false;
    }
    node_.onTxDiscarded(tx->outbound);
    ++stats_.tx_discarded;
    removeFront();
    return true;
  }

  bool pollDelivery(CprDelivery* out) {
    const bool available = node_.pollDelivery(out);
    if (available) {
      ++stats_.deliveries_polled;
    }
    return available;
  }

 private:
  std::uint32_t packetAirtimeMs(std::size_t wire_bytes) const {
    return airtime_configured_ ? cprFrameAirtimeMs(airtime_config_, wire_bytes)
                              : packet_airtime_ms_;
  }

  std::size_t enqueueBatch(const CprOutboundFrame* batch, std::size_t count) {
    if (batch == nullptr) {
      return 0;
    }
    std::size_t queued = 0;
    for (std::size_t i = 0; i < count; ++i) {
      if (enqueueOne(batch[i])) {
        ++queued;
      }
    }
    return queued;
  }

  bool enqueueOne(const CprOutboundFrame& outbound) {
    if (tx_count_ >= kMaxCprRuntimeTx) {
      cancelUnqueued(outbound);
      ++stats_.tx_queue_drops;
      return false;
    }
    const CprEncodedFrame encoded = encodeCprFrame(outbound.frame);
    if (encoded.size == 0) {
      cancelUnqueued(outbound);
      ++stats_.tx_encode_errors;
      return false;
    }
    tx_queue_[tx_count_].outbound = outbound;
    tx_queue_[tx_count_].encoded = encoded;
    ++tx_count_;
    ++stats_.tx_enqueued;
    return true;
  }

  void cancelUnqueued(const CprOutboundFrame& outbound) {
    node_.onTxDiscarded(outbound);
  }

  void purgeCanceled() {
    std::size_t write = 0;
    for (std::size_t read = 0; read < tx_count_; ++read) {
      const PendingTxToken* pending = tx_queue_[read].outbound.pending;
      if (pending != nullptr &&
          (pending->lease != tx_queue_[read].outbound.pending_lease ||
           (pending->canceled && !pending->committed))) {
        ++stats_.tx_canceled;
        continue;
      }
      if (write != read) {
        tx_queue_[write] = tx_queue_[read];
      }
      ++write;
    }
    tx_count_ = write;
  }

  void removeFront() {
    if (tx_count_ == 0) {
      return;
    }
    for (std::size_t i = 1; i < tx_count_; ++i) {
      tx_queue_[i - 1U] = tx_queue_[i];
    }
    --tx_count_;
  }

  CprNode node_;
  std::array<CprRuntimeTx, kMaxCprRuntimeTx> tx_queue_{};
  std::size_t tx_count_ = 0;
  CprRuntimeStats stats_{};
  std::uint32_t packet_airtime_ms_ = 0;
  CprLoRaBudgetConfig airtime_config_{};
  bool airtime_configured_ = false;
};

}  // namespace meshecho_cpr
