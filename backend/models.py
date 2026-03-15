# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import uuid
from django.utils.text import slugify
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.files.base import ContentFile
from django.urls import reverse
from PIL import Image, ImageOps
from io import BytesIO
import os
import re
from decimal import Decimal
from urllib.parse import quote


def _normalize_image_for_save(image_obj):
    image_obj = ImageOps.exif_transpose(image_obj)
    has_alpha = 'A' in image_obj.getbands()

    if image_obj.mode not in ('RGB', 'RGBA'):
        image_obj = image_obj.convert('RGBA' if has_alpha else 'RGB')

    return image_obj, has_alpha


def _optimize_image_at_path(file_path, jpeg_quality=88, webp_quality=88, target_size=None):
    if not file_path or not os.path.exists(file_path):
        return

    try:
        with Image.open(file_path) as raw_image:
            image, has_alpha = _normalize_image_for_save(raw_image)
            image_format = (raw_image.format or os.path.splitext(file_path)[1].replace('.', '')).upper()

            if target_size:
                image = ImageOps.fit(image, target_size, Image.LANCZOS)

            if image_format in ('JPEG', 'JPG'):
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(
                    file_path,
                    format='JPEG',
                    optimize=True,
                    progressive=True,
                    quality=jpeg_quality,
                )
            elif image_format == 'PNG':
                image.save(
                    file_path,
                    format='PNG',
                    optimize=True,
                )
            elif image_format == 'WEBP':
                image.save(
                    file_path,
                    format='WEBP',
                    quality=webp_quality,
                    method=6,
                )
            else:
                fallback = image.convert('RGBA' if has_alpha else 'RGB')
                fallback.save(
                    file_path,
                    format='PNG' if has_alpha else 'JPEG',
                    optimize=True,
                    quality=jpeg_quality,
                )
    except Exception:
        pass

class CustomUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 0)  # Admin by default
        extra_fields.setdefault('status', 1)     # Active by default

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User Model for Admin, Vendor, and Customer users"""
    
    # Remove username field, use email instead
    username = None
    email = models.EmailField(_('email address'), unique=True)
    
    # Additional fields
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    
    # User Type choices (0=Admin, 1=Customer, 2=Vendor)
    USER_TYPE_CHOICES = (
        (0, 'Admin'),
        (1, 'Customer'),
        (2, 'Vendor'),
    )
    user_type = models.IntegerField(choices=USER_TYPE_CHOICES, default=1)  # Default to Customer
    
    # Status choices (0=Inactive, 1=Active, 2=Suspended)
    STATUS_CHOICES = (
        (0, 'Inactive'),
        (1, 'Active'),
        (2, 'Suspended'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)  # Default to Active
    
    # Fix the groups and user_permissions reverse accessor clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Set email as the USERNAME_FIELD
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = CustomUserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        return self.first_name
    
    @property
    def is_admin_user(self):
        return self.user_type == 0 or self.is_superuser
    
    @property
    def is_customer(self):
        return self.user_type == 1
    
    @property
    def is_vendor(self):
        return self.user_type == 2
    
    @property
    def is_inactive(self):
        return self.status == 0
    
    @property
    def is_active_user(self):
        return self.status == 1
    
    @property
    def is_suspended(self):
        return self.status == 2
    
    def get_user_type_display(self):
        """Get the display value for user_type"""
        return dict(self.USER_TYPE_CHOICES).get(self.user_type, 'Unknown')
    
    def get_status_display(self):
        """Get the display value for status"""
        return dict(self.STATUS_CHOICES).get(self.status, 'Unknown')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.profile_image:
            _optimize_image_at_path(
                self.profile_image.path,
                jpeg_quality=85,
                webp_quality=85,
                target_size=(400, 400),
            )
    
    
    
    
class Slider(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='slider_images/')
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_text = models.CharField(max_length=100, blank=True)  # e.g., "starting at $"
    button_text = models.CharField(max_length=50, default='Shop Now')
    button_link = models.CharField(max_length=200, default='#')
    order = models.IntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            _optimize_image_at_path(
                self.image.path,
                jpeg_quality=86,
                webp_quality=86,
                target_size=(674, 380),
            )


class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteBranding(SingletonModel):
    site_name = models.CharField(max_length=150, default='Ekka')
    footer_tagline = models.CharField(max_length=255, blank=True, default='Your trusted destination for quality products.')
    footer_copyright = models.CharField(max_length=255, blank=True, default='All rights reserved.')
    logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    footer_logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    dark_logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    dark_footer_logo = models.ImageField(upload_to='branding/', blank=True, null=True)
    favicon = models.ImageField(upload_to='branding/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Branding'
        verbose_name_plural = 'Site Branding'

    def __str__(self):
        return 'Site Branding'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        for image_field in ['logo', 'footer_logo', 'dark_logo', 'dark_footer_logo', 'favicon']:
            image = getattr(self, image_field)
            if image:
                _optimize_image_at_path(image.path, jpeg_quality=88, webp_quality=88)


class AboutPage(SingletonModel):
    page_title = models.CharField(max_length=150, default='About Us')
    section_title = models.CharField(max_length=150, default='About Us')
    subtitle = models.CharField(max_length=255, blank=True, default='About our business')
    heading = models.CharField(max_length=255, default='Who we are')
    description = models.TextField(blank=True, default='Tell customers about your company, your products, and what makes your brand different.')
    image = models.ImageField(upload_to='site_content/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'About Us Page'
        verbose_name_plural = 'About Us Page'

    def __str__(self):
        return 'About Us Page'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            _optimize_image_at_path(self.image.path, jpeg_quality=86, webp_quality=86)


class ContactPage(SingletonModel):
    page_title = models.CharField(max_length=150, default='Contact Us')
    heading = models.CharField(max_length=150, default='Contact us')
    subtitle = models.CharField(max_length=255, blank=True, default='We would love to hear from you.')
    address = models.TextField(blank=True, default='Add your business address here.')
    phone = models.CharField(max_length=50, blank=True, default='+880')
    email = models.EmailField(blank=True, default='support@example.com')
    map_embed_url = models.URLField(blank=True, max_length=1000)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Contact Us Page'
        verbose_name_plural = 'Contact Us Page'

    def __str__(self):
        return 'Contact Us Page'

    @property
    def whatsapp_phone_digits(self):
        raw_phone = re.sub(r'\D', '', self.phone or '')
        if not raw_phone:
            return ''

        if raw_phone.startswith('880'):
            return raw_phone

        if raw_phone.startswith('0'):
            return f'88{raw_phone}'

        return raw_phone

    def get_whatsapp_message(self, site_name='our store'):
        message = f'Hi, I need assistance from {site_name}.'
        return quote(message)

    def get_whatsapp_url(self, site_name='our store'):
        if not self.whatsapp_phone_digits:
            return ''
        return f'https://wa.me/{self.whatsapp_phone_digits}?text={self.get_whatsapp_message(site_name)}'


class ContactMessage(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=11)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class AdminNotification(models.Model):
    TYPE_ORDER = 'order'
    TYPE_USER = 'user'
    TYPE_CONTACT = 'contact'

    TYPE_CHOICES = (
        (TYPE_ORDER, 'Order'),
        (TYPE_USER, 'User'),
        (TYPE_CONTACT, 'Contact'),
    )

    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Notification'
        verbose_name_plural = 'Admin Notifications'

    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"

    @property
    def icon_class(self):
        return {
            self.TYPE_ORDER: 'mdi mdi-cart',
            self.TYPE_USER: 'mdi mdi-account-plus',
            self.TYPE_CONTACT: 'mdi mdi-email-outline',
        }.get(self.notification_type, 'mdi mdi-bell-outline')

    @property
    def badge_class(self):
        return {
            self.TYPE_ORDER: 'bg-primary',
            self.TYPE_USER: 'bg-success',
            self.TYPE_CONTACT: 'bg-warning',
        }.get(self.notification_type, 'bg-info')


class Category(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    short_description = models.TextField(max_length=500, blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.image:
            _optimize_image_at_path(self.image.path, jpeg_quality=84, webp_quality=84)

# Signal to auto-generate slug
@receiver(pre_save, sender=Category)
def generate_slug(sender, instance, *args, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.name)
        
        # Ensure slug is unique
        original_slug = instance.slug
        counter = 1
        while Category.objects.filter(slug=instance.slug).exclude(id=instance.id).exists():
            instance.slug = f"{original_slug}-{counter}"
            counter += 1
            
            



def generate_unique_slug(instance, model, slug_field, title_field):
    """Generate unique slug from title"""
    slug = slugify(getattr(instance, title_field))
    unique_slug = slug
    counter = 1
    
    while model.objects.filter(**{slug_field: unique_slug}).exclude(pk=instance.pk).exists():
        unique_slug = f'{slug}-{counter}'
        counter += 1
    
    return unique_slug

class Product(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('discontinued', 'Discontinued'),
    )
    
    STOCK_STATUS = (
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('pre_order', 'Pre Order'),
        ('coming_soon', 'Coming Soon'),
    )
    
    # Basic Information
    sku = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name="SKU",
        help_text="Stock Keeping Unit (e.g., PROD-001, ABC-123)"
    )
    title = models.CharField(max_length=200)
    model = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Model Number",
        help_text="Product model/number"
    )
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    
    # Descriptions
    short_description = models.TextField(max_length=500, blank=True, verbose_name="Short Description")
    description = models.TextField(blank=True, verbose_name="Full Description")
    specification = models.TextField(blank=True, verbose_name="Specifications")
    
    # Pricing
    buy_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Cost Price",
        help_text="Purchase cost"
    )
    selling_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        verbose_name="Selling Price",
        help_text="Retail price"
    )

    
    # Main Image - REQUIRED
    thumbnail_image = models.ImageField(
        upload_to='products/thumbnails/%Y/%m/',
        verbose_name="Main Image",
        help_text="Primary product image (required)"
    )
    
    # Category & Status
    category = models.ForeignKey(
        'Category', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products',
        verbose_name="Category"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name="Status"
    )
    stock_availability = models.CharField(
        max_length=20, 
        choices=STOCK_STATUS, 
        default='in_stock',
        verbose_name="Stock Status"
    )
    stock_quantity = models.IntegerField(
        default=0,
        verbose_name="Stock Quantity"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Meta
    meta_title = models.CharField(max_length=200, null=True, blank=True, verbose_name="Meta Title")
    meta_description = models.TextField(blank=True, null=True, verbose_name="Meta Description")
    meta_keywords = models.CharField(max_length=300, blank=True, null=True, verbose_name="Meta Keywords")
    
    # Flags
    featured = models.BooleanField(default=False, verbose_name="Featured Product")
    best_seller = models.BooleanField(default=False, verbose_name="Best Seller")
    trending = models.BooleanField(default=False, verbose_name="Trending")
    new = models.BooleanField(default=False, verbose_name="New")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product"
        verbose_name_plural = "Products"
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['category', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.sku})"
    
    def save(self, *args, **kwargs):
        # Generate SKU if not provided
        if not self.sku:
            raise ValueError("SKU is required for product")
        
        # Slug generation logic
        if not self.slug:
            self.slug = generate_unique_slug(self, Product, 'slug', 'title')
        
        # Set published_at if status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)
        
        # Optimize thumbnail after saving
        self._optimize_thumbnail()
    
    def _optimize_thumbnail(self):
        """Optimize thumbnail image"""
        try:
            if not self.thumbnail_image:
                return

            _optimize_image_at_path(self.thumbnail_image.path, jpeg_quality=88, webp_quality=88)
        except Exception:
            pass
    
    def get_discounted_price(self):
        """Get discounted price if any active discount exists"""
        current_time = timezone.now()
        
        active_discount = self.discounts.filter(
            active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        ).order_by('-created_at').first()
        
        if not active_discount:
            return self.selling_price
        
        if active_discount.discount_type == 'fixed':
            discounted = self.selling_price - active_discount.discount_value
            return max(Decimal('0'), discounted)
        elif active_discount.discount_type == 'percentage':
            discount_amount = (self.selling_price * active_discount.percentage) / Decimal('100')
            discounted = self.selling_price - discount_amount
            return max(Decimal('0'), discounted)
        
        return self.selling_price
    
    def get_stock_status_display(self):
        """Get human-readable stock status"""
        if self.stock_quantity <= 0:
            return "Out of Stock"
        elif self.stock_quantity < 10:
            return f"Only {self.stock_quantity} left"
        else:
            return "In Stock"
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage if any"""
        discounted_price = self.get_discounted_price()
        if discounted_price < self.selling_price:
            discount = ((self.selling_price - discounted_price) / self.selling_price) * 100
            return int(round(discount, 0))
        return 0
    @property
    def current_discount(self):
        """Get current active discount"""
        current_time = timezone.now()
        return self.discounts.filter(
            active=True,
            start_date__lte=current_time,
            end_date__gte=current_time
        ).order_by('-created_at').first()
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.buy_price > 0:
            profit = self.selling_price - self.buy_price
            margin = (profit / self.buy_price) * 100
            return round(margin, 2)
        return 0
    
    @property
    def is_available(self):
        """Check if product is available for purchase"""
        return (self.status == 'published' and 
                self.stock_availability in ['in_stock', 'pre_order'] and
                self.stock_quantity > 0)


    @property
    def profit(self):
        """Calculate actual profit amount after discount"""
        try:
            discounted_price = self.get_discounted_price()
            # Ensure both are Decimals before subtracting
            return discounted_price - self.buy_price 
        except (ValueError, TypeError):
            return Decimal('0.00')

    @property
    def profit_margin_percentage(self):
        """Calculate profit margin percentage after discount"""
        try:
            discounted_price = self.get_discounted_price()
            if self.buy_price > 0:
                profit = discounted_price - self.buy_price
                return (profit / self.buy_price) * 100
            return Decimal('0.00')
        except (ValueError, TypeError):
            return Decimal('0.00')
    
    # You might want to add these properties for clarity:
    @property
    def original_profit(self):
        """Calculate profit before any discount (for reference)"""
        try:
            return float(self.selling_price) - float(self.buy_price)
        except (ValueError, TypeError):
            return 0
    
    @property
    def discount_savings(self):
        """How much customer saves with discount"""
        try:
            savings = float(self.selling_price) - float(self.get_discounted_price())
            return round(savings, 2) # <--- Ensure it doesn't run to 10 decimal places
        except (ValueError, TypeError):
            return 0
        

    
    @property
    def is_low_stock(self):
        """Check if stock is low (< 10)"""
        return self.stock_quantity < 10
    
    @property
    def is_out_of_stock(self):
        """Check if product is out of stock"""
        return self.stock_quantity <= 0    
    

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='images',
        on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to='products/images/%Y/%m/%d/')
    image_small = models.ImageField(upload_to='products/images/small/%Y/%m/%d/', blank=True, null=True)
    position = models.PositiveIntegerField(default=0)
    alt_text = models.CharField(max_length=200, blank=True, help_text="Alt text for SEO")
    is_primary = models.BooleanField(default=False, help_text="Set as primary image")
    
    class Meta:
        ordering = ['position', '-is_primary']
        unique_together = ['product', 'position']
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
    
    def __str__(self):
        return f"{self.product.title} - Image {self.position}"
    
    def save(self, *args, **kwargs):
        # If this is set as primary, unset others
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        
        super().save(*args, **kwargs)
        
        # Optimize image
        if self.image:
            self._optimize_image()
    
    def _optimize_image(self):
        """Optimize product image and create small version"""
        try:
            img_path = self.image.path
            if not os.path.exists(img_path):
                return

            _optimize_image_at_path(img_path, jpeg_quality=86, webp_quality=86)

            with Image.open(img_path) as raw_image:
                img_small, _ = _normalize_image_for_save(raw_image)

            img_small.thumbnail((500, 500), Image.LANCZOS)

            buffer = BytesIO()
            img_small.save(buffer, format='WEBP', quality=82, method=6)
            buffer.seek(0)

            file_name = f"{os.path.splitext(os.path.basename(self.image.name))[0]}_small.webp"
            self.image_small.save(file_name, ContentFile(buffer.read()), save=False)

            buffer.close()
            super().save(update_fields=['image_small'])
        except Exception:
            pass


