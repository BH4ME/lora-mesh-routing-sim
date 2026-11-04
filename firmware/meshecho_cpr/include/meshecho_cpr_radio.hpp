#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

#include "meshecho_cpr_wire.hpp"

#if !defined(MESHECHO_CPR_NATIVE)
#ifndef MESHECHO_CPR_RADIO_SX1262
#define MESHECHO_CPR_RADIO_SX1262 0
#endif
#ifndef MESHECHO_CPR_RADIO_SX127X
#define MESHECHO_CPR_RADIO_SX127X 0
#endif
#if ((MESHECHO_CPR_RADIO_SX1262 != 0) && (MESHECHO_CPR_RADIO_SX1262 != 1)) || \
    ((MESHECHO_CPR_RADIO_SX127X != 0) && (MESHECHO_CPR_RADIO_SX127X != 1)) || \
    ((MESHECHO_CPR_RADIO_SX1262 + MESHECHO_CPR_RADIO_SX127X) != 1)
#error "Select exactly one radio kind: MESHECHO_CPR_RADIO_SX1262=1 or MESHECHO_CPR_RADIO_SX127X=1"
#endif

#include <Arduino.h>
#include <RadioLib.h>

// The legacy nRF5 Arduino core exports min/max as macros. They interfere with
// standard-library headers included by the CPR runtime, so keep the C++ API
// names available after the hardware headers have been parsed.
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

#ifndef MESHECHO_CPR_LORA_NSS
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_NSS 5
#else
// Adafruit Feather nRF52840 default profile. Verify against the SX1262 board
// wiring before powering a physical node; the pin map is compile-time only.
#define MESHECHO_CPR_LORA_NSS 10
#endif
#endif

#ifndef MESHECHO_CPR_LORA_DIO1
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_DIO1 26
#else
#define MESHECHO_CPR_LORA_DIO1 6
#endif
#endif

// SX127x uses separate DIO0 (packet interrupt) and DIO1 pins. These defaults
// are compile-time profiles only; the attached module wiring still determines
// whether a physical node can operate.
#ifndef MESHECHO_CPR_LORA_DIO0
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_DIO0 26
#else
#define MESHECHO_CPR_LORA_DIO0 6
#endif
#endif

#ifndef MESHECHO_CPR_LORA_SX127X_DIO1
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_SX127X_DIO1 27
#else
#define MESHECHO_CPR_LORA_SX127X_DIO1 9
#endif
#endif

#ifndef MESHECHO_CPR_LORA_RST
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_RST 14
#else
#define MESHECHO_CPR_LORA_RST 5
#endif
#endif

#ifndef MESHECHO_CPR_LORA_BUSY
#if defined(ARDUINO_ARCH_ESP32)
#define MESHECHO_CPR_LORA_BUSY 27
#else
#define MESHECHO_CPR_LORA_BUSY 9
#endif
#endif

#ifndef MESHECHO_CPR_LORA_GAIN
#define MESHECHO_CPR_LORA_GAIN 0
#endif
#endif

#ifndef MESHECHO_CPR_LORA_FREQ_MHZ
#define MESHECHO_CPR_LORA_FREQ_MHZ 915.0F
#endif
#ifndef MESHECHO_CPR_LORA_BW_KHZ
#define MESHECHO_CPR_LORA_BW_KHZ 125.0F
#endif
#ifndef MESHECHO_CPR_LORA_SF
#define MESHECHO_CPR_LORA_SF 9
#endif
#ifndef MESHECHO_CPR_LORA_CR
#define MESHECHO_CPR_LORA_CR 7
#endif
#ifndef MESHECHO_CPR_LORA_POWER_DBM
#define MESHECHO_CPR_LORA_POWER_DBM 17
#endif
#ifndef MESHECHO_CPR_LORA_TCXO_VOLTAGE
#define MESHECHO_CPR_LORA_TCXO_VOLTAGE 1.6F
#endif
#ifndef MESHECHO_CPR_LORA_USE_LDO
#define MESHECHO_CPR_LORA_USE_LDO 0
#endif
#ifndef MESHECHO_CPR_LORA_DIO2_RF_SWITCH
#define MESHECHO_CPR_LORA_DIO2_RF_SWITCH 1
#endif

