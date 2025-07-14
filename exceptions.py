class BadRequestException(Exception):
    """Raised when a bad request is made."""

    pass


class MethodNotAllowedException(Exception):
    """Raised when an invalid HTTP method is used."""

    pass
