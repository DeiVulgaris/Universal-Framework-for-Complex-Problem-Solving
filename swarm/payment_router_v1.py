#!/usr/bin/env python3
"""
UFCPS Level 2 — Payment Router v1

Routes supported payment rails for UFCPS services.

Supported rails:
- Resource Credits (RC)
- crypto
- fiat purchase of Resource Credits

Core rules:
1. RC is a non-cash service-credit unit.
2. Crypto is an optional participant-selected settlement rail.
3. Internal crypto <-> RC conversion has:
       protocol commission = 0
       internal spread = 0
4. A mandatory author royalty of 0.001% applies to EVERY transaction.
   The royalty is distinct from protocol commission and internal spread.
5. Service pricing may be anchored in RC for stability.
6. This is a reference implementation, not a payment processor or wallet.

No blockchain/network operations are performed here.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from datetime import datetime, timezone
from typing import Any, Optional


AUTHOR_ROYALTY_RATE = Decimal("0.00001")  # 0.001%
SUPPORTED_RAILS = {"resource_credits", "crypto", "fiat"}
CRYPTO_TO_RC_ROYALTY_CHARGED_IN = "crypto"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def D(value: Decimal | str | int | float) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def money(value: Decimal) -> Decimal:
    """Normalize monetary/service amounts to 8 decimal places."""
    return D(value).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


class PaymentRouterError(ValueError):
    """Raised for invalid payment-routing operations."""


@dataclass(frozen=True)
class TransactionResult:
    transaction_id: str
    rail: str
    gross_amount: Decimal
    author_royalty: Decimal
    protocol_commission: Decimal
    internal_spread: Decimal
    net_amount: Decimal
    asset: str
    status: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class ConversionQuote:
    quote_id: str
    source_asset: str
    target_asset: str
    gross_source_amount: Decimal
    author_royalty_source: Decimal
    protocol_commission_source: Decimal
    internal_spread_source: Decimal
    net_source_amount: Decimal
    reference_rate: Decimal
    target_amount: Decimal
    expires_in_seconds: int


class PaymentRouter:
    """
    Reference router for UFCPS payment rails.

    The router treats internal conversion as a transaction, therefore the
    universal author royalty applies to it even though protocol commission
    and internal spread remain zero.
    """

    def __init__(
        self,
        *,
        rc_per_fiat: Decimal | str = "1.0",
        crypto_to_rc_rate: Decimal | str = "1.0",
        quote_ttl_seconds: int = 60,
    ) -> None:
        self.rc_per_fiat = D(rc_per_fiat)
        self.crypto_to_rc_rate = D(crypto_to_rc_rate)
        self.quote_ttl_seconds = int(quote_ttl_seconds)

        if self.rc_per_fiat <= 0:
            raise PaymentRouterError("rc_per_fiat must be > 0")
        if self.crypto_to_rc_rate <= 0:
            raise PaymentRouterError("crypto_to_rc_rate must be > 0")
        if self.quote_ttl_seconds <= 0:
            raise PaymentRouterError("quote_ttl_seconds must be > 0")

    @staticmethod
    def author_royalty(amount: Decimal | str | int | float) -> Decimal:
        amount = D(amount)
        if amount < 0:
            raise PaymentRouterError("amount cannot be negative")
        return money(amount * AUTHOR_ROYALTY_RATE)

    @staticmethod
    def _validate_positive(amount: Decimal) -> None:
        if amount <= 0:
            raise PaymentRouterError("amount must be > 0")

    @staticmethod
    def _validate_rail(rail: str) -> None:
        if rail not in SUPPORTED_RAILS:
            raise PaymentRouterError(
                f"unsupported payment rail: {rail}; "
                f"supported={sorted(SUPPORTED_RAILS)}"
            )

    def settle_transaction(
        self,
        *,
        rail: str,
        amount: Decimal | str | int | float,
        asset: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> TransactionResult:
        """
        Settle a payment in its supplied rail.

        The amount is gross. The author royalty is always carved out from
        the gross amount in the same asset. Protocol commission and internal
        spread are both zero in the reference model.
        """
        self._validate_rail(rail)
        gross = money(D(amount))
        self._validate_positive(gross)

        if not asset.strip():
            raise PaymentRouterError("asset is required")

        royalty = self.author_royalty(gross)
        protocol_commission = Decimal("0")
        internal_spread = Decimal("0")
        net = money(gross - royalty)

        return TransactionResult(
            transaction_id=str(uuid.uuid4()),
            rail=rail,
            gross_amount=gross,
            author_royalty=royalty,
            protocol_commission=protocol_commission,
            internal_spread=internal_spread,
            net_amount=net,
            asset=asset,
            status="settled_reference",
            metadata=metadata or {},
        )

    def buy_resource_credits(
        self,
        *,
        fiat_amount: Decimal | str | int | float,
        currency: str = "FIAT",
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Purchase RC using fiat.

        The fiat transaction carries the universal author royalty.
        The remaining fiat amount is converted to RC at the published
        reference rate.
        """
        result = self.settle_transaction(
            rail="fiat",
            amount=fiat_amount,
            asset=currency,
            metadata={"operation": "buy_resource_credits", **(metadata or {})},
        )
        rc_issued = money(result.net_amount * self.rc_per_fiat)

        return {
            "transaction": asdict(result),
            "resource_credits_issued": rc_issued,
            "reference_rate_rc_per_fiat": self.rc_per_fiat,
        }

    def quote_crypto_to_rc(
        self,
        *,
        crypto_amount: Decimal | str | int | float,
    ) -> ConversionQuote:
        """
        Quote crypto -> RC.

        Internal UFCPS commission = 0.
        Internal UFCPS spread = 0.
        Author royalty still applies because the conversion itself is a
        transaction.
        """
        gross = money(D(crypto_amount))
        self._validate_positive(gross)

        royalty = self.author_royalty(gross)
        commission = Decimal("0")
        spread = Decimal("0")
        net_crypto = money(gross - royalty)
        target_rc = money(net_crypto * self.crypto_to_rc_rate)

        return ConversionQuote(
            quote_id=str(uuid.uuid4()),
            source_asset="CRYPTO",
            target_asset="RC",
            gross_source_amount=gross,
            author_royalty_source=royalty,
            protocol_commission_source=commission,
            internal_spread_source=spread,
            net_source_amount=net_crypto,
            reference_rate=self.crypto_to_rc_rate,
            target_amount=target_rc,
            expires_in_seconds=self.quote_ttl_seconds,
        )

    def convert_crypto_to_rc(
        self,
        *,
        crypto_amount: Decimal | str | int | float,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute reference crypto -> RC conversion."""
        quote = self.quote_crypto_to_rc(crypto_amount=crypto_amount)

        return {
            "conversion": asdict(quote),
            "status": "converted_reference",
            "metadata": metadata or {},
            "policy": {
                "protocol_commission": Decimal("0"),
                "internal_spread": Decimal("0"),
                "author_royalty_rate": AUTHOR_ROYALTY_RATE,
            },
        }

    def route_service_payment(
        self,
        *,
        preferred_rail: str,
        service_price_rc: Decimal | str | int | float,
        crypto_to_rc: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Route a service priced in RC.

        RC:
            pay RC directly.

        Crypto:
            convert enough crypto to RC at the reference rate, then settle
            the service in RC.

        Fiat:
            not a direct service rail here; fiat first buys RC.
        """
        service_rc = money(D(service_price_rc))
        self._validate_positive(service_rc)

        if preferred_rail == "resource_credits":
            tx = self.settle_transaction(
                rail="resource_credits",
                amount=service_rc,
                asset="RC",
                metadata={"operation": "service_payment", **(metadata or {})},
            )
            return {
                "mode": "direct_rc",
                "transaction": asdict(tx),
                "service_cost_rc": service_rc,
            }

        if preferred_rail == "crypto":
            if not crypto_to_rc:
                raise PaymentRouterError(
                    "crypto service routing requires crypto_to_rc=True "
                    "when service pricing is anchored in RC"
                )

            # Solve for gross crypto such that, after the 0.001% author
            # royalty, the received RC covers the service price.
            denominator = (
                Decimal("1")
                - AUTHOR_ROYALTY_RATE
            )
            gross_crypto = money(
                service_rc / self.crypto_to_rc_rate / denominator
            )
            conversion = self.convert_crypto_to_rc(
                crypto_amount=gross_crypto,
                metadata={
                    "operation": "crypto_to_rc_for_service",
                    **(metadata or {}),
                },
            )

            converted_rc = conversion["conversion"]["target_amount"]
            if D(converted_rc) < service_rc:
                # Decimal quantization can create a dust shortfall.
                raise PaymentRouterError(
                    "reference conversion produced insufficient RC for service"
                )

            service_tx = self.settle_transaction(
                rail="resource_credits",
                amount=service_rc,
                asset="RC",
                metadata={
                    "operation": "service_payment_after_crypto_conversion",
                    "conversion_quote_id": conversion["conversion"]["quote_id"],
                    **(metadata or {}),
                },
            )

            return {
                "mode": "crypto_via_rc",
                "crypto_gross": gross_crypto,
                "conversion": conversion,
                "service_transaction": asdict(service_tx),
                "service_cost_rc": service_rc,
            }

        if preferred_rail == "fiat":
            raise PaymentRouterError(
                "fiat is a funding rail; buy RC first, then pay for the service"
            )

        raise PaymentRouterError(f"unsupported preferred_rail: {preferred_rail}")

    def demo(self) -> dict[str, Any]:
        """
        Deterministic smoke test using an illustrative 1:1 reference rate.
        """
        direct = self.route_service_payment(
            preferred_rail="resource_credits",
            service_price_rc="100",
            metadata={"request_id": "req-rc"},
        )

        crypto = self.route_service_payment(
            preferred_rail="crypto",
            service_price_rc="100",
            crypto_to_rc=True,
            metadata={"request_id": "req-crypto"},
        )

        buy = self.buy_resource_credits(
            fiat_amount="1000",
            currency="USD",
            metadata={"campaign": "pilot"},
        )

        # Core invariants.
        assert D(direct["transaction"]["protocol_commission"]) == 0
        assert D(direct["transaction"]["internal_spread"]) == 0
        assert D(direct["transaction"]["author_royalty"]) == money(D("100") * AUTHOR_ROYALTY_RATE)

        conversion = crypto["conversion"]["conversion"]
        assert D(conversion["protocol_commission_source"]) == 0
        assert D(conversion["internal_spread_source"]) == 0
        assert D(conversion["author_royalty_source"]) == money(
            D(crypto["crypto_gross"]) * AUTHOR_ROYALTY_RATE
        )

        # Fiat funding also carries the universal royalty.
        assert D(buy["transaction"]["author_royalty"]) == money(
            D("1000") * AUTHOR_ROYALTY_RATE
        )

        return {
            "status": "PASS",
            "author_royalty_rate": str(AUTHOR_ROYALTY_RATE),
            "direct_rc": direct,
            "crypto_to_rc": crypto,
            "fiat_to_rc": buy,
        }


def decimal_to_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: decimal_to_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decimal_to_json(v) for v in value]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run deterministic smoke tests",
    )
    parser.add_argument(
        "--rc-per-fiat",
        default="1.0",
        help="illustrative RC per one unit of fiat",
    )
    parser.add_argument(
        "--crypto-to-rc",
        default="1.0",
        help="illustrative RC per one unit of crypto",
    )
    args = parser.parse_args()

    router = PaymentRouter(
        rc_per_fiat=args.rc_per_fiat,
        crypto_to_rc_rate=args.crypto_to_rc,
    )

    if args.demo:
        result = router.demo()
        print(
            json.dumps(
                decimal_to_json(result),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
