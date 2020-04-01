from django.views.generic import TemplateView


class DashboardView(TemplateView):
    template_name="dashboard/index.html"


class StateView(TemplateView):
    template_name="dashboard/state.html"


class CountyView(TemplateView):
    template_name="dashboard/county.html"


class FacilityView(TemplateView):
    template_name="dashboard/facility.html"