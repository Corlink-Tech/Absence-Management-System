# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer

from identity.models import EmployeeProfile, RoleAssignment
from leave.balances import BalanceService
from leave.models import LeaveEntitlement, LeaveRequest, LeaveType
from leave.serializers import BalanceSerializer, DecisionSerializer, EntitlementChangeSerializer, EntitlementCreateSerializer, LeaveRequestCreateSerializer, LeaveRequestSerializer, LeaveTypeSerializer, ReplacementChoiceSerializer
from leave.services import RequestService


def _run_domain_action(action):
	try:
		return action()
	except ObjectDoesNotExist as error:
		raise NotFound() from error
	except DjangoValidationError as error:
		if hasattr(error, 'message_dict'):
			raise ValidationError(error.message_dict)
		raise ValidationError(error.messages)
	except DjangoPermissionDenied as error:
		raise PermissionDenied(str(error))


def _visible_requests(user):
	queryset = LeaveRequest.objects.select_related('employee__user', 'manager__user', 'leave_type', 'company')
	conditions = Q(employee__user=user)
	conditions |= Q(manager__user=user)
	company_ids = RoleAssignment.objects.filter(user=user, role=RoleAssignment.Role.HR).values_list('company_id', flat=True)
	conditions |= Q(company_id__in=company_ids)
	return queryset.filter(conditions).distinct()


class RequestPagination(LimitOffsetPagination):
	default_limit = 25
	max_limit = 100


class RequestListCreateView(GenericAPIView):
	permission_classes = [IsAuthenticated]
	pagination_class = RequestPagination
	serializer_class = LeaveRequestSerializer

	@extend_schema(operation_id='requests_list', responses=inline_serializer(name='PaginatedRequestList', fields={
		'count': serializers.IntegerField(),
		'next': serializers.URLField(allow_null=True),
		'previous': serializers.URLField(allow_null=True),
		'results': LeaveRequestSerializer(many=True),
	}))
	def get(self, request):
		queryset = _visible_requests(request.user).order_by('-created_at')
		status_filter = request.query_params.get('status')
		if status_filter:
			allowed_statuses = {value for value, label in LeaveRequest.Status.choices}
			if status_filter not in allowed_statuses:
				raise ValidationError({'status': 'Unknown request status.'})
			queryset = queryset.filter(status=status_filter)
		from_value = request.query_params.get('from')
		if from_value:
			from_date = parse_date(from_value)
			if from_date is None:
				raise ValidationError({'from': 'Enter a date in YYYY-MM-DD format.'})
			queryset = queryset.filter(end_date__gte=from_date)
		to_value = request.query_params.get('to')
		if to_value:
			to_date = parse_date(to_value)
			if to_date is None:
				raise ValidationError({'to': 'Enter a date in YYYY-MM-DD format.'})
			queryset = queryset.filter(start_date__lte=to_date)
		page = self.paginate_queryset(queryset)
		serializer = LeaveRequestSerializer(page, many=True, context={'request': request})
		return self.get_paginated_response(serializer.data)

	@extend_schema(operation_id='requests_create', request=LeaveRequestCreateSerializer, responses={201: LeaveRequestSerializer})
	def post(self, request):
		input_serializer = LeaveRequestCreateSerializer(data=request.data)
		input_serializer.is_valid(raise_exception=True)
		data = input_serializer.validated_data
		actor = request.user
		if data.get('employee_id') is not None:
			hr_company_ids = RoleAssignment.objects.filter(
				user=actor,
				role=RoleAssignment.Role.HR,
			).values_list('company_id', flat=True)
			employee = get_object_or_404(
				EmployeeProfile.objects.filter(company_id__in=hr_company_ids).select_related('user', 'company', 'manager__user'),
				pk=data['employee_id'],
			)
		else:
			employee = get_object_or_404(EmployeeProfile.objects.select_related('user', 'company', 'manager__user'), user=actor)
		leave_type = get_object_or_404(LeaveType, pk=data['leave_type_id'])
		replacement = None
		if data.get('replacement_id') is not None:
			replacement = get_object_or_404(EmployeeProfile.objects.select_related('user'), pk=data['replacement_id'])
		created = _run_domain_action(lambda: RequestService.create_request(
			actor=actor,
			employee=employee,
			leave_type=leave_type,
			start_date=data['start_date'],
			end_date=data['end_date'],
			working_days=data['working_days'],
			reason=data.get('reason', ''),
			replacement=replacement,
		))
		serializer = LeaveRequestSerializer(created, context={'request': request})
		return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaveTypeListView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='leave_types_list', responses=LeaveTypeSerializer(many=True))
	def get(self, request):
		company_ids = RoleAssignment.objects.filter(user=request.user).values_list('company_id', flat=True)
		hr_company_ids = RoleAssignment.objects.filter(
			user=request.user,
			role=RoleAssignment.Role.HR,
		).values_list('company_id', flat=True)
		profile = EmployeeProfile.objects.filter(user=request.user, is_active=True).values_list('company_id', flat=True)
		queryset = LeaveType.objects.filter(is_active=True).filter(Q(company_id__in=company_ids) | Q(company_id__in=profile) | Q(company__isnull=True))
		queryset = queryset.order_by('name')
		if RoleAssignment.objects.filter(user=request.user, role=RoleAssignment.Role.HR).exists():
			queryset = queryset.filter(Q(confidential=False) | Q(company_id__in=hr_company_ids) | Q(company__isnull=True))
		else:
			queryset = queryset.filter(confidential=False)
		return Response(LeaveTypeSerializer(queryset.distinct(), many=True).data)


