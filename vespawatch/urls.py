from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'vespawatch'


urlpatterns = [
    path('', views.index, name='index'),
    path('get-involved/', views.getinvolved, name='getinvolved'),
    path('identification/', views.identification, name='identification'),

    path('about/links/', views.about_links, name='about_links'),
    path('about/management/', views.about_management, name='about_management'),
    path('about/privacy-policy/', views.about_privacypolicy, name='about_privacypolicy'),
    path('about/project/', views.about_project, name='about_project'),
    path('about/vespa-velutina/', views.about_vespavelutina, name='about_vespavelutina'),

    path('management/', views.management, name='management'),
    path('management/nest/<int:pk>/', views.nest_detail, name='nest-detail'),

    path('obs/', views.latest_observations, name='latest-observations'),
    path('obs/add/', views.obs_create, name='observation-add'),

    path('obs/individual/', RedirectView.as_view(pattern_name='vespawatch:individual-add')),
    path('obs/individual/add/', views.create_individual, name='individual-add'),

    path('obs/nest/', RedirectView.as_view(pattern_name='vespawatch:nest-add')),
    path('obs/nest/add/', views.create_nest, name='nest-add'),

    path('profile', views.profile, name='profile'),

    # API paths
    #path('api/observations/', views.observations_json, name='api_observations'),  TODO can we remove this one?
    path('api/individuals/', views.individuals_json, name='api_individuals'),
    path('api/individuals/<int:pk>', views.single_individual_json, name='api_single_individual'), # TODO can we remove this one?
    path('api/individual_pictures/', views.save_individual_picture, name='api_individual_picture'),
    path('api/individual_pictures/<int:pk>', views.get_individual_picture, name='api_single_individual_picture'),
    path('api/nests/', views.nests_json, name='api_nests'),
    path('api/nests/<int:pk>/', views.single_nest_json, name='api_single_nest'), # TODO can we remove this one?
    path('api/nest_pictures/', views.save_nest_picture, name='api_nest_picture'),
    path('api/nest_pictures/<int:pk>', views.get_nest_picture, name='api_single_nest_picture'),

    path('api/action_outcomes/', views.management_actions_outcomes_json, name='api_action_outcomes'),
    path('api/save_management_action/', views.save_management_action, name='api_action_save'),
    path('api/get_management_action/', views.get_management_action, name='api_action_get'),
    path('api/delete_management_action/', views.delete_management_action, name='api_action_delete'),

    path('api/csv_export/nests', views.csv_export_nests),
    path('api/csv_export/individuals', views.csv_export_individuals)
]