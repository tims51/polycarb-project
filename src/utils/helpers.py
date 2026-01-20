
"""
Helper Utilities Module
Generic utility functions used across the application.
"""

import socket
import qrcode
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

def get_local_ip() -> str:
    """
    Get the local IP address of the machine.
    Uses UDP connection probing to determine the preferred outgoing interface.
    """
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Try to connect to a public IP (Google DNS)
        # No data is actually sent
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception as e:
        logger.warning(f"Could not determine local IP via socket probe: {e}")
        # Fallback
        ip = socket.gethostbyname(socket.gethostname())
    finally:
        if s:
            s.close()
    return ip

def generate_qr_code(data: str) -> BytesIO:
    """
    Generate a QR code image from string data.
    Returns:
        BytesIO object containing the PNG image.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return BytesIO()
