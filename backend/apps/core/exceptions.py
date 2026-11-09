from django.core.exceptions import ValidationError


class ClosedPeriodError(ValidationError):
    """Raised when attempting to post or mutate transactions in a closed accounting period."""

    def __init__(self, message: str = "El período contable está cerrado."):
        super().__init__(message)
        self.detail = message
