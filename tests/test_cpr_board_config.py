import configparser
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


FIRMWARE = Path(__file__).resolve().parents[1] / "firmware" / "meshecho_cpr"

ARDUINO_STUB = """
#pragma once
#include <cstdint>
constexpr std::uint32_t SCK = 18;
constexpr std::uint32_t MISO = 19;
constexpr std::uint32_t MOSI = 23;
inline std::uint32_t fake_now_ms = 0;
inline std::uint32_t millis() { return fake_now_ms; }
inline void delay(std::uint32_t milliseconds) { fake_now_ms += milliseconds; }
"""

RADIOLIB_STUB = """
#pragma once
#include <cstddef>
#include <cstdint>
constexpr int16_t RADIOLIB_ERR_NONE = 0;
inline std::uint32_t last_module_nss = 0;
inline float last_tcxo_voltage = -1.0F;
inline bool last_ldo = false;
inline bool last_dio2_rf_switch = true;
inline int16_t dio2_result = RADIOLIB_ERR_NONE;
inline unsigned rx_starts = 0;
inline unsigned tx_starts = 0;
inline unsigned tx_finishes = 0;
inline std::uint32_t tx_start_ms = 0;
inline std::uint32_t tx_done_delay_ms = 10;
inline std::uint32_t packet_airtime_us = 2000;
inline bool tx_completes = true;
inline int16_t tx_start_result = RADIOLIB_ERR_NONE;
inline int16_t tx_finish_result = RADIOLIB_ERR_NONE;
inline int16_t rx_start_result = RADIOLIB_ERR_NONE;
inline unsigned packet_reads = 0;
inline std::uint32_t tx_done_mask = 0;
inline void (*packet_callback)() = nullptr;
class Module {
 public:
  Module(std::uint32_t nss, std::uint32_t, std::uint32_t, std::uint32_t) {
    last_module_nss = nss;
  }
};
class StubRadio {
 public:
  explicit StubRadio(Module*) {}
  void setPacketReceivedAction(void (*callback)()) { packet_callback = callback; }
  int16_t startTransmit(const std::uint8_t*, std::size_t) {
    ++tx_starts;
    tx_start_ms = fake_now_ms;
    return tx_start_result;
  }
  std::uint32_t getTimeOnAir(std::size_t) { return packet_airtime_us; }
  std::uint32_t getIrqFlags() {
    if (tx_completes &&
        static_cast<std::uint32_t>(fake_now_ms - tx_start_ms) >= tx_done_delay_ms) {
      if (packet_callback) { packet_callback(); }
      return tx_done_mask;
    }
    return 0x42;  // RX/header flags must not be mistaken for TX_DONE.
  }
  int16_t finishTransmit() { ++tx_finishes; return tx_finish_result; }
  int16_t startReceive() { ++rx_starts; return rx_start_result; }
  std::size_t getPacketLength() { return 1; }
  int16_t readData(std::uint8_t*, std::size_t) { ++packet_reads; return 0; }
  float getRSSI() { return -80.0F; }
  float getSNR() { return 10.0F; }
};
class SX1262 : public StubRadio {
 public:
  explicit SX1262(Module* module) : StubRadio(module) { tx_done_mask = 0x01; }
  int16_t begin(float, float, std::uint8_t, std::uint8_t, std::uint8_t,
                std::int8_t, std::uint16_t, float tcxo, bool ldo) {
    last_tcxo_voltage = tcxo;
    last_ldo = ldo;
    return 0;
  }
  int16_t setDio2AsRfSwitch(bool enabled) {
    last_dio2_rf_switch = enabled;
    return dio2_result;
  }
};
class SX1276 : public StubRadio {
 public:
  explicit SX1276(Module* module) : StubRadio(module) { tx_done_mask = 0x08; }
  int16_t begin(float, float, std::uint8_t, std::uint8_t, std::uint8_t,
                std::int8_t, std::uint16_t, std::uint8_t) { return 0; }
};
constexpr std::uint32_t RADIOLIB_SX126X_IRQ_TX_DONE = 0x01;
constexpr std::uint32_t RADIOLIB_SX127X_CLEAR_IRQ_FLAG_TX_DONE = 0x08;
"""


