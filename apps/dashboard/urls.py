from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "dashboard"


urlpatterns = [
    path("", views.DashboardView.as_view(), name="index"),
    path("states/<code>/", views.StateView.as_view(), name="state"),
    path("states/<state_code>/counties/<slug:slug>/", views.CountyView.as_view(), name="county"),
    path("states/<state_code>/counties/<slug:county_slug>/facilities/<int:cms_id>/<slug:slug>/", views.FacilityView.as_view(), name="facility"),
]
