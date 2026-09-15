import re


def to_e164_india(phone: str) -> str:
    """
    Normalizes a phone number to E.164 for an India-only customer base (all NDR customers
    are in India - see src/intelligence_domains/ndr/config.py's same assumption for calling
    hours). ShopDeck's `customer_info.customer_number` is stored and passed through
    completely unformatted (plain 10-digit local numbers, confirmed via real production
    failures on 2026-09-15 - every real Sarvam dispatch was rejected with a 422 "Invalid
    phone number format" until this normalization existed), while Sarvam's Instant Outbound
    API strictly requires E.164.

    Handles the realistic input variety: bare 10-digit (`9876543210`), with a leading 0
    (`09876543210`), with a 91 country code but no `+` (`919876543210`), already-correct
    E.164 (`+919876543210`), and any of the above with stray spaces/dashes. A genuinely
    unexpected format (wrong digit count) is returned unchanged rather than guessed at, so
    Sarvam's own validation still rejects it clearly instead of this function silently
    fabricating a wrong number.
    """
    if not phone:
        return phone

    digits = re.sub(r"[^\d+]", "", phone.strip())

    if digits.startswith("+91") and len(digits) == 13:
        return digits
    if digits.startswith("91") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("0") and len(digits) == 11:
        return "+91" + digits[1:]
    if len(digits) == 10:
        return "+91" + digits

    return phone
