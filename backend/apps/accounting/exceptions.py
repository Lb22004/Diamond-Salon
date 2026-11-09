from django.core.exceptions import ValidationError


class AccountingError(ValidationError):
    """Base exception for accounting and posting engine rules."""

    def __init__(self, message: str):
        super().__init__(message)
        self.detail = message


class UnbalancedEntryError(AccountingError):
    """Raised when a journal entry does not satisfy RN-01 (sum(debit) == sum(credit) > 0)."""


class InvalidAccountError(AccountingError):
    """Raised when attempting to post to a non-leaf or inactive account (RN-04)."""


class ImmutableEntryError(AccountingError):
    """Raised when attempting to edit or delete a POSTED or REVERSED journal entry (RN-02)."""