def compile_adapter(source, defines=(), run=False):
    compiler = shutil.which("c++")
    if compiler is None:
        raise unittest.SkipTest("C++17 compiler is required for adapter checks")
    with tempfile.TemporaryDirectory(prefix="meshecho-radio-test-") as directory:
        temporary = Path(directory)
        (temporary / "Arduino.h").write_text(ARDUINO_STUB)
        (temporary / "RadioLib.h").write_text(RADIOLIB_STUB)
        (temporary / "test.cpp").write_text(source)
        executable = temporary / "test"
        result = subprocess.run(
            [compiler, "-std=c++17", "-DARDUINO_ARCH_ESP32=1",
             *[f"-D{define}" for define in defines],
             "-I", str(temporary), "-I", str(FIRMWARE / "include"),
             str(temporary / "test.cpp"), "-o", str(executable)],
            text=True, capture_output=True, check=False, timeout=30,
        )
        if run and result.returncode == 0:
            return subprocess.run(
                [str(executable)], text=True, capture_output=True, check=False,
                timeout=5,
            )
        return result


def profile_defines(environment):
    config = configparser.ConfigParser(interpolation=None)
    config.read(FIRMWARE / "platformio.ini")
    result = {}
    for flag in shlex.split(config[f"env:{environment}"]["build_flags"]):
        if flag.startswith("-D"):
            name, _, value = flag[2:].partition("=")
            result[name] = value or "1"
    return result