namespace meshecho_cpr {

// Radio parameters are kept independent from the CPR state machine so that a
// test double and a board-specific driver use the same public contract.
struct CprRadioConfig {
  float frequency_mhz = 915.0F;
  float bandwidth_khz = 125.0F;
  std::uint8_t spreading_factor = 9;
  std::uint8_t coding_rate = 7;
  std::uint8_t sync_word = 0x12;
  std::int8_t tx_power_dbm = 17;
  std::uint16_t preamble_length = 8;
  float tcxo_voltage = 1.6F;
  bool use_regulator_ldo = false;
  bool dio2_rf_switch = true;

  static constexpr CprRadioConfig defaults() { return CprRadioConfig{}; }
  static constexpr CprRadioConfig fromBuildFlags() {
    return CprRadioConfig{
        MESHECHO_CPR_LORA_FREQ_MHZ,
        MESHECHO_CPR_LORA_BW_KHZ,
        static_cast<std::uint8_t>(MESHECHO_CPR_LORA_SF),
        static_cast<std::uint8_t>(MESHECHO_CPR_LORA_CR),
        0x12,
        static_cast<std::int8_t>(MESHECHO_CPR_LORA_POWER_DBM),
        8,
        MESHECHO_CPR_LORA_TCXO_VOLTAGE,
        MESHECHO_CPR_LORA_USE_LDO != 0,
        MESHECHO_CPR_LORA_DIO2_RF_SWITCH != 0,
    };
  }
};

struct CprRadioPacket {
  std::array<std::uint8_t, kCprMaxFrameSize> bytes{};
  std::size_t size = 0;
  std::int16_t rssi_dbm = 0;
  float snr_db = 0.0F;
};

class CprRadioPort {
 public:
  virtual ~CprRadioPort() = default;

  virtual bool begin(const CprRadioConfig& config) = 0;
  // Starts physical TX. A successful return is the CPR physical-start
  // boundary; the caller must commit the CPR marker immediately, then invoke
  // finishTransmit() to wait for completion and return the radio to RX.
  virtual bool transmit(const std::uint8_t* bytes, std::size_t length) = 0;
  // Synchronous/fake radios can use the default; RadioLib implementations
  // wait for asynchronous TX completion and return to RX mode here.
  virtual bool finishTransmit() { return true; }
  virtual bool startReceive() = 0;
  virtual bool packetAvailable() const = 0;
  virtual bool receive(CprRadioPacket* out) = 0;
};

#if defined(MESHECHO_CPR_NATIVE)

// Native builds intentionally avoid a hardware dependency. Tests can provide
// a small fake implementing CprRadioPort, while this symbol keeps shared
// application code board-neutral.
class CprSx1262Radio final : public CprRadioPort {
 public:
  bool begin(const CprRadioConfig&) override { return false; }
  bool transmit(const std::uint8_t*, std::size_t) override { return false; }
  bool finishTransmit() override { return false; }
  bool startReceive() override { return false; }
  bool packetAvailable() const override { return false; }
  bool receive(CprRadioPacket*) override { return false; }
};

class CprSx127xRadio final : public CprRadioPort {
 public:
  bool begin(const CprRadioConfig&) override { return false; }
  bool transmit(const std::uint8_t*, std::size_t) override { return false; }
  bool finishTransmit() override { return false; }
  bool startReceive() override { return false; }
  bool packetAvailable() const override { return false; }
  bool receive(CprRadioPacket*) override { return false; }
};

#else

namespace detail {

inline std::uint32_t cprTxTimeoutMs(std::uint32_t airtime_us) {
  return 5U + static_cast<std::uint32_t>(
                  (5ULL * airtime_us + 999ULL) / 1000ULL);
}

template <typename Radio>
bool cprWaitForTxDone(Radio& radio, std::uint32_t tx_done_mask,
                     std::uint32_t started_ms, std::uint32_t timeout_ms) {
  while ((radio.getIrqFlags() & tx_done_mask) == 0) {
    if (static_cast<std::uint32_t>(millis() - started_ms) >= timeout_ms) {
      return false;
    }
    delay(1);
  }
  return true;
}

}  // namespace detail

class CprSx1262Radio final : public CprRadioPort {
 public:
  CprSx1262Radio(std::uint32_t nss = MESHECHO_CPR_LORA_NSS,
                 std::uint32_t dio1 = MESHECHO_CPR_LORA_DIO1,
                 std::uint32_t rst = MESHECHO_CPR_LORA_RST,
                 std::uint32_t busy = MESHECHO_CPR_LORA_BUSY)
      : module_(nss, dio1, rst, busy), radio_(&module_) {}

