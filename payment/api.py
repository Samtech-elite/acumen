import logging
import requests
from django.conf import settings
import base64
from django.urls import reverse  # Import reverse

logger = logging.getLogger(__name__)
payment_logger = logging.getLogger("payment")


def initiate_stk_push(phone_number, amount, reference):
    """Initiates STK Push via PayHero API using Basic Auth."""

    if phone_number.startswith("+"):
        phone_number = phone_number[1:]

    if not phone_number.startswith("254"):
        logger.warning(
            f"Phone number {phone_number} might not be in correct 254 format."
        )

        if phone_number.startswith("07") and len(phone_number) == 10:
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("01") and len(phone_number) == 10:
            phone_number = "254" + phone_number[1:]

    api_url = f"{settings.PAYHERO_BASE_URL}/payments"

    try:
        callback_url_path = reverse('payment:payhero_withdrawal_webhook')
    except Exception:
        logger.error("Could not resolve payment webhook URL using reverse. Falling back to hardcoded path.")
        callback_url_path = "/payment/withdrawal-webhook/"

    base_url = settings.BASE_URL.rstrip('/')
    callback_path = callback_url_path.lstrip('/')
    absolute_callback_url = f"{base_url}/{callback_path}"
    logger.info(f"Using callback URL: {absolute_callback_url}")
    """
    payload = {
        "amount": float(amount),
        "phone_number": phone_number,
        "channel_id": settings.PAYHERO_CHANNEL_ID,
        "provider": "sasapay",
        "network_code": "63902",
        "external_reference": reference,
        "customer_name": "Customer",
        "callback_url": absolute_callback_url,
    }
    """
    payload = {
        "amount": float(amount),
        "phone_number": phone_number,
        "channel_id": settings.PAYHERO_CHANNEL_ID,
        "provider": "m-pesa",
        "external_reference": reference,
        "customer_name": "Customer",
        "callback_url": absolute_callback_url,
    }
     
    headers = {
        "Content-Type": "application/json",
        "Authorization": settings.PAYHERO_BASIC_AUTH,
    }

    payment_logger.info(f"Initiating PayHero STK Push: URL={api_url}, Payload={payload}")

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        payment_logger.debug(f"PayHero STK Push Raw Response Status: {response.status_code}")
        payment_logger.debug(f"PayHero STK Push Raw Response Body: {response.text}")
        response.raise_for_status()

        if response.status_code == 201:
            result = response.json()
            payment_logger.info(f"PayHero STK Push Success Response: {result}")
            transaction_reference = result.get("reference")
            if transaction_reference:
                return {
                    "success": True,
                    "transaction_id": transaction_reference,
                    "message": "STK Push initiated successfully",
                }
            else:
                payment_logger.error(f"PayHero STK push response missing reference: {result}")
                return {
                    "success": False,
                    "message": "STK push response missing reference.",
                }
        else:
            payment_logger.error(
                f"PayHero STK push returned unexpected status code {response.status_code}: {response.text}"
            )
            return {
                "success": False,
                "message": f"PayHero returned status {response.status_code}",
            }

    except requests.exceptions.HTTPError as e:
        payment_logger.error(f"PayHero STK push HTTPError: {e.response.status_code} - {e.response.text}")
        error_message = "STK push request failed."
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", error_message)
        except ValueError:
             error_message = e.response.text or error_message
        return {"success": False, "message": error_message}
    except requests.exceptions.RequestException as e:
        payment_logger.error(f"PayHero STK push RequestException: {e}")
        return {"success": False, "message": "STK push request failed due to network or connection issue."}


def verify_payment_status(reference):
    """Verifies payment status via PayHero API using the reference and Basic Auth."""
    api_username = settings.STK_PUSH_API_USERNAME
    api_password = settings.STK_PUSH_API_PASSWORD

    credentials = f"{api_username}:{api_password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    verify_url = f"{settings.PAYHERO_BASE_URL}/transaction-status?reference={reference}"

    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(verify_url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        payhero_status = data.get("status", "").upper()

        if payhero_status == "SUCCESS":
            internal_status = "completed"
        elif payhero_status in ["FAILED", "CANCELLED", "EXPIRED", "INVALID_REQUEST"]:
            internal_status = "failed"
        else:
            internal_status = "pending"

        return {
            "success": True,
            "status": internal_status,
            "amount": data.get("amount"),
            "message": data.get("message", "Status retrieved"),
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"PayHero status verification failed for {reference}: {e}")

        error_message = "Status verification failed."
        try:
            error_data = e.response.json()
            error_message = error_data.get("message", error_message)
        except:
            pass
        return {"success": False, "status": "error", "message": error_message}


def initiate_payhero_withdrawal(phone_number, amount, reference):
    """Initiates Withdrawal to Mobile via PayHero API using Basic Auth."""

    if phone_number.startswith("+"):
        phone_number = phone_number[1:]
    if not phone_number.startswith("254"):
        logger.warning(
            f"Withdrawal phone number {phone_number} might not be in correct 254 format."
        )

        if phone_number.startswith("07") and len(phone_number) == 10:
            phone_number = "254" + phone_number[1:]
        elif phone_number.startswith("01") and len(phone_number) == 10:
            phone_number = "254" + phone_number[1:]
        else:
            return {
                "success": False,
                "message": "Invalid phone number format for withdrawal. Must start with 254.",
            }

    api_url = f"{settings.PAYHERO_BASE_URL}/withdraw"

    base_url = settings.BASE_URL.rstrip('/')
    callback_path = 'payment/withdrawal-webhook/'
    absolute_callback_url = f"{base_url}/{callback_path}"

    payload = {
        "external_reference": reference,
        "amount": int(amount),
        "phone_number": phone_number,
        "network_code": "63902",
        "channel": "mobile",
        "channel_id": settings.PAYHERO_PAYMENT_ID,
        "payment_service": "b2c",
        "callback_url": absolute_callback_url,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": settings.PAYHERO_BASIC_AUTH,
    }

    logger.info(f"Initiating PayHero withdrawal: URL={api_url}, Payload={payload}")

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=45)
        response.raise_for_status()

        if response.status_code == 200:
            result = response.json()

            merchant_ref = result.get("merchant_reference")
            initial_api_status = result.get("status", "UNKNOWN").upper()
            message = result.get("message", "Withdrawal request received.")

            logger.info(f"PayHero withdrawal success response: {result}")

            if initial_api_status == "QUEUED":
                internal_status = "processing"
            else:
                internal_status = "pending"

            return {
                "success": True,
                "merchant_reference": merchant_ref,
                "message": message,
                "status": internal_status,
            }
        else:
            logger.error(
                f"PayHero withdrawal returned unexpected status code {response.status_code}: {response.text}"
            )
            return {
                "success": False,
                "message": f"PayHero returned status {response.status_code}",
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"PayHero withdrawal failed: {e}")
        error_message = "Withdrawal request failed."
        status_code = 500
        if e.response is not None:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                error_message = error_data.get("message", error_message)
                logger.error(f"PayHero withdrawal error response: {error_data}")
            except:
                logger.error(
                    f"PayHero withdrawal error response (non-JSON): {e.response.text}"
                )
                error_message = f"PayHero error: {e.response.reason}"

        return {"success": False, "message": error_message, "status_code": status_code}


def verify_withdrawal_status(reference):
    """Verifies withdrawal status via PayHero API using the reference (same as payment verification)."""
    return verify_payment_status(reference)