class ProductDiscount(models.Model):
    DISCOUNT_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='discounts'
    )
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0, 
        help_text="Percentage discount (e.g., 10.00 for 10%)"
    )
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Fixed discount amount (e.g., 5.00 for $5 off)"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product Discount"
        verbose_name_plural = "Product Discounts"
    
    def __str__(self):
        return f"{self.product.title} - {self.get_discount_type_display()}"
    
    @property
    def is_active(self):
        """Check if discount is currently active"""
        now = timezone.localdate()
        return self.active and self.start_date <= now <= self.end_date
    
    def get_discount_amount(self, product_price):
        """Calculate discount amount for given price"""
        if self.discount_type == 'percentage':
            return (product_price * self.percentage) / Decimal('100')
        else:
            return self.discount_value
        
        
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    
    # Guest User Fields
    name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100)
    number = models.CharField(max_length=15, blank=True, null=True) # Phone number
    
    # Review Details
    rating = models.IntegerField(default=5) # 1 to 5
    review = models.TextField(max_length=500)
    
    # Meta
    status = models.BooleanField(default=True) # To toggle visibility
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.product.title}"

    class Meta:
        ordering = ['-created_at']
        
        
class DeliveryCharge(models.Model):
    # If thana is empty, this charge applies to the whole district
    district = models.CharField(max_length=100)
    thana = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.district} - {self.thana or 'All'} : {self.amount}"
    
    
    
