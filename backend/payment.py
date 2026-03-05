from payos import AsyncPayOS
from payos.types import CreatePaymentLinkRequest
from config import PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY, WEBHOOK_BASE_URL
from utils.logger import logger

_client: AsyncPayOS | None = None


def get_payos() -> AsyncPayOS:
    global _client
    if _client is None:
        _client = AsyncPayOS(
            client_id=PAYOS_CLIENT_ID,
            api_key=PAYOS_API_KEY,
            checksum_key=PAYOS_CHECKSUM_KEY,
        )
    return _client


async def create_payment_link(
    order_code: int,
    amount: int,
    description: str,
) -> dict:
    """Create a payOS payment link. Returns dict with checkoutUrl, qrCode, paymentLinkId."""
    client = get_payos()
    cancel_url = f"{WEBHOOK_BASE_URL}/payment/cancel"
    return_url = f"{WEBHOOK_BASE_URL}/payment/success"

    response = await client.payment_requests.create(
        payment_data=CreatePaymentLinkRequest(
            order_code=order_code,
            amount=amount,
            description=description[:25],
            cancel_url=cancel_url,
            return_url=return_url,
        )
    )
    logger.info(f"payment_created order_code={order_code} amount={amount}")
    return {
        "checkoutUrl": response.checkout_url,
        "qrCode": response.qr_code,
        "paymentLinkId": response.payment_link_id,
    }


async def check_payment_status(order_code: int) -> str | None:
    """Check payment status via payOS API. Returns 'PAID', 'CANCELLED', or None if still pending."""
    client = get_payos()
    try:
        response = await client.payment_requests.get(order_code)
        status = response.status
        if status == "PAID":
            return "PAID"
        if status in ("CANCELLED", "EXPIRED"):
            return "CANCELLED"
        return None
    except Exception as e:
        logger.error(f"check_payment_status error order_code={order_code}: {e}")
        return None
