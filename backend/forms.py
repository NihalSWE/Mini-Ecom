# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import *
from PIL import Image
from django.core.validators import RegexValidator
import os
import re

class RichTextWidget(forms.Textarea):
    template_name = 'django/forms/widgets/textarea.html'

    def __init__(self, attrs=None):
        attrs = attrs or {}
        existing_class = attrs.get('class', '')
        attrs['class'] = f"{existing_class} quill-source".strip()
        attrs.setdefault('data-quill-editor', 'true')
        attrs.setdefault('rows', 6)
        super().__init__(attrs)


class UserCreationForm(UserCreationForm):
    """Custom user creation form with all required fields"""
    
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'id': 'password1'
        }),
        help_text="Minimum 8 characters."
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password',
            'id': 'password2'
        })
    )
    
    class Meta:
        model = User
        fields = [
            'profile_image', 'first_name', 'last_name', 'email',
            'phone', 'address', 'user_type', 'status'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name',
                'id': 'firstName'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name',
                'id': 'lastName'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address',
                'id': 'email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+1 234 567 8900',
                'id': 'phone'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter address',
                'id': 'address',
                'rows': 3
            }),
            'user_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'user_type'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'id': 'status'
            }),
            'profile_image': forms.FileInput(attrs={
                'class': 'custom-file-input',
                'id': 'coverImage'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field since we're using email
        self.fields.pop('username', None)
        
        # Make email required
        self.fields['email'].required = True
        
        # Make first_name and last_name required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Set default choices for user_type and status
        self.fields['user_type'].initial = 1  # Default to Customer
        self.fields['status'].initial = 1     # Default to Active
        
        # Update user_type choices labels in form
        self.fields['user_type'].choices = User.USER_TYPE_CHOICES
        self.fields['status'].choices = User.STATUS_CHOICES
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        
        if password1 and len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information (without password)"""
    
    class Meta:
        model = User
        fields = [
            'profile_image', 'first_name', 'last_name', 'email',
            'phone', 'address', 'user_type', 'status', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'custom-file-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email read-only for existing users
        self.fields['email'].widget.attrs['readonly'] = True
        
        # Update user_type and status choices labels in form
        self.fields['user_type'].choices = User.USER_TYPE_CHOICES
        self.fields['status'].choices = User.STATUS_CHOICES


class UserProfileForm(forms.ModelForm):
    """Form for users to update their own profile"""
    
    class Meta:
        model = User
        fields = [
            'profile_image', 'first_name', 'last_name', 'phone', 'address'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'profile_image': forms.FileInput(attrs={'class': 'custom-file-input'}),
        }


class BackendAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        }),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class BackendSignupForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
        }),
        min_length=8,
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password',
        }),
    )
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email address'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None
        user.user_type = 0
        user.status = 1
        user.is_active = True
        user.is_staff = True
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
        
        
class SliderForm(forms.ModelForm):
    REQUIRED_WIDTH = 1374
    REQUIRED_HEIGHT = 575

    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        help_text="Recommended banner size: 1374x575px. Auto-optimized on upload."
    )
    
    class Meta:
        model = Slider
        fields = [
            'title', 'subtitle', 'description', 'image', 
            'price', 'price_text', 'button_text', 'button_link', 
            'order', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter slider title'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter subtitle (optional)'}),
            'description': RichTextWidget(attrs={'class': 'form-control', 'placeholder': 'Enter description (optional)'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 29.99', 'step': '0.01'}),
            'price_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., starting at $'}),
            'button_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Shop Now'}),
            'button_link': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., /products/ or https://...'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        # If no image is provided during edit, keep existing one
        if not image and self.instance and self.instance.pk:
            return self.instance.image
        
        # If image is provided, validate it
        if image:
            # Keep upload generous and optimize automatically after save
            if image.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Image file too large ( > 10MB )")
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            ext = os.path.splitext(image.name)[1].lower()
            if ext not in valid_extensions:
                raise forms.ValidationError("Unsupported file extension. Please upload JPG, PNG, GIF or WebP.")
            
            # Check image dimensions (1375 x 545)
            try:
                img = Image.open(image)
                width, height = img.size
                
                if width != self.REQUIRED_WIDTH or height != self.REQUIRED_HEIGHT:
                    raise forms.ValidationError(
                        f"Image must be exactly {self.REQUIRED_WIDTH}px width × {self.REQUIRED_HEIGHT}px height. "
                        f"Your image is {width}px × {height}px."
                    )
                
                # Check image mode for compatibility
                if img.mode not in ['RGB', 'RGBA', 'L']:
                    img = img.convert('RGB')
                
            except Exception as e:
                raise forms.ValidationError(f"Invalid image file: {str(e)}")
            
            # Reset file pointer
            image.seek(0)
        
        return image
    

class CategoryForm(forms.ModelForm):
    image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        help_text="Recommended category image size: 512x512px. Auto-optimized on upload."
    )

    class Meta:
        model = Category
        fields = ['name', 'short_description', 'image', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control here slug-title',
                'placeholder': 'Enter category name',
                'id': 'text'
            }),
            'short_description': RichTextWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Enter short description',
                'id': 'sortdescription'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        

# ========================================================
# 1. UPDATE THIS CLASS (ProductForm)
# ========================================================
class ProductForm(forms.ModelForm):
    # Explicitly define thumbnail_image field
    thumbnail_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.png,.jpg,.jpeg,.webp',
        }),
        help_text="Recommended display size: 800x700px. Auto-optimized on upload."
    )
    
    class Meta:
        model = Product
        fields = [
            'sku', 'title', 'model', 'category',
            'short_description', 'description', 'specification',
            'buy_price', 'selling_price', 
            'thumbnail_image', 
            'stock_quantity', 'stock_availability', 'status',
            'featured', 'best_seller', 'trending', 'new',
            'meta_title', 'meta_description', 'meta_keywords'
        ]
        widgets = {
            'sku': forms.TextInput(attrs={
                'class': 'form-control slug-title',
                'placeholder': 'e.g., PROD-001, ABC-123',
                'required': True
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control slug-title',
                'placeholder': 'Product title',
                'required': True
            }),
            'model': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Model number'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'short_description': RichTextWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description'
            }),
            'description': RichTextWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Full description'
            }),
            'specification': RichTextWidget(attrs={
                'class': 'form-control',
                'placeholder': 'Technical specifications'
            }),
            'buy_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'required': True,
                'min': '0.01'
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'required': True,
                'min': '0.01'
            }),
            'stock_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
            'stock_availability': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'best_seller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'trending': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'new': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'meta_title': forms.TextInput(attrs={'class': 'form-control'}),
            'meta_description': RichTextWidget(attrs={
                'class': 'form-control',
            }),
            'meta_keywords': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories
        self.fields['category'].queryset = Category.objects.filter(status='active')
        
        # Make thumbnail required ONLY for new products
        if not self.instance.pk:
            self.fields['thumbnail_image'].required = True
        else:
            self.fields['thumbnail_image'].required = False
    
    def clean_sku(self):
        sku = self.cleaned_data.get('sku')
        if not sku:
            raise ValidationError("SKU is required")
        
        qs = Product.objects.filter(sku=sku)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError("SKU already exists. Use a unique SKU.")
        return sku
    
    def clean_thumbnail_image(self):
        thumbnail_image = self.cleaned_data.get('thumbnail_image')
        
        # If editing and no new image provided, keep existing
        if not thumbnail_image and self.instance and self.instance.pk:
            return self.instance.thumbnail_image
        
        # If adding new product, thumbnail is required
        if not thumbnail_image and not self.instance.pk:
            raise ValidationError("Main product image is required for new products.")
        
        # Validate new image if provided
        if thumbnail_image:
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            ext = os.path.splitext(thumbnail_image.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError("Unsupported file format. Use JPG, PNG, or WebP.")

            # 2. Check Dimensions (Strict 800x700)
            try:
                # We use PIL (imported as Image) to open the file
                img = Image.open(thumbnail_image)
                width, height = img.size
                
                if width != 800 or height != 700:
                    raise ValidationError(
                        f"Invalid dimensions. Image must be exactly 800x700 pixels. "
                        f"Uploaded image is {width}x{height}."
                    )
            except Exception:
                raise ValidationError("Invalid image file or cannot read image data.")
        
        return thumbnail_image
    
    def clean_selling_price(self):
        selling_price = self.cleaned_data.get('selling_price')
        buy_price = self.cleaned_data.get('buy_price')
        
        if selling_price and buy_price and selling_price <= buy_price:
            raise ValidationError("Selling price must be higher than cost price.")
        return selling_price


# ========================================================
# 2. ADD THIS NEW CLASS (ProductImageForm)
# ========================================================
class ProductImageForm(forms.ModelForm):
    """Form for additional gallery images with strict validation"""
    image = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.png,.jpg,.jpeg,.webp'
        }),
        help_text="Recommended display size: 800x700px. Auto-optimized on upload."
    )

    class Meta:
        model = ProductImage
        fields = ['image', 'position', 'alt_text', 'is_primary']
        widgets = {
            'position': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Order'}),
            'alt_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SEO Alt Text'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if image:
            # Keep dimensions consistent for the storefront layout
            try:
                img = Image.open(image)
                width, height = img.size
                
                if width != 800 or height != 700:
                    raise ValidationError(
                        f"Image must be 800x700 pixels. Yours is {width}x{height}."
                    )
            except Exception:
                raise ValidationError("Invalid image file.")
        
        return image


# ========================================================
# 3. ADD THIS NEW FORMSET (ProductImageFormSet)
# ========================================================
ProductImageFormSet = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageForm,
    extra=1,           # Show 1 empty slot by default
    max_num=4,         # Limit to 5 gallery images max
    can_delete=True
)


class SiteBrandingForm(forms.ModelForm):
    class Meta:
        model = SiteBranding
        fields = '__all__'
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'footer_copyright': forms.TextInput(attrs={'class': 'form-control'}),
        }


class AboutPageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['image'].help_text = 'Recommended size: 674 x 380 px. Uploaded images will be resized and optimized automatically.'

    class Meta:
        model = AboutPage
        fields = '__all__'
        widgets = {
            'page_title': forms.TextInput(attrs={'class': 'form-control'}),
            'section_title': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'heading': forms.TextInput(attrs={'class': 'form-control'}),
            'description': RichTextWidget(attrs={'class': 'form-control', 'placeholder': 'Write the About Us content'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class ContactPageForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='This phone number is used in the footer and for the floating WhatsApp chat button.',
    )

    map_embed_url = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Paste Google Maps embed URL or full iframe code',
            }
        ),
        help_text='Paste the Google Maps embed URL or the full iframe embed code.',
    )

    class Meta:
        model = ContactPage
        fields = '__all__'
        widgets = {
            'page_title': forms.TextInput(attrs={'class': 'form-control'}),
            'heading': forms.TextInput(attrs={'class': 'form-control'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-control'}),
            'address': RichTextWidget(attrs={'class': 'form-control', 'placeholder': 'Write the contact address'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_url': forms.URLInput(attrs={'class': 'form-control'}),
            'youtube_url': forms.URLInput(attrs={'class': 'form-control'}),
        }

    def clean_map_embed_url(self):
        value = (self.cleaned_data.get('map_embed_url') or '').strip()
        if not value:
            return ''

        if '<iframe' in value.lower():
            match = re.search(r'src=["\']([^"\']+)["\']', value, re.IGNORECASE)
            if not match:
                raise ValidationError('Paste a valid Google Maps iframe embed code.')
            value = match.group(1).strip()

        if 'maps.app.goo.gl' in value or '/maps/place/' in value:
            raise ValidationError('Google Maps share links do not work in the embedded map. Use the embed URL or paste the full iframe code.')

        if 'google.com/maps/embed' not in value:
            raise ValidationError('Use a Google Maps embed URL or paste the full iframe embed code.')

        return value




class ProductDiscountForm(forms.ModelForm):
    """Form for managing product discounts"""
    
    class Meta:
        model = ProductDiscount
        fields = ['discount_type', 'percentage', 'discount_value', 'start_date', 'end_date', 'active']
        widgets = {
            'discount_type': forms.Select(attrs={
                'class': 'form-control discount-type',
            }),
            'percentage': forms.NumberInput(attrs={
                'class': 'form-control percentage-field',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g., 10.00'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control fixed-field',
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 5.00'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control datepicker',
                'type': 'date'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # For empty extra forms (not saved), mark all fields as not required
        # This prevents validation errors on empty forms
        self.fields['discount_type'].required = False
        self.fields['percentage'].required = False
        self.fields['discount_value'].required = False
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False
        self.fields['active'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get all fields
        discount_type = cleaned_data.get('discount_type')
        percentage = cleaned_data.get('percentage', 0)
        discount_value = cleaned_data.get('discount_value', 0)
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        active = cleaned_data.get('active', False)
        
        # Check if this is an empty extra form (no discount type selected)
        # If no discount type, don't validate other fields
        if not discount_type:
            # This is an empty extra form, mark it for deletion
            cleaned_data['DELETE'] = True
            return cleaned_data
        
        # Now we have a discount type, so validate the required fields
        if not start_date:
            self.add_error('start_date', 'Start date is required')
        
        if not end_date:
            self.add_error('end_date', 'End date is required')
        
        # Validate date range if both dates exist
        if start_date and end_date and start_date >= end_date:
            self.add_error('end_date', 'End date must be after start date')
        
        # Validate discount values based on type
        if discount_type == 'percentage':
            if not percentage or percentage <= 0:
                self.add_error('percentage', 'Percentage must be greater than 0')
            if percentage > 100:
                self.add_error('percentage', 'Percentage cannot exceed 100%')
            # Clear discount_value for percentage type
            cleaned_data['discount_value'] = 0
        elif discount_type == 'fixed':
            if not discount_value or discount_value <= 0:
                self.add_error('discount_value', 'Discount value must be greater than 0')
            # Clear percentage for fixed type
            cleaned_data['percentage'] = 0
        
        return cleaned_data


# Custom formset to handle empty forms
class CustomProductDiscountFormSet(forms.BaseInlineFormSet):
    def clean(self):
        """Override clean to handle empty extra forms"""
        super().clean()
        
        for form in self.forms:
            # Check if form has discount_type field in cleaned_data
            if form.cleaned_data.get('discount_type'):
                # This form has a discount type, validate dates
                if not form.cleaned_data.get('start_date'):
                    form.add_error('start_date', 'Start date is required')
                if not form.cleaned_data.get('end_date'):
                    form.add_error('end_date', 'End date is required')
            else:
                # Empty extra form, mark for deletion
                form.cleaned_data['DELETE'] = True
    
    def save(self, commit=True):
        """Override save to skip empty forms"""
        instances = super().save(commit=False)
        
        # Filter out instances that are empty (no discount_type)
        instances_to_save = []
        for instance in instances:
            if instance.discount_type:  # Only save if discount_type is set
                instances_to_save.append(instance)
        
        if commit:
            # Save only non-empty instances
            for instance in instances_to_save:
                instance.save()
            self.save_m2m()
        
        return instances_to_save


# Create inline formset factory
ProductDiscountFormSet = inlineformset_factory(
    Product,
    ProductDiscount,
    form=ProductDiscountForm,
    formset=CustomProductDiscountFormSet,
    extra=1,
    can_delete=True,
    max_num=5,
    validate_max=True
)


class ReviewForm(forms.ModelForm):
    # BD Phone Number Regex: Starts with 01, followed by 3-9, then 8 digits
    phone_regex = RegexValidator(
        regex=r'^01[3-9]\d{8}$',
        message="Phone number must be a valid BD number (e.g., 017XXXXXXXX)."
    )

    number = forms.CharField(validators=[phone_regex], max_length=11)

    class Meta:
        model = Review
        fields = ['name', 'email', 'number', 'review', 'rating']


class ContactMessageForm(forms.ModelForm):
    phone = forms.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                regex=r'^01[3-9]\d{8}$',
                message='Your number is not matching BD format.',
            )
        ],
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': '01XXXXXXXXX',
                'maxlength': 11,
                'inputmode': 'numeric',
                'autocomplete': 'tel',
            }
        ),
    )

    class Meta:
        model = ContactMessage
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name',
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address',
                'autocomplete': 'email',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Please leave your comments here..',
                'rows': 5,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

    def clean_phone(self):
        phone = re.sub(r'\D', '', (self.cleaned_data.get('phone') or ''))
        if len(phone) > 11:
            phone = phone[:11]

        if not re.fullmatch(r'01[3-9]\d{8}', phone):
            raise ValidationError('Your number is not matching BD format.')

        return phone


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'district', 'thana']
