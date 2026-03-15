from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from backend.models import *
from backend.forms import ReviewForm, OrderForm, ContactMessageForm
from django.db.models import Count, Q
from django.db.models import Avg
from django.db.models import Min, Max
from decimal import Decimal
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from backend.auth_utils import clear_frontend_user, set_backend_user, set_frontend_user
from backend.forms import UserProfileForm
# Create your views here.

from django.db.models import Count, Q, Avg  # <--- Make sure Avg is imported

def home(request):
    # Get active sliders
    sliders = Slider.objects.filter(status='active').order_by('order')
    
    # Get active categories
    categories = Category.objects.filter(status='active').annotate(
        product_count=Count('products', filter=Q(products__status='published'))
    ).order_by('name')[:8]
    
    # --- STEP 1: Define the Rating Logic ---
    # This calculates the average of 'reviews__rating' ONLY where status=True
    # We create this variable once to reuse it in all queries below.
    rating_annotation = Avg('reviews__rating', filter=Q(reviews__status=True))

    # --- STEP 2: Add .annotate(avg_rating=rating_annotation) to queries ---

    # 1. New Products
    new_products = Product.objects.filter(
        status='published',
        new=True
    ).annotate(avg_rating=rating_annotation).select_related('category').order_by('-created_at')[:12]
    
    # 2. Featured Products
    featured_products = Product.objects.filter(
        status='published',
        featured=True
    ).annotate(avg_rating=rating_annotation).select_related('category').order_by('-created_at')[:12]
    
    # 3. Best Sellers
    best_sellers = Product.objects.filter(
        status='published',
        best_seller=True
    ).annotate(avg_rating=rating_annotation).select_related('category').order_by('-created_at')[:4]
    
    # 4. Trending Products
    trending_products = Product.objects.filter(
        status='published',
        trending=True
    ).annotate(avg_rating=rating_annotation).select_related('category').order_by('-created_at')[:4]
    
    # 5. Top Rated Products
    # Ideally, we order this list by the rating we just calculated ('-avg_rating')
    top_rated = Product.objects.filter(
        status='published'
    ).annotate(avg_rating=rating_annotation).select_related('category').order_by('-avg_rating')[:4]
    
    context = {
        'sliders': sliders,
        'categories': categories,
        'new_products': new_products,
        'featured_products': featured_products,
        'best_sellers': best_sellers,
        'trending_products': trending_products,
        'top_rated': top_rated,
    }
    return render(request, 'front/index.html', context)

