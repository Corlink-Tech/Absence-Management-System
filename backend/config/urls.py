# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.urls import include, path
from django.contrib import admin
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import CsrfTokenView, HealthView, LoginView, LogoutView, SessionView

urlpatterns = [
	path('admin/', admin.site.urls),
	path('api/v1/schema', SpectacularAPIView.as_view(), name='openapi-schema'),
	path('api/docs', SpectacularSwaggerView.as_view(url_name='openapi-schema'), name='swagger-ui'),
	path('api/v1/health/live', HealthView.as_view(), name='health-live'),
	path('api/v1/auth/csrf', CsrfTokenView.as_view(), name='auth-csrf'),
	path('api/v1/auth/login', LoginView.as_view(), name='auth-login'),
	path('api/v1/auth/logout', LogoutView.as_view(), name='auth-logout'),
	path('api/v1/auth/me', SessionView.as_view(), name='auth-me'),
	path('api/v1/', include('leave.urls')),
]