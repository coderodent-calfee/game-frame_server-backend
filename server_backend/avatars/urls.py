from django.urls import path
from .views import image_list, image_detail, image_single_info

urlpatterns = [
    path('images/', image_list, name='image-list'),
    path('images/<uuid:image_id>/', image_detail, name='image-detail'),
    path('images/<uuid:image_id>/info/', image_single_info, name='image-info'), 
]
