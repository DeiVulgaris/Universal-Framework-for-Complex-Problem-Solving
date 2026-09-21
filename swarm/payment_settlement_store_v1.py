#!/usr/bin/env python3
"""UFCPS Level 2 — Payment Settlement Store v1.

Durable, idempotent settlement state machine for economic effects.

Core model
----------

    VERIFIED
       -> SETTLEMENT_PREPARED
       -> SETTLED

A single ``economic_contribution_id`` is the idempotency identity of a
settlement. Repeating ``settle()`` for that contribution must return the
existing settlement instead of creating a second internal economic effect.

Crash model
-----------

A crash may occur after an external executor has accepted the settlement but
before the local ``SETTLED`` event is appended. Recovery therefore retries the
same idempotency key. An external executor can provide true exactly-once
side-effects only when it itself supports durable idempotency. The reference
executor below does so, in-memory for deterministic tests.

Internal guarantee
------------------

The store provides exactly-once *recorded economic effect* for a contribution:
there is at most one SETTLED record for the idempotency key. The materialized
ledger is reconstructed from the durable event history.

This module is reference infrastructure only. It does not call banks,
blockchains, PayPal, or any real payment provider.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from checkpointed_event_store_v1 import CheckpointedEventStore, canonical

SCHEMA_VERSION = "payment-settlement-store-v1"
AUTHOR_ROYALTY_RATE = Decimal("0.00001")  # 0.001%

STATUS_PREPARED = "SETTLEMENT_PREPARED"
STATUS_SETTLED = "SETTLED"
SUPPORTED_RAILS = {"resource_credits", "crypto"}


class SettlementError(ValueError):
    """Raised for invalid settlement transitions or payloads."""


def D(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SettlementError(f"invalid decimal value: {value!r}") from exc


def q8(value: Any) -> Decimal:
    return D(value).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def decimal_to_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: decimal_to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decimal_to_json(v) for v in value]
    return value


@dataclass(frozen=True)
class SettlementRecord:
    contribution_id: str
    settlement_key: str
    reward_id: str
    provider_id: str
    resource_id: str
    rail: str
    gross: Decimal
    author_royalty: Decimal
    protocol_fee: Decimal
    internal_spread: Decimal
    provider_net: Decimal
    status: str
    external_reference: Optional[str]
    created_event_id: str
    settled_event_id: Optional[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return decimal_to_json(asdict(self))


@dataclass(frozen=True)
class SettlementEffect:
    contribution_id: str
    settlement_key: str
    external_reference: str
    provider_id: str
    provider_net: Decimal
    author_royalty: Decimal
    rail: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return decimal_to_json(asdict(self))


class ReferenceIdempotentExecutor:
    """Deterministic external settlement simulator with durable-like memory.

    The executor models a provider API that honors an idempotency key. A crash
    after ``execute`` therefore does not create a second external effect when
    the same key is retried after restart.
    """

    def __init__(self) -> None:
        self._effects: dict[str, SettlementEffect] = {}
        self.calls = 0

    def execute(self, *, idempotency_key: str, payload: Mapping[str, Any]) -> SettlementEffect:
        self.calls += 1
        if idempotency_key in self._effects:
            return self._effects[idempotency_key]

        effect = SettlementEffect(
            contribution_id=str(payload["contribution_id"]),
            settlement_key=idempotency_key,
            external_reference=f"ref-{uuid.uuid4()}",
            provider_id=str(payload["provider_id"]),
            provider_net=q8(payload["provider_net"]),
            author_royalty=q8(payload["author_royalty"]),
            rail=str(payload["rail"]),
            status="executed_reference",
        )
        self._effects[idempotency_key] = effect
        return effect


class PaymentSettlementStore:
    """Crash-safe settlement state machine backed by the UFCPS event store."""

    def __init__(
        self,
        base_path: str | Path,
        *,
        journal_batch_size: int = 1,
        checkpoint_interval: int = 1,
        durable: bool = True,
    ) -> None:
        self.base_path = Path(base_path)
        self.store = CheckpointedEventStore(
            self.base_path,
            journal_batch_size=journal_batch_size,
            checkpoint_interval=checkpoint_interval,
            durable=durable,
        )
        self._settlements: dict[str, SettlementRecord] = {}
        self._hydrate_materialized_state()

    # --------------------------- lifecycle ---------------------------

    def _hydrate_materialized_state(self) -> None:
        snapshot = self.store.checkpoint_snapshot()
        if snapshot is not None and isinstance(snapshot.state, dict):
            self._load_snapshot_state(snapshot.state)
            start_sequence = snapshot.event_count + 1
        else:
            start_sequence = 1

        for event in self.store.events():
            if event.sequence < start_sequence:
                continue
            self._apply_event(event.payload)

    def _snapshot_state(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "settlements": {
                key: record.to_dict() for key, record in sorted(self._settlements.items())
            },
        }

    def _load_snapshot_state(self, state: Mapping[str, Any]) -> None:
        if state.get("schema_version") != SCHEMA_VERSION:
            raise SettlementError("unsupported settlement snapshot schema")
        raw_settlements = state.get("settlements", {})
        if not isinstance(raw_settlements, dict):
            raise SettlementError("invalid settlements snapshot")
        self._settlements.clear()
        for key, raw in raw_settlements.items():
            data = dict(raw)
            self._settlements[str(key)] = SettlementRecord(
                contribution_id=str(data["contribution_id"]),
                settlement_key=str(data["settlement_key"]),
                reward_id=str(data["reward_id"]),
                provider_id=str(data["provider_id"]),
                resource_id=str(data["resource_id"]),
                rail=str(data["rail"]),
                gross=q8(data["gross"]),
                author_royalty=q8(data["author_royalty"]),
                protocol_fee=q8(data["protocol_fee"]),
                internal_spread=q8(data["internal_spread"]),
                provider_net=q8(data["provider_net"]),
                status=str(data["status"]),
                external_reference=(
                    str(data["external_reference"])
                    if data.get("external_reference") is not None
                    else None
                ),
                created_event_id=str(data["created_event_id"]),
                settled_event_id=(
                    str(data["settled_event_id"])
                    if data.get("settled_event_id") is not None
                    else None
                ),
                metadata=dict(data.get("metadata", {})),
            )

    def close(self) -> None:
        self.store.close()

    @property
    def event_count(self) -> int:
        return self.store.event_count

    # ---------------------------- validation ----------------------------

    @staticmethod
    def settlement_key(contribution_id: str) -> str:
        contribution_id = contribution_id.strip()
        if not contribution_id:
            raise SettlementError("contribution_id is required")
        return f"ufcps-settlement:{contribution_id}"

    @staticmethod
    def _validate_amounts(
        *, gross: Decimal, royalty: Decimal, protocol_fee: Decimal, spread: Decimal, provider_net: Decimal
    ) -> None:
        if gross <= 0:
            raise SettlementError("gross must be > 0")
        if royalty < 0 or protocol_fee < 0 or spread < 0 or provider_net < 0:
            raise SettlementError("settlement components cannot be negative")
        expected_net = q8(gross - royalty - protocol_fee - spread)
        if provider_net != expected_net:
            raise SettlementError(
                f"provider_net mismatch: expected {expected_net}, got {provider_net}"
            )
        expected_royalty = q8(gross * AUTHOR_ROYALTY_RATE)
        if royalty != expected_royalty:
            raise SettlementError(
                f"author_royalty mismatch: expected {expected_royalty}, got {royalty}"
            )

    # ---------------------------- transitions ----------------------------

    def _append_event(self, *, event_type: str, payload: Mapping[str, Any], force_checkpoint: bool = False) -> Any:
        return self.store.append(
            event_id=str(uuid.uuid4()),
            payload={"event_type": event_type, **dict(payload)},
            checkpoint_state=self._snapshot_state(),
            force_checkpoint=force_checkpoint,
        )

    def prepare(
        self,
        *,
        contribution_id: str,
        reward_id: str,
        provider_id: str,
        resource_id: str,
        rail: str,
        gross: Any,
        author_royalty: Any,
        protocol_fee: Any = "0",
        internal_spread: Any = "0",
        provider_net: Any = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> SettlementRecord:
        contribution_id = contribution_id.strip()
        reward_id = reward_id.strip()
        provider_id = provider_id.strip()
        resource_id = resource_id.strip()
        if not contribution_id or not reward_id or not provider_id or not resource_id:
            raise SettlementError("contribution_id, reward_id, provider_id and resource_id are required")
        if rail not in SUPPORTED_RAILS:
            raise SettlementError(f"unsupported settlement rail: {rail}")

        key = self.settlement_key(contribution_id)
        existing = self._settlements.get(key)
        if existing is not None:
            fingerprint = (
                existing.reward_id,
                existing.provider_id,
                existing.resource_id,
                existing.rail,
                existing.gross,
                existing.author_royalty,
                existing.protocol_fee,
                existing.internal_spread,
                existing.provider_net,
            )
            requested = (
                reward_id,
                provider_id,
                resource_id,
                rail,
                q8(gross),
                q8(author_royalty),
                q8(protocol_fee),
                q8(internal_spread),
                q8(provider_net if provider_net is not None else D(gross) - D(author_royalty) - D(protocol_fee) - D(internal_spread)),
            )
            if fingerprint != requested:
                raise SettlementError("idempotency key reused with different settlement payload")
            return existing

        gross_d = q8(gross)
        royalty_d = q8(author_royalty)
        protocol_d = q8(protocol_fee)
        spread_d = q8(internal_spread)
        net_d = q8(
            provider_net
            if provider_net is not None
            else gross_d - royalty_d - protocol_d - spread_d
        )
        self._validate_amounts(
            gross=gross_d,
            royalty=royalty_d,
            protocol_fee=protocol_d,
            spread=spread_d,
            provider_net=net_d,
        )

        event = self._append_event(
            event_type="settlement_prepared",
            payload={
                "contribution_id": contribution_id,
                "settlement_key": key,
                "reward_id": reward_id,
                "provider_id": provider_id,
                "resource_id": resource_id,
                "rail": rail,
                "gross": str(gross_d),
                "author_royalty": str(royalty_d),
                "protocol_fee": str(protocol_d),
                "internal_spread": str(spread_d),
                "provider_net": str(net_d),
                "metadata": dict(metadata or {}),
            },
        )
        # _append_event stored the event; apply after event creation so the
        # checkpoint created by the event contains the new materialized state.
        self._apply_event(event.payload, event_id=event.event_id)
        # The original checkpoint may have captured the pre-event state because
        # the event store snapshots before caller-side materialization. Rewrite
        # a checkpoint immediately with post-event state.
        self.store.checkpoint(self._snapshot_state())
        return self._settlements[key]

    def _apply_event(self, payload: Mapping[str, Any], *, event_id: Optional[str] = None) -> None:
        event_type = payload.get("event_type")
        if event_type == "settlement_prepared":
            key = str(payload["settlement_key"])
            existing = self._settlements.get(key)
            if existing is not None:
                return
            self._settlements[key] = SettlementRecord(
                contribution_id=str(payload["contribution_id"]),
                settlement_key=key,
                reward_id=str(payload["reward_id"]),
                provider_id=str(payload["provider_id"]),
                resource_id=str(payload["resource_id"]),
                rail=str(payload["rail"]),
                gross=q8(payload["gross"]),
                author_royalty=q8(payload["author_royalty"]),
                protocol_fee=q8(payload["protocol_fee"]),
                internal_spread=q8(payload["internal_spread"]),
                provider_net=q8(payload["provider_net"]),
                status=STATUS_PREPARED,
                external_reference=None,
                created_event_id=str(event_id or payload.get("event_id", "replayed")),
                settled_event_id=None,
                metadata=dict(payload.get("metadata", {})),
            )
            return

        if event_type == "settlement_settled":
            key = str(payload["settlement_key"])
            existing = self._settlements.get(key)
            if existing is None:
                raise SettlementError(f"settlement event without prepared record: {key}")
            if existing.status == STATUS_SETTLED:
                # Idempotent replay of duplicate source event is harmless only
                # when its immutable effect matches the existing record.
                if existing.external_reference != str(payload["external_reference"]):
                    raise SettlementError("conflicting duplicate settlement event")
                return
            self._settlements[key] = SettlementRecord(
                **{
                    **asdict(existing),
                    "status": STATUS_SETTLED,
                    "external_reference": str(payload["external_reference"]),
                    "settled_event_id": str(event_id or payload.get("event_id", "replayed")),
                }
            )
            return

        raise SettlementError(f"unknown settlement event type: {event_type!r}")

    def settle(
        self,
        *,
        contribution_id: str,
        executor: Callable[..., SettlementEffect],
    ) -> SettlementRecord:
        key = self.settlement_key(contribution_id)
        record = self._settlements.get(key)
        if record is None:
            raise SettlementError("settlement must be prepared before settle")
        if record.status == STATUS_SETTLED:
            return record

        effect = executor(
            idempotency_key=key,
            payload={
                "contribution_id": record.contribution_id,
                "settlement_key": record.settlement_key,
                "reward_id": record.reward_id,
                "provider_id": record.provider_id,
                "resource_id": record.resource_id,
                "rail": record.rail,
                "gross": str(record.gross),
                "author_royalty": str(record.author_royalty),
                "protocol_fee": str(record.protocol_fee),
                "internal_spread": str(record.internal_spread),
                "provider_net": str(record.provider_net),
            },
        )
        if effect.settlement_key != key:
            raise SettlementError("executor returned mismatched idempotency key")

        event = self._append_event(
            event_type="settlement_settled",
            payload={
                "contribution_id": record.contribution_id,
                "settlement_key": key,
                "external_reference": effect.external_reference,
            },
        )
        self._apply_event(event.payload, event_id=event.event_id)
        self.store.checkpoint(self._snapshot_state())
        return self._settlements[key]

    # ------------------------------ read ------------------------------

    def get(self, contribution_id: str) -> Optional[SettlementRecord]:
        return self._settlements.get(self.settlement_key(contribution_id))

    def settled_records(self) -> list[SettlementRecord]:
        return [
            record for record in self._settlements.values()
            if record.status == STATUS_SETTLED
        ]

    def verify_integrity(self) -> dict[str, Any]:
        recovery = self.store.verify_integrity()
        records = list(self._settlements.values())
        settled_keys = [record.settlement_key for record in records if record.status == STATUS_SETTLED]
        unique_keys = len(set(settled_keys)) == len(settled_keys)
        return {
            **recovery.to_dict(),
            "integrity_ok": recovery.integrity_ok and unique_keys,
            "settlement_count": len(records),
            "settled_count": len(settled_keys),
            "unique_settlement_keys": unique_keys,
        }

    # --------------------------- deterministic tests ---------------------------

    def assert_no_double_settlement(self, contribution_id: str) -> None:
        key = self.settlement_key(contribution_id)
        matches = [
            event for event in self.store.events()
            if event.payload.get("event_type") == "settlement_settled"
            and event.payload.get("settlement_key") == key
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one settled event for {key}, found {len(matches)}")


def _crash_worker(base_path: str, phase: str) -> None:
    store = PaymentSettlementStore(base_path, journal_batch_size=1, checkpoint_interval=1, durable=True)
    try:
        store.prepare(
            contribution_id="contrib-crash-001",
            reward_id="reward-001",
            provider_id="provider-001",
            resource_id="gpu-001",
            rail="resource_credits",
            gross="100.00000000",
            author_royalty="0.00100000",
            provider_net="99.99900000",
        )
        executor = ReferenceIdempotentExecutor()
        effect = executor.execute(
            idempotency_key=store.settlement_key("contrib-crash-001"),
            payload={
                "contribution_id": "contrib-crash-001",
                "settlement_key": store.settlement_key("contrib-crash-001"),
                "provider_id": "provider-001",
                "provider_net": "99.99900000",
                "author_royalty": "0.00100000",
                "rail": "resource_credits",
            },
        )
        if phase == "after_external_effect":
            # Simulate process destruction after the provider accepted the
            # idempotent request but before UFCPS could record SETTLED.
            del effect
            os._exit(23)
        raise AssertionError(f"unknown crash phase: {phase}")
    finally:
        try:
            store.close()
        except Exception:
            pass


def _self_test() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="ufcps-payment-settlement-") as temp_dir:
        base = Path(temp_dir) / "settlement"
        executor = ReferenceIdempotentExecutor()
        store = PaymentSettlementStore(base, journal_batch_size=4, checkpoint_interval=4, durable=True)

        prepared = store.prepare(
            contribution_id="contrib-001",
            reward_id="reward-001",
            provider_id="provider-001",
            resource_id="gpu-001",
            rail="resource_credits",
            gross="50.00000000",
            author_royalty="0.00050000",
            provider_net="49.99950000",
        )
        checks["prepare"] = prepared.status == STATUS_PREPARED

        settled = store.settle(contribution_id="contrib-001", executor=executor.execute)
        checks["settle"] = settled.status == STATUS_SETTLED
        checks["single_external_effect"] = executor.calls == 1

        repeated = store.settle(contribution_id="contrib-001", executor=executor.execute)
        checks["idempotent_repeat"] = repeated.external_reference == settled.external_reference and executor.calls == 1
        store.assert_no_double_settlement("contrib-001")
        checks["exactly_one_settled_event"] = True
        checks["royalty_0_001_percent"] = settled.author_royalty == Decimal("0.00050000")

        store.close()

        restored = PaymentSettlementStore(base, journal_batch_size=4, checkpoint_interval=4, durable=True)
        recovered = restored.get("contrib-001")
        checks["restart_preserves_settled"] = recovered is not None and recovered.status == STATUS_SETTLED
        checks["hash_chain"] = bool(restored.verify_integrity()["integrity_ok"])

        # Crash window test: external effect exists, local SETTLED event does not.
        crash_base = Path(temp_dir) / "crash"
        child = subprocess.run(
            [sys.executable, __file__, "--crash-worker", str(crash_base), "after_external_effect"],
            capture_output=True,
            text=True,
        )
        checks["crash_occurred"] = child.returncode == 23

        # The worker's external executor is process-local, so now use a
        # durable provider-side idempotency ledger to reproduce the same key.
        provider_ledger = {"ufcps-settlement:contrib-crash-001": "provider-ref-001"}
        restored_crash = PaymentSettlementStore(crash_base, journal_batch_size=1, checkpoint_interval=1, durable=True)
        crash_record = restored_crash.get("contrib-crash-001")
        checks["prepared_survives_crash"] = crash_record is not None and crash_record.status == STATUS_PREPARED

        class DurableLikeExecutor:
            def __init__(self, ledger: dict[str, str]) -> None:
                self.ledger = ledger
                self.calls = 0

            def execute(self, *, idempotency_key: str, payload: Mapping[str, Any]) -> SettlementEffect:
                self.calls += 1
                reference = self.ledger.setdefault(idempotency_key, "provider-ref-001")
                return SettlementEffect(
                    contribution_id=str(payload["contribution_id"]),
                    settlement_key=idempotency_key,
                    external_reference=reference,
                    provider_id=str(payload["provider_id"]),
                    provider_net=q8(payload["provider_net"]),
                    author_royalty=q8(payload["author_royalty"]),
                    rail=str(payload["rail"]),
                    status="executed_reference",
                )

        provider = DurableLikeExecutor(provider_ledger)
        recovered_after_crash = restored_crash.settle(
            contribution_id="contrib-crash-001",
            executor=provider.execute,
        )
        second_retry = restored_crash.settle(
            contribution_id="contrib-crash-001",
            executor=provider.execute,
        )
        checks["crash_recovery_settles"] = recovered_after_crash.status == STATUS_SETTLED
        checks["crash_recovery_same_reference"] = recovered_after_crash.external_reference == second_retry.external_reference == "provider-ref-001"
        checks["crash_retry_idempotent"] = provider.calls == 1
        restored_crash.assert_no_double_settlement("contrib-crash-001")
        checks["crash_exactly_one_settled_event"] = True
        checks["crash_hash_chain"] = bool(restored_crash.verify_integrity()["integrity_ok"])

    passed = all(checks.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": passed,
        "checks": checks,
        "guarantees": {
            "internal_recorded_effect": "exactly_one_settled_event_per_contribution",
            "retry_semantics": "idempotent_by_settlement_key",
            "external_effect": "exactly_once_requires_provider_side_idempotency_support",
            "real_payment_execution": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--print-schema", action="store_true")
    parser.add_argument("--crash-worker", nargs=2, metavar=("BASE_PATH", "PHASE"))
    args = parser.parse_args()

    if args.crash_worker:
        _crash_worker(args.crash_worker[0], args.crash_worker[1])
        return 0

    if args.print_schema:
        print(json.dumps({
            "schema_version": SCHEMA_VERSION,
            "state_machine": ["VERIFIED", "SETTLEMENT_PREPARED", "SETTLED"],
            "idempotency_key": "ufcps-settlement:{contribution_id}",
            "supported_rails": sorted(SUPPORTED_RAILS),
            "author_royalty_rate": str(AUTHOR_ROYALTY_RATE),
            "invariants": [
                "one economic contribution maps to one settlement key",
                "reusing a settlement key with different payload is rejected",
                "SETTLED is idempotent on retry",
                "at most one SETTLED event exists per settlement key",
                "settlement totals are reconstructed from durable events",
                "external exactly-once requires provider-side idempotency",
                "no real payment provider is contacted",
            ],
        }, ensure_ascii=False, indent=2))
        return 0

    if args.self_test or len(sys.argv) == 1:
        print(json.dumps(_self_test(), ensure_ascii=False, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