  bool begin(const CprRadioConfig& config) override {
    const int16_t state = radio_.begin(config.frequency_mhz, config.bandwidth_khz,
                                       config.spreading_factor, config.coding_rate,
                                       config.sync_word, config.tx_power_dbm,
                                       config.preamble_length, config.tcxo_voltage,
                                       config.use_regulator_ldo);
    if (state != RADIOLIB_ERR_NONE) {
      return false;
    }
    if (radio_.setDio2AsRfSwitch(config.dio2_rf_switch) != RADIOLIB_ERR_NONE) {
      return false;
    }
    active_instance_ = this;
    packet_received_ = false;
    radio_.setPacketReceivedAction(onPacketReceived);
    return startReceive();
  }

  bool transmit(const std::uint8_t* bytes, std::size_t length) override {
    if (tx_in_progress_ || bytes == nullptr || length == 0 || length > kCprMaxFrameSize) {
      return false;
    }
    tx_timeout_ms_ = detail::cprTxTimeoutMs(radio_.getTimeOnAir(length));
    packet_received_ = false;
    if (radio_.startTransmit(bytes, length) != RADIOLIB_ERR_NONE) {
      (void)startReceive();
      return false;
    }
    tx_started_ms_ = millis();
    tx_in_progress_ = true;
    return true;
  }

  bool finishTransmit() override {
    if (!tx_in_progress_) {
      return false;
    }
    // RadioLib finishTransmit() only cleans up; it does not wait for TX_DONE.
    const bool completed = detail::cprWaitForTxDone(
        radio_, RADIOLIB_SX126X_IRQ_TX_DONE, tx_started_ms_, tx_timeout_ms_);
    const int16_t state = radio_.finishTransmit();
    tx_in_progress_ = false;
    packet_received_ = false;
    const bool receiving = startReceive();
    return completed && state == RADIOLIB_ERR_NONE && receiving;
  }

  bool startReceive() override {
    return !tx_in_progress_ && radio_.startReceive() == RADIOLIB_ERR_NONE;
  }

  bool packetAvailable() const override { return !tx_in_progress_ && packet_received_; }

  bool receive(CprRadioPacket* out) override {
    if (tx_in_progress_ || out == nullptr || !packet_received_) {
      return false;
    }
    const std::size_t packet_length = radio_.getPacketLength();
    if (packet_length == 0 || packet_length > out->bytes.size()) {
      packet_received_ = false;
      (void)startReceive();
      return false;
    }
    const int16_t state = radio_.readData(out->bytes.data(), packet_length);
    if (state != RADIOLIB_ERR_NONE) {
      packet_received_ = false;
      (void)startReceive();
      return false;
    }
    out->size = packet_length;
    out->rssi_dbm = static_cast<std::int16_t>(radio_.getRSSI());
    out->snr_db = radio_.getSNR();
    packet_received_ = false;
    (void)startReceive();
    return true;
  }

 private:
  static void onPacketReceived() {
    if (active_instance_ != nullptr) {
      active_instance_->packet_received_ = true;
    }
  }