class CprBoardConfigTests(unittest.TestCase):
    def check_both_adapters(self, body):
        for kind, adapter in (("SX1262", "CprSx1262Radio"), ("SX127X", "CprSx127xRadio")):
            with self.subTest(kind=kind):
                source = """
#include <cassert>
#include "meshecho_cpr_radio.hpp"
int main() {
  meshecho_cpr::ADAPTER radio;
  assert(radio.begin(meshecho_cpr::CprRadioConfig::defaults()));
  const std::uint8_t bytes[] = {1, 2, 3};
BODY
}
""".replace("ADAPTER", adapter).replace("BODY", body)
                result = compile_adapter(
                    source, (f"MESHECHO_CPR_RADIO_{kind}=1",), run=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_default_spi_chip_select_is_not_a_bus_signal(self):
        profiles = {
            "esp32dev_sx1262": {18, 19, 23},
            "esp32dev_sx127x": {18, 19, 23},
            "nrf52840_sx1262": {24, 25, 26},
        }
        for environment, spi_pins in profiles.items():
            with self.subTest(environment=environment):
                defines = profile_defines(environment)
                chip_select = int(defines["MESHECHO_CPR_LORA_NSS"])
                self.assertNotIn(chip_select, spi_pins)

    def test_board_build_requires_exactly_one_radio_kind(self):
        source = '#include "meshecho_cpr_radio.hpp"\nint main() {}\n'
        for sx1262, sx127x in ((0, 0), (1, 1), (2, 0), (-1, 0)):
            with self.subTest(sx1262=sx1262, sx127x=sx127x):
                result = compile_adapter(source, (
                    f"MESHECHO_CPR_RADIO_SX1262={sx1262}",
                    f"MESHECHO_CPR_RADIO_SX127X={sx127x}",
                ))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Select exactly one", result.stderr)
        for radio_kind in ("SX1262", "SX127X"):
            result = compile_adapter(source, (f"MESHECHO_CPR_RADIO_{radio_kind}=1",))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_sx1262_applies_module_power_and_rf_switch_options(self):
        result = compile_adapter(
            """
#include <cassert>
#include "meshecho_cpr_radio.hpp"
int main() {
  meshecho_cpr::CprRadioConfig config;
  config.tcxo_voltage = 0.0F;
  config.use_regulator_ldo = true;
  config.dio2_rf_switch = false;
  meshecho_cpr::CprSx1262Radio radio;
  assert(radio.begin(config));
  assert(last_tcxo_voltage == 0.0F);
  assert(last_ldo);
  assert(!last_dio2_rf_switch);
  assert(rx_starts == 1);
  config.tcxo_voltage = 1.8F;
  config.use_regulator_ldo = false;
  config.dio2_rf_switch = true;
  assert(radio.begin(config));
  assert(last_tcxo_voltage == 1.8F);
  assert(!last_ldo);
  assert(last_dio2_rf_switch);
}
""", ("MESHECHO_CPR_RADIO_SX1262=1",), run=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_flags_reach_the_sx1262_driver(self):
        result = compile_adapter(
            """
#include <cassert>
#include "meshecho_cpr_radio.hpp"
int main() {
  constexpr auto config = meshecho_cpr::CprRadioConfig::fromBuildFlags();
  static_assert(config.tcxo_voltage == 0.0F);
  static_assert(config.use_regulator_ldo);
  static_assert(!config.dio2_rf_switch);
  meshecho_cpr::CprSx1262Radio radio;
  assert(radio.begin(config));
  assert(last_tcxo_voltage == 0.0F && last_ldo && !last_dio2_rf_switch);
}
""", (
                "MESHECHO_CPR_RADIO_SX1262=1",
                "MESHECHO_CPR_LORA_TCXO_VOLTAGE=0.0",
                "MESHECHO_CPR_LORA_USE_LDO=1",
                "MESHECHO_CPR_LORA_DIO2_RF_SWITCH=0",
            ), run=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_finish_transmit_waits_for_tx_done_before_radio_cleanup(self):
        for kind, adapter in (("SX1262", "CprSx1262Radio"), ("SX127X", "CprSx127xRadio")):
            with self.subTest(kind=kind):
                result = compile_adapter(
                    f"""
#include <cassert>
#include "meshecho_cpr_radio.hpp"
int main() {{
  meshecho_cpr::{adapter} radio;
  assert(radio.begin(meshecho_cpr::CprRadioConfig::defaults()));
  const std::uint8_t bytes[] = {{1, 2, 3}};
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(fake_now_ms == 0);
  assert(radio.finishTransmit());
  assert(fake_now_ms >= tx_done_delay_ms);
  assert(tx_starts == 1 && tx_finishes == 1);
  assert(rx_starts == 2);
  assert(!radio.packetAvailable());
}}
""", (f"MESHECHO_CPR_RADIO_{kind}=1",), run=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_tx_done_times_out_and_restores_receive_without_replay(self):
        self.check_both_adapters("""
  tx_completes = false;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.finishTransmit());
  assert(fake_now_ms == 15);  // 5 ms + five times the 2 ms packet airtime.
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
  assert(!radio.packetAvailable());
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
""")

    def test_completion_timeout_tracks_packet_airtime_with_upward_rounding(self):
        self.check_both_adapters("""
  tx_completes = false;
  packet_airtime_us = 2001;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.finishTransmit());
  assert(fake_now_ms == 16);
  packet_airtime_us = 20000;
  const auto second_start = fake_now_ms;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.finishTransmit());
  assert(fake_now_ms - second_start == 105);
  assert(tx_starts == 2 && tx_finishes == 2 && rx_starts == 3);
""")

    def test_tx_done_and_timeout_work_across_millis_rollover(self):
        self.check_both_adapters("""
  fake_now_ms = UINT32_MAX - 4;
  tx_done_delay_ms = 10;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(radio.finishTransmit());
  assert(fake_now_ms == 5);
  fake_now_ms = UINT32_MAX - 4;
  tx_completes = false;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.finishTransmit());
  assert(fake_now_ms == 10);
  assert(tx_starts == 2 && tx_finishes == 2 && rx_starts == 3);
""")

    def test_cleanup_failure_still_restores_receive_without_replay(self):
        self.check_both_adapters("""
  tx_finish_result = -7;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.finishTransmit());
  assert(fake_now_ms == tx_done_delay_ms);
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
  assert(!radio.packetAvailable());
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
""")

    def test_failed_physical_start_restores_receive_without_completion_or_replay(self):
        self.check_both_adapters("""
  tx_start_result = -8;
  assert(!radio.transmit(bytes, sizeof(bytes)));
  assert(tx_starts == 1 && tx_finishes == 0 && rx_starts == 2);
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 0 && rx_starts == 2);
  tx_start_result = RADIOLIB_ERR_NONE;
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(radio.finishTransmit());
  assert(tx_starts == 2 && tx_finishes == 1 && rx_starts == 3);
""")

    def test_active_tx_rejects_overlap_and_receive_even_after_an_irq(self):
        self.check_both_adapters("""
  assert(radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.transmit(bytes, sizeof(bytes)));
  assert(!radio.startReceive());
  assert(tx_starts == 1 && rx_starts == 1);
  packet_callback();  // A shared DIO callback during TX is not a received DATA.
  assert(!radio.packetAvailable());
  meshecho_cpr::CprRadioPacket packet;
  assert(!radio.receive(&packet));
  assert(packet_reads == 0 && rx_starts == 1);
  assert(radio.finishTransmit());
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
""")

    def test_receive_restart_failure_reports_failure_without_replaying_tx(self):
        self.check_both_adapters("""
  assert(radio.transmit(bytes, sizeof(bytes)));
  rx_start_result = -9;
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
  assert(!radio.packetAvailable());
  assert(!radio.finishTransmit());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 2);
  rx_start_result = RADIOLIB_ERR_NONE;
  assert(radio.startReceive());
  assert(tx_starts == 1 && tx_finishes == 1 && rx_starts == 3);
""")


if __name__ == "__main__":
    unittest.main()
