from fastapi import FastAPI
from fastapi.responses import JSONResponse
from backend.webhook import webhook_router

app = FastAPI(title="Telegram Shop Bot API")
app.include_router(webhook_router)


@app.get("/")
async def root():
    return JSONResponse({"status": "ok"})


@app.get("/payment/success")
async def payment_success():
    return JSONResponse({"message": "Thanh toán thành công! Bạn có thể đóng trang này."})


@app.get("/payment/cancel")
async def payment_cancel():
    return JSONResponse({"message": "Thanh toán đã bị hủy."})