class Order(models.Model):
    ORDER_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    # User is optional (for Guest checkout)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Billing Details
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    district = models.CharField(max_length=100) # City/District
    thana = models.CharField(max_length=100, blank=True, null=True) # Area/Thana
    
    # Order Stats
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, default='COD')
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # System
    order_id = models.CharField(max_length=100, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Generate a unique Order ID like "ORD-2024-8392"
        if not self.order_id:
            import uuid
            self.order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_id
    
    # Helper to calculate total
    def get_grand_total(self):
        return self.total_amount
    
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2) # Price at time of purchase
    quantity = models.PositiveIntegerField(default=1)
    
    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.title} (x{self.quantity})"


def _create_admin_notification(notification_type, title, message, link=''):
    AdminNotification.objects.create(
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


@receiver(post_save, sender=Order)
def create_order_notification(sender, instance, created, **kwargs):
    if not created:
        return

    customer_name = f"{instance.first_name} {instance.last_name}".strip() or instance.email
    _create_admin_notification(
        AdminNotification.TYPE_ORDER,
        f"New order {instance.order_id}",
        f"{customer_name} placed a new order for {instance.total_amount}.",
        reverse('order_details', args=[instance.order_id]),
    )


@receiver(post_save, sender=User)
def create_user_notification(sender, instance, created, **kwargs):
    if not created:
        return

    display_name = instance.get_full_name() or instance.email
    _create_admin_notification(
        AdminNotification.TYPE_USER,
        "New user registered",
        f"{display_name} joined with {instance.email}.",
        reverse('edit_user', args=[instance.id]) if instance.id else reverse('user_list'),
    )


@receiver(post_save, sender=ContactMessage)
def create_contact_notification(sender, instance, created, **kwargs):
    if not created:
        return

    sender_name = f"{instance.first_name} {instance.last_name}".strip() or instance.email
    _create_admin_notification(
        AdminNotification.TYPE_CONTACT,
        "New contact message",
        f"{sender_name} sent a new contact message.",
        reverse('contact_message_list'),
    )
