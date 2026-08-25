from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from data_service.routers import lists, people, ratings, sync, titles, watchlist
from data_service.services.exceptions import NotFoundError

app = FastAPI(title="TMDB Local Data Service", version="0.1.0")


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
