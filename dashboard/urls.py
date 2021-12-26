from django.urls import path
from . import views
urlpatterns = [
    path('', views.index),
    path("api/order/filter", views.order_filter_api),
    path("api/order/data_vis", views.order_data_vis_api),
    path("api/order/send_email", views.order_send_email_api),
    path("api/spider/ifeng", views.spider_ifeng_api),

]