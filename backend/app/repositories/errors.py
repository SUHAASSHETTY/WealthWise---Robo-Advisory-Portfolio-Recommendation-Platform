"""Persistence-layer errors."""


class PublishedVersionMutation(RuntimeError):
    """An UPDATE or DELETE was attempted on a PUBLISHED policy/template version (AC-10, NFR-08)."""


class AppendOnlyViolation(RuntimeError):
    """An UPDATE or DELETE was attempted on an append-only table (NFR-02, app_spec §5.3)."""
