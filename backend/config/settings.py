# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
	if not DEBUG:
		raise ImproperlyConfigured('DJANGO_SECRET_KEY must be configured outside debug mode.')
	SECRET_KEY = 'development-only-change-me'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'drf_spectacular',
	'identity',
	'leave',
]

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.middleware.locale.LocaleMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
	'BACKEND': 'django.template.backends.django.DjangoTemplates',
	'APP_DIRS': True,
	'OPTIONS': {
		'context_processors': [
			'django.template.context_processors.request',
			'django.contrib.auth.context_processors.auth',
			'django.contrib.messages.context_processors.messages',
		],
	},
}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

if os.environ.get('DB_ENGINE') == 'postgresql':
	DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.postgresql',
			'NAME': os.environ.get('DB_NAME', 'zsh_leave'),
			'USER': os.environ.get('DB_USER', 'zsh_leave'),
			'PASSWORD': os.environ.get('DB_PASSWORD', ''),
			'HOST': os.environ.get('DB_HOST', 'localhost'),
			'PORT': os.environ.get('DB_PORT', '5432'),
			'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
		},
	}
else:
	DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
	{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
	{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
	{'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
	{'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = os.environ.get('TZ', 'Asia/Tehran')
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'identity.User'

REST_FRAMEWORK = {
	'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
	'DEFAULT_AUTHENTICATION_CLASSES': [
		'rest_framework.authentication.SessionAuthentication',
	],
	'DEFAULT_PERMISSION_CLASSES': [
		'rest_framework.permissions.IsAuthenticated',
	],
	'DEFAULT_THROTTLE_CLASSES': [
		'rest_framework.throttling.AnonRateThrottle',
		'rest_framework.throttling.UserRateThrottle',
	],
	'DEFAULT_THROTTLE_RATES': {
		'anon': '30/minute',
		'user': '120/minute',
	},
}

SPECTACULAR_SETTINGS = {
	'TITLE': 'Zakaria Shimi Leave Management API',
	'DESCRIPTION': 'Versioned API for the independent leave and absence management system.',
	'VERSION': '0.1.0',
	'SERVE_INCLUDE_SCHEMA': False,
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'