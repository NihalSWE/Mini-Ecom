from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *
from .forms import *

class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserUpdateForm
    add_form = UserCreationForm
    
    # The fields to be used in displaying the User model
    list_display = ('email', 'first_name', 'last_name', 'get_user_type_display', 'get_status_display', 'is_active', 'created_at')
    list_filter = ('user_type', 'status', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'date_joined')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'address', 'profile_image')}),
        ('User Type & Status', {'fields': ('user_type', 'status')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'profile_image', 'phone', 'address', 'user_type', 'status'),
        }),
    )
    
    filter_horizontal = ('groups', 'user_permissions',)
    
    def get_user_type_display(self, obj):
        return obj.get_user_type_display()
    get_user_type_display.short_description = 'User Type'
    
    def get_status_display(self, obj):
        return obj.get_status_display()
    get_status_display.short_description = 'Status'

# Register the new UserAdmin
admin.site.register(User, UserAdmin)

class QuillAdminMixin:
    class Media:
        css = {
            'all': (
                'https://cdn.jsdelivr.net/npm/quill@1.3.7/dist/quill.snow.css',
                'backend/css/quill-admin.css',
            )
        }
        js = (
            'https://cdn.jsdelivr.net/npm/quill@1.3.7/dist/quill.min.js',
            'backend/js/quill-admin.js',
        )


@admin.register(Slider)
class SliderAdmin(QuillAdminMixin, admin.ModelAdmin):
    form = SliderForm
    list_display = ('title', 'subtitle', 'order', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'subtitle')
    list_editable = ('order', 'status')


@admin.register(SiteBranding)
class SiteBrandingAdmin(admin.ModelAdmin):
    form = SiteBrandingForm
    def has_add_permission(self, request):
        return not SiteBranding.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AboutPage)
class AboutPageAdmin(QuillAdminMixin, admin.ModelAdmin):
    form = AboutPageForm

    def has_add_permission(self, request):
        return not AboutPage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactPage)
class ContactPageAdmin(QuillAdminMixin, admin.ModelAdmin):
    form = ContactPageForm

    def has_add_permission(self, request):
        return not ContactPage.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Product)
class ProductAdmin(QuillAdminMixin, admin.ModelAdmin):
    form = ProductForm
    list_display = ('title', 'sku', 'category', 'selling_price', 'status', 'created_at')
    list_filter = ('status', 'category', 'featured')
    search_fields = ('title', 'sku', 'description')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Category)
class CategoryAdmin(QuillAdminMixin, admin.ModelAdmin):
    form = CategoryForm
    list_display = ('name', 'slug', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'position', 'is_primary')
    list_filter = ('product', 'is_primary')

@admin.register(ProductDiscount)
class ProductDiscountAdmin(admin.ModelAdmin):
    list_display = ('product', 'discount_type', 'percentage', 'discount_value', 'is_active')
    list_filter = ('active', 'discount_type')
    
    
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'number', 'review', 'rating')
    list_filter = ('name', 'rating')
    
    
@admin.register(DeliveryCharge)
class DeliveryChargeAdmin(admin.ModelAdmin):
    list_display = ( 'district', 'thana', 'amount')
    list_filter = ('district', 'thana')
    
    
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'first_name', 'last_name', 'district', 'thana', 
                    'total_amount', 'delivery_charge', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'district')
    search_fields = ('order_id', 'first_name', 'last_name', 'email', 'phone')
    
    
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'price', 'quantity', 'subtotal')
    list_filter = ('order__status',)
    search_fields = ('order__order_id', 'product__title')
    
    def subtotal(self, obj):
        return obj.price * obj.quantity
    subtotal.short_description = 'Subtotal'


@admin.register(AdminNotification)
class AdminNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'link')
