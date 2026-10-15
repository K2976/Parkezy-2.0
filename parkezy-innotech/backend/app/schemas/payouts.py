import re
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.domain.enums import PayoutStatus
from app.schemas.common import Schema

UPI_RE = re.compile(r"^[A-Za-z0-9._-]{2,256}@[A-Za-z][A-Za-z0-9]{1,63}$")
IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class UpiAccountIn(Schema):
    method: Literal["upi"]
    upi_id: str = Field(max_length=256)

    @field_validator("upi_id")
    @classmethod
    def _upi(cls, v: str) -> str:
        if not UPI_RE.match(v):
            raise ValueError("Enter a UPI id like name@bank")
        return v.lower()


class BankAccountIn(Schema):
    method: Literal["bank_account"]
    account_holder_name: str = Field(min_length=2, max_length=120)
    account_number: str = Field(pattern=r"^\d{9,18}$")
    ifsc: str = Field(max_length=11)

    @field_validator("ifsc")
    @classmethod
    def _ifsc(cls, v: str) -> str:
        if not IFSC_RE.match(v):
            raise ValueError("Enter an 11-character IFSC like HDFC0001234")
        return v


PayoutAccountIn = Annotated[UpiAccountIn | BankAccountIn, Field(discriminator="method")]


class PayoutAccountOut(Schema):
    method: str
    upi_id: str | None = None
    account_holder_name: str | None = None
    account_number_last4: str | None = None
    ifsc: str | None = None
    updated_at: datetime


class PayoutBalanceOut(Schema):
    currency: str
    available: Decimal
    pending: Decimal
    paid_out: Decimal


class PayoutRequestIn(Schema):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PayoutOut(Schema):
    id: uuid.UUID
    amount: Decimal
    currency: str
    status: PayoutStatus
    method: str
    destination: dict
    reference: str | None
    reject_reason: str | None
    requested_at: datetime
    paid_at: datetime | None


class MarkPaidIn(Schema):
    reference: str = Field(min_length=1, max_length=128)


class RejectPayoutIn(Schema):
    reason: str = Field(min_length=1, max_length=500)
