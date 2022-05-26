from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from files import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/<int:year>/<int:month>', views.DashboardView.as_view(), name='dashboard-month'),
    path("rufnummern/<int:year>/<int:month>", views.RufnummernListView.as_view(), name='rufnummern-month'),
    path("rufnummern/", views.RufnummernListView.as_view(), name='rufnummern'),
    path('rufnummer/<int:rufnummer>/<int:year>/<int:month>', views.RufnummerRechnungsPositionenListView.as_view(), name='detail'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