def allProducts(request):
    def _clean_price(value, default):
        cleaned = ''.join(ch for ch in str(value or '') if ch.isdigit())
        try:
            return int(cleaned) if cleaned else default
        except (TypeError, ValueError):
            return default

    rating_annotation = Avg('reviews__rating', filter=Q(reviews__status=True))
    category_slug = (request.GET.get('category') or '').strip()
    search_query = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'newest').strip()
    per_page_raw = (request.GET.get('per_page') or '12').strip().lower()

    catalog_queryset = Product.objects.filter(
        status='published'
    ).select_related('category').annotate(avg_rating=rating_annotation)
    base_queryset = catalog_queryset

    active_categories = Category.objects.filter(status='active').annotate(
        product_count=Count('products', filter=Q(products__status='published'))
    ).order_by('name')

    selected_category = None
    if category_slug:
        selected_category = active_categories.filter(slug=category_slug).first()
        if selected_category:
            catalog_queryset = catalog_queryset.filter(category=selected_category)

    if search_query:
        catalog_queryset = catalog_queryset.filter(
            Q(title__icontains=search_query) |
            Q(sku__icontains=search_query) |
            Q(model__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        ).distinct()

    price_bounds = catalog_queryset.aggregate(
        max_price=Max('selling_price'),
    )
    catalog_min_price = 0
    catalog_max_price = int(price_bounds['max_price'] or 0)

    min_price = _clean_price(request.GET.get('min_price', catalog_min_price), catalog_min_price)
    max_price = _clean_price(request.GET.get('max_price', catalog_max_price), catalog_max_price)

    if min_price > max_price:
        min_price, max_price = max_price, min_price

    if catalog_queryset.exists():
        catalog_queryset = catalog_queryset.filter(
            selling_price__gte=min_price,
            selling_price__lte=max_price,
        )

    sort_map = {
        'newest': '-created_at',
        'name_asc': 'title',
        'name_desc': '-title',
        'price_asc': 'selling_price',
        'price_desc': '-selling_price',
    }
    catalog_queryset = catalog_queryset.order_by(sort_map.get(sort, '-created_at'))

    per_page_map = {
        '8': 8,
        '12': 12,
        '24': 24,
        'all': catalog_queryset.count() or 1,
    }
    selected_per_page = per_page_raw if per_page_raw in per_page_map else '12'

    paginator = Paginator(catalog_queryset, per_page_map[selected_per_page])
    page_obj = paginator.get_page(request.GET.get('page'))

    query_without_page = request.GET.copy()
    query_without_page.pop('page', None)
    query_without_page = query_without_page.urlencode()

    category_links = []
    for category in active_categories:
        category_query = request.GET.copy()
        category_query.pop('page', None)
        category_query['category'] = category.slug
        category_links.append({
            'category': category,
            'url': category_query.urlencode(),
            'is_active': selected_category and selected_category.id == category.id,
        })

    all_products_query = request.GET.copy()
    all_products_query.pop('page', None)
    all_products_query.pop('category', None)
    all_products_query = all_products_query.urlencode()

    all_products_count = base_queryset.count()

    page_start = ((page_obj.number - 1) * paginator.per_page) + 1 if paginator.count else 0
    page_end = page_start + len(page_obj.object_list) - 1 if paginator.count else 0

    if search_query:
        page_title = f'Search results for "{search_query}"'
    else:
        page_title = selected_category.name if selected_category else 'All Products'

    context = {
        'products': page_obj,
        'active_categories': active_categories,
        'category_links': category_links,
        'selected_category': selected_category,
        'selected_sort': sort,
        'search_query': search_query,
        'selected_min_price': min_price,
        'selected_max_price': max_price,
        'catalog_min_price': catalog_min_price,
        'catalog_max_price': catalog_max_price,
        'selected_per_page': selected_per_page,
        'query_without_page': query_without_page,
        'all_products_query': all_products_query,
        'all_products_count': all_products_count,
        'page_start': page_start,
        'page_end': page_end,
        'page_title': page_title,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'toolbar_html': render_to_string('front/products/_catalog_toolbar.html', context, request=request),
            'results_html': render_to_string('front/products/_catalog_results.html', context, request=request),
            'category_html': render_to_string('front/products/_category_filter.html', context, request=request),
            'price_html': render_to_string('front/products/_price_filter.html', context, request=request),
            'page_title': page_title,
        })

    return render(request, 'front/products/allproducts.html', context)

def singleproduct(request, slug):
    product = get_object_or_404(Product, slug=slug)
    
    # Fetch reviews for this product
    reviews = Review.objects.filter(product=product, status=True)
    
    # --- NEW LOGIC: Calculate Average ---
    # This calculates the average of the 'rating' field
    avg_data = reviews.aggregate(Avg('rating'))
    avg_rating = avg_data['rating__avg']
    
    # Handle the case where there are no reviews yet
    if avg_rating is None:
        avg_rating = 5
        int_avg_rating = 5
    else:
        avg_rating = round(avg_rating, 1)      # e.g., 4.3
        int_avg_rating = round(avg_rating)     # e.g., 4 (used for star loop)
    # ------------------------------------
    
    context = {
        'product': product,
        'reviews': reviews,
        'review_count': reviews.count(),
        'avg_rating': avg_rating,         
        'int_avg_rating': int_avg_rating,
    }
    return render(request, 'front/products/singleproduct.html', context)

