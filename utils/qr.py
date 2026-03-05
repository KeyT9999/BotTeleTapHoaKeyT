import qrcode
from io import BytesIO


def generate_qr_bytes(data: str) -> BytesIO:
    """Generate a QR code PNG as BytesIO from the given data string."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
