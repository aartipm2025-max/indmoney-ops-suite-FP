from __future__ import annotations

import datetime as dt
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

NonEmptyStr = Annotated[str, Field(min_length=1, max_length=10000)]
ShortStr = Annotated[str, Field(min_length=1, max_length=200)]
DocId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_\-]{3,64}$")]
UtcDateTime = Annotated[dt.datetime, Field(...)]


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class OpsSuiteBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("*", mode="before", check_fields=False)
    @classmethod
    def _check_utc(cls, v: object) -> object:
        if isinstance(v, dt.datetime):
            if v.tzinfo is None:
                raise ValueError(
                    "datetime must be timezone-aware (UTC). "
                    "Use datetime.now(datetime.UTC) or datetime(..., tzinfo=datetime.UTC)."
                )
            offset = v.utcoffset()
            if offset is not None and offset.total_seconds() != 0:
                raise ValueError(
                    f"datetime must be UTC (offset=0), got offset={offset}. "
                    "Convert to UTC before passing."
                )
        return v
