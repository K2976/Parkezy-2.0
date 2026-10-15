"""Host withdrawals. The ledger says what the platform owes each host; a payout request moves
that money into `payouts_pending` until an admin confirms the bank/UPI transfer went out.

Requests for one host are serialised on the host's user row, so parallel taps can never
withdraw the same rupee twice."""

import uuid
from decimal import Decimal

from sqlalchemy import func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.db.models import Payout, PayoutAccount, User
from app.domain.enums import PayoutMethod, PayoutStatus
from app.domain.rules import PlatformRules
from app.services.ledger_service import LedgerService
from app.services.outbox import Event, Outbox
from app.services.pagination import decode_cursor, page

IDEMPOTENCY_CONSTRAINT = "uq_payouts_host_idempotency"


def destination_of(account: PayoutAccount) -> dict:
    """What we store on the payout and show back: never the full account number."""
    if account.method == PayoutMethod.UPI.value:
        return {"method": account.method, "upi_id": account.upi_id}
    return {
        "method": account.method,
        "account_holder_name": account.account_holder_name,
        "account_number_last4": (account.account_number or "")[-4:],
        "ifsc": account.ifsc,
    }


class PayoutService:
    def __init__(self, session: AsyncSession, clock: Clock) -> None:
        self._session = session
        self._clock = clock
        self._ledger = LedgerService(session, clock)
        self._outbox = Outbox(session, clock)

    # ------------------------------------------------------------ payout account
    async def account(self, host: User) -> PayoutAccount:
        account = await self._session.get(PayoutAccount, host.id)
        if account is None:
            raise NotFound("Add a UPI id or bank account to receive payouts", code="no_payout_account")
        return account

    async def set_account(self, host: User, data: dict) -> PayoutAccount:
        values = {
            "method": data["method"],
            "upi_id": data.get("upi_id"),
            "account_holder_name": data.get("account_holder_name"),
            "account_number": data.get("account_number"),
            "ifsc": data.get("ifsc"),
            "updated_at": self._clock.now(),
        }
        stmt = insert(PayoutAccount).values(user_id=host.id, **values)
        await self._session.execute(stmt.on_conflict_do_update(index_elements=["user_id"], set_=values))
        await self._session.commit()
        account = await self._session.get(PayoutAccount, host.id, populate_existing=True)
        assert account is not None
        return account

    # ------------------------------------------------------------ balance
    async def _sum(self, host: User, status: PayoutStatus) -> Decimal:
        total = await self._session.scalar(
            select(func.coalesce(func.sum(Payout.amount), 0)).where(
                Payout.host_id == host.id, Payout.status == status.value
            )
        )
        return Decimal(total or 0).quantize(Decimal("0.01"))

    async def balance(self, host: User, rules: PlatformRules) -> dict:
        return {
            "currency": rules.currency,
            "available": (await self._ledger.host_withdrawable(host.id)).quantize(Decimal("0.01")),
            "pending": await self._sum(host, PayoutStatus.REQUESTED),
            "paid_out": await self._sum(host, PayoutStatus.PAID),
        }

    # ------------------------------------------------------------ host actions
    async def _by_key(self, host: User, key: str) -> Payout | None:
        return (
            await self._session.execute(select(Payout).where(Payout.host_id == host.id, Payout.idempotency_key == key))
        ).scalar_one_or_none()

    def _replay(self, payout: Payout, amount: Decimal) -> Payout:
        if payout.amount != amount:
            raise Conflict("Idempotency-Key was already used for a different payout", code="idempotency_mismatch")
        return payout

    async def request(
        self, host: User, amount: Decimal, idempotency_key: str, rules: PlatformRules
    ) -> tuple[Payout, bool]:
        """Returns (payout, created)."""
        existing = await self._by_key(host, idempotency_key)
        if existing:
            return self._replay(existing, amount), False
        if amount < rules.min_payout_amount:
            raise ValidationFailed(
                f"The smallest payout is {rules.currency} {rules.min_payout_amount}",
                code="below_minimum_payout",
                details={"min_amount": str(rules.min_payout_amount)},
            )
        account = await self.account_or_conflict(host)
        # Serialise this host's withdrawals: the balance below is read under the lock.
        await self._session.execute(select(User.id).where(User.id == host.id).with_for_update())
        existing = await self._by_key(host, idempotency_key)  # a concurrent replay may have won the lock
        if existing:
            await self._session.commit()
            return self._replay(existing, amount), False
        available = await self._ledger.host_withdrawable(host.id)
        if amount > available:
            raise Conflict(
                "That's more than your available balance",
                code="insufficient_balance",
                details={"available": str(available.quantize(Decimal("0.01")))},
            )
        now = self._clock.now()
        payout = Payout(
            host_id=host.id,
            amount=amount,
            currency=rules.currency,
            status=PayoutStatus.REQUESTED.value,
            method=account.method,
            destination=destination_of(account),
            idempotency_key=idempotency_key,
            requested_at=now,
        )
        self._session.add(payout)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            replay = await self._by_key(host, idempotency_key)
            if replay is None:
                raise
            return self._replay(replay, amount), False
        self._ledger.post_payout_requested(host.id, amount, rules.currency)
        await self._session.commit()
        return payout, True

    async def account_or_conflict(self, host: User) -> PayoutAccount:
        account = await self._session.get(PayoutAccount, host.id)
        if account is None:
            raise Conflict("Add a UPI id or bank account before requesting a payout", code="no_payout_account")
        return account

    async def _locked(self, payout_id: uuid.UUID) -> Payout:
        payout = (
            await self._session.execute(select(Payout).where(Payout.id == payout_id).with_for_update())
        ).scalar_one_or_none()
        if payout is None:
            raise NotFound("Payout not found")
        return payout

    @staticmethod
    def _ensure_requested(payout: Payout) -> None:
        if payout.status != PayoutStatus.REQUESTED.value:
            raise Conflict(
                f"This payout is already {payout.status}",
                code="invalid_payout_transition",
                details={"status": payout.status},
            )

    async def cancel(self, host: User, payout_id: uuid.UUID) -> Payout:
        payout = await self._locked(payout_id)
        if payout.host_id != host.id:
            raise NotFound("Payout not found")
        self._ensure_requested(payout)
        payout.status = PayoutStatus.CANCELLED.value
        self._ledger.post_payout_returned(host.id, payout.amount, payout.currency)
        await self._session.commit()
        await self._session.refresh(payout)
        return payout

    async def list_for_host(self, host: User, *, cursor: str | None, limit: int) -> tuple[list[Payout], str | None]:
        return await self._list(Payout.host_id == host.id, cursor=cursor, limit=limit)

    # ------------------------------------------------------------ admin
    async def list_all(
        self, *, status: PayoutStatus | None, cursor: str | None, limit: int
    ) -> tuple[list[Payout], str | None]:
        clause = Payout.status == status.value if status else None
        return await self._list(clause, cursor=cursor, limit=limit)

    async def _list(self, clause, *, cursor: str | None, limit: int) -> tuple[list[Payout], str | None]:
        query = select(Payout)
        if clause is not None:
            query = query.where(clause)
        if cursor:
            created, pid = decode_cursor(cursor)
            query = query.where(tuple_(Payout.created_at, Payout.id) < tuple_(created, pid))
        rows = list(
            (await self._session.execute(query.order_by(Payout.created_at.desc(), Payout.id.desc()).limit(limit + 1)))
            .scalars()
            .all()
        )
        return page(rows, limit, key=lambda p: (p.created_at, p.id))

    async def mark_paid(self, admin: User, payout_id: uuid.UUID, reference: str) -> Payout:
        payout = await self._locked(payout_id)
        self._ensure_requested(payout)
        payout.status = PayoutStatus.PAID.value
        payout.reference = reference
        payout.paid_at = self._clock.now()
        payout.decided_by = admin.id
        self._ledger.post_payout_paid(payout.host_id, payout.amount, payout.currency)
        self._outbox.add(Event.PAYOUT_PAID, {"payout_id": str(payout.id)})
        await self._session.commit()
        await self._session.refresh(payout)
        return payout

    async def reject(self, admin: User, payout_id: uuid.UUID, reason: str) -> Payout:
        payout = await self._locked(payout_id)
        self._ensure_requested(payout)
        payout.status = PayoutStatus.REJECTED.value
        payout.reject_reason = reason
        payout.decided_by = admin.id
        self._ledger.post_payout_returned(payout.host_id, payout.amount, payout.currency)
        self._outbox.add(Event.PAYOUT_REJECTED, {"payout_id": str(payout.id)})
        await self._session.commit()
        await self._session.refresh(payout)
        return payout
