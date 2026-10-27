# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer


class HealthView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	@extend_schema(responses=inline_serializer(name='HealthResponse', fields={'status': serializers.CharField()}))
	def get(self, request):
		return Response({'status': 'ok'})


class CsrfTokenView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]

	@method_decorator(ensure_csrf_cookie)
	@extend_schema(responses=inline_serializer(name='CsrfTokenResponse', fields={'csrf_token': serializers.CharField()}))
	def get(self, request):
		return Response({'csrf_token': get_token(request)})


class LoginSerializer(serializers.Serializer):
	username = serializers.CharField(max_length=150)
	password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
	authentication_classes = []
	permission_classes = [AllowAny]
	throttle_classes = [AnonRateThrottle]

	@extend_schema(
		request=LoginSerializer,
		responses={200: inline_serializer(name='LoginResponse', fields={
			'authenticated': serializers.BooleanField(),
			'username': serializers.CharField(),
			'csrf_token': serializers.CharField(),
		}), 401: OpenApiTypes.OBJECT},
	)
	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = authenticate(request, **serializer.validated_data)
		if user is None:
			return Response({'detail': 'نام کاربری یا گذرواژه نادرست است.'}, status=status.HTTP_401_UNAUTHORIZED)
		login(request, user)
		return Response({'authenticated': True, 'username': user.get_username(), 'csrf_token': get_token(request)})


class LogoutView(APIView):
	permission_classes = [IsAuthenticated]
	authentication_classes = [SessionAuthentication]

	@extend_schema(request=None, responses={204: None})
	def post(self, request):
		logout(request)
		return Response(status=204)


class SessionView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(responses=inline_serializer(name='SessionResponse', fields={
		'username': serializers.CharField(),
		'display_name': serializers.CharField(),
		'is_superuser': serializers.BooleanField(),
		'is_manager': serializers.BooleanField(),
		'profile_id': serializers.IntegerField(allow_null=True),
		'roles': inline_serializer(name='SessionRole', fields={
			'company_id': serializers.IntegerField(),
			'role': serializers.CharField(),
		}, many=True),
	}))
	def get(self, request):
		profile = getattr(request.user, 'employee_profile', None)
		roles = list(request.user.role_assignments.values_list('company_id', 'role'))
		return Response({
			'username': request.user.get_username(),
			'display_name': request.user.get_full_name() or request.user.get_username(),
			'is_superuser': request.user.is_superuser,
			'is_manager': profile.direct_reports.filter(is_active=True, user__is_active=True).exists() if profile else False,
			'profile_id': profile.pk if profile else None,
			'roles': [{'company_id': company_id, 'role': role} for company_id, role in roles],
		})