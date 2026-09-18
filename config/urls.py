from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("", include("posts.urls")),
    path("", include("accounts.urls")),
    path("", include("dms.urls")),
]
