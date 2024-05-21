from django.urls import path
from . import views
from rest_framework import routers
from file_upload import views
from django.conf.urls import include

app_name = 'file_upload'
router = routers.DefaultRouter()
router.register(r'response', views.ResponseViewSet, basename='response')

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('list/', views.file_list, name='list'),
    path('remove/<int:id>/', views.delete_file, name='remove'),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]


"""http://127.0.0.1:8000/file/api/response/"""