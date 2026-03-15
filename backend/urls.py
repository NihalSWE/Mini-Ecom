# urls.py (in your app)
from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard_entry, name='admin_dashboard_entry'),
    path('login/', views.backend_login, name='backend_login'),
    path('signup/', views.backend_signup, name='backend_signup'),
    path('logout/', views.backend_logout, name='backend_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # User management
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/<int:user_id>/', views.user_profile, name='view_user_profile'),
    #
    #home
    path('banner/add/', views.add_banner, name='add_banner'),
    path('banner/list/', views.banner_list, name='banner_list'),
    path('banner/edit/<int:id>/', views.edit_banner, name='edit_banner'),
    path('banner/delete/', views.delete_banner, name='delete_banner'),
    #
    # website content
    path('site-branding/', views.site_branding_settings, name='site_branding_settings'),
    path('about-page/', views.about_page_settings, name='about_page_settings'),
    path('contact-page/', views.contact_page_settings, name='contact_page_settings'),
    path('contact-messages/', views.contact_message_list, name='contact_message_list'),
    path('contact-messages/<int:pk>/toggle-read/', views.contact_message_toggle_read, name='contact_message_toggle_read'),
    path('contact-messages/<int:pk>/delete/', views.contact_message_delete, name='contact_message_delete'),
    path('notifications/<int:pk>/open/', views.notification_open, name='notification_open'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('search/', views.admin_search, name='admin_search'),
    #
    
    #category
    path('category/', views.category, name='category'),
    path('category/delete/<int:id>/', views.delete_category, name='delete_category'),
    #
    #product
    path('product/add/', views.add_product, name='add_product'),
    path('product/edit/<int:id>/', views.edit_product, name='edit_product'),
    path('product/delete/<int:id>/', views.delete_product, name='delete_product'),
    path('product/image/delete/<int:id>/', views.delete_product_image, name='delete_product_image'),
    path('product/image/set-primary/<int:id>/', views.set_primary_image, name='set_primary_image'),
    path('product/list/', views.product_list, name='product_list'),
    path('product/review/', views.review, name='review'),
    path('product/reviews/delete/<int:pk>/', views.review_delete, name='review_delete'),
    path('product/reviews/status/<int:pk>/', views.review_status, name='review_status'),
    #
    #delivery charge
    path('delivery-charge/', views.delivery_charge_list, name='delivery_charge_list'),
    path('delivery-charge/add/', views.delivery_charge_add, name='delivery_charge_add'),
    path('delivery-charge/edit/<int:pk>/', views.delivery_charge_edit, name='delivery_charge_edit'),
    path('delivery-charge/delete/<int:pk>/', views.delivery_charge_delete, name='delivery_charge_delete'),
    #
    #order
    path('order_list/', views.order_list, name='order_list'),
    path('order_details/<str:order_id>/', views.order_details, name='order_details'),
    path('order/update-status/<str:order_id>/', views.update_order_status, name='update_order_status'),
    path('invoice/<str:order_id>/', views.invoice, name='invoice'),
    #
    
]
