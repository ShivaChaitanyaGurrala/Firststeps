from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from data_service.rate_limit import RateLimiter
from data_service.routers import lists, people, ratings, sync, titles, watchlist
from data_service.services.exceptions import NotFoundError

app = FastAPI(title="TMDB Local Data Service", version="0.1.0")

# Generous on purpose — a solo-user local dev lab shouldn't trip this
# during normal manual testing / Inspector use. See rate_limit.py's
# docstring for the mechanism this is verifying, not tuning.
_rate_limiter = RateLimiter(max_requests=100, window_seconds=10)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    key = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(key):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"},
            headers={"Retry-After": str(int(_rate_limiter.window_seconds))},
        )
    return await call_next(request)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


app.include_router(titles.router)
app.include_router(people.router)
app.include_router(watchlist.router)
app.include_router(ratings.router)
app.include_router(lists.router)
app.include_router(sync.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
