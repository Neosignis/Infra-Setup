"""Trusted image-installed provider seam; never load code from request parameters."""

import importlib
from typing import Protocol

from .contracts import Capabilities, Capability, Language, RecognizeRequest, RecognizeResult, RenderRequest, RenderResult


class EngineUnavailable(Exception):
    pass


class EngineProvider(Protocol):
    """Implement in a separately reviewed model image, with real artifact checks."""

    def capabilities(self) -> Capabilities: ...
    def recognize(self, request: RecognizeRequest) -> RecognizeResult: ...
    def render(self, request: RenderRequest) -> RenderResult: ...


class UnavailableProvider:
    def capabilities(self) -> Capabilities:
        return Capabilities(languages=[Capability(language=language) for language in Language])

    def recognize(self, request: RecognizeRequest) -> RecognizeResult:
        raise EngineUnavailable("No approved recognition provider installed")

    def render(self, request: RenderRequest) -> RenderResult:
        raise EngineUnavailable("No approved rendering provider installed")


def load_provider(path: str) -> EngineProvider:
    if not path:
        return UnavailableProvider()
    module_name, separator, factory_name = path.partition(":")
    if not separator or not module_name or not factory_name.isidentifier():
        raise ValueError("ENGINE_PROVIDER must be package.module:factory")
    provider = getattr(importlib.import_module(module_name), factory_name)()
    for method in ("capabilities", "recognize", "render"):
        if not callable(getattr(provider, method, None)):
            raise TypeError(f"Engine provider lacks {method}")
    Capabilities.model_validate(provider.capabilities())
    return provider
