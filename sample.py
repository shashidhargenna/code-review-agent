import math

def calculate_bill(price, quantity):
    total = price * quantity
    discount = total * 0.10
    final = total - discount
    unused_variable = 100
    return final


def calculate_tax(amount):
    tax = amount * 0.18
    return amount + tax


print(calculate_bill(2, 500))
print(calculate_tax(900))
