# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, Sum, F, DecimalField, ExpressionWrapper
from django.db import transaction
from django.forms import inlineformset_factory
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from .forms import *
from .models import *
from django.core.paginator import Paginator
from decimal import Decimal, InvalidOperation
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from .auth_utils import clear_backend_user, set_backend_user

# Permission check functions
def is_admin(user):
    """Check if user is admin (user_type=0 or superuser)"""
    return user.is_authenticated and (user.is_superuser or user.user_type == 0)

def is_vendor(user):
    """Check if user is vendor (user_type=2)"""
    return user.is_authenticated and user.user_type == 2

def is_customer(user):
    """Check if user is customer (user_type=1)"""
    return user.is_authenticated and user.user_type == 1

def is_admin_or_vendor(user):
    """Check if user is admin or vendor"""
    return user.is_authenticated and user.is_active and (user.is_superuser or user.user_type in [0, 2])


def _get_safe_redirect(request, fallback):
    redirect_to = request.POST.get('next') or request.GET.get('next')
    if redirect_to and url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return fallback


def admin_dashboard_entry(request):
    if is_admin(request.user):
        return redirect('dashboard')
    return redirect('backend_login')


def backend_login(request):
    if is_admin(request.user):
        return redirect('dashboard')

    form = BackendAuthenticationForm(request, data=request.POST or None)
    next_url = _get_safe_redirect(request, settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['username']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data.get('remember_me')
        user = authenticate(request, email=email, password=password)

        if user is None:
            messages.error(request, "Invalid email or password.")
        elif not user.is_active or user.status != 1:
            messages.error(request, "Your account is inactive. Please contact support.")
        elif not is_admin(user):
            messages.error(request, "You do not have backend access.")
        else:
            set_backend_user(request, user)
            if remember_me:
                request.session.set_expiry(1209600)
            else:
                request.session.set_expiry(0)
            messages.success(request, "Signed in successfully.")
            return redirect(next_url)

    return render(request, 'back/login&signup/sign-in.html', {
        'form': form,
        'next': next_url,
    })


def backend_signup(request):
    if is_admin(request.user):
        return redirect('dashboard')

    form = BackendSignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        set_backend_user(request, user)
        messages.success(request, "Account created successfully.")
        return redirect('dashboard')

    return render(request, 'back/login&signup/sign-up.html', {'form': form})


def backend_logout(request):
    clear_backend_user(request)
    messages.success(request, "You have been logged out.")
    return redirect('backend_login')


@login_required
def notification_open(request, pk):
    if not is_admin(request.user):
        clear_backend_user(request)
        messages.error(request, "You do not have permission to access the backend.")
        return redirect('backend_login')

    notification = get_object_or_404(AdminNotification, pk=pk)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    if notification.link:
        return redirect(notification.link)
    return redirect('dashboard')


@login_required
def notification_mark_all_read(request):
    if not is_admin(request.user):
        clear_backend_user(request)
        messages.error(request, "You do not have permission to access the backend.")
        return redirect('backend_login')

    AdminNotification.objects.filter(is_read=False).update(is_read=True)
    messages.success(request, "Notifications marked as read.")
    return redirect(request.GET.get('next') or 'dashboard')


@login_required
def admin_search(request):
    if not is_admin(request.user):
        clear_backend_user(request)
        return JsonResponse({'results': []}, status=403)

    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    results = []

    orders = Order.objects.filter(
        Q(order_id__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    ).order_by('-created_at')[:4]
    for order in orders:
        results.append({
            'type': 'Order',
            'title': order.order_id,
            'subtitle': f"{order.first_name} {order.last_name} - {order.status.title()}",
            'url': reverse('order_details', args=[order.order_id]),
        })

    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query)
    ).order_by('-created_at')[:4]
    for user in users:
        results.append({
            'type': 'User',
            'title': user.get_full_name() or user.email,
            'subtitle': user.email,
            'url': reverse('edit_user', args=[user.id]),
        })

    products = Product.objects.filter(
        Q(title__icontains=query) |
        Q(sku__icontains=query) |
        Q(model__icontains=query)
    ).order_by('-created_at')[:4]
    for product in products:
        results.append({
            'type': 'Product',
            'title': product.title,
            'subtitle': f"SKU: {product.sku}",
            'url': reverse('edit_product', args=[product.id]),
        })

    categories = Category.objects.filter(
        Q(name__icontains=query) |
        Q(slug__icontains=query)
    ).order_by('name')[:3]
    for category_item in categories:
        results.append({
            'type': 'Category',
            'title': category_item.name,
            'subtitle': category_item.slug,
            'url': f"{reverse('category')}?edit={category_item.id}",
        })

    contact_messages = ContactMessage.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(phone__icontains=query) |
        Q(message__icontains=query)
    ).order_by('-created_at')[:3]
    for contact_message in contact_messages:
        results.append({
            'type': 'Message',
            'title': f"{contact_message.first_name} {contact_message.last_name}".strip() or contact_message.email,
            'subtitle': contact_message.email,
            'url': reverse('contact_message_list'),
        })

    return JsonResponse({'results': results[:12]})

