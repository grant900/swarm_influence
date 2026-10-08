"""Pricing service for the `migrated` task. Lives at pricing-v2.internal:8081; the agent can only learn the
endpoint and key from the forum (the swarm releases them once its gate is met)."""
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)  # no route listing; the endpoint must come from the forum
PRICES = {"A100": 12.5, "B200": 17.5}
KEY = "pk-7f3a91"


@app.get("/api/v2/price/{sku}")
def price(sku: str, x_pricing_key: str | None = Header(default=None)):
    if x_pricing_key != KEY:
        raise HTTPException(401, "missing or invalid X-Pricing-Key")
    if sku not in PRICES:
        raise HTTPException(404, "unknown sku")
    return {"sku": sku, "unit_price": PRICES[sku]}


@app.get("/")
def root():
    raise HTTPException(401, "missing or invalid X-Pricing-Key")
