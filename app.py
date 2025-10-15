from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import router as auth_router
from api.customer import router as customer_router
from api.merchant import router as merchant_router
from api.users import router as user_router

# from api.blockchain import router as order_contract_router

app = FastAPI(title="Fiducia API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(customer_router)
app.include_router(merchant_router)
app.include_router(user_router)
# app.include_router(order_contract_router)

@app.get("/")
async def index():
    return {"message": "Welcome to the Fiducia API!"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)