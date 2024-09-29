from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('download_files/', views.download_files, name='download_files'),
    # path('signup/', views.signup, name='signup'),
    # path('login/', views.login_view, name='login'),
]
