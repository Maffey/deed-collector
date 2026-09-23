"""Root exceptions for the deed-collector package.

Every domain-specific error derives from :class:`DeedCollectorError`, so callers
can catch the whole family with a single ``except`` clause while still being able
to handle individual failure modes if they need to.
"""


class DeedCollectorError(Exception):
    """Base exception for all deed-collector errors."""
