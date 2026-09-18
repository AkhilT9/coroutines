from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", lambda request: HttpResponse("ok"), name="healthz"),
    path("robots.txt", TemplateView.as_view(template_name="pages/robots.txt", content_type="text/plain")),
    path("terms/", TemplateView.as_view(template_name="pages/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="pages/privacy.html"), name="privacy"),
    path("", include("posts.urls")),
    path("", include("accounts.urls")),
    path("", include("dms.urls")),
]
