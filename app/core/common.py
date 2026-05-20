import random
from datetime import datetime

def generate_order_number():
    year = datetime.now().year
    random_part = random.randint(10000000, 99999999)  # 8 random digits
    return f"{year}{random_part}"
