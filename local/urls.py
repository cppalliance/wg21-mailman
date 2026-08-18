# Production-like URL layout (matches ansible-mailman3 defaults and lists.wg21.org).
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

urlpatterns = [
    path(
        "",
        RedirectView.as_view(url=reverse_lazy("list_index"), permanent=True),
    ),
    path("mailman3/", include("postorius.urls")),
    path("archives/", include("hyperkitty.urls")),
    path("", include("django_mailman3.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]
