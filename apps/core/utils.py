from decimal import Decimal


def rupees_to_paise(amount_rupees):
    return int(Decimal(str(amount_rupees)) * 100)


def paise_to_rupees(amount_paise):
    return round(float(amount_paise) / 100, 2)