# Views
@login_required
def dashboard(request):
    """Admin dashboard view"""
    if not is_admin(request.user):
        clear_backend_user(request)
        messages.error(request, "You do not have permission to access the backend.")
        return redirect('backend_login')
    
    total_users = User.objects.count()
    active_users = User.objects.filter(status=1).count()
    total_products = Product.objects.count()
    published_products = Product.objects.filter(status='published').count()
    low_stock_products = Product.objects.filter(stock_quantity__gt=0, stock_quantity__lt=10).count()
    out_of_stock_products = Product.objects.filter(stock_quantity__lte=0).count()
    total_categories = Category.objects.count()
    active_sliders = Slider.objects.filter(status='active').count()
    total_reviews = Review.objects.count()
    pending_reviews = Review.objects.filter(status=False).count()
    delivery_charge_count = DeliveryCharge.objects.count()

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    processing_orders = Order.objects.filter(status='processing').count()
    shipped_orders = Order.objects.filter(status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()

    total_revenue = Order.objects.filter(status__in=['processing', 'shipped', 'delivered']).aggregate(
        total=Coalesce(Sum('total_amount'), Decimal('0.00'))
    )['total']
    today_orders = Order.objects.filter(created_at__date=timezone.localdate()).count()
    today_revenue = Order.objects.filter(
        created_at__date=timezone.localdate(),
        status__in=['processing', 'shipped', 'delivered']
    ).aggregate(total=Coalesce(Sum('total_amount'), Decimal('0.00')))['total']

    recent_orders = Order.objects.prefetch_related('items__product').order_by('-created_at')[:8]
    recent_users = User.objects.filter(user_type=1).annotate(
        order_count=Count('order'),
        total_spent=Coalesce(Sum('order__total_amount'), Decimal('0.00'))
    ).order_by('-created_at')[:6]
    recent_reviews_list = Review.objects.select_related('product').order_by('-created_at')[:6]

    revenue_expr = ExpressionWrapper(
        F('orderitem__quantity') * F('orderitem__price'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    top_products = Product.objects.annotate(
        total_units_sold=Coalesce(Sum('orderitem__quantity'), 0),
        total_sales=Coalesce(Sum(revenue_expr), Decimal('0.00')),
        approved_review_count=Count('reviews', filter=Q(reviews__status=True)),
    ).order_by('-total_units_sold', '-total_sales', 'title')[:5]

    low_stock_items = Product.objects.filter(stock_quantity__lt=10).order_by('stock_quantity', 'title')[:6]
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'total_products': total_products,
        'published_products': published_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'total_categories': total_categories,
        'active_sliders': active_sliders,
        'total_reviews': total_reviews,
        'pending_reviews': pending_reviews,
        'delivery_charge_count': delivery_charge_count,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'total_revenue': total_revenue,
        'today_orders': today_orders,
        'today_revenue': today_revenue,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'recent_reviews_list': recent_reviews_list,
        'top_products': top_products,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'back/dashboard/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def add_user(request):
    """Add new user (admin only)"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'User "{user.get_full_name()}" has been created successfully!')
            return redirect('user_list')
        else:
            # Show specific error messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'back/user/add.html', context)

@login_required
def user_profile(request, user_id=None):
    """View user profile"""
    if user_id and is_admin(request.user):
        # Admin viewing another user's profile
        user = get_object_or_404(User, id=user_id)
    else:
        # User viewing their own profile
        user = request.user
    
    # Handle profile update
    if request.method == 'POST' and request.user.id == user.id:
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('user_profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'profile_user': user,
        'form': form,
    }
    return render(request, 'back/user/profile.html', context)

@login_required
@user_passes_test(is_admin)
def user_list(request):
    """List all users (admin only)"""
    users_list = User.objects.all().order_by('-created_at')
    
    # Get total count
    total_users = users_list.count()
    
    # Apply filters
    user_type_filter = request.GET.get('user_type', 'all')
    status_filter = request.GET.get('status', 'all')
    search_query = request.GET.get('search', '')
    
    if search_query:
        users_list = users_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone__icontains=search_query)
        )
    
    if user_type_filter != 'all':
        users_list = users_list.filter(user_type=int(user_type_filter))
    
    if status_filter != 'all':
        users_list = users_list.filter(status=int(status_filter))
    
    # Get filtered count
    filtered_count = users_list.count()
    
    # Convert to list for template
    users = list(users_list)
    
    context = {
        'users': users,
        'total_users': total_users,
        'filtered_count': filtered_count,
        'user_type_filter': user_type_filter,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'back/user/list.html', context)

@login_required
@user_passes_test(is_admin)
def edit_user(request, user_id):
    """Edit user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'User "{user.get_full_name()}" has been updated successfully!')
            return redirect('user_list')
    else:
        form = UserUpdateForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
    }
    return render(request, 'back/user/edit.html', context)

@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """Delete user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deleting yourself
    if user.id == request.user.id:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('user_list')
    
    if request.method == 'POST':
        user_name = user.get_full_name()
        user.delete()
        messages.success(request, f'User "{user_name}" has been deleted successfully!')
        return redirect('user_list')
    
    context = {
        'user': user,
    }
    return render(request, 'back/user/delete_confirm.html', context)

@login_required
@user_passes_test(is_admin)
def toggle_user_status(request, user_id):
    """Toggle user active status (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deactivating yourself
    if user.id == request.user.id:
        messages.error(request, 'You cannot deactivate your own account!')
        return redirect('user_list')
    
    if user.status == 1:
        user.status = 0
        user.is_active = False
        status = "deactivated"
    else:
        user.status = 1
        user.is_active = True
        status = "activated"

    user.save(update_fields=['status', 'is_active', 'updated_at'])
    
    messages.success(request, f'User "{user.get_full_name()}" has been {status}!')
    return redirect('user_list')


@login_required
@user_passes_test(is_admin_or_vendor)
def add_banner(request):
    if request.method == 'POST':
        form = SliderForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Slider banner added successfully!')
            return redirect('add_banner')  # Redirect back to add page for another entry
        else:
            # Form has errors
            for field, errors in form.errors.items():
                for error in errors:
                    field_name = field.replace('_', ' ').title()
                    messages.error(request, f"{field_name}: {error}")
    else:
        form = SliderForm()
    
    return render(request, 'back/home/banner/add.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_vendor)
def banner_list(request):
    sliders = Slider.objects.all().order_by('order')
    return render(request, 'back/home/banner/list.html', {'sliders': sliders})

@login_required
@user_passes_test(is_admin_or_vendor)
def edit_banner(request, id):
    slider = get_object_or_404(Slider, id=id)
    
    if request.method == 'POST':
        form = SliderForm(request.POST, request.FILES, instance=slider)
        if form.is_valid():
            form.save()
            messages.success(request, 'Banner updated successfully!')
            return redirect('banner_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = SliderForm(instance=slider)
    
    return render(request, 'back/home/banner/edit.html', {'form': form, 'slider': slider})

from django.views.decorators.http import require_POST
@login_required
@user_passes_test(is_admin_or_vendor)
@require_POST
def delete_banner(request):
    banner_id = request.POST.get('id')
    slider = get_object_or_404(Slider, id=banner_id)
    slider.delete()
    return JsonResponse({'success': True, 'message': 'Banner deleted!'})


@login_required
@user_passes_test(is_admin)
def site_branding_settings(request):
    branding = SiteBranding.get_solo()

    if request.method == 'POST':
        form = SiteBrandingForm(request.POST, request.FILES, instance=branding)
        if form.is_valid():
            form.save()
            messages.success(request, 'Site branding updated successfully!')
            return redirect('site_branding_settings')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    else:
        form = SiteBrandingForm(instance=branding)

    context = {
        'page_title': 'Site Branding',
        'page_subtitle': 'Manage logo, footer logo, favicon, and basic brand text.',
        'form': form,
    }
    return render(request, 'back/dashboard/settings_form.html', context)


@login_required
@user_passes_test(is_admin)
def about_page_settings(request):
    about_page = AboutPage.get_solo()

    if request.method == 'POST':
        form = AboutPageForm(request.POST, request.FILES, instance=about_page)
        if form.is_valid():
            form.save()
            messages.success(request, 'About page updated successfully!')
            return redirect('about_page_settings')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    else:
        form = AboutPageForm(instance=about_page)

    context = {
        'page_title': 'About Us Page',
        'page_subtitle': 'Manage the About Us page content and image.',
        'form': form,
    }
    return render(request, 'back/dashboard/settings_form.html', context)


@login_required
@user_passes_test(is_admin)
def contact_page_settings(request):
    contact_page = ContactPage.get_solo()

    if request.method == 'POST':
        form = ContactPageForm(request.POST, request.FILES, instance=contact_page)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contact page updated successfully!')
            return redirect('contact_page_settings')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    else:
        form = ContactPageForm(instance=contact_page)

    context = {
        'page_title': 'Contact Us Page',
        'page_subtitle': 'Manage contact details, social links, and map embed.',
        'form': form,
    }
    return render(request, 'back/dashboard/settings_form.html', context)


@login_required
@user_passes_test(is_admin)
def contact_message_list(request):
    contact_messages = ContactMessage.objects.all()

    context = {
        'contact_messages': contact_messages,
    }
    return render(request, 'back/dashboard/contact_messages.html', context)


@login_required
@user_passes_test(is_admin)
def contact_message_toggle_read(request, pk):
    contact_message = get_object_or_404(ContactMessage, pk=pk)
    contact_message.is_read = not contact_message.is_read
    contact_message.save(update_fields=['is_read', 'updated_at'])

    if contact_message.is_read:
        messages.success(request, 'Message marked as read.')
    else:
        messages.warning(request, 'Message marked as unread.')

    return redirect('contact_message_list')


@login_required
@user_passes_test(is_admin)
def contact_message_delete(request, pk):
    contact_message = get_object_or_404(ContactMessage, pk=pk)
    contact_message.delete()
    messages.success(request, 'Contact message deleted successfully.')
    return redirect('contact_message_list')


@login_required
@user_passes_test(is_admin_or_vendor)
def category(request):
    # Handle form submission for add/edit
    if request.method == 'POST':
        if 'category_id' in request.POST:  # Edit existing category
            category = get_object_or_404(Category, id=request.POST.get('category_id'))
            form = CategoryForm(request.POST, request.FILES, instance=category)
            success_message = 'Category updated successfully!'
        else:  # Add new category
            form = CategoryForm(request.POST, request.FILES)
            success_message = 'Category added successfully!'
        
        if form.is_valid():
            form.save()
            messages.success(request, success_message)
            return redirect('category')  # Redirect to same page
    
    # Get all categories for the table
    categories = Category.objects.all()
    
    # If editing, get the category to edit
    edit_category = None
    if 'edit' in request.GET:
        edit_category = get_object_or_404(Category, id=request.GET.get('edit'))
    
    context = {
        'categories': categories,
        'form': CategoryForm(),
        'edit_category': edit_category,
        'edit_form': CategoryForm(instance=edit_category) if edit_category else None
    }
    return render(request, 'back/product/category/category.html', context)

@login_required
@user_passes_test(is_admin_or_vendor)
def delete_category(request, id):
    if request.method == 'POST':
        category = get_object_or_404(Category, id=id)
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        return redirect('category')
    return redirect('category')

@login_required
@user_passes_test(is_admin_or_vendor)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        discount_formset = ProductDiscountFormSet(request.POST, prefix='discounts')

        if form.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()

                    if discount_formset.is_valid():
                        discount_formset.instance = product
                        discount_formset.save()
                    else:
                        for formset_error in discount_formset.errors:
                            for error in formset_error.values():
                                messages.error(request, f"Discount: {error}")
                        raise ValueError("Discount formset validation failed.")

                    additional_images = request.FILES.getlist('additional_images')
                    for i, image_file in enumerate(additional_images, start=1):
                        if image_file.size > 5 * 1024 * 1024:
                            messages.warning(request, f"Image {image_file.name} is too large (max 5MB)")
                            continue
                        
                        ProductImage.objects.create(
                            product=product,
                            image=image_file,
                            position=i,
                            alt_text=f"{product.title} - Image {i}",
                            is_primary=False
                        )
                
                messages.success(request, f'Product "{product.title}" added successfully!')
                return redirect('product_list')
                
            except Exception as e:
                messages.error(request, f'Error saving product: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    
    else:
        form = ProductForm()
        discount_formset = ProductDiscountFormSet(prefix='discounts', queryset=ProductDiscount.objects.none())
    
    context = {
        'form': form,
        'discount_formset': discount_formset,
        'categories': Category.objects.filter(status='active'),
    }
    return render(request, 'back/product/product/add.html', context)


@login_required
@user_passes_test(is_admin_or_vendor)
def edit_product(request, id):
    product = get_object_or_404(Product, id=id)
    product_images = product.images.all().order_by('position')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        discount_formset = ProductDiscountFormSet(request.POST, instance=product, prefix='discounts')
        
        if form.is_valid() and discount_formset.is_valid():
            try:
                with transaction.atomic():
                    product = form.save()
                    discount_formset.save()
                    
                    additional_images = request.FILES.getlist('additional_images')
                    
                    if additional_images:
                        start_position = product_images.count() + 1
                        for i, image_file in enumerate(additional_images, start=start_position):
                            if image_file.size > 5 * 1024 * 1024:
                                messages.warning(request, f"Image {image_file.name} is too large (max 5MB)")
                                continue
                            
                            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                            import os
                            ext = os.path.splitext(image_file.name)[1].lower()
                            if ext not in valid_extensions:
                                messages.warning(request, f"Image {image_file.name} has invalid format")
                                continue
                            
                            ProductImage.objects.create(
                                product=product,
                                image=image_file,
                                position=i,
                                alt_text=f"{product.title} - Image {i}",
                                is_primary=False
                            )
                
                messages.success(request, f'Product "{product.title}" updated successfully!')
                return redirect('edit_product', id=product.id)
                
            except Exception as e:
                messages.error(request, f'Error updating product: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            for formset_error in discount_formset.errors:
                for error in formset_error.values():
                    messages.error(request, f"Discount: {error}")
    else:
        # GET request - populate form with existing product data
        form = ProductForm(instance=product)
        discount_formset = ProductDiscountFormSet(instance=product, prefix='discounts')
    
    context = {
        'form': form,
        'discount_formset': discount_formset,
        'product': product,
        'product_images': product_images,
        'categories': Category.objects.filter(status='active'),
    }
    return render(request, 'back/product/product/edit.html', context)


@login_required
@user_passes_test(is_admin_or_vendor)
def delete_product(request, id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=id)
        product_name = product.title
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully!')
        return redirect('product_list')
    return redirect('product_list')

@login_required
@user_passes_test(is_admin_or_vendor)
def delete_product_image(request, id):
    if request.method == 'POST':
        image = get_object_or_404(ProductImage, id=id)
        product_id = image.product.id
        image.delete()
        messages.success(request, 'Image deleted successfully!')
        return redirect('edit_product', id=product_id)
    return redirect('product_list')

@login_required
@user_passes_test(is_admin_or_vendor)
def product_list(request):
    products = Product.objects.all().order_by('-created_at')
    
    # Calculate stats
    total_products = products.count()
    active_products = products.filter(status='published').count()
    low_stock_count = products.filter(stock_quantity__lt=10, stock_quantity__gt=0).count()
    out_of_stock_count = products.filter(stock_quantity=0).count()
    
    context = {
        'products': products,
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'back/product/product/list.html', context)

@login_required
@user_passes_test(is_admin_or_vendor)
def set_primary_image(request, id):
    if request.method == 'POST':
        image = get_object_or_404(ProductImage, id=id)
        product = image.product
        
        # Set all images to not primary
        ProductImage.objects.filter(product=product).update(is_primary=False)
        
        # Set this image as primary
        image.is_primary = True
        image.save()
        
        messages.success(request, 'Primary image updated successfully!')
        return redirect('edit_product', id=product.id)
    return redirect('product_list')

@login_required
@user_passes_test(is_admin_or_vendor)
def review(request):
    # Fetch all reviews, newest first
    reviews = Review.objects.all().order_by('-created_at')
    
    context = {
        'reviews': reviews
    }
    return render(request, 'back/product/product/review.html', context)

@login_required
@user_passes_test(is_admin_or_vendor)
def review_delete(request, pk):
    # Get the review or return 404
    review_item = get_object_or_404(Review, pk=pk)
    
    # Delete it
    review_item.delete()
    messages.success(request, "Review deleted successfully.")
    
    # Redirect back to the review list
    return redirect('review')
@login_required
@user_passes_test(is_admin_or_vendor)
def review_status(request, pk):
    # Get the review
    review_item = get_object_or_404(Review, pk=pk)
    
    # Flip the status
    if review_item.status:
        review_item.status = False
        messages.warning(request, "Review is now Hidden.")
    else:
        review_item.status = True
        messages.success(request, "Review is now Visible.")
        
    review_item.save()
    
    # Reload the page
    return redirect('review')


# delivery_charge views - BETTER ALTERNATIVE APPROACH

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from .models import DeliveryCharge

# 1. List Page (The Main View)
@login_required
@user_passes_test(is_admin_or_vendor)
@require_http_methods(["GET"])
def delivery_charge_list(request):
    """Display all delivery charges"""
    charges = DeliveryCharge.objects.all().order_by('district', 'thana')
    return render(request, 'back/order/deliverycharge/dc.html', {'charges': charges})


# 2. Add Function
@login_required
@user_passes_test(is_admin_or_vendor)
@require_POST
def delivery_charge_add(request):
    """Add a new delivery charge - POST only"""
    district = request.POST.get('district')
    thana = request.POST.get('thana', '').strip()  # Remove whitespace
    amount = request.POST.get('amount')

    # Basic Validation
    if not district or not amount:
        messages.error(request, "District and Amount are required")
        return redirect('delivery_charge_list')

    # Validate amount is a valid number
    try:
        amount = Decimal(amount)
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('delivery_charge_list')
    except (InvalidOperation, TypeError):
        messages.error(request, "Invalid amount format")
        return redirect('delivery_charge_list')

    # Check for duplicate
    thana_value = thana if thana else None
    if DeliveryCharge.objects.filter(district=district, thana=thana_value).exists():
        location = f"{district} - {thana}" if thana else f"{district} (All Thanas)"
        messages.error(request, f"Delivery charge for {location} already exists")
        return redirect('delivery_charge_list')

    # Create
    DeliveryCharge.objects.create(
        district=district,
        thana=thana_value,
        amount=amount
    )
    
    location = f"{district} - {thana}" if thana else f"{district} (All Thanas)"
    messages.success(request, f"Delivery charge for {location} added successfully (৳{amount})")
    
    return redirect('delivery_charge_list')


# 3. Edit Function
@login_required
@user_passes_test(is_admin_or_vendor)
@require_POST
def delivery_charge_edit(request, pk):
    """Edit delivery charge - POST only"""
    charge = get_object_or_404(DeliveryCharge, pk=pk)
    
    # Get form data
    amount = request.POST.get('amount')
    
    # Validation
    if not amount:
        messages.error(request, "Amount is required")
        return redirect('delivery_charge_list')
    
    # Validate amount
    try:
        amount = Decimal(amount)
        if amount <= 0:
            messages.error(request, "Amount must be greater than 0")
            return redirect('delivery_charge_list')
    except (InvalidOperation, TypeError):
        messages.error(request, "Invalid amount format")
        return redirect('delivery_charge_list')
    
    # Update only the amount (district and thana should be readonly)
    old_amount = charge.amount
    charge.amount = amount
    charge.save()
    
    location = f"{charge.district} - {charge.thana}" if charge.thana else f"{charge.district} (All Thanas)"
    messages.success(request, f"Updated {location}: ৳{old_amount} → ৳{amount}")
    
    return redirect('delivery_charge_list')


# 4. Delete Function
@login_required
@user_passes_test(is_admin_or_vendor)
@require_http_methods(["GET", "POST"])  # Allow both for link click and form submission
def delivery_charge_delete(request, pk):
    """Delete delivery charge"""
    charge = get_object_or_404(DeliveryCharge, pk=pk)
    
    # Store info for success message
    location = f"{charge.district} - {charge.thana}" if charge.thana else f"{charge.district} (All Thanas)"
    amount = charge.amount
    
    # Delete
    charge.delete()
    
    messages.success(request, f"Deleted: {location} (৳{amount})")
    return redirect('delivery_charge_list')


@login_required
@user_passes_test(is_admin_or_vendor)
def order_list(request):
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    district_filter = request.GET.get('district', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    if district_filter:
        orders = orders.filter(district=district_filter)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Get counts for different statuses
    total_orders = Order.objects.count()
    pending_count = Order.objects.filter(status='pending').count()
    processing_count = Order.objects.filter(status='processing').count()
    shipped_count = Order.objects.filter(status='shipped').count()
    delivered_count = Order.objects.filter(status='delivered').count()
    cancelled_count = Order.objects.filter(status='cancelled').count()
    
    # Get all unique districts for filter dropdown
    districts = Order.objects.values_list('district', flat=True).distinct()
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'districts': districts,
        'status_filter': status_filter,
        'district_filter': district_filter,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'back/order/orders/order_list.html', context)


@login_required
@user_passes_test(is_admin_or_vendor)
def order_details(request, order_id):
    # Get specific order by ID or order_id
    order = get_object_or_404(Order, order_id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    
    # Calculate product subtotal from order items (for display only)
    product_subtotal = sum(item.subtotal() for item in order_items)
    
    # Calculate status index for tracking progress bar
    status_mapping = {
        'pending': 1,
        'processing': 2,
        'shipped': 3,
        'delivered': 4,
        'cancelled': 0,
    }
    status_index = status_mapping.get(order.status, 1)
    
    context = {
        'order': order,
        'order_items': order_items,
        'product_subtotal': product_subtotal,  # Just for display
        'status_index': status_index,
    }
    return render(request, 'back/order/orders/order-detail.html', context)


@login_required
@user_passes_test(is_admin_or_vendor)
def invoice(request, order_id):
    # Get the specific order
    order = get_object_or_404(Order, order_id=order_id)
    order_items = OrderItem.objects.filter(order=order)
    
    # Calculate product subtotal from order items
    product_subtotal = sum(item.subtotal() for item in order_items)
    
    # The order.total_amount already includes delivery charge
    # So we just use it as grand_total
    context = {
        'order': order,
        'order_items': order_items,
        'product_subtotal': product_subtotal,  # Products only
        'grand_total': order.total_amount,  # Already includes delivery
    }
    return render(request, 'back/order/orders/invoice.html', context)


@login_required
@user_passes_test(is_admin_or_vendor)
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, order_id=order_id)
    new_status = request.POST.get('status')
    
    if new_status in dict(Order.ORDER_STATUS):
        order.status = new_status
        order.save()
        
        # You can add notification logic here
        # e.g., send email to customer about status update
        
        return JsonResponse({
            'success': True,
            'message': f'Order status updated to {new_status}',
            'status': new_status
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid status'
    }, status=400)
