"""
Mocked geographic lookup (see ARCHITECTURE.md section 9.5).

A real deployment would swap this for a MaxMind GeoIP2 (or similar)
database/service lookup keyed on the actual client IP. We deliberately
don't do that here to avoid an external data dependency in a portfolio
project — but the call site (worker `process_message`) is the single
place that would change, everything downstream (schema, analytics
aggregation, dashboard) is already real.
"""
import hashlib

_MOCK_COUNTRIES = ["US", "GB", "DE", "IN", "BR", "JP", "CA", "AU", "FR", "SG"]


def mock_country_for_ip_hash(ip_hash: str | None) -> str:
    """
    Deterministic pseudo-geo: derives a stable "country" from the
    (already-hashed) IP so the same visitor consistently maps to the same
    mocked country across requests, without ever touching a real
    geolocation provider or the raw IP itself.
    """
    if not ip_hash:
        return "XX"
    digest = hashlib.sha256(ip_hash.encode()).hexdigest()
    index = int(digest, 16) % len(_MOCK_COUNTRIES)
    return _MOCK_COUNTRIES[index]