def submit_review(request, product_id):
    if request.method == 'POST':
        try:
            # We don't check for login anymore. We just save the form.
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = form.save(commit=False)
                data.product_id = product_id
                data.save()
                messages.success(request, "Thank you! Your review has been submitted.")
            else:
                messages.error(request, "Please fill required fields correctly.")
                
        except Exception as e:
            messages.error(request, "Something went wrong.")

        return redirect(request.META.get('HTTP_REFERER', 'singleproduct'))
        
    return redirect('singleproduct')


def contactus(request):
    try:
        contact_page = ContactPage.get_solo()
    except Exception:
        contact_page = ContactPage()

    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message was sent successfully.')
            return redirect('contactus')

        messages.error(request, 'Please fill out the required fields correctly.')
    else:
        form = ContactMessageForm()

    return render(
        request,
        'front/contactus/contactus.html',
        {
            'contact_page': contact_page,
            'contact_form': form,
        },
    )

def aboutus(request):
    try:
        about_page = AboutPage.get_solo()
    except Exception:
        about_page = AboutPage()

    return render(
        request,
        'front/aboutus/aboutus.html',
        {'about_page': about_page},
    )

from .cart_logic import calculate_item_price
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json


def _build_side_cart_payload(request):
    cart_session = request.session.get('cart', {})
    cart_count = 0
    side_cart_items = []
    cart_total = Decimal("0.00")

    if not isinstance(cart_session, dict):
        cart_session = {}

    product_ids = [int(k) for k in cart_session.keys() if str(k).isdigit()]
    products = Product.objects.in_bulk(product_ids)

    for item_id_str, item_data in list(cart_session.items()):
        try:
            product_id = int(item_id_str)
            quantity = int(item_data.get('quantity', 0))
        except (TypeError, ValueError):
            continue

        if quantity <= 0 or product_id not in products:
            continue

        product = products[product_id]
        calc = calculate_item_price(product, quantity)
        cart_count += quantity
        cart_total += calc['subtotal']
        side_cart_items.append({
            'product': product,
            'quantity': quantity,
            'price': calc['final_unit_price'],
            'subtotal': calc['subtotal'],
        })

    sidebar_html = render_to_string(
        'front/partial/side_cart_items.html',
        {'side_cart_items': side_cart_items},
        request=request,
    )

    return {
        'cart_count': max(0, cart_count),
        'cart_total': str(cart_total.quantize(Decimal("0.01"))),
        'sidebar_html': sidebar_html,
    }


# 1. Cart Page View
def cart(request):
    # 1. Get the cart data from session
    cart_session = request.session.get('cart', {})
    
    cart_items = []
    grand_total = Decimal("0.00")
    
    if cart_session:
        # 2. Get all Product IDs from the session keys
        # We convert keys to int because session keys are stored as strings
        product_ids = [int(k) for k in cart_session.keys()]
        
        # 3. Fetch all actual Product objects from DB in one query
        products = Product.objects.in_bulk(product_ids)
        
        # 4. Loop through session items and match with DB objects
        for item_id_str, item_data in cart_session.items():
            product_id = int(item_id_str)
            
            if product_id in products:
                product = products[product_id]
                qty = int(item_data.get('quantity', 0))
                
                # Calculate prices using your logic helper
                calc = calculate_item_price(product, qty)
                
                # Add to grand total
                grand_total += calc['subtotal']
                
                # Append to list to send to template
                cart_items.append({
                    'product': product,
                    'quantity': qty,
                    'unit_price': calc['final_unit_price'],
                    'subtotal': calc['subtotal'],
                })
    
    context = {
        'cart_items': cart_items,
        'grand_total': grand_total,
    }
    
    return render(request, 'front/order/cart.html', context)

