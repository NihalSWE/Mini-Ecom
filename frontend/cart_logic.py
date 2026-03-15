from decimal import Decimal
from django.utils import timezone
from django.db.models import Q
from backend.models import Product, ProductDiscount

def calculate_item_price(product, quantity):
    """
    Calculates totals based strictly on your Product and ProductDiscount models.
    """
    # 1. Setup Basic Data
    now_date = timezone.now().date() # Your model uses DateField, so we need .date()
    original_price = product.selling_price
    discount_amount = Decimal("0.00")

    # 2. Check for Active Discounts based on your model fields
    # We look for: active=True, date range covers today
    active_discount = product.discounts.filter(
        active=True,
        start_date__lte=now_date,
        end_date__gte=now_date
    ).first() # We take the most recent/first one found

    # 3. Apply Logic based on your DISCOUNT_TYPES choice
    if active_discount:
        if active_discount.discount_type == 'fixed':
            discount_amount = active_discount.discount_value
        
        elif active_discount.discount_type == 'percentage':
            # Formula: Price * (Percent / 100)
            discount_amount = original_price * (active_discount.percentage / Decimal("100"))

    # 4. Safety Check: Discount cannot exceed price
    if discount_amount > original_price:
        discount_amount = original_price

    final_unit_price = original_price - discount_amount
    
    # 5. Calculate Totals
    total_line_price = final_unit_price * quantity
    total_saved = discount_amount * quantity

    return {
        'original_price': original_price,
        'discount_amount_per_unit': discount_amount,
        'final_unit_price': final_unit_price,
        'subtotal': total_line_price,
        'total_saved': total_saved
    }