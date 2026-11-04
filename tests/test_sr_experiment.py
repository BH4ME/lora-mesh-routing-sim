import csv
import hashlib
import json
import subprocess
import sys
import unittest
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional
from unittest.mock import patch

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, Transmission, build_protocol
from tools import run_sr_experiment as sr_experiment
from tools.run_sr_experiment import (
    BAR_PROTOCOLS,
    CLAR_PROTOCOLS,
    DHR_PROTOCOLS,
    DPA_PROTOCOLS,
    LPR_PROTOCOLS,
    MAG_PROTOCOLS,
    RAC_PROTOCOLS,
    RecordingSimulator,
    SR_CASES,
    SrExperiment,
    SrRun,
    main,
    SR_PROTOCOLS,
    SrCase,
    confirmatory_comparison_eligible,
    observed_tx_airtime,
    summarize_windowed_transmissions,
    paired_ci95,
    parse_args,
    run_matrix,
    run_one_sr,
    seeds_for_split,
    summarize_paired,
    source_hashes,
    validate_bar_development_manifest,
    validate_dpa_development_manifest,
    validate_rac_development_manifest,
    validate_clar_development_manifest,
    validate_dhr_development_manifest,
    write_artifacts,
)


class SrExperimentTest(unittest.TestCase):
    def synthetic_bar_development_manifest(
        self, directory: str, exposed_seeds: int = 10,
    ) -> Path:
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        flows = []
        actions = []
        for seed_index, seed in enumerate(seeds_for_split("bar-development")):
            trace = [(flow_id * 0.1, 0, 3, flow_id) for flow_id in range(1, 5)]
            trace_hash = hashlib.sha256(json.dumps(
                trace, separators=(",", ":")
            ).encode("ascii")).hexdigest()
            for protocol in BAR_PROTOCOLS:
                acked_count = 4 if protocol == BAR_PROTOCOLS[0] else 3
                for flow_id in range(1, 5):
                    enqueued_at = flow_id * 0.1
                    acked = flow_id <= acked_count
                    flows.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "bar-development", "flow_id": flow_id,
                        "src": 0, "dst": 3, "source_action": "F",
                        "first_data_delivery_kind": "F", "registered": True,
                        "bar_extra_ack_tx_count": (
                            1 if protocol == BAR_PROTOCOLS[0]
                            and seed_index < exposed_seeds and flow_id <= 2 else 0
                        ),
                        "enqueued_at": enqueued_at,
                        "deadline_at": enqueued_at + 30.0,
                        "delivered_at": enqueued_at + 1.0,
                        "acked_at": enqueued_at + 2.0 if acked else None,
                        "delivery_by_deadline": True,
                        "ack_by_deadline": acked,
                        "late_delivery": False, "late_ack": False,
                        "completion_delay_capped_s": 2.0 if acked else 30.0,
                    })
                rows.append({
                    "case": case.key, "case_config_sha256": case_hash,
                    "protocol": protocol, "seed": seed,
                    "seed_split": "bar-development",
                    "generation_horizon_s": 600.0, "drain_until_s": 630.0,
                    "scheduled_trace_sha256": trace_hash,
                    "scheduled_unicast_flows": 4,
                    "registered_unicast_flows": 4,
                    "application_deadline_s": 30.0,
                    "ack_by_deadline": acked_count,
                    "delivery_by_deadline": 4,
                    "late_ack_count": 0, "late_delivery_count": 0,
                    "ack_pdr_deadline": acked_count / 4,
                    "destination_pdr_deadline": 1.0,
                    "mean_completion_delay_capped_s": (
                        2.0 if protocol == BAR_PROTOCOLS[0] else 9.0
                    ),
                    "bar_first_flood_receipts": (
                        2 if protocol == BAR_PROTOCOLS[0]
                        and seed_index < exposed_seeds else 0
                    ),
                    "bar_candidate_events": (
                        2 if protocol == BAR_PROTOCOLS[0]
                        and seed_index < exposed_seeds else 0
                    ),
                    "windowed_destination_ack_attempts": (
                        6 if protocol == BAR_PROTOCOLS[0]
                        and seed_index < exposed_seeds else 4
                    ),
                    "windowed_ack_tx": (
                        6 if protocol == BAR_PROTOCOLS[0]
                        and seed_index < exposed_seeds else 4
                    ),
                    "whole_network_tx_airtime_s": (
                        1.03 if protocol == BAR_PROTOCOLS[0] else 1.0
                    ),
                    "bar_extra_ack_tx_events": (
                        2 if protocol == BAR_PROTOCOLS[0]
                        and seed_index < exposed_seeds else 0
                    ),
                })
                if protocol == BAR_PROTOCOLS[0] and seed_index < exposed_seeds:
                    for flow_id in (1, 2):
                        first_at = flow_id * 0.1 + 1.0
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "bar-development", "flow_id": flow_id,
                            "event": "bar_first_flood_rx", "time": first_at,
                            "src": 0, "dst": 3, "path": [0, 1, 3],
                            "repair_index": None, "tracked": True,
                        })
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "bar-development", "flow_id": flow_id,
                            "event": "bar_candidate", "time": first_at + 0.05,
                            "src": 0, "dst": 3, "first_path": [0, 1, 3],
                            "alternate_path": [0, 2, 3],
                            "reply_path": [0, 2, 3],
                            "repair_index": None, "mode": "alternate",
                        })
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "bar-development", "flow_id": flow_id,
                            "event": "bar_extra_ack_tx", "time": first_at + 0.1,
                            "path": [0, 2, 3], "mode": "alternate",
                        })
        comparisons = summarize_paired(rows, BAR_PROTOCOLS[0], BAR_PROTOCOLS[1:])
        for comparison in comparisons:
            comparison["seed_split"] = "bar-development"
        bundle = SrExperiment(
            case, BAR_PROTOCOLS, seeds_for_split("bar-development"), 30.0,
            rows, flows, actions, comparisons, "bar-development", source_hashes("bar"),
        )
        return write_artifacts(Path(directory) / "synthetic-bar-dev", bundle)["manifest"]

    def synthetic_lpr_development_manifest(
        self, directory: str, trigger_f_ack: float = 0.7,
        repair_decisions_per_seed: int = 2,
        inserted_repairs_per_seed: int = 1,
    ) -> Path:
        prefix = Path(directory) / "synthetic-lpr-dev"
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        for seed in seeds_for_split("lpr-development"):
            for protocol in LPR_PROTOCOLS:
                ack_pdr = (
                    0.9 if protocol == "meshecho-lpr" else
                    trigger_f_ack if protocol == "meshecho-lpr-trigger-f" else 0.7
                )
                rows.append({
                    "case": case.key,
                    "case_config_sha256": case_hash,
                    "protocol": protocol,
                    "seed": seed,
                    "seed_split": "lpr-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": ack_pdr,
                    "whole_network_tx_airtime_s": 1.0,
                    "repair_decisions": (
                        repair_decisions_per_seed if protocol == "meshecho-lpr" else 0
                    ),
                    "ack_confirmed_inserted_repairs": (
                        inserted_repairs_per_seed if protocol == "meshecho-lpr" else 0
                    ),
                })
        paths = {
            "runs": Path(f"{prefix}.runs.csv"),
            "paired": Path(f"{prefix}.paired.csv"),
            "flows": Path(f"{prefix}.flows.jsonl"),
            "actions": Path(f"{prefix}.actions.jsonl"),
        }
        with paths["runs"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        comparisons = summarize_paired(rows, LPR_PROTOCOLS[0], LPR_PROTOCOLS[1:])
        with paths["paired"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
            writer.writeheader()
            writer.writerows(comparisons)
        paths["flows"].write_text("", encoding="utf-8")
        paths["actions"].write_text("", encoding="utf-8")
        manifest = {
            "case": asdict(case),
            "protocols": list(LPR_PROTOCOLS),
            "seeds": list(seeds_for_split("lpr-development")),
            "seed_split": "lpr-development",
            "application_deadline_s": 30.0,
            "source_sha256": source_hashes(),
            "artifact_sha256": {
                key: hashlib.sha256(path.read_bytes()).hexdigest()
                for key, path in paths.items()
            },
            "runs": len(rows),
        }
        manifest_path = Path(f"{prefix}.manifest.json")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def synthetic_dpa_development_manifest(
        self, directory: str, repeat_ack: float = 0.7,
        opportunity_seed_count: int = 10, opportunities_per_seed: int = 2,
    ) -> Path:
        prefix = Path(directory) / "synthetic-dpa-dev"
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        flows = []
        actions = []
        for seed_index, seed in enumerate(seeds_for_split("dpa-development")):
            opportunities = opportunities_per_seed if seed_index < opportunity_seed_count else 0
            for protocol in DPA_PROTOCOLS:
                ack_pdr = (
                    0.9 if protocol == "meshecho-dpa" else
                    repeat_ack if protocol == "meshecho-dpa-repeat" else 0.7
                )
                rows.append({
                    "case": case.key,
                    "case_config_sha256": case_hash,
                    "protocol": protocol,
                    "seed": seed,
                    "seed_split": "dpa-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "ack_by_deadline": int(40 * ack_pdr),
                    "delivery_by_deadline": int(40 * ack_pdr),
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": ack_pdr,
                    "whole_network_tx_airtime_s": 1.0,
                    "dpa_second_path_opportunities": (
                        opportunities if protocol != "meshecho-dpa-fr" else 0
                    ),
                })
                for flow_id in range(1, 41):
                    flows.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "dpa-development", "flow_id": flow_id,
                        "ack_by_deadline": flow_id <= int(40 * ack_pdr),
                        "delivery_by_deadline": flow_id <= int(40 * ack_pdr),
                    })
                if protocol != "meshecho-dpa-fr":
                    for flow_id in range(1, opportunities + 1):
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "dpa-development", "flow_id": flow_id,
                            "event": "dpa_second_path", "action": "F",
                            "time": float(flow_id), "src": 0, "dst": 3,
                            "first_path": [0, 1, 3], "second_path": [0, 2, 3],
                        })
        paths = {
            "runs": Path(f"{prefix}.runs.csv"),
            "paired": Path(f"{prefix}.paired.csv"),
            "flows": Path(f"{prefix}.flows.jsonl"),
            "actions": Path(f"{prefix}.actions.jsonl"),
        }
        with paths["runs"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        comparisons = summarize_paired(rows, DPA_PROTOCOLS[0], DPA_PROTOCOLS[1:])
        with paths["paired"].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
            writer.writeheader()
            writer.writerows(comparisons)
        for key, records in (("flows", flows), ("actions", actions)):
            with paths[key].open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
        manifest = {
            "case": asdict(case),
            "protocols": list(DPA_PROTOCOLS),
            "seeds": list(seeds_for_split("dpa-development")),
            "seed_split": "dpa-development",
            "application_deadline_s": 30.0,
            "dpa_joint_primary_gate": bool(comparisons[0]["dpa_joint_primary_gate"]),
            "source_sha256": source_hashes("dpa"),
            "artifact_sha256": {
                key: hashlib.sha256(path.read_bytes()).hexdigest()
                for key, path in paths.items()
            },
            "runs": len(rows),
        }
        manifest_path = Path(f"{prefix}.manifest.json")
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def synthetic_rac_development_manifest(
        self, directory: str, repeat_ack: float = 0.7,
        exposure_seed_count: int = 10, events_per_seed: int = 2,
    ) -> Path:
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        flows = []
        actions = []
        for seed_index, seed in enumerate(seeds_for_split("rac-development")):
            exposure = events_per_seed if seed_index < exposure_seed_count else 0
            for protocol in RAC_PROTOCOLS:
                ack_pdr = (
                    0.9 if protocol == "meshecho-rac" else
                    repeat_ack if protocol == "meshecho-rac-repeat" else 0.7
                )
                acked = int(40 * ack_pdr)
                rows.append({
                    "case": case.key,
                    "case_config_sha256": case_hash,
                    "protocol": protocol,
                    "seed": seed,
                    "seed_split": "rac-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "ack_by_deadline": acked,
                    "delivery_by_deadline": acked,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": ack_pdr,
                    "whole_network_tx_airtime_s": 1.0,
                    "rac_corridor_eligible": exposure if protocol == "meshecho-rac" else 0,
                })
                for flow_id in range(1, 41):
                    flows.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "rac-development", "flow_id": flow_id,
                        "src": 0, "dst": 3, "source_action": "F",
                        "enqueued_at": 0.0, "deadline_at": 30.0,
                        "ack_by_deadline": flow_id <= acked,
                        "delivery_by_deadline": flow_id <= acked,
                    })
                if protocol == "meshecho-rac":
                    for flow_id in range(1, exposure + 1):
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "rac-development", "flow_id": flow_id,
                            "event": "rac_corridor_eligible", "action": "F",
                            "time": float(flow_id), "src": 0, "dst": 3,
                            "candidate": 2, "next_hop": 1, "path": [0, 1, 3],
                        })
        comparisons = summarize_paired(rows, RAC_PROTOCOLS[0], RAC_PROTOCOLS[1:])
        for comparison in comparisons:
            comparison["seed_split"] = "rac-development"
        bundle = SrExperiment(
            case, RAC_PROTOCOLS, seeds_for_split("rac-development"), 30.0,
            rows, flows, actions, comparisons, "rac-development", source_hashes("rac"),
        )
        return write_artifacts(Path(directory) / "synthetic-rac-dev", bundle)["manifest"]

    def synthetic_clar_development_manifest(
        self, directory: str, repeat_acked: int = 2,
        exposure_seed_count: int = 20, exposures_per_seed: int = 2,
    ) -> Path:
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        flows = []
        actions = []
        for seed_index, seed in enumerate(seeds_for_split("clar-development")):
            for protocol in CLAR_PROTOCOLS:
                acked = (repeat_acked if protocol in {
                    "meshecho-clar-repeat", "meshecho-clar-fr"
                } else 4)
                exposure = (
                    exposures_per_seed if seed_index < exposure_seed_count
                    and protocol in {"meshecho-clar", "meshecho-clar-nocancel"}
                    else 0
                )
                done = acked if protocol != "meshecho-clar-fr" else 0
                cancelled = exposure if protocol == "meshecho-clar" else 0
                repaired = exposure if protocol == "meshecho-clar-nocancel" else 0
                ack_tx = 2 * acked + repaired
                rows.append({
                    "case": case.key, "case_config_sha256": case_hash,
                    "protocol": protocol, "seed": seed,
                    "seed_split": "clar-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 4,
                    "generation_horizon_s": 600.0, "application_deadline_s": 30.0,
                    "drain_until_s": 630.0,
                    "ack_by_deadline": acked, "delivery_by_deadline": 4,
                    "ack_pdr_deadline": acked / 4,
                    "destination_pdr_deadline": 1.0,
                    "whole_network_tx_airtime_s": (
                        1.1 if protocol == "meshecho-clar-nocancel" else 1.0
                    ),
                    "windowed_ack_tx": ack_tx,
                    "windowed_ack_bytes": 19 * ack_tx,
                    "windowed_done_tx": done,
                    "windowed_done_bytes": 10 * done,
                    "windowed_control_tx": ack_tx + done,
                    "windowed_control_bytes": 19 * ack_tx + 10 * done,
                    "clar_candidate_eligible": exposure,
                    "clar_cancellations": cancelled,
                    "clar_done_cancellations": cancelled,
                    "clar_continuation_cancellations": 0,
                    "clar_done_tx_events": done,
                    "clar_done_rx_events": exposure,
                    "clar_repair_tx_events": repaired,
                    "clar_repeat_tx_events": 0,
                    "clar_source_ack_accepted": acked,
                })
                for flow_id in range(1, 5):
                    flows.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "clar-development", "flow_id": flow_id,
                        "src": 0, "dst": 3, "source_action": "F",
                        "enqueued_at": 0.0, "deadline_at": 30.0,
                        "ack_by_deadline": flow_id <= acked,
                        "delivery_by_deadline": True,
                        "acked_at": 2.05 + flow_id * .01 if flow_id <= acked else None,
                        "delivered_at": 1.0,
                        "f_ack_repair_index": 255 if flow_id <= acked else None,
                        "f_ack_stage": (
                            "initial" if flow_id <= acked else "destination_only"
                        ),
                    })
                    if flow_id <= acked:
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "clar-development", "flow_id": flow_id,
                            "event": "clar_source_ack_rx", "time": 2.05 + flow_id * .01,
                            "src": 0, "dst": 3, "action": "F",
                            "accepted": True, "repair_index": 255,
                        })
                        if done:
                            actions.append({
                                "case": case.key, "protocol": protocol, "seed": seed,
                                "seed_split": "clar-development", "flow_id": flow_id,
                                "event": "clar_done_tx", "time": 2.06 + flow_id * .01,
                                "src": 0, "dst": 3, "action": "F",
                            })
                for flow_id in range(1, exposure + 1):
                    actions.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "clar-development", "flow_id": flow_id,
                        "event": "clar_candidate_eligible", "action": "F",
                        "time": 2.0 + flow_id * .01, "src": 0, "dst": 3,
                        "candidate": 2, "next_hop": 0, "path": [0, 1, 3],
                    })
                    actions.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "clar-development", "flow_id": flow_id,
                        "event": "clar_done_rx", "time": 2.10 + flow_id * .01,
                        "src": 0, "dst": 3, "receiver": 2,
                    })
                    if cancelled:
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "clar-development", "flow_id": flow_id,
                            "event": "clar_cancel", "time": 2.11 + flow_id * .01,
                            "src": 0, "dst": 3, "receiver": 2,
                            "reason": "source-done",
                        })
                    if repaired:
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "clar-development", "flow_id": flow_id,
                            "event": "clar_repair_tx", "time": 2.5 + flow_id * .01,
                            "src": 0, "dst": 3, "sender": 2,
                            "path": [0, 1, 3],
                        })
        comparisons = summarize_paired(rows, CLAR_PROTOCOLS[0], CLAR_PROTOCOLS[1:])
        for item in comparisons:
            item["seed_split"] = "clar-development"
        bundle = SrExperiment(
            case, CLAR_PROTOCOLS, seeds_for_split("clar-development"), 30.0,
            rows, flows, actions, comparisons, "clar-development", source_hashes("clar"),
        )
        return write_artifacts(Path(directory) / "synthetic-clar-dev", bundle)["manifest"]

    def synthetic_dhr_development_manifest(
        self, directory: str, recovery_seed_count: int = 10,
        repeat_ack_count: int = 3, repeat_guard_action: Optional[str] = None,
    ) -> Path:
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        flows = []
        actions = []
        ack_counts = {
            "meshecho-dhr": 4,
            "meshecho-dhr-none": 2,
            "meshecho-dhr-repeat": repeat_ack_count,
            "meshecho-dhr-flood": 4,
        }
        for seed_index, seed in enumerate(seeds_for_split("dhr-development")):
            for protocol in DHR_PROTOCOLS:
                acked_count = ack_counts[protocol]
                active_recovery = (
                    protocol == "meshecho-dhr"
                    and seed_index < recovery_seed_count
                )
                control_guard = (
                    protocol == "meshecho-dhr-repeat"
                    and repeat_guard_action is not None
                )
                run_flows = []
                for flow_id in range(1, 5):
                    enqueued_at = float(flow_id) / 10
                    marker = (
                        flow_id if active_recovery and flow_id in {1, 2}
                        else None
                    )
                    acked = flow_id <= acked_count
                    acked_at = (20.0 + enqueued_at if marker is not None
                                else 2.0 + enqueued_at) if acked else None
                    flow = {
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "dhr-development", "flow_id": flow_id,
                        "src": 0, "dst": 3, "source_action": "R",
                        "enqueued_at": enqueued_at,
                        "deadline_at": enqueued_at + 30.0,
                        "acked_at": acked_at,
                        "delivered_at": 1.0 + enqueued_at if acked else None,
                        "ack_by_deadline": acked,
                        "delivery_by_deadline": acked,
                        "completion_delay_capped_s": (
                            acked_at - enqueued_at if acked else 30.0
                        ),
                    }
                    flows.append(flow)
                    run_flows.append(flow)
                    if acked:
                        actions.append({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "dhr-development", "flow_id": flow_id,
                            "event": "dhr_source_ack_rx", "time": acked_at,
                            "src": 0, "dst": 3, "accepted": True,
                            "repair_index": marker,
                        })
                    if active_recovery and marker is not None:
                        action = "R" if marker == 1 else "F"
                        actions.extend(({
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "dhr-development", "flow_id": flow_id,
                            "event": "dhr_guard", "time": 15.0 + enqueued_at,
                            "src": 0, "dst": 3, "admitted": True,
                            "reason": "admitted", "selected_action": action,
                        }, {
                            "case": case.key, "protocol": protocol, "seed": seed,
                            "seed_split": "dhr-development", "flow_id": flow_id,
                            "event": "dhr_recovery_tx", "time": 16.0 + enqueued_at,
                            "end": 16.1 + enqueued_at, "src": 0, "dst": 3,
                            "action": action, "repair_index": marker,
                        }))
                if control_guard:
                    actions.append({
                        "case": case.key, "protocol": protocol, "seed": seed,
                        "seed_split": "dhr-development", "flow_id": 4,
                        "event": "dhr_guard", "time": 15.4,
                        "src": 0, "dst": 3, "admitted": True,
                        "reason": "admitted", "selected_action": repeat_guard_action,
                    })
                rows.append({
                    "case": case.key, "case_config_sha256": case_hash,
                    "protocol": protocol, "seed": seed,
                    "seed_split": "dhr-development",
                    "generation_horizon_s": 600.0,
                    "drain_until_s": 630.0,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 4,
                    "application_deadline_s": 30.0,
                    "ack_by_deadline": acked_count,
                    "delivery_by_deadline": acked_count,
                    "ack_pdr_deadline": acked_count / 4,
                    "destination_pdr_deadline": acked_count / 4,
                    "whole_network_tx_airtime_s": (
                        0.9 if protocol == "meshecho-dhr" else 1.0
                    ),
                    "mean_completion_delay_capped_s": sum(
                        flow["completion_delay_capped_s"] for flow in run_flows
                    ) / 4,
                    "dhr_guard_events": 2 if active_recovery else int(control_guard),
                    "dhr_admitted_guards": 2 if active_recovery else int(control_guard),
                    "dhr_rejected_guards": 0,
                    "dhr_selected_r": (
                        int(active_recovery)
                        + int(control_guard and repeat_guard_action == "R")
                    ),
                    "dhr_selected_f": (
                        int(active_recovery)
                        + int(control_guard and repeat_guard_action == "F")
                    ),
                    "dhr_selected_none": 0,
                    "dhr_recovery_r_tx": 1 if active_recovery else 0,
                    "dhr_recovery_f_tx": 1 if active_recovery else 0,
                    "windowed_dhr_recovery_r_source_tx": 1 if active_recovery else 0,
                    "windowed_dhr_recovery_f_source_tx": 1 if active_recovery else 0,
                    "dhr_source_ack_accepted": acked_count,
                    "dhr_source_ack_accepted_initial": (
                        acked_count - 2 if active_recovery else acked_count
                    ),
                    "dhr_source_ack_accepted_r": 1 if active_recovery else 0,
                    "dhr_source_ack_accepted_f": 1 if active_recovery else 0,
                    "dhr_duplicate_destination_receptions": 0,
                })
        comparisons = summarize_paired(rows, DHR_PROTOCOLS[0], DHR_PROTOCOLS[1:])
        for comparison in comparisons:
            comparison["seed_split"] = "dhr-development"
        bundle = SrExperiment(
            case, DHR_PROTOCOLS, seeds_for_split("dhr-development"), 30.0,
            rows, flows, actions, comparisons, "dhr-development", source_hashes("dhr"),
        )
        return write_artifacts(Path(directory) / "synthetic-dhr-dev", bundle)["manifest"]

    def tiny_case(self) -> SrCase:
        return SrCase(
            key="tiny_random",
            nodes=2,
            area_m=1.0,
            duration_s=8.0,
            rate_per_min=60.0,
            pair_mode="random",
            pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

    def test_deadline_uses_scheduled_flows_and_preserves_trace(self) -> None:
        case = self.tiny_case()

        immediate = run_one_sr(case, "meshtastic", seed=7, deadline_s=0.0)
        drained = run_one_sr(case, "meshtastic", seed=7, deadline_s=30.0)

        self.assertGreater(immediate.row["scheduled_unicast_flows"], 0)
        self.assertEqual(
            immediate.row["scheduled_unicast_flows"],
            drained.row["scheduled_unicast_flows"],
        )
        self.assertEqual(
            immediate.row["scheduled_trace_sha256"],
            drained.row["scheduled_trace_sha256"],
        )
        self.assertEqual(immediate.row["ack_pdr_deadline"], 0.0)
        self.assertGreater(drained.row["ack_pdr_deadline"], 0.0)
        self.assertGreater(immediate.row["late_ack_count"], 0)
        self.assertEqual(
            immediate.row["late_ack_count"],
            sum(flow["late_ack"] for flow in immediate.flows),
        )

    def test_paired_summary_uses_identical_trace_per_seed(self) -> None:
        rows = [
            run_one_sr(self.tiny_case(), protocol, seed, deadline_s=30.0).row
            for seed in (7, 8)
            for protocol in ("meshtastic", "meshcore")
        ]

        summary = summarize_paired(rows, "meshtastic", ("meshcore",))

        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["n_seeds"], 2)
        self.assertAlmostEqual(
            summary[0]["ack_pdr_gain"],
            sum(
                next(row["ack_pdr_deadline"] for row in rows if row["seed"] == seed and row["protocol"] == "meshtastic")
                - next(row["ack_pdr_deadline"] for row in rows if row["seed"] == seed and row["protocol"] == "meshcore")
                for seed in (7, 8)
            ) / 2,
        )

    def test_paired_summary_rejects_different_application_trace(self) -> None:
        first = run_one_sr(self.tiny_case(), "meshtastic", 7).row
        second = dict(run_one_sr(self.tiny_case(), "meshcore", 7).row)
        second["scheduled_trace_sha256"] = "different-trace"

        with self.assertRaisesRegex(ValueError, "paired trace"):
            summarize_paired([first, second], "meshtastic", ("meshcore",))

    def test_paired_summary_rejects_same_trace_with_different_case_config(self) -> None:
        case = self.tiny_case()
        first = run_one_sr(case, "meshtastic", 7).row
        second = run_one_sr(replace(case, payload_bytes=64), "meshcore", 7).row

        self.assertEqual(
            first["scheduled_trace_sha256"], second["scheduled_trace_sha256"]
        )
        with self.assertRaisesRegex(ValueError, "case config"):
            summarize_paired([first, second], "meshtastic", ("meshcore",))

    def test_paired_summary_rejects_case_config_changes_between_seeds(self) -> None:
        case = self.tiny_case()
        rows = [
            run_one_sr(selected_case, protocol, seed).row
            for seed, selected_case in (
                (7, case), (8, replace(case, payload_bytes=64))
            )
            for protocol in ("meshtastic", "meshcore")
        ]

        with self.assertRaisesRegex(ValueError, "case config"):
            summarize_paired(rows, "meshtastic", ("meshcore",))

    def test_forty_seed_interval_uses_student_t_not_normal(self) -> None:
        values = [0.0, 1.0] * 20

        mean, low, high = paired_ci95(values)

        self.assertEqual(mean, 0.5)
        self.assertAlmostEqual(high - mean, mean - low)
        self.assertGreater(high - mean, 1.96 * 0.5064 / (40**0.5))

    def test_one_seed_smoke_cannot_pass_reliability_cost_gate(self) -> None:
        focus = dict(run_one_sr(self.tiny_case(), "meshtastic", 7).row)
        control = dict(run_one_sr(self.tiny_case(), "meshcore", 7).row)
        focus["ack_pdr_deadline"] = 0.9
        control["ack_pdr_deadline"] = 0.1
        focus["whole_network_tx_airtime_s"] = 0.5
        control["whole_network_tx_airtime_s"] = 1.0

        comparison = summarize_paired(
            [focus, control], "meshtastic", ("meshcore",)
        )[0]

        self.assertFalse(comparison["gate_evaluable"])
        self.assertFalse(comparison["reliability_cost_gate"])

    def test_seed_splits_and_default_deadline_are_explicit(self) -> None:
        self.assertEqual(seeds_for_split("development"), tuple(range(3001, 3021)))
        self.assertEqual(seeds_for_split("holdout"), tuple(range(4001, 4041)))
        self.assertTrue(
            set(seeds_for_split("development")).isdisjoint(seeds_for_split("holdout"))
        )

        args = parse_args(["--case", "recurring_fading", "--split", "development"])
        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols[0], "meshecho-sr")

    def test_lpr_uses_fresh_development_seeds_and_full_matched_suite(self) -> None:
        self.assertEqual(
            seeds_for_split("lpr-development"), tuple(range(5001, 5021))
        )
        self.assertTrue(
            set(seeds_for_split("lpr-development")).isdisjoint(
                seeds_for_split("lpr-holdout")
            )
        )

        args = parse_args(["--suite", "lpr", "--split", "lpr-development"])

        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols, (
            "meshecho-lpr",
            "meshecho-lpr-fr",
            "meshecho-lpr-trigger-f",
            "meshecho-lpr-periodic",
            "meshecho-lpr-unobserved-edge",
        ))

    def test_dpa_uses_fresh_development_seeds_and_full_matched_suite(self) -> None:
        self.assertEqual(
            seeds_for_split("dpa-development"), tuple(range(6001, 6021))
        )
        self.assertTrue(
            set(seeds_for_split("dpa-development")).isdisjoint(
                seeds_for_split("dpa-holdout")
            )
        )

        args = parse_args(["--suite", "dpa", "--split", "dpa-development"])

        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols, (
            "meshecho-dpa",
            "meshecho-dpa-fr",
            "meshecho-dpa-repeat",
        ))

    def test_rac_uses_fresh_development_seeds_and_matched_controls(self) -> None:
        self.assertEqual(seeds_for_split("rac-development"), tuple(range(7001, 7021)))
        self.assertTrue(set(seeds_for_split("rac-development")).isdisjoint(
            seeds_for_split("rac-holdout")
        ))

        args = parse_args(["--suite", "rac", "--split", "rac-development"])

        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols, (
            "meshecho-rac", "meshecho-rac-repeat", "meshecho-rac-fr",
        ))

    def test_clar_uses_fresh_development_seeds_and_four_matched_arms(self) -> None:
        self.assertEqual(seeds_for_split("clar-development"), tuple(range(8001, 8021)))
        self.assertTrue(set(seeds_for_split("clar-development")).isdisjoint(
            seeds_for_split("clar-holdout")
        ))
        args = parse_args(["--suite", "clar", "--split", "clar-development"])
        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols, (
            "meshecho-clar", "meshecho-clar-nocancel",
            "meshecho-clar-repeat", "meshecho-clar-fr",
        ))
        self.assertEqual(args.protocols, CLAR_PROTOCOLS)

    def test_dhr_cli_selects_fresh_development_and_four_matched_arms(self) -> None:
        args = parse_args(["--suite", "dhr", "--split", "dhr-development"])

        self.assertEqual(seeds_for_split(args.split), tuple(range(9001, 9021)))
        self.assertEqual(args.deadline_s, 30.0)
        self.assertEqual(args.protocols, (
            "meshecho-dhr", "meshecho-dhr-none",
            "meshecho-dhr-repeat", "meshecho-dhr-flood",
        ))

    def test_bar_cli_reserves_three_matched_arms_and_seed_splits(self) -> None:
        args = parse_args(["--suite", "bar", "--split", "bar-development"])

        self.assertEqual(args.protocols, (
            "meshecho-bar-alternate", "meshecho-dhr-flood", "meshecho-bar-same",
        ))
        self.assertEqual(seeds_for_split("bar-development"), tuple(range(16001, 16021)))
        self.assertEqual(seeds_for_split("bar-holdout"), tuple(range(17001, 17041)))
        self.assertEqual(args.deadline_s, 30.0)

    def test_bar_arms_require_positive_application_deadline_in_runner(self) -> None:
        for protocol in (BAR_PROTOCOLS[0], BAR_PROTOCOLS[2]):
            with self.subTest(protocol=protocol):
                with self.assertRaisesRegex(ValueError, "requires a positive"):
                    run_one_sr(self.tiny_case(), protocol, seed=7, deadline_s=0.0)

    def test_bar_recovery_and_ack_packets_share_dhr_family_accounting(self) -> None:
        flood = Packet(
            "FLOOD", 1, 0, 3, 6, 0.0, BAR_PROTOCOLS[0],
            request_id=1, path=(0,), repair_index=2,
        )
        ack = Packet(
            "ACK", 1, 3, 0, 6, 0.0, BAR_PROTOCOLS[0],
            request_id=1, path=(0, 1, 3), path_index=1,
            app_payload=False, repair_index=2,
        )
        transmissions = [
            Transmission(1, 0, flood, 1.0, 1.2),
            Transmission(2, 3, ack, 1.3, 1.4),
        ]

        observed = summarize_windowed_transmissions(transmissions, cutoff_s=2.0)

        self.assertEqual(observed["windowed_dhr_recovery_f_source_tx"], 1)
        self.assertEqual(observed["windowed_dhr_flood_ack_tx"], 1)
        self.assertEqual(observed["windowed_ack_tx"], 1)
        self.assertEqual(observed["windowed_tx_bytes"],
                         flood.wire_size_bytes(32) + ack.wire_size_bytes(32))
        self.assertAlmostEqual(observed["whole_network_tx_airtime_s"], 0.3)

    def test_bar_run_exports_actual_extra_ack_event_counts(self) -> None:
        result = run_one_sr(self.tiny_case(), BAR_PROTOCOLS[0], seed=7)

        self.assertEqual(result.row["bar_first_flood_receipts"], sum(
            event.get("event") == "bar_first_flood_rx" for event in result.actions
        ))
        self.assertEqual(result.row["bar_candidate_events"], sum(
            event.get("event") == "bar_candidate" for event in result.actions
        ))
        self.assertEqual(result.row["bar_extra_ack_tx_events"], sum(
            event.get("event") == "bar_extra_ack_tx"
            and event["time"] <= result.row["drain_until_s"]
            for event in result.actions
        ))

    def test_ack_hop_summary_counts_only_observed_completed_attempts(self) -> None:
        packets = [
            Packet("ACK", flow_id, 3, 0, 6, 0.0, BAR_PROTOCOLS[0],
                   request_id=flow_id, path=path, path_index=index,
                   app_payload=False)
            for flow_id, path, index in (
                (1, (0, 1, 3), 1), (1, (0, 1, 3), 0),
                (2, (0, 2, 3), 1), (3, (0, 2, 3), 1),
            )
        ]
        transmissions = [
            Transmission(1, 3, packets[0], 1.0, 1.1),
            Transmission(2, 1, packets[1], 1.2, 1.3),
            Transmission(3, 3, packets[2], 2.0, 2.1),
            Transmission(4, 3, packets[3], 3.0, 3.5),
        ]

        summary = sr_experiment.summarize_ack_hop_observations(
            transmissions, {1}, cutoff_s=3.2,
        )

        self.assertEqual(summary["windowed_destination_ack_attempts"], 3)
        self.assertEqual(summary["ack_expected_hop_observed_tx"], 3)
        self.assertEqual(summary["ack_expected_hop_physical_failures"], 2)
        self.assertEqual(summary["ack_expected_hop_censored_tx"], 1)
        self.assertEqual(json.loads(summary["ack_physical_failures_by_reverse_hop"]),
                         {"1": 1, "2": 1})

    def test_passive_ack_hop_observer_preserves_protocol_replay(self) -> None:
        sims = []
        for simulator_type in (Simulator, RecordingSimulator):
            sim = simulator_type(
                [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                RadioConfig(sf=7, shadow_sigma_db=0.0),
                build_protocol("meshecho-dhr-flood"), seed=17, max_hops=6,
                independent_random_streams=True,
            )
            sim.schedule(1.0, "app_send", (0, 1, 1))
            sim.run(4.0)
            sims.append(sim)
        plain, recorded = sims

        self.assertEqual(plain.metrics.tx_count, recorded.metrics.tx_count)
        self.assertEqual(plain.metrics.flows[1], recorded.metrics.flows[1])
        self.assertEqual(plain.channel_random.getstate(),
                         recorded.channel_random.getstate())
        ack_tx = next(tx for tx in recorded.tx_history if tx.packet.kind == "ACK")
        self.assertIn(ack_tx.tx_id, recorded.ack_expected_decodes)

    def test_run_row_reports_physical_ack_hop_observations(self) -> None:
        row = run_one_sr(self.tiny_case(), "meshecho-dhr-flood", seed=7).row

        self.assertGreater(row["windowed_destination_ack_attempts"], 0)
        self.assertEqual(
            row["ack_expected_hop_observed_tx"]
            + row["ack_expected_hop_censored_tx"]
            + row["ack_no_expected_hop_tx"],
            row["windowed_ack_tx"],
        )
        self.assertLessEqual(row["ack_expected_hop_physical_failures"],
                             row["ack_expected_hop_observed_tx"])
        self.assertIsInstance(
            json.loads(row["ack_physical_failures_by_reverse_hop"]), dict,
        )

    def test_first_data_delivery_kind_is_observed_only_on_first_delivery(self) -> None:
        sims = []
        for simulator_type in (Simulator, RecordingSimulator):
            sim = simulator_type(
                [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                RadioConfig(sf=7, shadow_sigma_db=0.0),
                build_protocol("meshecho-dhr-flood"), seed=17, max_hops=6,
            )
            for flow_id in (1, 2, 3):
                sim.metrics.register_flow(flow_id, 0, 1, 0.0)
            routed = Packet("DATA", 1, 0, 1, 6, 0.0, "meshecho-dhr-flood")
            flood_duplicate = Packet("FLOOD", 1, 0, 1, 6, 0.0,
                                     "meshecho-dhr-flood")
            flood_first = Packet("FLOOD", 2, 0, 1, 6, 0.0,
                                 "meshecho-dhr-flood")
            sim.now = 1.0
            sim.mark_delivered(1, 1, routed)
            sim.now = 2.0
            sim.mark_delivered(1, 1, flood_duplicate)
            sim.mark_delivered(2, 1, flood_first)
            sim.mark_delivered(3, 0, flood_first)
            sims.append(sim)
        plain, recorded = sims

        self.assertEqual(plain.metrics.flows, recorded.metrics.flows)
        self.assertEqual(recorded.first_data_delivery_kind, {1: "R", 2: "F"})

    def test_bar_flow_rows_link_exposure_to_offline_delivery_strata(self) -> None:
        result = run_one_sr(self.tiny_case(), BAR_PROTOCOLS[0], seed=7)
        extra_by_flow = {}
        for action in result.actions:
            if (action.get("event") == "bar_extra_ack_tx"
                    and action["time"] <= result.row["drain_until_s"]):
                flow_id = action["flow_id"]
                extra_by_flow[flow_id] = extra_by_flow.get(flow_id, 0) + 1

        self.assertEqual(
            sum(flow["bar_extra_ack_tx_count"] for flow in result.flows),
            result.row["bar_extra_ack_tx_events"],
        )
        for flow in result.flows:
            self.assertEqual(flow["bar_extra_ack_tx_count"],
                             extra_by_flow.get(flow["flow_id"], 0))
            self.assertIn(flow["first_data_delivery_kind"], {None, "R", "F"})
            if flow["delivery_by_deadline"]:
                self.assertIn(flow["first_data_delivery_kind"], {"R", "F"})

    def test_bar_custom_smoke_reaches_simulation_only_as_full_seed_16000_suite(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr",
                   side_effect=RuntimeError("simulation would start")) as simulate:
            with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                run_matrix(self.tiny_case(), BAR_PROTOCOLS, (16000,), split="custom")
            simulate.assert_called_once()

    def test_bar_custom_mode_rejects_partial_suite_and_reserved_seeds(self) -> None:
        invalid = (
            (BAR_PROTOCOLS[:1], (16000,)),
            (BAR_PROTOCOLS, (16001,)),
            (BAR_PROTOCOLS, (17001,)),
        )
        for protocols, seeds in invalid:
            with self.subTest(protocols=protocols, seeds=seeds), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaises(ValueError):
                    run_matrix(self.tiny_case(), protocols, seeds, split="custom")
                simulate.assert_not_called()

    def test_bar_reserved_seeds_reject_cross_suite_custom_runs(self) -> None:
        for seed in (16000, 16001, 17001):
            with self.subTest(seed=seed), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaisesRegex(ValueError, "BAR reserved"):
                    run_matrix(self.tiny_case(), ("meshtastic",), (seed,),
                               split="custom")
                simulate.assert_not_called()

    def test_bar_development_frozen_matrix_reaches_simulation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr",
                   side_effect=RuntimeError("simulation would start")) as simulate:
            with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                run_matrix(
                    SR_CASES["recurring_fading"], BAR_PROTOCOLS,
                    seeds_for_split("bar-development"), split="bar-development",
                )
            simulate.assert_called_once()

    def test_bar_development_rejects_changes_to_frozen_matrix(self) -> None:
        case = SR_CASES["recurring_fading"]
        seeds = seeds_for_split("bar-development")
        invalid = (
            (case, BAR_PROTOCOLS[:1], seeds, 30.0),
            (self.tiny_case(), BAR_PROTOCOLS, seeds, 30.0),
            (case, BAR_PROTOCOLS, seeds[:-1], 30.0),
            (case, BAR_PROTOCOLS, seeds, 31.0),
        )
        for selected_case, protocols, selected_seeds, deadline in invalid:
            with self.subTest(protocols=protocols, seeds=selected_seeds,
                              deadline=deadline), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaises(ValueError):
                    run_matrix(selected_case, protocols, selected_seeds,
                               deadline, split="bar-development")
                simulate.assert_not_called()

    def test_bar_holdout_requires_development_manifest_before_simulation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "BAR holdout requires"):
                run_matrix(
                    SR_CASES["recurring_fading"], BAR_PROTOCOLS,
                    seeds_for_split("bar-holdout"), split="bar-holdout",
                )
            simulate.assert_not_called()

    def test_bar_holdout_rejects_missing_development_evidence_before_simulation(self) -> None:
        with TemporaryDirectory() as directory, patch(
            "tools.run_sr_experiment.run_one_sr"
        ) as simulate:
            with self.assertRaises((ValueError, FileNotFoundError)):
                run_matrix(
                    SR_CASES["recurring_fading"], BAR_PROTOCOLS,
                    seeds_for_split("bar-holdout"), split="bar-holdout",
                    development_manifest=Path(directory) / "missing.manifest.json",
                )
            simulate.assert_not_called()

    def test_bar_source_hashes_bind_refrozen_ack_contract(self) -> None:
        hashes = source_hashes("bar")

        self.assertEqual(set(hashes), {
            "lora_mesh_sim.py", "tools/run_fair_multihop_probe.py",
            "tools/run_sr_experiment.py",
            "docs/research/meshecho_bounded_reverse_ack_candidate.md",
            "tests/test_meshecho_bar.py", "tests/test_sr_experiment.py",
        })
        self.assertTrue(all(len(digest) == 64 for digest in hashes.values()))

    def test_bar_holdout_rejects_insufficient_actual_extra_ack_exposure(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_bar_development_manifest(
                directory, exposed_seeds=9,
            )

            with self.assertRaisesRegex(ValueError, "BAR.*exposure"):
                validate_bar_development_manifest(manifest, source_hashes("bar"))

    def test_bar_manifest_records_paired_and_actual_exposure_gates(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertTrue(manifest["bar_joint_primary_gate"])
            self.assertEqual(manifest["bar_extra_ack_tx_events"], 20)
            self.assertEqual(manifest["bar_extra_ack_exposed_seeds"], 10)
            self.assertTrue(manifest["bar_exposure_gate"])
            self.assertTrue(manifest["bar_project_gate"])
            self.assertTrue(manifest["bar_development_open_gate"])
            validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_recomputes_paired_gate_from_run_rows(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            paired_path = manifest_path.with_name("synthetic-bar-dev.paired.csv")
            with paired_path.open(newline="", encoding="utf-8") as handle:
                paired_rows = list(csv.DictReader(handle))
            paired_rows[0]["ack_pdr_gain"] = "0.0"
            with paired_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(paired_rows[0]))
                writer.writeheader()
                writer.writerows(paired_rows)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["paired"] = hashlib.sha256(
                paired_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*paired"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_reconciles_rehashed_flow_outcomes_with_runs(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            flows_path = manifest_path.with_name("synthetic-bar-dev.flows.jsonl")
            flows = [json.loads(line) for line in flows_path.read_text().splitlines()]
            flow = next(item for item in flows
                        if item["protocol"] == BAR_PROTOCOLS[0])
            flow["ack_by_deadline"] = False
            flow["acked_at"] = None
            flow["completion_delay_capped_s"] = 30.0
            flows_path.write_text("".join(json.dumps(item) + "\n" for item in flows))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["flows"] = hashlib.sha256(
                flows_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*flow"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_reconciles_extra_ack_events_with_run_counts(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            runs_path = manifest_path.with_name("synthetic-bar-dev.runs.csv")
            with runs_path.open(newline="", encoding="utf-8") as handle:
                run_rows = list(csv.DictReader(handle))
            run_rows[0]["bar_extra_ack_tx_events"] = "0"
            with runs_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
                writer.writeheader()
                writer.writerows(run_rows)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["runs"] = hashlib.sha256(
                runs_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*extra ACK"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_rejects_rehashed_out_of_split_extra_ack_actions(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            actions_path = manifest_path.with_name("synthetic-bar-dev.actions.jsonl")
            runs_path = manifest_path.with_name("synthetic-bar-dev.runs.csv")
            flows_path = manifest_path.with_name("synthetic-bar-dev.flows.jsonl")
            actions = [json.loads(line) for line in actions_path.read_text().splitlines()]
            for action in actions:
                action["seed"] += 2000
            actions_path.write_text("".join(json.dumps(item) + "\n" for item in actions))
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row["bar_extra_ack_tx_events"] = "0"
            with runs_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            flows = [json.loads(line) for line in flows_path.read_text().splitlines()]
            for flow in flows:
                flow["bar_extra_ack_tx_count"] = 0
            flows_path.write_text("".join(json.dumps(item) + "\n" for item in flows))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key, path in (("actions", actions_path), ("runs", runs_path),
                              ("flows", flows_path)):
                manifest["artifact_sha256"][key] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*action"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_rejects_duplicate_extra_ack_for_one_flow(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            actions_path = manifest_path.with_name("synthetic-bar-dev.actions.jsonl")
            actions = [json.loads(line) for line in actions_path.read_text().splitlines()]
            first_extra = next(item for item in actions
                               if item["event"] == "bar_extra_ack_tx")
            actions.append(dict(first_extra))
            actions_path.write_text("".join(json.dumps(item) + "\n" for item in actions))
            runs_path = manifest_path.with_name("synthetic-bar-dev.runs.csv")
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            row = next(item for item in rows
                       if item["seed"] == str(first_extra["seed"])
                       and item["protocol"] == BAR_PROTOCOLS[0])
            row["bar_extra_ack_tx_events"] = "3"
            with runs_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key, path in (("actions", actions_path), ("runs", runs_path)):
                manifest["artifact_sha256"][key] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
            manifest["bar_extra_ack_tx_events"] += 1
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*extra ACK action"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_holdout_rejects_rehashed_nondiverse_candidate_path(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_bar_development_manifest(directory)
            actions_path = manifest_path.with_name("synthetic-bar-dev.actions.jsonl")
            actions = [json.loads(line) for line in actions_path.read_text().splitlines()]
            candidate = next(item for item in actions
                             if item["event"] == "bar_candidate")
            candidate["alternate_path"] = candidate["first_path"]
            candidate["reply_path"] = candidate["first_path"]
            extra = next(item for item in actions
                         if item["event"] == "bar_extra_ack_tx"
                         and item["seed"] == candidate["seed"]
                         and item["flow_id"] == candidate["flow_id"])
            extra["path"] = candidate["first_path"]
            actions_path.write_text("".join(json.dumps(item) + "\n" for item in actions))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["actions"] = hashlib.sha256(
                actions_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "BAR.*candidate"):
                validate_bar_development_manifest(manifest_path, source_hashes("bar"))

    def test_bar_matrix_uses_bar_source_hashes_despite_fixed_f_control(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr",
                   return_value=SrRun({}, [], [])), patch(
            "tools.run_sr_experiment.summarize_paired", return_value=[]
        ):
            bundle = run_matrix(self.tiny_case(), BAR_PROTOCOLS, (16000,), split="custom")

        self.assertEqual(bundle.source_sha256, source_hashes("bar"))

    def test_bar_paired_gate_uses_distinct_fixed_f_and_same_path_thresholds(self) -> None:
        rows = []
        for seed in seeds_for_split("bar-development"):
            for protocol, ack_pdr, airtime in (
                (BAR_PROTOCOLS[0], 0.80, 1.04),
                (BAR_PROTOCOLS[1], 0.75, 1.00),
                (BAR_PROTOCOLS[2], 0.77, 1.00),
            ):
                rows.append({
                    "case": "recurring_fading", "case_config_sha256": "same-case",
                    "protocol": protocol, "seed": seed,
                    "seed_split": "bar-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": 0.90,
                    "whole_network_tx_airtime_s": airtime,
                })

        comparisons = summarize_paired(rows, BAR_PROTOCOLS[0], BAR_PROTOCOLS[1:])

        self.assertEqual({item["comparator"] for item in comparisons},
                         set(BAR_PROTOCOLS[1:]))
        self.assertTrue(all(item["bar_primary_gate"] for item in comparisons))
        self.assertTrue(all(item["bar_joint_primary_gate"] for item in comparisons))

    def test_bar_holdout_reports_preregistered_replication_gate(self) -> None:
        seeds = seeds_for_split("bar-holdout")
        rows = []
        for seed in seeds:
            for protocol, ack_pdr, airtime in (
                (BAR_PROTOCOLS[0], 0.80, 1.04),
                (BAR_PROTOCOLS[1], 0.75, 1.00),
                (BAR_PROTOCOLS[2], 0.77, 1.00),
            ):
                rows.append({
                    "case": "recurring_fading", "case_config_sha256": "same-case",
                    "protocol": protocol, "seed": seed, "seed_split": "bar-holdout",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": 0.90,
                    "whole_network_tx_airtime_s": airtime,
                })
        comparisons = summarize_paired(rows, BAR_PROTOCOLS[0], BAR_PROTOCOLS[1:])
        self.assertTrue(all(item["bar_joint_primary_gate"] for item in comparisons))
        self.assertTrue(all(confirmatory_comparison_eligible(
            "bar-holdout", "recurring_fading", BAR_PROTOCOLS[0],
            item["comparator"],
        ) for item in comparisons))
        actions = [
            {"event": "bar_extra_ack_tx", "protocol": BAR_PROTOCOLS[0],
             "seed": seed, "time": float(index), "flow_id": index}
            for seed in seeds[:20] for index in (1, 2)
        ]
        with TemporaryDirectory() as directory:
            bundle = SrExperiment(
                SR_CASES["recurring_fading"], BAR_PROTOCOLS, seeds, 30.0,
                rows, [], actions, comparisons, "bar-holdout", source_hashes("bar"),
            )
            manifest_path = write_artifacts(
                Path(directory) / "passing", bundle,
            )["manifest"]
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(manifest["bar_joint_primary_gate"])
            self.assertEqual(manifest["bar_extra_ack_tx_events"], 40)
            self.assertEqual(manifest["bar_extra_ack_exposed_seeds"], 20)
            self.assertTrue(manifest["bar_exposure_gate"])
            self.assertTrue(manifest["bar_project_gate"])
            self.assertTrue(manifest["bar_holdout_replication_gate"])

            short_bundle = replace(bundle, actions=actions[:-1])
            short_path = write_artifacts(
                Path(directory) / "underexposed", short_bundle,
            )["manifest"]
            short_manifest = json.loads(short_path.read_text(encoding="utf-8"))
            self.assertFalse(short_manifest["bar_exposure_gate"])
            self.assertFalse(short_manifest["bar_project_gate"])
            self.assertFalse(short_manifest["bar_holdout_replication_gate"])

    def test_only_frozen_dhr_holdout_primary_comparisons_are_confirmatory(self) -> None:
        for comparator in DHR_PROTOCOLS[2:]:
            self.assertTrue(confirmatory_comparison_eligible(
                "dhr-holdout", "recurring_fading", DHR_PROTOCOLS[0], comparator,
            ))
        self.assertFalse(confirmatory_comparison_eligible(
            "dhr-holdout", "recurring_fading", DHR_PROTOCOLS[0], DHR_PROTOCOLS[1],
        ))
        self.assertFalse(confirmatory_comparison_eligible(
            "dhr-development", "recurring_fading", DHR_PROTOCOLS[0],
            DHR_PROTOCOLS[2],
        ))

    def test_dhr_custom_split_cannot_open_holdout_before_validation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "dhr-holdout"):
                run_matrix(
                    SR_CASES["recurring_fading"], DHR_PROTOCOLS,
                    (10001,), split="custom",
                )
            simulate.assert_not_called()

    def test_dhr_custom_mode_is_only_for_seed_9000_smoke(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "seed-9000 preflight"):
                run_matrix(
                    self.tiny_case(), DHR_PROTOCOLS,
                    (9001,), split="custom",
                )
            simulate.assert_not_called()

    def test_dhr_development_requires_frozen_four_arm_matrix(self) -> None:
        case = SR_CASES["recurring_fading"]
        invalid = (
            (case, DHR_PROTOCOLS[:1], seeds_for_split("dhr-development"), 30.0),
            (self.tiny_case(), DHR_PROTOCOLS, seeds_for_split("dhr-development"), 30.0),
            (case, DHR_PROTOCOLS, tuple(range(9001, 9020)), 30.0),
            (case, DHR_PROTOCOLS, seeds_for_split("dhr-development"), 31.0),
        )
        for selected_case, protocols, seeds, deadline in invalid:
            with self.subTest(case=selected_case.key, seeds=seeds,
                              deadline=deadline, protocols=protocols), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaises(ValueError):
                    run_matrix(selected_case, protocols, seeds, deadline,
                               split="dhr-development")
                simulate.assert_not_called()

    def test_dhr_development_accepts_frozen_matrix_before_simulation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr",
                   side_effect=RuntimeError("simulation would start")) as simulate:
            with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                run_matrix(
                    SR_CASES["recurring_fading"], DHR_PROTOCOLS,
                    seeds_for_split("dhr-development"), split="dhr-development",
                )
            simulate.assert_called_once()

    def test_dhr_holdout_requires_development_manifest_before_simulation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "DHR holdout requires"):
                run_matrix(
                    SR_CASES["recurring_fading"], DHR_PROTOCOLS,
                    seeds_for_split("dhr-holdout"), split="dhr-holdout",
                )
            simulate.assert_not_called()

    def test_dhr_source_hashes_include_frozen_design_and_runners(self) -> None:
        hashes = source_hashes("dhr")

        self.assertEqual(set(hashes), {
            "lora_mesh_sim.py", "tools/run_fair_multihop_probe.py",
            "tools/run_sr_experiment.py", "docs/research/meshecho_dhr_design.md",
        })
        self.assertTrue(all(len(digest) == 64 for digest in hashes.values()))

    def test_dhr_holdout_accepts_complete_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)

            validate_dhr_development_manifest(manifest, source_hashes("dhr"))
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertTrue(metadata["dhr_project_gate"])
            self.assertEqual(metadata["dhr_admitted_guard_events"], 20)
            self.assertEqual(metadata["dhr_r_rescue_events"], 10)
            self.assertEqual(metadata["dhr_f_rescue_events"], 10)

    def test_dhr_holdout_rejects_insufficient_action_exposure(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(
                directory, recovery_seed_count=9,
            )

            with self.assertRaisesRegex(ValueError, "action exposure gate"):
                validate_dhr_development_manifest(manifest, source_hashes("dhr"))

    def test_dhr_holdout_rejects_failed_repeat_reliability_gate(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(
                directory, repeat_ack_count=4,
            )

            with self.assertRaisesRegex(ValueError, "joint primary gate"):
                validate_dhr_development_manifest(manifest, source_hashes("dhr"))

    def test_dhr_holdout_rejects_fixed_repeat_selecting_flood(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(
                directory, repeat_guard_action="F",
            )

            with self.assertRaisesRegex(ValueError, "guard evidence is invalid"):
                validate_dhr_development_manifest(manifest, source_hashes("dhr"))

    def test_dhr_holdout_validates_development_before_first_simulation(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)
            with patch("tools.run_sr_experiment.run_one_sr",
                       side_effect=RuntimeError("simulation would start")) as simulate:
                with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DHR_PROTOCOLS,
                        seeds_for_split("dhr-holdout"), split="dhr-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_called_once()

    def test_dhr_holdout_rejects_rehashed_missing_recovery_event(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = [json.loads(line) for line in actions.read_text(
                encoding="utf-8"
            ).splitlines()]
            removed = next(index for index, event in enumerate(records)
                           if event.get("event") == "dhr_recovery_tx")
            records.pop(removed)
            actions.write_text("".join(json.dumps(event) + "\n" for event in records),
                               encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(
                actions.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "rescue ACK lacks TX|action counts"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DHR_PROTOCOLS,
                        seeds_for_split("dhr-holdout"), split="dhr-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dhr_holdout_rejects_changed_development_source_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)
            expected = source_hashes("dhr")
            expected["lora_mesh_sim.py"] = "0" * 64

            with self.assertRaisesRegex(ValueError, "source hash"):
                validate_dhr_development_manifest(manifest, expected)

    def test_dhr_holdout_rejects_rehashed_paired_result(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)
            paired = Path(str(manifest).replace(".manifest.json", ".paired.csv"))
            with paired.open(newline="", encoding="utf-8") as handle:
                comparisons = list(csv.DictReader(handle))
            comparisons[0]["ack_pdr_ci95_low"] = "0.99"
            with paired.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
                writer.writeheader()
                writer.writerows(comparisons)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["paired"] = hashlib.sha256(
                paired.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "paired evidence differs"):
                validate_dhr_development_manifest(manifest, source_hashes("dhr"))

    def test_dhr_holdout_rejects_rehashed_incomplete_flow_denominator(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dhr_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = flows.read_text(encoding="utf-8").splitlines()
            flows.write_text("\n".join(records[1:]) + "\n", encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(
                flows.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "flow evidence differs"):
                validate_dhr_development_manifest(manifest, source_hashes("dhr"))

    def test_dhr_development_joint_gate_uses_distinct_repeat_and_flood_rules(self) -> None:
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        rows = []
        settings = {
            "meshecho-dhr": (0.9, 0.9),
            "meshecho-dhr-none": (0.7, 0.8),
            "meshecho-dhr-repeat": (0.8, 1.0),
            "meshecho-dhr-flood": (0.9, 1.0),
        }
        for seed in seeds_for_split("dhr-development"):
            for protocol, (ack, airtime) in settings.items():
                rows.append({
                    "case": case.key, "case_config_sha256": case_hash,
                    "protocol": protocol, "seed": seed,
                    "seed_split": "dhr-development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack,
                    "destination_pdr_deadline": ack,
                    "whole_network_tx_airtime_s": airtime,
                })

        comparisons = summarize_paired(rows, DHR_PROTOCOLS[0], DHR_PROTOCOLS[1:])

        self.assertTrue(all(item["dhr_joint_primary_gate"] for item in comparisons))
        by_control = {item["comparator"]: item for item in comparisons}
        self.assertTrue(by_control["meshecho-dhr-repeat"]["dhr_primary_gate"])
        self.assertTrue(by_control["meshecho-dhr-flood"]["dhr_primary_gate"])
        self.assertFalse(by_control["meshecho-dhr-none"]["dhr_primary_gate"])

        incomplete = [row for row in rows
                      if row["protocol"] != "meshecho-dhr-none"]
        missing_control = summarize_paired(
            incomplete, DHR_PROTOCOLS[0], DHR_PROTOCOLS[2:]
        )
        self.assertFalse(any(item["dhr_joint_primary_gate"]
                             for item in missing_control))

    def test_dhr_run_reports_capped_completion_and_logged_recovery_actions(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-dhr", seed=7)
        guards = [event for event in run.actions if event.get("event") == "dhr_guard"]
        rescues = [event for event in run.actions
                   if event.get("event") == "dhr_recovery_tx"]
        accepted = [event for event in run.actions
                    if event.get("event") == "dhr_source_ack_rx"
                    and event.get("accepted")]

        self.assertEqual(run.row["dhr_guard_events"], len(guards))
        self.assertEqual(run.row["dhr_admitted_guards"], sum(
            event["admitted"] for event in guards
        ))
        self.assertEqual(run.row["dhr_selected_r"], sum(
            event.get("selected_action") == "R" for event in guards
        ))
        self.assertEqual(run.row["dhr_selected_f"], sum(
            event.get("selected_action") == "F" for event in guards
        ))
        self.assertEqual(run.row["dhr_selected_none"], sum(
            event.get("selected_action") == "none" for event in guards
        ))
        self.assertEqual(run.row["dhr_recovery_r_tx"], sum(
            event["action"] == "R" and event["repair_index"] == 1
            for event in rescues
        ))
        self.assertEqual(run.row["dhr_recovery_f_tx"], sum(
            event["action"] == "F" and event["repair_index"] == 2
            for event in rescues
        ))
        self.assertEqual(run.row["dhr_source_ack_accepted"], len(accepted))
        self.assertEqual(run.row["dhr_duplicate_destination_receptions"], sum(
            event.get("event") == "dhr_destination_rx" and event.get("duplicate")
            for event in run.actions
        ))
        self.assertAlmostEqual(run.row["mean_completion_delay_capped_s"], sum(
            flow["completion_delay_capped_s"] for flow in run.flows
        ) / len(run.flows))
        for flow in run.flows:
            expected = (flow["acked_at"] - flow["enqueued_at"]
                        if flow["ack_by_deadline"] else 30.0)
            self.assertAlmostEqual(flow["completion_delay_capped_s"], expected)

    def test_clar_preflight_rejects_noncanonical_splits_before_simulation(self) -> None:
        case = SR_CASES["recurring_fading"]
        invalid = (
            (case, CLAR_PROTOCOLS, (8000,), "development", 30.0),
            (case, CLAR_PROTOCOLS, (4001,), "custom", 30.0),
            (case, CLAR_PROTOCOLS, (8001,), "custom", 30.0),
            (case, (CLAR_PROTOCOLS[0],), (8000,), "custom", 30.0),
            (case, (CLAR_PROTOCOLS[0],), seeds_for_split("clar-development"),
             "clar-development", 30.0),
            (case, CLAR_PROTOCOLS, tuple(range(8001, 8020)),
             "clar-development", 30.0),
            (self.tiny_case(), CLAR_PROTOCOLS, seeds_for_split("clar-development"),
             "clar-development", 30.0),
            (case, CLAR_PROTOCOLS, seeds_for_split("clar-development"),
             "clar-development", 31.0),
        )
        for selected_case, protocols, seeds, split, deadline in invalid:
            with self.subTest(split=split, seeds=seeds, protocols=protocols), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaises(ValueError):
                    run_matrix(selected_case, protocols, seeds, deadline, split)
                simulate.assert_not_called()

    def test_clar_source_hashes_include_simulator_runner_and_frozen_design(self) -> None:
        hashes = source_hashes("clar")

        self.assertEqual(set(hashes), {
            "lora_mesh_sim.py", "tools/run_fair_multihop_probe.py",
            "tools/run_sr_experiment.py", "docs/research/meshecho_clar_design.md",
        })
        self.assertTrue(all(len(digest) == 64 for digest in hashes.values()))

    def test_rac_development_requires_the_full_matched_suite(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "full RAC policy suite"):
                run_matrix(
                    SR_CASES["recurring_fading"], ("meshecho-rac",),
                    seeds_for_split("rac-development"), split="rac-development",
                )
            simulate.assert_not_called()

    def test_rac_development_requires_the_frozen_case(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "frozen recurring_fading case"):
                run_matrix(
                    self.tiny_case(), RAC_PROTOCOLS,
                    seeds_for_split("rac-development"), split="rac-development",
                )
            simulate.assert_not_called()

    def test_rac_development_requires_the_frozen_deadline(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "30-second deadline"):
                run_matrix(
                    SR_CASES["recurring_fading"], RAC_PROTOCOLS,
                    seeds_for_split("rac-development"), deadline_s=31.0,
                    split="rac-development",
                )
            simulate.assert_not_called()

    def test_rac_development_requires_exactly_7001_through_7020(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "frozen seed list"):
                run_matrix(
                    SR_CASES["recurring_fading"], RAC_PROTOCOLS,
                    tuple(range(7001, 7020)), split="rac-development",
                )
            simulate.assert_not_called()

    def test_custom_rac_run_cannot_open_a_holdout_seed(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "rac-holdout"):
                run_matrix(
                    self.tiny_case(), ("meshecho-rac",), (4001,), split="custom",
                )
            simulate.assert_not_called()

    def test_generic_development_cannot_label_rac_as_frozen_evidence(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "RAC policies require"):
                run_matrix(
                    SR_CASES["recurring_fading"], RAC_PROTOCOLS,
                    seeds_for_split("development"), split="development",
                )
            simulate.assert_not_called()

    def test_rac_custom_preflight_rejects_every_seed_except_7000(self) -> None:
        for seed in (7, 5001, 6001, 7001, 7020):
            with self.subTest(seed=seed), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaisesRegex(ValueError, "seed-7000 preflight"):
                    run_matrix(
                        self.tiny_case(), RAC_PROTOCOLS, (seed,), split="custom",
                    )
                simulate.assert_not_called()

    def test_rac_custom_preflight_requires_all_matched_arms(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "full RAC preflight suite"):
                run_matrix(
                    self.tiny_case(), ("meshecho-rac",), (7000,), split="custom",
                )
            simulate.assert_not_called()

    def test_rac_source_freeze_includes_its_written_design(self) -> None:
        hashes = source_hashes("rac")

        self.assertEqual(len(hashes["docs/research/meshecho_rac_design.md"]), 64)

    def test_rac_matrix_records_its_own_design_hash(self) -> None:
        bundle = run_matrix(self.tiny_case(), RAC_PROTOCOLS, (7000,), split="custom")

        self.assertEqual(bundle.source_sha256, source_hashes("rac"))

    def test_rac_joint_gate_requires_both_matched_controls(self) -> None:
        rows = []
        for seed in seeds_for_split("rac-development"):
            for protocol, ack_pdr in (
                ("meshecho-rac", 0.9),
                ("meshecho-rac-repeat", 0.9),
                ("meshecho-rac-fr", 0.7),
            ):
                rows.append({
                    "case": "recurring_fading",
                    "case_config_sha256": "fixed-case",
                    "seed": seed,
                    "seed_split": "rac-development",
                    "protocol": protocol,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": 0.9,
                    "whole_network_tx_airtime_s": 1.0,
                })

        comparisons = summarize_paired(
            rows, RAC_PROTOCOLS[0], RAC_PROTOCOLS[1:]
        )

        self.assertFalse(comparisons[0]["reliability_cost_gate"])
        self.assertTrue(comparisons[1]["reliability_cost_gate"])
        self.assertTrue(all(not row["rac_joint_primary_gate"] for row in comparisons))

    def test_custom_twenty_seed_rows_cannot_claim_rac_joint_gate(self) -> None:
        rows = []
        for seed in seeds_for_split("rac-development"):
            for protocol in RAC_PROTOCOLS:
                rows.append({
                    "case": "recurring_fading",
                    "case_config_sha256": "fixed-case",
                    "seed": seed,
                    "seed_split": "custom",
                    "protocol": protocol,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": 0.9 if protocol == "meshecho-rac" else 0.7,
                    "destination_pdr_deadline": 0.9,
                    "whole_network_tx_airtime_s": 1.0,
                })

        comparisons = summarize_paired(rows, RAC_PROTOCOLS[0], RAC_PROTOCOLS[1:])

        self.assertTrue(all(not item["rac_joint_primary_gate"] for item in comparisons))

    def test_rac_holdout_requires_development_manifest_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "development manifest"):
                run_matrix(
                    SR_CASES["recurring_fading"], RAC_PROTOCOLS,
                    seeds_for_split("rac-holdout"), split="rac-holdout",
                )
            simulate.assert_not_called()

    def test_rac_holdout_rejects_changed_development_source_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "rac-dev.manifest.json"
            manifest.write_text(json.dumps({"source_sha256": {}}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source hash"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_noncanonical_development_configuration(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "rac-dev.manifest.json"
            manifest.write_text(json.dumps({
                "source_sha256": source_hashes("rac"),
                "case": asdict(self.tiny_case()),
                "protocols": list(RAC_PROTOCOLS),
                "seeds": list(seeds_for_split("rac-development")),
                "seed_split": "rac-development",
                "application_deadline_s": 30.0,
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "frozen configuration"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_requires_hashed_development_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "rac-dev.manifest.json"
            manifest.write_text(json.dumps({
                "source_sha256": source_hashes("rac"),
                "case": asdict(SR_CASES["recurring_fading"]),
                "protocols": list(RAC_PROTOCOLS),
                "seeds": list(seeds_for_split("rac-development")),
                "seed_split": "rac-development",
                "application_deadline_s": 30.0,
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "artifact hashes"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_manifest_records_joint_and_exposure_gates(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))

            self.assertTrue(metadata["rac_joint_primary_gate"])
            self.assertTrue(metadata["rac_exposure_gate"])

    def test_rac_holdout_rejects_missing_policy_row_even_with_valid_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows.pop(0)
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "three policy rows per seed"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_changed_run_case_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["case_config_sha256"] = "0" * 64
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "frozen case config"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_incomplete_flow_log_even_with_valid_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = flows.read_text(encoding="utf-8").splitlines()
            flows.write_text("\n".join(records[1:]) + "\n", encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "flow evidence"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_requires_exposure_across_ten_seeds(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(
                directory, exposure_seed_count=9, events_per_seed=3,
            )

            with self.assertRaisesRegex(ValueError, "corridor exposure"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_recomputes_paired_bounds_before_running(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            paired = Path(str(manifest).replace(".manifest.json", ".paired.csv"))
            with paired.open(newline="", encoding="utf-8") as handle:
                comparisons = list(csv.DictReader(handle))
            comparisons[0]["ack_pdr_ci95_low"] = "0.9"
            with paired.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
                writer.writeheader()
                writer.writerows(comparisons)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["paired"] = hashlib.sha256(paired.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "paired evidence differs from runs"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_accepts_complete_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)

            validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_starts_only_after_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            with patch(
                "tools.run_sr_experiment.run_one_sr",
                side_effect=RuntimeError("simulation would start"),
            ) as simulate:
                with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                    run_matrix(
                        SR_CASES["recurring_fading"], RAC_PROTOCOLS,
                        seeds_for_split("rac-holdout"), split="rac-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_called_once()

    def test_rac_holdout_requires_both_development_primary_gates(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory, repeat_ack=0.9)

            with self.assertRaisesRegex(ValueError, "joint primary gate"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_exposure_not_backed_by_action_log(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = actions.read_text(encoding="utf-8").splitlines()
            actions.write_text("\n".join(records[1:]) + "\n", encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(
                actions.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exposure differs from action log"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_duplicate_corridor_exposure(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = actions.read_text(encoding="utf-8").splitlines()
            actions.write_text("\n".join(records + records[:1]) + "\n", encoding="utf-8")
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            focus = next(row for row in rows if row["seed"] == "7001"
                         and row["protocol"] == "meshecho-rac")
            focus["rac_corridor_eligible"] = "3"
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["rac_corridor_eligible_events"] = 21
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(actions.read_bytes()).hexdigest()
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate corridor exposure"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_corridor_exposure_on_non_f_flow(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = [json.loads(line) for line in flows.read_text(encoding="utf-8").splitlines()]
            focus = next(flow for flow in records if flow["seed"] == 7001
                         and flow["protocol"] == "meshecho-rac"
                         and flow["flow_id"] == 1)
            focus["source_action"] = "R"
            flows.write_text("".join(json.dumps(flow) + "\n" for flow in records),
                             encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "corridor action is invalid"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_corridor_exposure_on_undelivered_flow(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = [json.loads(line) for line in flows.read_text(encoding="utf-8").splitlines()]
            focus = {flow["flow_id"]: flow for flow in records
                     if flow["seed"] == 7001 and flow["protocol"] == "meshecho-rac"}
            for field in ("ack_by_deadline", "delivery_by_deadline"):
                focus[1][field] = False
                focus[40][field] = True
            flows.write_text("".join(json.dumps(flow) + "\n" for flow in records),
                             encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "corridor action is invalid"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_corridor_exposure_after_flow_deadline(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = [json.loads(line) for line in actions.read_text(encoding="utf-8").splitlines()]
            records[0]["time"] = 31.0
            actions.write_text("".join(json.dumps(event) + "\n" for event in records),
                               encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(actions.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "corridor action is invalid"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_rac_holdout_rejects_unpaired_application_trace(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_rac_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[1]["scheduled_trace_sha256"] = "different-trace"
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "paired trace or config"):
                validate_rac_development_manifest(manifest, source_hashes("rac"))

    def test_only_frozen_rac_holdout_comparisons_are_confirmatory(self) -> None:
        self.assertTrue(confirmatory_comparison_eligible(
            "rac-holdout", "recurring_fading", "meshecho-rac", "meshecho-rac-fr",
        ))
        self.assertTrue(confirmatory_comparison_eligible(
            "rac-holdout", "recurring_fading", "meshecho-rac", "meshecho-rac-repeat",
        ))
        self.assertFalse(confirmatory_comparison_eligible(
            "rac-development", "recurring_fading", "meshecho-rac", "meshecho-rac-fr",
        ))

    def test_rac_custom_cli_runs_only_non_evaluable_seed_7000(self) -> None:
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "rac-smoke"
            with patch.dict(
                "tools.run_sr_experiment.SR_CASES",
                {"recurring_fading": self.tiny_case()},
            ):
                main([
                    "--suite", "rac", "--split", "custom", "--seed", "7000",
                    "--out-prefix", str(prefix),
                ])
            manifest = json.loads(Path(f"{prefix}.manifest.json").read_text(encoding="utf-8"))
            with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
                paired = list(csv.DictReader(handle))

        self.assertEqual(manifest["seeds"], [7000])
        self.assertEqual(manifest["protocols"], list(RAC_PROTOCOLS))
        self.assertEqual(manifest["seed_split"], "custom")
        self.assertFalse(manifest["rac_joint_primary_gate"])
        self.assertFalse(manifest["rac_exposure_gate"])
        self.assertTrue(all(row["gate_evaluable"] == "False" for row in paired))

    def test_rac_manifest_distinguishes_marker_hops_from_offpath_relay_tx(self) -> None:
        bundle = run_matrix(self.tiny_case(), RAC_PROTOCOLS, (7000,), split="custom")
        with TemporaryDirectory() as directory:
            paths = write_artifacts(Path(directory) / "rac-smoke", bundle)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

        self.assertIn("including on-path forwards", manifest["rac_tx_count_interpretation"])
        self.assertIn("physical off-path relay starts", manifest["rac_tx_count_interpretation"])

    def test_rac_requires_positive_application_deadline(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive application deadline"):
            run_one_sr(self.tiny_case(), "meshecho-rac", 7, deadline_s=0.0)

    def test_rac_run_reports_corridor_exposure_from_action_log(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-rac", seed=7)

        self.assertEqual(
            run.row["rac_corridor_eligible"],
            sum(event.get("event") == "rac_corridor_eligible"
                for event in run.actions),
        )

    def test_rac_flow_log_identifies_f_and_r_source_actions(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-rac", seed=7)
        decisions = {
            event["flow_id"]: event["action"] for event in run.actions
            if event.get("event") == "decision"
        }

        self.assertTrue(decisions)
        self.assertEqual(
            {flow["flow_id"]: flow["source_action"] for flow in run.flows},
            decisions,
        )

    def test_rac_run_reports_ack_continuation_and_source_acceptance(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-rac", seed=7)

        for field, event_name in (
            ("rac_cancellations", "rac_cancel"),
            ("rac_repair_tx_events", "rac_repair_tx"),
            ("rac_repeat_tx_events", "rac_repeat_tx"),
        ):
            self.assertEqual(run.row[field], sum(
                event.get("event") == event_name for event in run.actions
            ))
        self.assertEqual(run.row["rac_source_ack_accepted"], sum(
            event.get("event") == "rac_source_ack_rx" and event.get("accepted")
            for event in run.actions
        ))

    def test_rac_flow_log_records_the_accepted_f_ack_stage(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-rac", seed=7)
        accepted = {
            event["flow_id"]: event["repair_index"] for event in run.actions
            if event.get("event") == "rac_source_ack_rx" and event.get("accepted")
        }
        stages = {255: "initial", 0: "repair", 1: "repeat"}

        self.assertTrue(accepted)
        for flow in run.flows:
            if flow["source_action"] != "F":
                continue
            marker = accepted.get(flow["flow_id"])
            self.assertEqual(flow["f_ack_repair_index"], marker)
            expected_stage = (
                stages[marker] if marker is not None else
                "destination_only" if flow["delivery_by_deadline"] else "not_delivered"
            )
            self.assertEqual(flow["f_ack_stage"], expected_stage)

    def test_clar_run_reconciles_action_counts_and_f_ack_stage(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-clar", seed=7)
        counted_events = {
            "clar_candidate_eligible": "clar_candidate_eligible",
            "clar_cancellations": "clar_cancel",
            "clar_done_tx_events": "clar_done_tx",
            "clar_done_rx_events": "clar_done_rx",
            "clar_repair_tx_events": "clar_repair_tx",
            "clar_repeat_tx_events": "clar_repeat_tx",
        }

        for metric, name in counted_events.items():
            self.assertEqual(run.row[metric], sum(
                event.get("event") == name for event in run.actions
            ), metric)
        self.assertEqual(run.row["clar_done_cancellations"], sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") == "source-done" for event in run.actions
        ))
        self.assertEqual(run.row["clar_continuation_cancellations"], sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") in {"ack-continuation", "ack-continuation-repeat"}
            for event in run.actions
        ))
        accepted = {
            event["flow_id"]: event["repair_index"]
            for event in run.actions
            if event.get("event") == "clar_source_ack_rx" and event.get("accepted")
        }
        self.assertEqual(run.row["clar_source_ack_accepted"], len(accepted))
        self.assertEqual(run.row["clar_done_tx_events"], run.row["windowed_done_tx"])
        stages = {255: "initial", 0: "repair", 1: "repeat"}
        for flow in run.flows:
            if flow["source_action"] != "F":
                continue
            marker = accepted.get(flow["flow_id"])
            self.assertEqual(flow["f_ack_repair_index"], marker)
            self.assertEqual(flow["f_ack_stage"], (
                stages[marker] if marker is not None else
                "destination_only" if flow["delivery_by_deadline"] else "not_delivered"
            ))

    def test_clar_joint_gate_requires_gain_and_airtime_against_both_primary_controls(self) -> None:
        rows = []
        for seed in seeds_for_split("clar-development"):
            for protocol, ack_pdr in (
                ("meshecho-clar", 0.9),
                ("meshecho-clar-nocancel", 0.9),
                ("meshecho-clar-repeat", 0.7),
                ("meshecho-clar-fr", 0.7),
            ):
                rows.append({
                    "case": "recurring_fading", "case_config_sha256": "fixed-case",
                    "seed": seed, "seed_split": "clar-development", "protocol": protocol,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40, "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr, "destination_pdr_deadline": 0.9,
                    "whole_network_tx_airtime_s": 1.0,
                })

        comparisons = summarize_paired(rows, CLAR_PROTOCOLS[0], CLAR_PROTOCOLS[1:])
        self.assertTrue(all(item["clar_joint_primary_gate"] for item in comparisons))
        self.assertEqual({item["comparator"] for item in comparisons},
                         set(CLAR_PROTOCOLS[1:]))

        for row in rows:
            if row["protocol"] == "meshecho-clar-repeat":
                row["ack_pdr_deadline"] = 0.9
        comparisons = summarize_paired(rows, CLAR_PROTOCOLS[0], CLAR_PROTOCOLS[1:])
        self.assertTrue(next(item for item in comparisons
                             if item["comparator"] == "meshecho-clar-fr")
                        ["reliability_cost_gate"])
        self.assertTrue(all(not item["clar_joint_primary_gate"]
                            for item in comparisons))

    def test_clar_custom_smoke_labels_four_arms_and_cannot_pass_any_gate(self) -> None:
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "clar-smoke"
            with patch.dict(
                "tools.run_sr_experiment.SR_CASES",
                {"recurring_fading": self.tiny_case()},
            ):
                main([
                    "--suite", "clar", "--split", "custom", "--seed", "8000",
                    "--out-prefix", str(prefix),
                ])
            manifest = json.loads(Path(f"{prefix}.manifest.json").read_text(
                encoding="utf-8"
            ))
            with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
                paired = list(csv.DictReader(handle))

        self.assertEqual(manifest["seeds"], [8000])
        self.assertEqual(manifest["protocols"], list(CLAR_PROTOCOLS))
        self.assertEqual(manifest["seed_split"], "custom")
        self.assertIn("docs/research/meshecho_clar_design.md", manifest["source_sha256"])
        self.assertFalse(manifest["clar_joint_primary_gate"])
        self.assertFalse(manifest["clar_exposure_gate"])
        self.assertEqual({item["comparator"] for item in paired}, set(CLAR_PROTOCOLS[1:]))
        self.assertTrue(all(item["gate_evaluable"] == "False" for item in paired))

    def test_clar_holdout_requires_development_manifest_before_simulation(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "CLAR holdout requires"):
                run_matrix(
                    SR_CASES["recurring_fading"], CLAR_PROTOCOLS,
                    seeds_for_split("clar-holdout"), split="clar-holdout",
                )
            simulate.assert_not_called()

    def test_clar_holdout_rejects_gate_markers_without_hashed_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "clar-dev.manifest.json"
            manifest_path.write_text(json.dumps({
                "case": asdict(SR_CASES["recurring_fading"]),
                "protocols": list(CLAR_PROTOCOLS),
                "seeds": list(seeds_for_split("clar-development")),
                "seed_split": "clar-development",
                "application_deadline_s": 30.0,
                "source_sha256": source_hashes("clar"),
                "clar_joint_primary_gate": True,
                "clar_exposure_gate": True,
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "artifact hashes"):
                validate_clar_development_manifest(manifest_path, source_hashes("clar"))

    def test_clar_holdout_accepts_complete_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)

            validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_accepts_source_done_repeat_cancellation(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            repeat_row = next(row for row in rows if row["seed"] == "8001"
                              and row["protocol"] == "meshecho-clar-repeat")
            repeat_row["clar_cancellations"] = str(int(repeat_row["clar_cancellations"]) + 1)
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            with actions.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "case": "recurring_fading", "protocol": "meshecho-clar-repeat",
                    "seed": 8001, "seed_split": "clar-development", "flow_id": 1,
                    "event": "clar_cancel", "time": 2.2, "src": 0, "dst": 3,
                    "receiver": 1, "reason": "source-done-repeat",
                }) + "\n")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            for key, path in (("runs", runs), ("actions", actions)):
                metadata["artifact_sha256"][key] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_accepts_queued_done_after_tx_cost_window(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            focus_row = next(row for row in rows if row["seed"] == "8001"
                             and row["protocol"] == "meshecho-clar")
            for field, amount in (
                ("windowed_done_tx", 1), ("windowed_done_bytes", 10),
                ("windowed_control_tx", 1), ("windowed_control_bytes", 10),
            ):
                focus_row[field] = str(int(focus_row[field]) - amount)
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            events = [json.loads(line) for line in actions.read_text(encoding="utf-8").splitlines()]
            queued_done = next(event for event in events
                               if event["seed"] == 8001
                               and event["protocol"] == "meshecho-clar"
                               and event["event"] == "clar_done_tx")
            queued_done["time"] = 631.0
            queued_done["end"] = 631.041216
            actions.write_text("".join(json.dumps(event) + "\n" for event in events),
                               encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            for key, path in (("runs", runs), ("actions", actions)):
                metadata["artifact_sha256"][key] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_missing_policy_row_even_with_valid_file_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows[1:])
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            metadata["runs"] -= 1
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "four policy rows"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_incomplete_flow_denominator_after_rehash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = flows.read_text(encoding="utf-8").splitlines()
            flows.write_text("\n".join(records[1:]) + "\n", encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "flow evidence"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_exposure_not_backed_by_action_log(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = [json.loads(line) for line in actions.read_text(encoding="utf-8").splitlines()]
            removed = next(index for index, event in enumerate(records)
                           if event.get("protocol") == "meshecho-clar"
                           and event.get("event") == "clar_candidate_eligible")
            records.pop(removed)
            actions.write_text("".join(json.dumps(event) + "\n" for event in records),
                               encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(
                actions.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exposure differs from action log"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_recomputes_paired_bounds_after_rehash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            paired = Path(str(manifest).replace(".manifest.json", ".paired.csv"))
            with paired.open(newline="", encoding="utf-8") as handle:
                comparisons = list(csv.DictReader(handle))
            comparisons[0]["relative_airtime_ci95_high"] = "0.09"
            with paired.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
                writer.writeheader()
                writer.writerows(comparisons)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["paired"] = hashlib.sha256(
                paired.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "paired evidence differs from runs"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_f_ack_stage_not_backed_by_acceptance(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = [json.loads(line) for line in flows.read_text(encoding="utf-8").splitlines()]
            flow = next(item for item in records if item["seed"] == 8001
                        and item["protocol"] == "meshecho-clar" and item["flow_id"] == 1)
            flow["f_ack_repair_index"] = 0
            flow["f_ack_stage"] = "repair"
            flows.write_text("".join(json.dumps(item) + "\n" for item in records),
                             encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "F ACK stage"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_validates_nocancel_candidate_identity_too(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = [json.loads(line) for line in actions.read_text(encoding="utf-8").splitlines()]
            event = next(item for item in records
                         if item.get("protocol") == "meshecho-clar-nocancel"
                         and item.get("event") == "clar_candidate_eligible")
            event["candidate"] = event["next_hop"]
            actions.write_text("".join(json.dumps(item) + "\n" for item in records),
                               encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(
                actions.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "candidate action is invalid"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_only_frozen_clar_primary_holdout_comparisons_are_confirmatory(self) -> None:
        for comparator in ("meshecho-clar-repeat", "meshecho-clar-fr"):
            self.assertTrue(confirmatory_comparison_eligible(
                "clar-holdout", "recurring_fading", "meshecho-clar", comparator,
            ))
        self.assertFalse(confirmatory_comparison_eligible(
            "clar-holdout", "recurring_fading", "meshecho-clar",
            "meshecho-clar-nocancel",
        ))
        self.assertFalse(confirmatory_comparison_eligible(
            "clar-development", "recurring_fading", "meshecho-clar",
            "meshecho-clar-fr",
        ))

    def test_clar_holdout_starts_only_after_verified_passing_development(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            with patch(
                "tools.run_sr_experiment.run_one_sr",
                side_effect=RuntimeError("simulation would start"),
            ) as simulate:
                with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                    run_matrix(
                        SR_CASES["recurring_fading"], CLAR_PROTOCOLS,
                        seeds_for_split("clar-holdout"), split="clar-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_called_once()

    def test_clar_holdout_rejects_exposure_confined_to_nine_seeds(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(
                directory, exposure_seed_count=9, exposures_per_seed=3,
            )

            with self.assertRaisesRegex(ValueError, "candidate exposure is insufficient"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_failure_against_repeat(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory, repeat_acked=4)

            with self.assertRaisesRegex(ValueError, "joint primary gate did not pass"):
                validate_clar_development_manifest(manifest, source_hashes("clar"))

    def test_clar_holdout_rejects_source_change_before_simulation(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_clar_development_manifest(directory)
            changed_source = dict(source_hashes("clar"))
            changed_source["lora_mesh_sim.py"] = "0" * 64

            with patch("tools.run_sr_experiment.source_hashes", return_value=changed_source), patch(
                "tools.run_sr_experiment.run_one_sr"
            ) as simulate:
                with self.assertRaisesRegex(ValueError, "source hash differs"):
                    run_matrix(
                        SR_CASES["recurring_fading"], CLAR_PROTOCOLS,
                        seeds_for_split("clar-holdout"), split="clar-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_development_rejects_incomplete_policy_matrix_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "full DPA policy suite"):
                run_matrix(
                    SR_CASES["recurring_fading"], ("meshecho-dpa",),
                    seeds_for_split("dpa-development"), split="dpa-development",
                )
            simulate.assert_not_called()

    def test_dpa_development_requires_frozen_recurring_fading_case(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "frozen recurring_fading case"):
                run_matrix(
                    self.tiny_case(),
                    ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
                    seeds_for_split("dpa-development"), split="dpa-development",
                )
            simulate.assert_not_called()

    def test_dpa_development_requires_frozen_thirty_second_deadline(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "30-second deadline"):
                run_matrix(
                    SR_CASES["recurring_fading"],
                    ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
                    seeds_for_split("dpa-development"), deadline_s=31.0,
                    split="dpa-development",
                )
            simulate.assert_not_called()

    def test_custom_dpa_smoke_cannot_consume_a_holdout_seed(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "dpa-holdout"):
                run_matrix(
                    self.tiny_case(), ("meshecho-dpa",), (4001,), split="custom",
                )
            simulate.assert_not_called()

    def test_dpa_joint_gate_requires_both_primary_controls(self) -> None:
        rows = []
        outcomes = {
            "meshecho-dpa": 0.8,
            "meshecho-dpa-fr": 0.7,
            "meshecho-dpa-repeat": 0.8,
        }
        for seed in range(6001, 6021):
            for protocol, ack_pdr in outcomes.items():
                rows.append({
                    "case": "recurring_fading",
                    "case_config_sha256": "fixed-case",
                    "seed": seed,
                    "protocol": protocol,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 40,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": ack_pdr,
                    "destination_pdr_deadline": 0.9,
                    "whole_network_tx_airtime_s": 1.0,
                })

        comparisons = summarize_paired(
            rows, "meshecho-dpa", ("meshecho-dpa-fr", "meshecho-dpa-repeat")
        )

        self.assertTrue(comparisons[0]["reliability_cost_gate"])
        self.assertFalse(comparisons[1]["reliability_cost_gate"])
        self.assertTrue(all(not item["dpa_joint_primary_gate"] for item in comparisons))

    def test_dpa_run_reports_actual_second_path_opportunities(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-dpa", seed=7)

        self.assertEqual(
            run.row["dpa_second_path_opportunities"],
            sum(event.get("event") == "dpa_second_path" for event in run.actions),
        )

    def test_dpa_requires_positive_application_deadline(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive application deadline"):
            run_one_sr(self.tiny_case(), "meshecho-dpa", 7, deadline_s=0.0)

    def test_dpa_holdout_requires_development_manifest_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "development manifest"):
                run_matrix(
                    SR_CASES["recurring_fading"],
                    ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
                    seeds_for_split("dpa-holdout"), split="dpa-holdout",
                )
            simulate.assert_not_called()

    def test_dpa_source_freeze_includes_its_written_design(self) -> None:
        hashes = source_hashes("dpa")

        self.assertEqual(
            len(hashes["docs/research/meshecho_dpa_design.md"]), 64
        )

    def test_dpa_matrix_records_its_own_design_hash(self) -> None:
        bundle = run_matrix(
            self.tiny_case(),
            ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
            (7,), split="custom",
        )

        self.assertEqual(bundle.source_sha256, source_hashes("dpa"))

    def test_dpa_holdout_rejects_changed_development_source_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "dpa-dev.manifest.json"
            manifest.write_text(json.dumps({"source_sha256": {}}), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "source hash"):
                    run_matrix(
                        SR_CASES["recurring_fading"],
                        ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_rejects_noncanonical_development_configuration(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = Path(directory) / "dpa-dev.manifest.json"
            manifest.write_text(json.dumps({
                "source_sha256": source_hashes("dpa"),
                "case": asdict(self.tiny_case()),
                "protocols": [
                    "meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"
                ],
                "seeds": list(seeds_for_split("dpa-development")),
                "seed_split": "dpa-development",
                "application_deadline_s": 30.0,
            }), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "frozen configuration"):
                    run_matrix(
                        SR_CASES["recurring_fading"],
                        ("meshecho-dpa", "meshecho-dpa-fr", "meshecho-dpa-repeat"),
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_rejects_changed_development_artifact_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_rejects_missing_policy_row_even_with_valid_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows = [row for row in rows if not (
                row["seed"] == "6001" and row["protocol"] == "meshecho-dpa-repeat"
            )]
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            metadata["runs"] = len(rows)
            manifest.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "three protocol rows per seed"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_rejects_changed_run_case_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            runs = Path(str(manifest).replace(".manifest.json", ".runs.csv"))
            with runs.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["case_config_sha256"] = "0" * 64
            with runs.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["runs"] = hashlib.sha256(runs.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "frozen case config"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_requires_opportunities_across_ten_seeds(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(
                directory, opportunity_seed_count=9, opportunities_per_seed=3,
            )
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "second-path exposure"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_rejects_exposure_not_backed_by_action_log(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            actions = Path(str(manifest).replace(".manifest.json", ".actions.jsonl"))
            records = [json.loads(line) for line in actions.read_text(encoding="utf-8").splitlines()]
            removed = False
            retained = []
            for record in records:
                if record["protocol"] == "meshecho-dpa" and not removed:
                    removed = True
                else:
                    retained.append(record)
            actions.write_text(
                "".join(json.dumps(record) + "\n" for record in retained),
                encoding="utf-8",
            )
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["actions"] = hashlib.sha256(
                actions.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "exposure differs from action log"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_recomputes_paired_result_before_running(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            paired = Path(str(manifest).replace(".manifest.json", ".paired.csv"))
            with paired.open(newline="", encoding="utf-8") as handle:
                comparisons = list(csv.DictReader(handle))
            comparisons[0]["ack_pdr_ci95_low"] = "0.9"
            with paired.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
                writer.writeheader()
                writer.writerows(comparisons)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["paired"] = hashlib.sha256(
                paired.read_bytes()
            ).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "paired evidence differs from runs"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_holdout_requires_both_development_primary_gates(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(
                directory, repeat_ack=0.9,
            )
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "joint primary gate"):
                    run_matrix(
                        SR_CASES["recurring_fading"], DPA_PROTOCOLS,
                        seeds_for_split("dpa-holdout"), split="dpa-holdout",
                        development_manifest=manifest,
                    )
                simulate.assert_not_called()

    def test_dpa_custom_smoke_accepts_explicit_seed_6000(self) -> None:
        args = parse_args([
            "--suite", "dpa", "--split", "custom", "--seed", "6000",
        ])

        self.assertEqual(args.seeds, (6000,))
        self.assertEqual(args.protocols, DPA_PROTOCOLS)

    def test_dpa_custom_cli_runs_only_the_requested_seed(self) -> None:
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "dpa-smoke"
            with patch.dict(
                "tools.run_sr_experiment.SR_CASES",
                {"recurring_fading": self.tiny_case()},
            ):
                main([
                    "--suite", "dpa", "--split", "custom", "--seed", "6000",
                    "--out-prefix", str(prefix),
                ])
            manifest = json.loads(Path(f"{prefix}.manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["seeds"], [6000])
        self.assertEqual(manifest["protocols"], list(DPA_PROTOCOLS))
        self.assertEqual(manifest["seed_split"], "custom")

    def test_dpa_manifest_reports_joint_primary_gate(self) -> None:
        bundle = run_matrix(self.tiny_case(), DPA_PROTOCOLS, (7,), split="custom")
        with TemporaryDirectory() as directory:
            paths = write_artifacts(Path(directory) / "dpa-smoke", bundle)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

        self.assertFalse(manifest["dpa_joint_primary_gate"])

    def test_dpa_holdout_accepts_complete_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)

            validate_dpa_development_manifest(manifest, source_hashes("dpa"))

    def test_dpa_holdout_rejects_incomplete_flow_log_even_with_valid_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            flows = Path(str(manifest).replace(".manifest.json", ".flows.jsonl"))
            records = flows.read_text(encoding="utf-8").splitlines()
            flows.write_text("\n".join(records[1:]) + "\n", encoding="utf-8")
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["artifact_sha256"]["flows"] = hashlib.sha256(flows.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "flow evidence"):
                validate_dpa_development_manifest(manifest, source_hashes("dpa"))

    def test_dpa_holdout_rejects_false_manifest_gate_marker(self) -> None:
        with TemporaryDirectory() as directory:
            manifest = self.synthetic_dpa_development_manifest(directory)
            metadata = json.loads(manifest.read_text(encoding="utf-8"))
            metadata["dpa_joint_primary_gate"] = False
            manifest.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "manifest joint primary gate"):
                validate_dpa_development_manifest(manifest, source_hashes("dpa"))

    def test_lpr_run_reports_repair_exposure_and_ack_committed_bypasses(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-lpr", seed=7)
        decisions = [event for event in run.actions
                     if event.get("event") == "decision" and event.get("action") == "P"]
        commits = [event for event in run.actions
                   if event.get("event") == "commit"]

        self.assertEqual(run.row["repair_decisions"], len(decisions))
        self.assertEqual(
            run.row["ack_confirmed_inserted_repairs"],
            sum(event.get("action") == "P" and event.get("replaced_confirmed_path")
                for event in commits),
        )
        self.assertEqual(
            run.row["route_switches"],
            sum(bool(event.get("replaced_confirmed_path")) for event in commits),
        )
        self.assertGreaterEqual(run.row["collision_failures"], 0)

    def test_lpr_development_split_rejects_incomplete_policy_matrix(self) -> None:
        with self.assertRaisesRegex(ValueError, "full LPR policy suite"):
            run_matrix(
                self.tiny_case(),
                ("meshecho-lpr",),
                seeds_for_split("lpr-development"),
                split="lpr-development",
            )

    def test_lpr_development_rejects_noncanonical_case_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "frozen recurring_fading case"):
                run_matrix(
                    self.tiny_case(), LPR_PROTOCOLS,
                    seeds_for_split("lpr-development"), split="lpr-development",
                )
            simulate.assert_not_called()

    def test_lpr_development_rejects_changed_deadline_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "30-second deadline"):
                run_matrix(
                    SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                    seeds_for_split("lpr-development"),
                    deadline_s=31.0, split="lpr-development",
                )
            simulate.assert_not_called()

    def test_generic_holdout_cannot_run_lpr_policies(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "lpr-holdout"):
                run_matrix(
                    SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                    seeds_for_split("holdout"), split="holdout",
                )
            simulate.assert_not_called()

    def test_custom_lpr_smoke_cannot_consume_a_holdout_seed(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "lpr-holdout"):
                run_matrix(
                    self.tiny_case(), ("meshecho-lpr",), (4001,), split="custom",
                )
            simulate.assert_not_called()

    def test_lpr_holdout_requires_development_manifest_before_running(self) -> None:
        with patch("tools.run_sr_experiment.run_one_sr") as simulate:
            with self.assertRaisesRegex(ValueError, "development manifest"):
                run_matrix(
                    SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                    seeds_for_split("lpr-holdout"), split="lpr-holdout",
                )
            simulate.assert_not_called()

    def test_lpr_holdout_rejects_changed_development_source_hash(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dev.manifest.json"
            hashes = source_hashes()
            hashes["lora_mesh_sim.py"] = "0" * 64
            path.write_text(json.dumps({
                "case": asdict(SR_CASES["recurring_fading"]),
                "protocols": list(LPR_PROTOCOLS),
                "seeds": list(seeds_for_split("lpr-development")),
                "seed_split": "lpr-development",
                "application_deadline_s": 30.0,
                "source_sha256": hashes,
            }), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "source hash"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_rejects_noncanonical_development_case(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dev.manifest.json"
            path.write_text(json.dumps({
                "case": asdict(self.tiny_case()),
                "protocols": list(LPR_PROTOCOLS),
                "seeds": list(seeds_for_split("lpr-development")),
                "seed_split": "lpr-development",
                "application_deadline_s": 30.0,
                "source_sha256": source_hashes(),
            }), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "frozen configuration"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_requires_hash_checked_development_artifacts(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "dev.manifest.json"
            path.write_text(json.dumps({
                "case": asdict(SR_CASES["recurring_fading"]),
                "protocols": list(LPR_PROTOCOLS),
                "seeds": list(seeds_for_split("lpr-development")),
                "seed_split": "lpr-development",
                "application_deadline_s": 30.0,
                "source_sha256": source_hashes(),
            }), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "artifact"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_rejects_missing_policy_row_even_with_valid_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_lpr_development_manifest(directory)
            runs_path = Path(str(manifest_path).replace(".manifest.json", ".runs.csv"))
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            missing = next(row for row in rows if row["seed"] == "5001"
                           and row["protocol"] == "meshecho-lpr-periodic")
            missing["protocol"] = "meshecho-lpr"
            with runs_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["runs"] = hashlib.sha256(
                runs_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "five protocol"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=manifest_path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_rejects_changed_run_case_hash_with_valid_file_hash(self) -> None:
        with TemporaryDirectory() as directory:
            manifest_path = self.synthetic_lpr_development_manifest(directory)
            runs_path = Path(str(manifest_path).replace(".manifest.json", ".runs.csv"))
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            rows[0]["case_config_sha256"] = "0" * 64
            with runs_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["runs"] = hashlib.sha256(
                runs_path.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "frozen case config"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=manifest_path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_rejects_forged_paired_fields_with_valid_file_hash(self) -> None:
        for field, forged_value in (
            ("ack_pdr_ci95_low", "0.8"),
            ("lpr_joint_primary_gate", "False"),
        ):
            with self.subTest(field=field), TemporaryDirectory() as directory:
                manifest_path = self.synthetic_lpr_development_manifest(directory)
                paired_path = Path(str(manifest_path).replace(".manifest.json", ".paired.csv"))
                with paired_path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
                rows[0][field] = forged_value
                with paired_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["artifact_sha256"]["paired"] = hashlib.sha256(
                    paired_path.read_bytes()
                ).hexdigest()
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                    with self.assertRaisesRegex(ValueError, "paired evidence differs"):
                        run_matrix(
                            SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                            seeds_for_split("lpr-holdout"), split="lpr-holdout",
                            development_manifest=manifest_path,
                        )
                    simulate.assert_not_called()

    def test_lpr_holdout_requires_both_primary_development_gates(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.synthetic_lpr_development_manifest(
                directory, trigger_f_ack=0.9,
            )
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "joint primary gate"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_rejects_underexposed_repair_mechanism(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.synthetic_lpr_development_manifest(
                directory, repair_decisions_per_seed=0,
                inserted_repairs_per_seed=0,
            )
            with patch("tools.run_sr_experiment.run_one_sr") as simulate:
                with self.assertRaisesRegex(ValueError, "repair exposure"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_not_called()

    def test_lpr_holdout_accepts_verified_passing_development_evidence(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.synthetic_lpr_development_manifest(directory)
            with patch(
                "tools.run_sr_experiment.run_one_sr",
                side_effect=RuntimeError("simulation would start"),
            ) as simulate:
                with self.assertRaisesRegex(RuntimeError, "simulation would start"):
                    run_matrix(
                        SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                        seeds_for_split("lpr-holdout"), split="lpr-holdout",
                        development_manifest=path,
                    )
                simulate.assert_called_once()

    def test_lpr_joint_gate_requires_both_primary_comparisons(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.synthetic_lpr_development_manifest(
                directory, trigger_f_ack=0.9,
            )
            runs_path = Path(str(path).replace(".manifest.json", ".runs.csv"))
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        comparisons = summarize_paired(rows, LPR_PROTOCOLS[0], LPR_PROTOCOLS[1:])

        self.assertTrue(next(item for item in comparisons
                             if item["comparator"] == "meshecho-lpr-fr")["reliability_cost_gate"])
        self.assertFalse(next(item for item in comparisons
                              if item["comparator"] == "meshecho-lpr-trigger-f")["reliability_cost_gate"])
        self.assertTrue(all(not item["lpr_joint_primary_gate"] for item in comparisons))

    def test_lpr_manifest_reports_joint_primary_gate(self) -> None:
        with TemporaryDirectory() as directory:
            evidence = self.synthetic_lpr_development_manifest(directory)
            runs_path = Path(str(evidence).replace(".manifest.json", ".runs.csv"))
            with runs_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row["scheduled_unicast_flows"] = int(row["scheduled_unicast_flows"])
            comparisons = summarize_paired(rows, LPR_PROTOCOLS[0], LPR_PROTOCOLS[1:])
            bundle = SrExperiment(
                SR_CASES["recurring_fading"], LPR_PROTOCOLS,
                seeds_for_split("lpr-development"), 30.0,
                rows, [], [], comparisons, "lpr-development", source_hashes(),
            )
            paths = write_artifacts(Path(directory) / "joint-report", bundle)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

        self.assertTrue(manifest["lpr_joint_primary_gate"])

    def test_sr_actions_are_exported_and_legacy_actions_are_empty(self) -> None:
        sr = run_one_sr(self.tiny_case(), "meshecho-sr", 7)
        legacy = run_one_sr(self.tiny_case(), "meshtastic", 7)
        decisions = [
            event for event in sr.actions if event.get("event") == "decision"
        ]

        self.assertEqual(sr.row["action_decisions"], len(decisions))
        self.assertEqual(
            {event["flow_id"] for event in decisions},
            {flow["flow_id"] for flow in sr.flows},
        )
        self.assertTrue(
            all(
                {"time", "src", "dst", "action", "reason"} <= event.keys()
                for event in decisions
            )
        )
        self.assertEqual(legacy.actions, [])

    def test_mag_requires_positive_common_deadline(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive application deadline"):
            run_one_sr(self.tiny_case(), "meshecho-mag", 7, deadline_s=0.0)

    def test_only_frozen_mag_primary_controls_are_confirmatory(self) -> None:
        self.assertEqual(MAG_PROTOCOLS[0], "meshecho-mag")
        for comparator in ("meshecho-mag-fr", "meshecho-mag-trigger-f"):
            self.assertTrue(confirmatory_comparison_eligible(
                "holdout", "recurring_fading", "meshecho-mag", comparator,
            ))
        self.assertFalse(confirmatory_comparison_eligible(
            "development", "recurring_fading", "meshecho-mag", "meshecho-mag-fr",
        ))
        self.assertFalse(confirmatory_comparison_eligible(
            "holdout", "recurring_fading", "meshecho-mag", "meshecho-mag-periodic",
        ))
        self.assertFalse(confirmatory_comparison_eligible(
            "holdout", "recurring_fading", "meshecho-sr", "meshecho-sr-fr",
        ))

    def test_only_frozen_lpr_primary_controls_are_confirmatory(self) -> None:
        for comparator in ("meshecho-lpr-fr", "meshecho-lpr-trigger-f"):
            self.assertTrue(confirmatory_comparison_eligible(
                "lpr-holdout", "recurring_fading", "meshecho-lpr", comparator,
            ))
        for comparator in ("meshecho-lpr-periodic", "meshecho-lpr-unobserved-edge"):
            self.assertFalse(confirmatory_comparison_eligible(
                "lpr-holdout", "recurring_fading", "meshecho-lpr", comparator,
            ))
        self.assertFalse(confirmatory_comparison_eligible(
            "lpr-development", "recurring_fading", "meshecho-lpr", "meshecho-lpr-fr",
        ))

    def test_only_frozen_dpa_primary_controls_are_confirmatory(self) -> None:
        for comparator in ("meshecho-dpa-fr", "meshecho-dpa-repeat"):
            self.assertTrue(confirmatory_comparison_eligible(
                "dpa-holdout", "recurring_fading", "meshecho-dpa", comparator,
            ))
            self.assertFalse(confirmatory_comparison_eligible(
                "dpa-development", "recurring_fading", "meshecho-dpa", comparator,
            ))
        self.assertFalse(confirmatory_comparison_eligible(
            "dpa-holdout", "recurring_static", "meshecho-dpa", "meshecho-dpa-fr",
        ))

    def test_mag_controls_run_on_identical_seeded_application_traces(self) -> None:
        bundle = run_matrix(self.tiny_case(), MAG_PROTOCOLS, (7, 8))

        self.assertEqual(len(bundle.rows), 8)
        self.assertEqual(len(bundle.comparisons), 3)
        for seed in (7, 8):
            self.assertEqual(len({
                row["scheduled_trace_sha256"]
                for row in bundle.rows if row["seed"] == seed
            }), 1)
        self.assertTrue(all(
            row["action_decisions"] == row["scheduled_unicast_flows"]
            for row in bundle.rows
        ))
        self.assertTrue(all(
            not item["confirmatory_gate_eligible"]
            for item in bundle.comparisons
        ))

    def test_matrix_writes_reproducible_run_flow_and_action_files(self) -> None:
        bundle = run_matrix(
            self.tiny_case(),
            ("meshecho-sr", "meshtastic"),
            (7, 8),
            deadline_s=30.0,
        )

        with TemporaryDirectory() as directory:
            paths = write_artifacts(Path(directory) / "sr-smoke", bundle)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            run_columns = paths["runs"].read_text(encoding="utf-8").splitlines()[0].split(",")
            flow_lines = paths["flows"].read_text(encoding="utf-8").splitlines()
            action_lines = paths["actions"].read_text(encoding="utf-8").splitlines()

        self.assertEqual(manifest["seeds"], [7, 8])
        self.assertEqual(manifest["protocols"], ["meshecho-sr", "meshtastic"])
        self.assertEqual(manifest["seed_split"], "custom")
        self.assertEqual(manifest["tx_cost_window"]["last_tx_start_s"], 38.0)
        self.assertTrue(
            manifest["tx_cost_window"]["includes_post_flow_deadline_tx"]
        )
        self.assertTrue(
            manifest["tx_cost_window"]["windowed_packet_counts_share_start_cutoff"]
        )
        self.assertEqual(
            manifest["raw_packet_count_fields"],
            ["raw_tx_count", "raw_data_tx", "raw_control_tx", "raw_ack_tx"],
        )
        self.assertTrue({
            "windowed_tx_count", "windowed_patch_tx", "windowed_patch_relay_tx",
            "raw_tx_count", "raw_data_tx",
        } <= set(run_columns))
        self.assertEqual(len(manifest["source_sha256"]["lora_mesh_sim.py"]), 64)
        self.assertEqual(
            len(manifest["source_sha256"]["docs/research/meshecho_lpr_design.md"]),
            64,
        )
        self.assertEqual(manifest["source_sha256"], bundle.source_sha256)
        self.assertEqual(len(bundle.rows), 4)
        self.assertEqual(len(flow_lines), sum(row["scheduled_unicast_flows"] for row in bundle.rows))
        self.assertEqual(len(action_lines), len(bundle.actions))

    def test_artifact_writer_refuses_to_overwrite_prior_evidence(self) -> None:
        bundle = run_matrix(
            self.tiny_case(), ("meshecho-sr", "meshtastic"), (7, 8)
        )
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "frozen-run"
            paths = write_artifacts(prefix, bundle)
            original_manifest = paths["manifest"].read_bytes()

            with self.assertRaises(FileExistsError):
                write_artifacts(prefix, bundle)

            self.assertEqual(paths["manifest"].read_bytes(), original_manifest)

    def test_cli_preflights_existing_output_before_any_matrix_run(self) -> None:
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "lpr-holdout"
            Path(f"{prefix}.runs.csv").write_text("preserve me", encoding="utf-8")
            with patch("tools.run_sr_experiment.run_matrix") as run:
                with self.assertRaises(FileExistsError):
                    main([
                        "--suite", "lpr", "--split", "lpr-holdout",
                        "--out-prefix", str(prefix),
                    ])
                run.assert_not_called()
            self.assertEqual(
                Path(f"{prefix}.runs.csv").read_text(encoding="utf-8"),
                "preserve me",
            )

    def test_manifest_hashes_each_exported_result_file(self) -> None:
        bundle = run_matrix(
            self.tiny_case(), ("meshecho-sr", "meshtastic"), (7, 8)
        )
        with TemporaryDirectory() as directory:
            paths = write_artifacts(Path(directory) / "integrity", bundle)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

            for key in ("runs", "paired", "flows", "actions"):
                self.assertEqual(
                    manifest["artifact_sha256"][key],
                    hashlib.sha256(paths[key].read_bytes()).hexdigest(),
                )

    def test_phase_shift_changes_pair_population_mid_run(self) -> None:
        case = SrCase(
            key="tiny_shift",
            nodes=4,
            area_m=1.0,
            duration_s=20.0,
            rate_per_min=60.0,
            pair_mode="connected-multihop",
            pair_count=1,
            min_graph_hops=1,
            max_graph_hops=1,
            temporal_fading_sigma_db=0.0,
            traffic_pattern="phase-shift",
        )

        run = run_one_sr(case, "meshtastic", 7)
        early_pairs = {
            (flow["src"], flow["dst"])
            for flow in run.flows
            if flow["enqueued_at"] < case.duration_s / 2
        }
        late_pairs = {
            (flow["src"], flow["dst"])
            for flow in run.flows
            if flow["enqueued_at"] >= case.duration_s / 2
        }

        self.assertEqual(len(early_pairs), 1)
        self.assertGreater(len(late_pairs), 1)

    def test_direct_script_exposes_experiment_cli(self) -> None:
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "tools/run_sr_experiment.py", "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--split", completed.stdout)
        self.assertIn("--case", completed.stdout)

    def test_shadow_discovery_count_matches_decision_log(self) -> None:
        case = SrCase(
            key="stable_repeated",
            nodes=2,
            area_m=1.0,
            duration_s=600.0,
            rate_per_min=4.0,
            pair_mode="random",
            pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

        run = run_one_sr(case, "meshecho-sr", 7)
        shadow_decisions = [
            event for event in run.actions
            if event.get("event") == "decision"
            and event.get("action") == "D"
            and event.get("reason") == "aging-confirmed-route"
        ]

        self.assertGreater(len(shadow_decisions), 0)
        self.assertEqual(run.row["shadow_discoveries"], len(shadow_decisions))

    def test_custom_seeds_cannot_be_labeled_as_holdout(self) -> None:
        with self.assertRaisesRegex(ValueError, "holdout seeds"):
            run_matrix(
                self.tiny_case(),
                ("meshecho-sr", "meshtastic"),
                (7, 8),
                split="holdout",
            )

    def test_nondefault_deadline_reaches_sr_protocol_state(self) -> None:
        run = run_one_sr(self.tiny_case(), "meshecho-sr", 7, deadline_s=0.001)

        self.assertEqual(run.row["ack_pdr_deadline"], 0.0)
        self.assertEqual(
            [event for event in run.actions if event.get("event") == "commit"],
            [],
        )

    def test_tx_window_excludes_transmissions_queued_beyond_drain(self) -> None:
        airtime, future_count = observed_tx_airtime(
            [(1.0, 2.0), (37.9, 38.2), (38.1, 39.0)],
            cutoff_s=38.0,
        )

        self.assertAlmostEqual(airtime, 1.3)
        self.assertEqual(future_count, 1)

    def test_windowed_packet_counts_use_the_airtime_start_boundary(self) -> None:
        kinds = ("DATA", "PATCH", "PATCH_RELAY", "RREQ", "RREP", "ACK", "DATA", "ACK")
        starts = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 7.1)
        transmissions = [
            Transmission(
                tx_id=index,
                sender=0,
                packet=Packet(kind, 1, 0, 1, 6, 0.0, "meshecho-lpr"),
                start=start,
                end=start + 1.0,
            )
            for index, (kind, start) in enumerate(zip(kinds, starts), 1)
        ]

        summary = summarize_windowed_transmissions(transmissions, cutoff_s=7.0)

        self.assertEqual(summary["whole_network_tx_airtime_s"], 7.0)
        self.assertEqual(summary["windowed_tx_count"], 7)
        self.assertEqual(summary["windowed_data_tx"], 4)
        self.assertEqual(summary["windowed_control_tx"], 3)
        self.assertEqual(summary["windowed_ack_tx"], 1)
        self.assertEqual(summary["windowed_route_control_tx"], 2)
        self.assertEqual(summary["windowed_patch_tx"], 1)
        self.assertEqual(summary["windowed_patch_relay_tx"], 1)
        self.assertEqual(summary["windowed_repair_tx"], 2)
        self.assertEqual(summary["queued_future_tx_count"], 1)

    def test_windowed_rac_ack_bytes_and_repeats_use_actual_tx_starts(self) -> None:
        markers = (255, 0, 1, 0)
        packets = [
            Packet("ACK", 1, 3, 0, 6, 0.0, "meshecho-rac",
                   path=(0, 1, 3), path_index=1, app_payload=False,
                   repair_index=marker)
            for marker in markers
        ]
        transmissions = [
            Transmission(index, 3, packet, float(index), float(index) + 0.5)
            for index, packet in enumerate(packets, 1)
        ]

        summary = summarize_windowed_transmissions(transmissions, cutoff_s=3.0)

        self.assertEqual(summary["windowed_ack_bytes"],
                         sum(packet.wire_size_bytes(32) for packet in packets[:3]))
        self.assertEqual(summary["windowed_tx_bytes"], summary["windowed_ack_bytes"])
        self.assertEqual(summary["windowed_rac_repair_ack_tx"], 1)
        self.assertEqual(summary["windowed_rac_repeat_ack_tx"], 1)
        self.assertEqual(json.loads(summary["windowed_ack_tx_by_path_index"]), {"1": 3})

    def test_dhr_window_charges_full_rescue_and_ack_packets_at_start(self) -> None:
        packets = [
            Packet("DATA", 1, 0, 3, 6, 0.0, "meshecho-dhr",
                   request_id=1, path=(0, 1, 3), repair_index=1),
            Packet("FLOOD", 2, 0, 3, 6, 0.0, "meshecho-dhr",
                   request_id=2, path=(0,), repair_index=2),
            Packet("ACK", 1, 3, 0, 6, 0.0, "meshecho-dhr",
                   request_id=1, path=(0, 1, 3), path_index=1,
                   app_payload=False, repair_index=1),
            Packet("ACK", 2, 3, 0, 6, 0.0, "meshecho-dhr",
                   request_id=2, path=(0, 1, 3), path_index=1,
                   app_payload=False, repair_index=2),
            Packet("FLOOD", 3, 0, 3, 6, 0.0, "meshecho-dhr",
                   request_id=3, path=(0,), repair_index=2),
        ]
        transmissions = [
            Transmission(index, packet.origin, packet, float(index), float(index) + 0.5)
            for index, packet in enumerate(packets, 1)
        ]

        summary = summarize_windowed_transmissions(transmissions, cutoff_s=4.0)

        self.assertEqual(summary["windowed_dhr_recovery_r_source_tx"], 1)
        self.assertEqual(summary["windowed_dhr_recovery_f_source_tx"], 1)
        self.assertEqual(summary["windowed_dhr_repeat_ack_tx"], 1)
        self.assertEqual(summary["windowed_dhr_flood_ack_tx"], 1)
        self.assertEqual(summary["windowed_tx_bytes"], sum(
            packet.wire_size_bytes(32) for packet in packets[:4]
        ))
        self.assertEqual(summary["whole_network_tx_airtime_s"], 2.0)
        self.assertEqual(summary["queued_future_tx_count"], 1)

    def test_clar_window_charges_done_and_marker_control_bytes_at_actual_tx_start(self) -> None:
        packets = [
            Packet("ACK_DONE", 1, 0, 3, 1, 0.0, "meshecho-clar",
                   request_id=1, app_payload=False),
            Packet("ACK", 1, 3, 0, 6, 0.0, "meshecho-clar",
                   request_id=1, path=(0, 1, 3), path_index=1,
                   app_payload=False, repair_index=255),
            Packet("ACK", 1, 3, 0, 5, 0.0, "meshecho-clar",
                   request_id=1, path=(0, 1, 3), path_index=0,
                   app_payload=False, repair_index=0),
            Packet("ACK", 1, 3, 0, 5, 0.0, "meshecho-clar-repeat",
                   request_id=1, path=(0, 1, 3), path_index=0,
                   app_payload=False, repair_index=1),
            Packet("ACK_DONE", 2, 0, 3, 1, 0.0, "meshecho-clar",
                   request_id=2, app_payload=False),
        ]
        transmissions = [
            Transmission(index, 0, packet, float(index), float(index) + 0.5)
            for index, packet in enumerate(packets, 1)
        ]

        summary = summarize_windowed_transmissions(transmissions, cutoff_s=4.0)

        self.assertEqual(summary["windowed_done_tx"], 1)
        self.assertEqual(summary["windowed_done_bytes"], 10)
        self.assertEqual(summary["windowed_control_tx"], 4)
        self.assertEqual(summary["windowed_control_bytes"], sum(
            packet.wire_size_bytes(32) for packet in packets[:4]
        ))
        self.assertEqual(summary["windowed_clar_initial_ack_tx"], 1)
        self.assertEqual(summary["windowed_clar_repair_ack_tx"], 1)
        self.assertEqual(summary["windowed_clar_repeat_ack_tx"], 1)
        self.assertEqual(summary["queued_future_tx_count"], 1)

    def test_queued_clar_done_keeps_raw_event_but_not_windowed_airtime(self) -> None:
        protocol = build_protocol("meshecho-clar")
        sim = RecordingSimulator(
            [Node(0, 0.0, 0.0, tx_available_at=631.0), Node(3, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="ACK_DONE", flow_id=1, origin=0, final_dst=3,
            ttl=1, created_at=629.0, protocol="meshecho-clar",
            request_id=1, app_payload=False,
        ), delay_s=629.0)
        sim.run(630.0)

        done_events = [event for event in protocol.action_events
                       if event["event"] == "clar_done_tx"]
        windowed = summarize_windowed_transmissions(sim.tx_history, 630.0)
        self.assertEqual(len(done_events), 1)
        self.assertEqual(done_events[0]["time"], 631.0)
        self.assertEqual(windowed["windowed_done_tx"], 0)
        self.assertEqual(windowed["whole_network_tx_airtime_s"], 0.0)
        self.assertEqual(windowed["queued_future_tx_count"], 1)

    def test_run_exports_windowed_counts_without_losing_raw_counters(self) -> None:
        case = SrCase(
            key="queued_load",
            nodes=2,
            area_m=1.0,
            duration_s=2.0,
            rate_per_min=6000.0,
            pair_mode="random",
            pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

        row = run_one_sr(case, "meshtastic", seed=7, deadline_s=0.0).row

        self.assertGreater(row["queued_future_tx_count"], 0)
        self.assertEqual(
            row["raw_tx_count"],
            row["windowed_tx_count"] + row["queued_future_tx_count"],
        )
        self.assertEqual(row["data_tx"], row["raw_data_tx"])
        self.assertEqual(row["control_tx"], row["raw_control_tx"])
        self.assertEqual(row["ack_tx"], row["raw_ack_tx"])
        self.assertLess(row["windowed_data_tx"], row["raw_data_tx"])
        self.assertEqual(
            row["windowed_tx_count"],
            row["windowed_data_tx"] + row["windowed_control_tx"],
        )

    def test_all_sr_policy_variants_share_trace_in_matrix(self) -> None:
        bundle = run_matrix(self.tiny_case(), SR_PROTOCOLS, (7, 8))

        self.assertEqual(len(bundle.rows), 8)
        self.assertEqual(len(bundle.comparisons), 3)
        for seed in (7, 8):
            rows = [row for row in bundle.rows if row["seed"] == seed]
            self.assertEqual(len({row["scheduled_trace_sha256"] for row in rows}), 1)
            self.assertEqual(len({row["scheduled_unicast_flows"] for row in rows}), 1)


if __name__ == "__main__":
    unittest.main()
