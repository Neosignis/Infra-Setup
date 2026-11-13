"""Versioned HTTP contracts. Capture and linguistic confidence are distinct."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Language(StrEnum):
    ASL = "ase"
    NSL = "nsi"


class Point(StrictModel):
    # z is extractor-relative depth, NOT a metric 3D world coordinate.
    x: Annotated[float, Field(ge=-2, le=3)]
    y: Annotated[float, Field(ge=-2, le=3)]
    z: Annotated[float, Field(ge=-10, le=10)]
    visibility: Annotated[float, Field(ge=0, le=1)] | None = None


class Frame(StrictModel):
    t_ms: Annotated[int, Field(ge=0, le=10000, strict=True)]
    pose: Annotated[list[Point], Field(min_length=33, max_length=33)] | None = None
    left_hand: Annotated[list[Point], Field(min_length=21, max_length=21)] | None = None
    right_hand: Annotated[list[Point], Field(min_length=21, max_length=21)] | None = None
    face: Annotated[list[Point], Field(min_length=478, max_length=478)] | None = None

    @model_validator(mode="after")
    def has_observation(self):
        if all(group is None for group in (self.pose, self.left_hand, self.right_hand, self.face)):
            raise ValueError("at least one observed landmark group is required")
        return self


class RecognizeRequest(StrictModel):
    language: Language = Language.ASL
    feature_schema: Literal["neosignis.landmarks.v1"]
    extractor_version: Annotated[str, Field(min_length=1, max_length=100)]
    mirrored: bool
    frames: Annotated[list[Frame], Field(min_length=2, max_length=300)]

    @model_validator(mode="after")
    def ordered_frames(self):
        if self.frames[0].t_ms != 0:
            raise ValueError("utterance timestamps must start at zero")
        if any(b.t_ms <= a.t_ms for a, b in zip(self.frames, self.frames[1:])):
            raise ValueError("timestamps must increase strictly")
        return self


class RecognizeResult(StrictModel):
    language: Language
    status: Literal["final", "abstained"]
    text: Annotated[str, Field(max_length=4000)] | None = None
    model_version: Annotated[str, Field(min_length=1, max_length=200)]
    confidence: Annotated[float, Field(ge=0, le=1)] | None = None
    confidence_calibrated: bool = False
    reason: Annotated[str, Field(max_length=200)] | None = None

    @model_validator(mode="after")
    def honest_output(self):
        if self.confidence is not None and not self.confidence_calibrated:
            raise ValueError("uncalibrated linguistic confidence must be null")
        if self.status == "abstained" and (self.text is not None or not self.reason):
            raise ValueError("abstention requires a reason and no translated text")
        if self.status == "final" and (not self.text or not self.text.strip()):
            raise ValueError("final recognition requires text")
        return self


class RenderRequest(StrictModel):
    language: Language = Language.ASL
    text: Annotated[str, Field(min_length=1, max_length=2000)]
    signer_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]

    @model_validator(mode="after")
    def nonempty_text(self):
        if not self.text.strip():
            raise ValueError("text must contain non-whitespace content")
        return self


class RenderResult(StrictModel):
    language: Language
    signer_id: str
    renderer_version: Annotated[str, Field(min_length=1, max_length=200)]
    status: Literal["ready", "unsupported"]
    output_kind: Literal["recorded_signer", "rigged_avatar", "neural_human"] | None = None
    # An opaque authorized asset ID, never an arbitrary worker-supplied URL.
    asset_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,120}$")] | None = None
    reason: Annotated[str, Field(max_length=200)] | None = None

    @model_validator(mode="after")
    def valid_output(self):
        if self.status == "ready" and (not self.asset_id or not self.output_kind):
            raise ValueError("ready output requires an approved asset and output kind")
        if self.status == "unsupported" and (self.asset_id or self.output_kind or not self.reason):
            raise ValueError("unsupported output requires reason and no asset")
        return self


class Capability(StrictModel):
    language: Language
    recognize: bool = False
    render: bool = False
    approved: bool = False
    model_version: str | None = None
    scope: str = "unavailable"

    @model_validator(mode="after")
    def approval_required(self):
        if (self.recognize or self.render) and (not self.approved or not self.model_version or self.scope == "unavailable"):
            raise ValueError("enabled capability requires approval, version and bounded scope")
        return self


class Capabilities(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    languages: list[Capability]

    @model_validator(mode="after")
    def unique_languages(self):
        if len({item.language for item in self.languages}) != len(self.languages):
            raise ValueError("duplicate language capabilities")
        return self


class ErrorBody(StrictModel):
    code: str
    message: str


class ErrorResponse(StrictModel):
    error: ErrorBody
