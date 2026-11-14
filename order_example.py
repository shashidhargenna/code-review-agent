import math

def calculate_order(p, q):

    total = p * q

    discount = total * 0.10

    final = total - discount

    return final

print(calculate_order(2, 500))