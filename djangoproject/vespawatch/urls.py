from django.urls import path

from . import views

app_name = 'vespawatch'

urlpatterns = [
    path('', views.index, name='index'),
    path('observations/add/', views.ObservationCreate.as_view(), name='observation-add'),
    path('observations/<int:pk>/', views.ObservationUpdate.as_view(), name='observation-update'),
    path('observations/<int:pk>/delete/', views.ObservationDelete.as_view(), name='observation-delete'),
    path('api/observations', views.observations_json, name='api_observations'),
]