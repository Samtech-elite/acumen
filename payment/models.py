from django.db import models
from django.conf import settings
from applications.models import Application
from django.utils.translation import gettext_lazy as _

class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('paypal', _('PayPal')),
        ('mpesa', _('Mpesa (Kenya only)')),
        ('bank_transfer', _('Bank Transfer')),
        ('card', _('Card Payment')),
    ]

    STATUS_CHOICES = [
        ('pending', _('Pending Confirmation')),
        ('verified', _('Verified')),
        ('approved', _('Approved by Admin')),
        ('rejected', _('Rejected')),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text=_("Optional reference number for the payment"))
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # dynamic
    currency = models.CharField(max_length=10, default='USD', help_text=_("Currency code, e.g. USD, KES"))
    confirmation_proof = models.ImageField(upload_to='payment_confirmations/')
    confirmation_verified = models.BooleanField(default=False)
    internal_reference = models.CharField(
        max_length=100, 
        unique=True, 
        help_text=_("Unique internal reference for tracking this payment")
    )
    external_reference = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text=_("External reference ID from payment gateway (if applicable)")
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Support retry - allow clearing or replacing confirmation proof
    retry_allowed = models.BooleanField(default=True, help_text=_("Can user retry uploading payment proof?"))

    def __str__(self):
        return f"Payment for {self.application} ({self.get_status_display()})"


class PaymentDetails(models.Model):
    """Abstract base class for all payment method details"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text=_("External transaction ID"))
    
    class Meta:
        abstract = True


class PayPalDetails(PaymentDetails):
    """Details specific to PayPal payments"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='paypal_details')
    email = models.EmailField(help_text=_("PayPal account email"))
    
    # PayPal company details
    company_paypal_email = models.EmailField(
        default="payments@acumenink.com", 
        help_text=_("Company's PayPal email for receiving payments")
    )
    company_paypal_business_name = models.CharField(
        max_length=100, 
        default="Acumen Inc", 
        help_text=_("Company's business name on PayPal")
    )
    
    def __str__(self):
        return f"PayPal: {self.email}"


class MpesaDetails(PaymentDetails):
    """Details specific to M-Pesa payments"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='mpesa_details')
    phone_number = models.CharField(max_length=15, help_text=_("Phone number used for M-Pesa payment"))
    mpesa_code = models.CharField(max_length=30, help_text=_("M-Pesa confirmation code"))
    
    # M-Pesa company details
    company_mpesa_paybill = models.CharField(
        max_length=20, 
        default="123456", 
        help_text=_("Company's M-Pesa paybill number")
    )
    company_mpesa_account = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text=_("Company's M-Pesa account name (if applicable)")
    )
    company_mpesa_business_name = models.CharField(
        max_length=100, 
        default="Acumen Ink", 
        help_text=_("Company name displayed on M-Pesa")
    )
    company_mpesa_shortcode = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text=_("M-Pesa shortcode for STK Push")
    )
    
    def __str__(self):
        return f"M-Pesa: {self.mpesa_code} from {self.phone_number}"


class BankTransferDetails(PaymentDetails):
    """Details specific to bank transfer payments"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='bank_transfer_details')
    account_name = models.CharField(max_length=100, help_text=_("Name on the sending account"))
    bank_name = models.CharField(max_length=100, help_text=_("Name of the sending bank"))
    reference_number = models.CharField(max_length=100, help_text=_("Bank transfer reference number"))
    
    # Bank transfer company details
    company_bank_name = models.CharField(
        max_length=100, 
        default="International Bank", 
        help_text=_("Company's bank name")
    )
    company_bank_account_name = models.CharField(
        max_length=100, 
        default="Acumen Inc.", 
        help_text=_("Company's bank account name")
    )
    company_bank_account_number = models.CharField(
        max_length=50, 
        default="123456789", 
        help_text=_("Company's bank account number")
    )
    company_bank_swift_code = models.CharField(
        max_length=20, 
        default="ABCDEF12", 
        help_text=_("Company's bank SWIFT/BIC code")
    )
    company_bank_branch = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text=_("Company's bank branch (if applicable)")
    )
    company_bank_address = models.TextField(
        blank=True, 
        null=True, 
        help_text=_("Company's bank address")
    )
    company_bank_routing_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text=_("Company's bank routing/sort code")
    )
    company_bank_iban = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text=_("Company's bank IBAN (for international transfers)")
    )
    
    def __str__(self):
        return f"Bank Transfer: {self.reference_number} from {self.account_name}"


class CardPaymentDetails(PaymentDetails):
    """Details specific to card payments"""
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='card_details')
    card_type = models.CharField(max_length=20, help_text=_("Type of card (Visa, Mastercard, etc.)"))
    last_four = models.CharField(max_length=4, help_text=_("Last 4 digits of the card"))
    cardholder_name = models.CharField(max_length=100, help_text=_("Name on the card"))
    
    # Card payment gateway details
    company_card_gateway = models.CharField(
        max_length=50, 
        default="Stripe",
        help_text=_("Payment gateway for card payments")
    )
    company_card_merchant_id = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text=_("Merchant ID for card payments")
    )
    company_card_public_key = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text=_("Public API key for the payment gateway")
    )
    company_card_checkout_url = models.URLField(
        blank=True, 
        null=True, 
        help_text=_("URL for the payment gateway checkout")
    )
    company_card_business_name = models.CharField(
        max_length=100, 
        default="Acumen Ink", 
        help_text=_("Business name displayed on card statements")
    )
    
    def __str__(self):
        return f"Card: {self.card_type} ending in {self.last_four}"


class PaymentLog(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50, help_text=_("e.g., uploaded, verified, approved, rejected"))
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} by {self.performed_by} at {self.timestamp:%Y-%m-%d %H:%M}"
