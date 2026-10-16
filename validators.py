import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+\- ]+$")
INT_RE = re.compile(r"^-?\d+$")
DECIMAL_RE = re.compile(r"^-?\d+(\.\d+)?$")

TWO_PLACES = Decimal("0.01")
MAX_LINE_TOTAL = Decimal("99999999.99")
MIN_YEAR = 1900


def compute_line_total(quantity, unit_price, discount):
    """LineTotal = Quantity x UnitPrice x (1 - Discount / 100), rounded to 2 decimals."""
    total = (
        Decimal(quantity) * unit_price * (Decimal("100") - discount) / Decimal("100")
    )
    return total.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _bounds_error(value, spec):
    label = spec["label"]
    if "gt" in spec and not value > spec["gt"]:
        return "%s must be greater than %s." % (label, spec["gt"])
    if "min" in spec and value < spec["min"]:
        return "%s must be at least %s." % (label, spec["min"])
    if "max" in spec and value > spec["max"]:
        return "%s must be at most %s." % (label, spec["max"])
    return None


def validate_form(fields, form, options, existing=None):
    """
    Returns (cleaned, errors).
    fields   : list of field specs from entities.py
    form     : request.form
    options  : dict of field name -> list of {"id": ..., "label": ...} for foreign keys
    existing : current DB row when editing (lets a legacy choice value stay valid)
    """
    cleaned = {}
    errors = {}

    for spec in fields:
        name = spec["name"]
        label = spec["label"]
        ftype = spec["type"]
        raw = (form.get(name) or "").strip()

        if raw == "":
            if spec.get("required"):
                errors[name] = "%s is required." % label
            else:
                cleaned[name] = spec.get("default")
            continue

        if ftype in ("text", "textarea", "email", "phone"):
            max_len = spec.get("max_len", 255)
            if len(raw) > max_len:
                errors[name] = "%s must be at most %d characters." % (label, max_len)
            elif ftype == "email" and not EMAIL_RE.match(raw):
                errors[name] = "Enter a valid email address."
            elif ftype == "phone" and not PHONE_RE.match(raw):
                errors[name] = "%s may contain digits, spaces, + and - only." % label
            else:
                cleaned[name] = raw

        elif ftype == "int":
            if not INT_RE.match(raw):
                errors[name] = "%s must be a whole number." % label
                continue
            value = int(raw)
            problem = _bounds_error(value, spec)
            if problem:
                errors[name] = problem
            else:
                cleaned[name] = value

        elif ftype == "decimal":
            if not DECIMAL_RE.match(raw):
                errors[name] = "%s must be a valid number." % label
                continue
            try:
                value = Decimal(raw).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            except InvalidOperation:
                errors[name] = "%s is out of range." % label
                continue
            problem = _bounds_error(value, spec)
            if problem:
                errors[name] = problem
            else:
                cleaned[name] = value

        elif ftype == "date":
            try:
                value = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                errors[name] = "%s must be a valid date." % label
                continue
            if value.year < MIN_YEAR:
                errors[name] = "%s must be %d or later." % (label, MIN_YEAR)
            else:
                cleaned[name] = value

        elif ftype == "fk":
            valid_ids = set(str(o["id"]) for o in options.get(name, []))
            if raw in valid_ids:
                cleaned[name] = int(raw)
            else:
                errors[name] = "Select a valid option for %s." % label

        elif ftype == "choice":
            allowed = [str(c) for c in spec["choices"]]
            if existing is not None and existing.get(name) is not None:
                allowed.append(str(existing[name]))
            if raw in allowed:
                cleaned[name] = raw
            else:
                errors[name] = "Select a valid option for %s." % label

        else:
            errors[name] = "Unsupported field type."

    return cleaned, errors


def cross_validate(entity_key, cleaned, errors):
    """Rules that involve more than one field. Mutates errors."""
    if entity_key == "orders":
        order_date = cleaned.get("OrderDate")
        delivery = cleaned.get("DeliveryDate")
        if (
            order_date
            and delivery
            and "OrderDate" not in errors
            and "DeliveryDate" not in errors
            and delivery < order_date
        ):
            errors["DeliveryDate"] = "Delivery date cannot be earlier than the order date."

    if entity_key == "order-items":
        qty = cleaned.get("Quantity")
        price = cleaned.get("UnitPrice")
        discount = cleaned.get("Discount")
        if (
            qty is not None
            and price is not None
            and discount is not None
            and not any(k in errors for k in ("Quantity", "UnitPrice", "Discount"))
        ):
            if compute_line_total(qty, price, discount) > MAX_LINE_TOTAL:
                errors["Quantity"] = "Line total exceeds the maximum of %s." % MAX_LINE_TOTAL
                