# 2. Add To Cart (Handles both Home Page and Single Product Page)
@require_POST
def add_to_cart(request, id):
    product = get_object_or_404(Product, pk=id, status='published')
    product_id = str(id)
    cart = request.session.get('cart', {})
    
    # Get quantity: From POST data or default to 1
    try:
        qty = int(request.POST.get('qty', 1))
        if qty < 1: qty = 1
    except (ValueError, TypeError):
        qty = 1

    # Logic: Update or Create
    if product_id in cart:
        cart[product_id]['quantity'] += qty
    else:
        cart[product_id] = {'quantity': qty}

    # Safety Check
    if cart[product_id]['quantity'] < 1:
        cart[product_id]['quantity'] = 1

    request.session['cart'] = cart
    request.session.modified = True
    cart_payload = _build_side_cart_payload(request)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'cart_count': cart_payload['cart_count'],
            'cart_total': cart_payload['cart_total'],
            'sidebar_html': cart_payload['sidebar_html'],
            'product_id': product.id,
            'message': 'Product added to cart'
        })

    messages.success(request, "Product added to cart")
    return redirect('cart')


@require_POST
def buy_now(request, id):
    product = get_object_or_404(Product, pk=id, status='published')

    try:
        qty = int(request.POST.get('qty', 1))
        if qty < 1:
            qty = 1
    except (ValueError, TypeError):
        qty = 1

    request.session['cart'] = {
        str(product.id): {'quantity': qty}
    }
    request.session.modified = True

    return redirect('checkout')

# 3. Update Quantity (Plus/Minus in Cart Page)
@require_POST
def update_quantity(request):
    item_id = str(request.POST.get('id'))
    try:
        quantity = int(request.POST.get('quantity', 1))
        if quantity < 1: quantity = 1
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)

    cart = request.session.get('cart', {})

    if item_id in cart:
        product = get_object_or_404(Product, pk=item_id)
        
        # Stock Check
        if product.stock_quantity < quantity:
             return JsonResponse({
                 'success': False, 
                 'error': f"Only {product.stock_quantity} available"
             }, status=400)

        cart[item_id]['quantity'] = quantity
        request.session['cart'] = cart
        request.session.modified = True
        
        # Recalculate just this item for the AJAX update
        calc = calculate_item_price(product, quantity)
        
        # We also need the GLOBAL grand total to update the bottom bar
        # Simple loop to calculate global total for the JSON response
        grand_total = Decimal("0.00")
        products = Product.objects.in_bulk([int(k) for k in cart.keys()])
        for cid, data in cart.items():
            if int(cid) in products:
                c_prod = products[int(cid)]
                c_qty = int(data['quantity'])
                c_calc = calculate_item_price(c_prod, c_qty)
                grand_total += c_calc['subtotal']
        cart_payload = _build_side_cart_payload(request)

        return JsonResponse({
            'success': True,
            'cart_count': cart_payload['cart_count'],
            'item_subtotal': str(calc['subtotal'].quantize(Decimal("0.01"))),
            'grand_total': str(grand_total.quantize(Decimal("0.01"))),
            'cart_total': cart_payload['cart_total'],
            'sidebar_html': cart_payload['sidebar_html']
        })

    return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)

# 4. Remove Item
@require_POST
def remove_item(request):
    item_id = str(request.POST.get('id'))
    cart = request.session.get('cart', {})
    
    if item_id in cart:
        del cart[item_id]
        request.session['cart'] = cart
        request.session.modified = True
        
        # Recalculate Grand Total after removal
        grand_total = Decimal("0.00")
        products = Product.objects.in_bulk([int(k) for k in cart.keys()])
        for cid, data in cart.items():
            if int(cid) in products:
                c_prod = products[int(cid)]
                c_qty = int(data['quantity'])
                c_calc = calculate_item_price(c_prod, c_qty)
                grand_total += c_calc['subtotal']
        cart_payload = _build_side_cart_payload(request)

        return JsonResponse({
            'success': True,
            'cart_count': cart_payload['cart_count'],
            'grand_total': str(grand_total.quantize(Decimal("0.01"))),
            'cart_total': cart_payload['cart_total'],
            'sidebar_html': cart_payload['sidebar_html']
        })

    return JsonResponse({'success': False, 'error': 'Item not found'})

