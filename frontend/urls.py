from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('allproducts',views.allProducts,name='allProducts'),
    path('singleproduct/<slug:slug>/',views.singleproduct,name='singleproduct'),
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('contactus',views.contactus,name='contactus'),
    path('aboutus',views.aboutus,name='aboutus'),
    path('cart/', views.cart, name='cart'),
    # Note: <int:id> allows us to pass the product ID cleanly
    path('add-to-cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('buy-now/<int:id>/', views.buy_now, name='buy_now'),
    path('cart/update_quantity/', views.update_quantity, name='update_quantity'),
    path('cart/remove_item/', views.remove_item, name='remove_item'),
    path('checkout',views.checkout,name='checkout'),
    path('api/get-delivery-charge/', views.get_delivery_charge, name='get_delivery_charge'),
    # Order success page (optional)
    path('order-success/<str:order_id>/', views.order_success, name='order_success'),
    path('login',views.login,name='login'),
    path('register',views.register,name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('my-orders/', views.user_orders, name='user_orders'),
    path('change-password/', views.change_password, name='change_password'),
    path('policy',views.policy,name='policy'),
    path('terms',views.terms,name='terms'),
    path('blog',views.blog,name='blog'),
    path('blogDetails',views.blogDetails,name='blogDetails'),
    
]
