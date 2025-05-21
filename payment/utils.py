import pytesseract
from PIL import Image
import re

def verify_payment_confirmation(image_path: str, expected_amount: float, expected_method: str):
    """
    OCR-based verification of payment confirmation image.

    Args:
        image_path (str): Local file path to the uploaded confirmation image.
        expected_amount (float): The amount expected to be paid.
        expected_method (str): The payment method used (human-readable).

    Returns:
        tuple: (success: bool, error_message: str)
    """
    try:
        # Load image
        img = Image.open(image_path)

        # Use pytesseract to extract text from image
        extracted_text = pytesseract.image_to_string(img)

        # Normalize text for easier searching
        text = extracted_text.lower()

        # Debug: print or log extracted text
        # print(f"OCR Extracted Text:\n{text}")

        # Verify amount: find patterns like 123.45 or 1,234.56 in text
        amount_matches = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b', text)
        if not amount_matches:
            return False, "Could not detect any amount in the confirmation."

        # Normalize amounts (remove commas) and convert to float
        amounts = [float(a.replace(',', '')) for a in amount_matches]

        # Check if any detected amount matches expected amount (within small tolerance)
        tolerance = 0.5  # 50 cents tolerance
        amount_verified = any(abs(expected_amount - amt) <= tolerance for amt in amounts)
        if not amount_verified:
            return False, f"Expected amount {expected_amount} not found in confirmation."

        # Verify payment method mention in text (simplified check)
        # You can customize these keywords per method
        method_keywords = {
            'paypal': ['paypal'],
            'mpesa': ['mpesa', 'mpesa paybill', 'mpesa transaction'],
            'bank transfer': ['bank transfer', 'transfer', 'account number'],
            'card': ['card', 'credit card', 'debit card', 'visa', 'mastercard']
        }

        method_key = expected_method.lower()
        keywords = method_keywords.get(method_key, [])

        if keywords:
            if not any(keyword in text for keyword in keywords):
                return False, f"Payment method '{expected_method}' not clearly mentioned."

        # Passed all checks
        return True, ""

    except Exception as e:
        # Catch unexpected errors (e.g., image file issues)
        return False, f"Error processing confirmation image: {str(e)}"