  Module module_;
  SX1262 radio_;
  std::uint32_t tx_started_ms_ = 0;
  std::uint32_t tx_timeout_ms_ = 0;
  bool tx_in_progress_ = false;
  volatile bool packet_received_ = false;
  inline static CprSx1262Radio* active_instance_ = nullptr;
};

// RadioLib keeps SX127x and SX126x behind different concrete classes and
// initialization signatures. This adapter intentionally exposes the same
// byte-oriented CPR port so the runtime remains radio-family agnostic.
class CprSx127xRadio final : public CprRadioPort {
 public:
  CprSx127xRadio(std::uint32_t nss = MESHECHO_CPR_LORA_NSS,
                 std::uint32_t dio0 = MESHECHO_CPR_LORA_DIO0,
                 std::uint32_t rst = MESHECHO_CPR_LORA_RST,
                 std::uint32_t dio1 = MESHECHO_CPR_LORA_SX127X_DIO1)
      : module_(nss, dio0, rst, dio1), radio_(&module_) {}

  bool begin(const CprRadioConfig& config) override {
    const int16_t state = radio_.begin(config.frequency_mhz, config.bandwidth_khz,
                                       config.spreading_factor, config.coding_rate,
                                       config.sync_word, config.tx_power_dbm,
                                       config.preamble_length,
                                       MESHECHO_CPR_LORA_GAIN);
    if (state != RADIOLIB_ERR_NONE) {
      return false;
    }
    active_instance_ = this;
    packet_received_ = false;
    radio_.setPacketReceivedAction(onPacketReceived);
    return startReceive();
  }

  bool transmit(const std::uint8_t* bytes, std::size_t length) override {
    if (tx_in_progress_ || bytes == nullptr || length == 0 || length > kCprMaxFrameSize) {
      return false;
    }
    tx_timeout_ms_ = detail::cprTxTimeoutMs(radio_.getTimeOnAir(length));
    packet_received_ = false;
    if (radio_.startTransmit(bytes, length) != RADIOLIB_ERR_NONE) {
      (void)startReceive();
      return false;
    }
    tx_started_ms_ = millis();
    tx_in_progress_ = true;
    return true;
  }

  bool finishTransmit() override {
    if (!tx_in_progress_) {
      return false;
    }
    const bool completed = detail::cprWaitForTxDone(
        radio_, RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE, tx_started_ms_, tx_timeout_ms_);
    const int16_t state = radio_.finishTransmit();
    tx_in_progress_ = false;
    packet_received_ = false;
    const bool receiving = startReceive();
    return completed && state == RADIOLIB_ERR_NONE && receiving;
  }

  bool startReceive() override {
    return !tx_in_progress_ && radio_.startReceive() == RADIOLIB_ERR_NONE;
  }

  bool packetAvailable() const override { return !tx_in_progress_ && packet_received_; }

  bool receive(CprRadioPacket* out) override {
    if (tx_in_progress_ || out == nullptr || !packet_received_) {
      return false;
    }
    const std::size_t packet_length = radio_.getPacketLength();
    if (packet_length == 0 || packet_length > out->bytes.size()) {
      packet_received_ = false;
      (void)startReceive();
      return false;
    }
    const int16_t state = radio_.readData(out->bytes.data(), packet_length);
    if (state != RADIOLIB_ERR_NONE) {
      packet_received_ = false;
      (void)startReceive();
      return false;
    }
    out->size = packet_length;
    out->rssi_dbm = static_cast<std::int16_t>(radio_.getRSSI());
    out->snr_db = radio_.getSNR();
    packet_received_ = false;
    (void)startReceive();
    return true;
  }

 private:
  static void onPacketReceived() {
    if (active_instance_ != nullptr) {
      active_instance_->packet_received_ = true;
    }
  }

  Module module_;
  SX1276 radio_;
  std::uint32_t tx_started_ms_ = 0;
  std::uint32_t tx_timeout_ms_ = 0;
  bool tx_in_progress_ = false;
  volatile bool packet_received_ = false;
  inline static CprSx127xRadio* active_instance_ = nullptr;
};

#endif

}  // namespace meshecho_cpr
