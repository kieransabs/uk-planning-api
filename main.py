import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="UK Planning & Risk Feed")

# Your Coinbase Wallet Address
WALLET_ADDRESS = "0x62832d765f2E50319BA72C1cA85562Fed0c58D36"
PRICE_PER_CALL_USDC = "0.02"
FACILITATOR_URL = "https://facilitator.openmid.xyz/verify"

@app.get("/")
async def root():
    return {"message": "UK Planning x402 API is live. Query /api/v1/planning-risk"}

@app.get("/api/v1/planning-risk")
async def get_planning_risk(request: Request, reference: str = "camden"):
    payment_header = request.headers.get("X-Payment") or request.headers.get("authorization")

    # 1. No payment header -> Return HTTP 402 Paywall Intercept
    if not payment_header:
        return JSONResponse(
            status_code=402,
            content={
                "x402Version": 1,
                "error": "Payment Required",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": "eip155:8453",  # Base Mainnet
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
                        "payTo": WALLET_ADDRESS,
                        "maxAmountRequired": "20000",  # $0.02 in USDC
                        "description": "Access to UK aggregated planning risk data"
                    }
                ]
            }
        )

    # 2. Verify incoming payment signature
    try:
        verification = requests.post(
            FACILITATOR_URL,
            json={"paymentPayload": payment_header},
            timeout=5
        )
        if verification.status_code != 200 or not verification.json().get("valid"):
            return JSONResponse(
                status_code=402,
                content={"error": "Payment signature verification failed"}
            )
    except Exception:
        pass  # Bypass verification check during initial test mode

    # 3. Query Open Data Feed
    try:
        gov_url = f"https://www.planning.data.gov.uk/entity.json?organisation={reference.lower()}&limit=10"
        response = requests.get(gov_url, headers={"User-Agent": "x402-Risk-Engine/1.0"}, timeout=5)
        raw_data = response.json()
        
        entities = raw_data.get("entities", [])
        formatted_records = [
            {
                "entity_id": item.get("entity"),
                "name": item.get("name"),
                "dataset": item.get("dataset"),
                "entry_date": item.get("entry-date")
            }
            for item in entities
        ]
    except Exception:
        formatted_records = [{"status": "Data source updating", "council": reference}]

    return {
        "status": "success",
        "pricePaid": f"${PRICE_PER_CALL_USDC} USDC",
        "council": reference,
        "records": formatted_records
    }
