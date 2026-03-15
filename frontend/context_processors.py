# your_app/context_processors.py

# store/context_processors.py

from backend.models import AboutPage, ContactPage, Product, SiteBranding

def all_products_for_modals(request):
    return {
        # 'images' matches your related_name in models.py
        'modal_products': Product.objects.all().prefetch_related('images')
    }



def footer_context(request):
    """
    Context processor to determine which footer to show.
    Smart approach: Check if current page is home/index page.
    """
    # Get the current path
    current_path = request.path
    
    # Define paths that should use footer 1 (home page)
    home_paths = ['/', '/home/', '/index/']
    
    # Check if current path is home page
    # Also check for empty path (root URL)
    is_home_page = current_path in home_paths or current_path == '/'
    
    # You can also check by view name if using URL names
    # from django.urls import resolve
    # try:
    #     resolved = resolve(request.path_info)
    #     is_home_page = resolved.url_name in ['home', 'index']
    # except:
    #     is_home_page = False
    
    try:
        site_branding = SiteBranding.get_solo()
    except Exception:
        site_branding = SiteBranding()

    try:
        about_page = AboutPage.get_solo()
    except Exception:
        about_page = AboutPage()

    try:
        contact_page = ContactPage.get_solo()
    except Exception:
        contact_page = ContactPage()

    return {
        'is_home_page': is_home_page,
        'site_branding': site_branding,
        'about_page': about_page,
        'contact_page': contact_page,
    }
    
    
from backend.models import Product
from decimal import Decimal
from .cart_logic import calculate_item_price 

def cart_context(request):
    cart_session = request.session.get('cart', {})
    cart_count = 0
    side_cart_items = []
    global_total = Decimal("0.00")

    if not isinstance(cart_session, dict):
        cart_session = {}

    product_ids = [int(k) for k in cart_session.keys() if k.isdigit()]
    products = Product.objects.in_bulk(product_ids)

    # We use list(cart_session.items()) so we can delete keys while looping
    for item_id_str, item_data in list(cart_session.items()):
        try:
            p_id = int(item_id_str)
            if p_id in products:
                product = products[p_id]
                # CRITICAL: If qty is less than 1, fix it or remove it
                raw_qty = item_data.get('quantity', 0)
                qty = int(raw_qty)

                if qty <= 0:
                    del cart_session[item_id_str]
                    request.session.modified = True
                    continue

                calc = calculate_item_price(product, qty)
                cart_count += qty
                global_total += calc['subtotal']

                side_cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'price': calc['final_unit_price'],
                    'subtotal': calc['subtotal']
                })
        except (ValueError, TypeError):
            continue

    return {
        'cart_count': max(0, cart_count), # Force non-negative
        'side_cart_items': side_cart_items,
        'cart_global_total': global_total,
    }
