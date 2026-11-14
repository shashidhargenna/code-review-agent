import math


def calculate_bill(price, quantity):
    total = price * quantity
    discount = total * 0.10
    final_amount = total - discount
    return final_amount


def calculate_tax(amount):
    tax = amount * 0.18
    return amount + tax


print(calculate_bill(2, 500))
print(calculate_tax(900))