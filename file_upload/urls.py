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
    path('user_login/', views.user_login, name='user_login'),
    path('upload/', views.upload, name='upload'),
    path('list/', views.file_list, name='list'),
    path('remove/<int:id>/', views.delete_file, name='remove'),
    path('del_session/', views.del_session, name='del_session'),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('kakao/', views.kakaoView.as_view(), name='kakao'),
    path('accounts/kakao/login/callback/', views.kakaoView.as_view()),  # KakaoLoginCallbackView의 URL 패턴 추가
    path('kakao/callback/', views.kakaoCallBackView.as_view()),  # KakaoLoginCallbackView의 URL 패턴 추가
]


"""http://127.0.0.1:8000/file/api/response/"""