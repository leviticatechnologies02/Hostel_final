class Levitica NestoraError(Exception):
    """Base domain exception."""


class AuthorizationError(Levitica NestoraError):
    """Raised when role or tenancy checks fail."""


class BookingConflictError(Levitica NestoraError):
    """Raised when overlapping inventory is detected."""