class ReplacementChoicesView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='replacement_choices_list', responses=ReplacementChoiceSerializer(many=True))
	def get(self, request):
		profile = _employee_profile_for_user(request.user)
		employees = EmployeeProfile.objects.filter(
			company=profile.company,
			is_active=True,
			user__is_active=True,
		).exclude(pk=profile.pk).select_related('user').order_by('user__last_name', 'user__first_name')
		return Response([{
			'id': employee.pk,
			'name': employee.user.get_full_name() or employee.user.get_username(),
		} for employee in employees])


class RequestDetailView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='request_detail', responses=LeaveRequestSerializer)
	def get(self, request, request_id):
		leave_request = get_object_or_404(_visible_requests(request.user), pk=request_id)
		return Response(LeaveRequestSerializer(leave_request, context={'request': request}).data)


class RequestActionView(APIView):
	permission_classes = [IsAuthenticated]
	operation = None

	@extend_schema(request=DecisionSerializer, responses=LeaveRequestSerializer)
	def post(self, request, request_id):
		data = DecisionSerializer(data=request.data)
		data.is_valid(raise_exception=True)
		result = _run_domain_action(lambda: self.operation(actor=request.user, request_id=request_id, **data.validated_data))
		return Response(LeaveRequestSerializer(result, context={'request': request}).data)


@extend_schema_view(post=extend_schema(operation_id='request_approve'))
class ApproveRequestView(RequestActionView):
	operation = staticmethod(lambda **kwargs: RequestService.decide(approve=True, **kwargs))


@extend_schema_view(post=extend_schema(operation_id='request_reject'))
class RejectRequestView(RequestActionView):
	operation = staticmethod(lambda **kwargs: RequestService.decide(approve=False, **kwargs))


class CancelRequestView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='request_cancel', request=None, responses=LeaveRequestSerializer)
	def post(self, request, request_id):
		result = _run_domain_action(lambda: RequestService.cancel_pending(actor=request.user, request_id=request_id))
		return Response(LeaveRequestSerializer(result, context={'request': request}).data)


class RequestWithdrawalView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='request_withdraw', request=None, responses=LeaveRequestSerializer)
	def post(self, request, request_id):
		result = _run_domain_action(lambda: RequestService.request_withdrawal(actor=request.user, request_id=request_id))
		return Response(LeaveRequestSerializer(result, context={'request': request}).data)


@extend_schema_view(post=extend_schema(operation_id='request_withdrawal_approve'))
class DecideWithdrawalView(RequestActionView):
	operation = staticmethod(lambda **kwargs: RequestService.decide_withdrawal(approve=True, **kwargs))


@extend_schema_view(post=extend_schema(operation_id='request_withdrawal_reject'))
class RejectWithdrawalView(RequestActionView):
	operation = staticmethod(lambda **kwargs: RequestService.decide_withdrawal(approve=False, **kwargs))


def _employee_profile_for_user(user):
	return get_object_or_404(EmployeeProfile.objects.select_related('company'), user=user, is_active=True)


def _balance_allowed(user, employee):
	if employee.user_id == user.pk:
		return True
	if RoleAssignment.objects.filter(user=user, company=employee.company, role=RoleAssignment.Role.HR).exists():
		return True
	return employee.manager_id is not None and employee.manager.user_id == user.pk


def _visible_balances(user, employee, year):
	balances = BalanceService.for_employee(employee=employee, year=year)
	if RoleAssignment.objects.filter(user=user, company=employee.company, role=RoleAssignment.Role.HR).exists():
		return balances
	return [balance for balance in balances if not employee.leave_entitlements.get(leave_type_id=balance['leave_type_id']).leave_type.confidential]


