"""Domain-level exceptions raised by the services layer.

Deliberately HTTP-agnostic — a service shouldn't know what a 404 is, that's
a web-layer concept. main.py registers one global exception handler that
translates NotFoundError (and its subclasses) into an HTTP 404 for every
router at once, instead of each route doing its own try/except HTTPException.
"""


class NotFoundError(Exception):
    pass


class TitleNotFoundError(NotFoundError):
    pass


class PersonNotFoundError(NotFoundError):
    pass


class WatchlistEntryNotFoundError(NotFoundError):
    pass


class RatingNotFoundError(NotFoundError):
    pass


class ListNotFoundError(NotFoundError):
    pass


class ListItemNotFoundError(NotFoundError):
    pass


class SyncRunNotFoundError(NotFoundError):
    pass
