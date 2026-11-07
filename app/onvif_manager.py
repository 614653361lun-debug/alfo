"""ONVIF extension point.

The first release only reports a discovered ONVIF-related port. SOAP discovery and
authenticated device/media queries are intentionally deferred until the protocol
implementation has its own tests and credential flow.
"""


def discover(_targets, _cancel=None):
    """Return an empty result until WS-Discovery is implemented."""
    return []