class MyBalanceView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='balance_me', responses=BalanceSerializer(many=True))
	def get(self, request):
		employee = _employee_profile_for_user(request.user)
		try:
			year = int(request.query_params.get('year', timezone.localdate().year))
		except (TypeError, ValueError):
			raise ValidationError({'year': 'Enter a valid calendar year.'})
		if year < 1900 or year > 2200:
			raise ValidationError({'year': 'Year is outside the supported range.'})
		return Response(_visible_balances(request.user, employee, year))


class EmployeeBalanceView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='employee_balance', responses=BalanceSerializer(many=True))
	def get(self, request, employee_id):
		employee = get_object_or_404(EmployeeProfile.objects.select_related('company', 'manager__user'), pk=employee_id, is_active=True)
		if not _balance_allowed(request.user, employee):
			raise PermissionDenied('You may not view this employee balance.')
		try:
			year = int(request.query_params.get('year', timezone.localdate().year))
		except (TypeError, ValueError):
			raise ValidationError({'year': 'Enter a valid calendar year.'})
		if year < 1900 or year > 2200:
			raise ValidationError({'year': 'Year is outside the supported range.'})
		return Response(_visible_balances(request.user, employee, year))


class EntitlementCreateView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='entitlement_create', request=EntitlementCreateSerializer, responses=inline_serializer(name='CreatedEntitlementResponse', fields={
		'id': serializers.IntegerField(),
		'employee_id': serializers.IntegerField(),
		'leave_type_id': serializers.IntegerField(),
		'year': serializers.IntegerField(),
		'base_days': serializers.DecimalField(max_digits=6, decimal_places=1),
		'carry_over_days': serializers.DecimalField(max_digits=6, decimal_places=1),
		'manual_adjustment': serializers.DecimalField(max_digits=6, decimal_places=1),
	}), methods=['POST'])
	def post(self, request):
		input_serializer = EntitlementCreateSerializer(data=request.data)
		input_serializer.is_valid(raise_exception=True)
		data = input_serializer.validated_data
		employee = get_object_or_404(EmployeeProfile.objects.select_related('company'), pk=data['employee_id'])
		leave_type = get_object_or_404(LeaveType, pk=data['leave_type_id'])
		created = _run_domain_action(lambda: BalanceService.create(
			actor=request.user,
			employee=employee,
			leave_type=leave_type,
			year=data['year'],
			base_days=data['base_days'],
			carry_over_days=data.get('carry_over_days', 0),
			reason=data['reason'],
		))
		return Response({
			'id': created.pk,
			'employee_id': created.employee_id,
			'leave_type_id': created.leave_type_id,
			'year': created.year,
			'base_days': created.base_days,
			'carry_over_days': created.carry_over_days,
			'manual_adjustment': created.manual_adjustment,
		}, status=status.HTTP_201_CREATED)



class EntitlementDetailView(APIView):
	permission_classes = [IsAuthenticated]

	@extend_schema(operation_id='entitlement_update', request=EntitlementChangeSerializer, responses=inline_serializer(name='EntitlementResponse', fields={
		'id': serializers.IntegerField(),
		'employee_id': serializers.IntegerField(),
		'leave_type_id': serializers.IntegerField(),
		'year': serializers.IntegerField(),
		'base_days': serializers.DecimalField(max_digits=6, decimal_places=1),
		'carry_over_days': serializers.DecimalField(max_digits=6, decimal_places=1),
		'manual_adjustment': serializers.DecimalField(max_digits=6, decimal_places=1),
	}))
	def patch(self, request, entitlement_id):
		entitlement = get_object_or_404(LeaveEntitlement.objects.select_related('employee__company'), pk=entitlement_id)
		is_hr = RoleAssignment.objects.filter(
			user=request.user,
			company=entitlement.employee.company,
			role=RoleAssignment.Role.HR,
		).exists()
		if not is_hr:
			raise PermissionDenied('Only HR may adjust leave entitlements.')
		input_serializer = EntitlementChangeSerializer(data=request.data)
		input_serializer.is_valid(raise_exception=True)
		data = input_serializer.validated_data
		updated = _run_domain_action(lambda: BalanceService.adjust(
			actor=request.user,
			entitlement_id=entitlement_id,
			reason=data['reason'],
			base_days=data.get('base_days'),
			carry_over_days=data.get('carry_over_days'),
			adjustment_delta=data.get('adjustment_delta'),
			adjustment_set=data.get('adjustment_set'),
		))
		return Response({
			'id': updated.pk,
			'employee_id': updated.employee_id,
			'leave_type_id': updated.leave_type_id,
			'year': updated.year,
			'base_days': updated.base_days,
			'carry_over_days': updated.carry_over_days,
			'manual_adjustment': updated.manual_adjustment,
		})