def checkout(request):
    """Enhanced checkout with automatic delivery charge calculation"""
    
    # 1. Get Cart Data
    cart_session = request.session.get('cart', {})
    
    # Redirect if empty
    if not cart_session:
        messages.warning(request, "Your cart is empty.")
        return redirect('allProducts')

    # 2. Calculate Cart Totals
    cart_items = []
    grand_total = Decimal("0.00")
    
    product_ids = [int(k) for k in cart_session.keys()]
    products = Product.objects.in_bulk(product_ids)
    
    for item_id_str, item_data in cart_session.items():
        pid = int(item_id_str)
        if pid in products:
            product = products[pid]
            qty = int(item_data['quantity'])
            
            calc = calculate_item_price(product, qty)
            grand_total += calc['subtotal']
            
            cart_items.append({
                'product': product,
                'quantity': qty,
                'price': calc['final_unit_price'],
                'subtotal': calc['subtotal']
            })

    # 3. Handle POST Request (Place Order)
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Get delivery charge from POST
            delivery_charge = Decimal(request.POST.get('delivery_charge', '0'))
            
            # Create Order
            order = form.save(commit=False)
            
            if request.user.is_authenticated:
                order.user = request.user
            
            order.subtotal = grand_total
            order.delivery_charge = delivery_charge
            order.total_amount = grand_total + delivery_charge
            order.payment_method = request.POST.get('payment_method', 'COD')
            order.save()
            
            # Save Order Items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )
                
                # Reduce stock
                product = item['product']
                product.stock_quantity -= item['quantity']
                product.save()
            
            # Clear Cart
            request.session['cart'] = {}
            request.session.modified = True
            
            messages.success(request, f"Order #{order.order_id} placed successfully!")
            return redirect('order_success', order_id=order.order_id)
            
        else:
            messages.error(request, "Please fill all required fields correctly.")
    
    else:
        # Pre-fill form if user is logged in
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': getattr(request.user, 'phone', ''),
            }
        form = OrderForm(initial=initial_data)

    context = {
        'cart_items': cart_items,
        'grand_total': grand_total,
        'delivery_charge': Decimal('0.00'),  # Will be updated by AJAX
        'final_total': grand_total,
        'form': form
    }
    return render(request, 'front/order/checkout.html', context)


