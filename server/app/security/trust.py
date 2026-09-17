from __future__ import annotations

from ..models.state import DestinationClass, TrustLevel
from ..config import Settings


def normalize_host(host: str | None) -> str:
    if not host:
        return ""
    host = host.strip().lower()
    return host.split(":")[0]


def page_trust_for_host(host: str | None, settings: Settings) -> TrustLevel:
    host = normalize_host(host)
    if not host:
        return TrustLevel.PARTIAL
    if host in settings.internal_trusted_hosts:
        return TrustLevel.TRUSTED
    return TrustLevel.UNTRUSTED


def classify_destination(
    host: str | None,
    current_host: str | None,
    settings: Settings,
) -> tuple[DestinationClass, TrustLevel]:
    host = normalize_host(host)
    current = normalize_host(current_host)

    if not host:
        return DestinationClass.UNKNOWN, TrustLevel.UNTRUSTED
    if current and host == current:
        return DestinationClass.SAME_ORIGIN, TrustLevel.TRUSTED
    if host in settings.internal_trusted_hosts:
        return DestinationClass.INTERNAL, TrustLevel.TRUSTED
    if host in settings.trusted_external_vendors:
        return DestinationClass.TRUSTED_VENDOR, TrustLevel.PARTIAL
    return DestinationClass.EXTERNAL, TrustLevel.UNTRUSTED