@require_POST
def get_delivery_charge(request):
    """
    AJAX endpoint to fetch delivery charge based on district and thana.
    
    Priority Logic:
    1. First check for specific District + Thana combination
    2. If not found, check for District-wide charge (thana=null)
    3. If still not found, return 0
    """
    import json
    
    try:
        data = json.loads(request.body)
        district = data.get('district', '').strip()
        thana = data.get('thana', '').strip()
        
        if not district:
            return JsonResponse({
                'success': False,
                'error': 'District is required'
            }, status=400)
        
        # PRIORITY 1: Look for specific District + Thana
        if thana:
            specific_charge = DeliveryCharge.objects.filter(
                district=district,
                thana=thana
            ).first()
            
            if specific_charge:
                return JsonResponse({
                    'success': True,
                    'charge': float(specific_charge.amount),
                    'location': f"{district} - {thana}"
                })
        
        # PRIORITY 2: Look for District-wide charge (thana is null or empty)
        district_charge = DeliveryCharge.objects.filter(
            district=district,
            thana__isnull=True
        ).first()
        
        if district_charge:
            return JsonResponse({
                'success': True,
                'charge': float(district_charge.amount),
                'location': f"{district} (All Thanas)"
            })
        
        # PRIORITY 3: No charge found, return 0
        return JsonResponse({
            'success': True,
            'charge': 0,
            'location': district,
            'message': 'No delivery charge set for this location'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)



def order_success(request, order_id):
    """
    Display order success page after placing an order
    """
    try:
        # Try to get the order
        order = get_object_or_404(Order, order_id=order_id)
        
        # Optional: Check if the order belongs to the logged-in user
        # if request.user.is_authenticated and order.user != request.user:
        #     messages.error(request, "You don't have permission to view this order.")
        #     return redirect('home')
        
        context = {
            'order': order,
            'order_items': order.items.all(),
            'grand_total': order.total_amount + order.delivery_charge
        }
        
        return render(request, 'front/order/success.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading order: {str(e)}")
        return redirect('cart')








def login(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.user_type == 0:
            return redirect('dashboard')
        return redirect(request.GET.get('next') or 'user_dashboard')

    next_url = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''
        user = authenticate(request, email=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
        elif not user.is_active or user.status != 1:
            messages.error(request, "Your account is inactive.")
        elif user.is_superuser or user.user_type == 0:
            set_backend_user(request, user)
            messages.success(request, "Logged in successfully.")
            return redirect('dashboard')
        else:
            set_frontend_user(request, user)
            messages.success(request, "Logged in successfully.")

            if next_url:
                return redirect(next_url)
            return redirect('user_dashboard')

    return render(request, 'front/authentication/login.html', {'next': next_url})

def register(request):
    if request.user.is_authenticated:
        return redirect('user_dashboard')

    if request.method == 'POST':
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        phone = (request.POST.get('phone') or '').strip()
        address = (request.POST.get('address') or '').strip()
        password = request.POST.get('password') or ''
        confirm_password = request.POST.get('confirm_password') or ''

        if not first_name or not last_name or not email or not password or not confirm_password:
            messages.error(request, "Please fill in all required fields.")
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with this email already exists.")
        elif len(password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                address=address,
                user_type=1,
                status=1,
                is_active=True,
            )
            set_frontend_user(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('user_dashboard')

    return render(request, 'front/authentication/register.html')


def logout_view(request):
    clear_frontend_user(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')


@login_required(login_url='login')
def user_dashboard(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created_at')
    profile_form = UserProfileForm(instance=request.user)
    password_form = PasswordChangeForm(request.user)
    active_tab = (request.GET.get('tab') or 'overview').strip() or 'overview'

    def build_dashboard_context():
        status_counts = {
            'pending': orders.filter(status='pending').count(),
            'processing': orders.filter(status='processing').count(),
            'shipped': orders.filter(status='shipped').count(),
            'delivered': orders.filter(status='delivered').count(),
            'cancelled': orders.filter(status='cancelled').count(),
        }

        return {
            'profile_form': profile_form,
            'password_form': password_form,
            'orders': orders,
            'recent_orders': orders[:6],
            'status_counts': status_counts,
            'active_tab': active_tab,
        }

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'profile':
            profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
            active_tab = 'profile'
            if profile_form.is_valid():
                profile_form.save()
                context = build_dashboard_context()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Your profile was updated successfully.',
                        'tab': 'profile',
                        'html': render_to_string('front/account/partials/profile_tab.html', context, request=request),
                    })
                messages.success(request, "Your profile was updated successfully.")
                return redirect('user_dashboard')

            context = build_dashboard_context()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please check your profile details and try again.',
                    'tab': 'profile',
                    'html': render_to_string('front/account/partials/profile_tab.html', context, request=request),
                }, status=400)
            messages.error(request, "Please check your profile details and try again.")

        elif form_type == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            active_tab = 'password'
            if password_form.is_valid():
                password_form.save()
                password_form = PasswordChangeForm(request.user)
                context = build_dashboard_context()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Password updated successfully.',
                        'tab': 'password',
                        'html': render_to_string('front/account/partials/password_tab.html', context, request=request),
                    })
                messages.success(request, "Password updated successfully.")
                return redirect('user_dashboard')

            context = build_dashboard_context()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the password form errors.',
                    'tab': 'password',
                    'html': render_to_string('front/account/partials/password_tab.html', context, request=request),
                }, status=400)
            messages.error(request, "Please correct the password form errors.")

    context = build_dashboard_context()
    return render(request, 'front/account/dashboard.html', context)


@login_required(login_url='login')
def user_orders(request):
    return redirect('user_dashboard')


@login_required(login_url='login')
def change_password(request):
    return redirect('user_dashboard')

def policy(request):
    return render (request,'front/terms&policy/policy.html')

def terms(request):
    return render (request,'front/terms&policy/terms.html')

def blog(request):
    return render (request,'front/blog/blog.html')

def blogDetails(request):
    return render (request,'front/blog/blogdetail.html')
