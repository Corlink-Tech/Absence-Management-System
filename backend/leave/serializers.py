# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from rest_framework import serializers

from leave.models import LeaveEntitlement, LeaveRequest, LeaveType


class LeaveRequestSerializer(serializers.ModelSerializer):
	employee_id = serializers.IntegerField(read_only=True)
	employee_name = serializers.SerializerMethodField()
	leave_type_id = serializers.IntegerField(read_only=True)
	leave_type_name = serializers.SerializerMethodField()

	class Meta:
		model = LeaveRequest
		fields = [
			'id', 'employee_id', 'employee_name', 'leave_type_id', 'leave_type_name',
			'start_date', 'end_date', 'working_days', 'reason', 'replacement_id',
			'status', 'decision_comment', 'created_at', 'decided_at',
		]
		read_only_fields = fields

	def _is_hr(self, request):
		user = self.context['request'].user
		return user.role_assignments.filter(company_id=request.company_id, role='hr').exists()

	def get_employee_name(self, request) -> str:
		user = request.employee.user
		return user.get_full_name() or user.get_username()

	def get_leave_type_name(self, request) -> str:
		if request.leave_type.confidential and not self._is_hr(request):
			return 'Absent'
		return request.leave_type.name

	def to_representation(self, instance):
		data = super().to_representation(instance)
		if instance.leave_type.confidential and not self._is_hr(instance):
			data['leave_type_id'] = None
			data['reason'] = ''
			data['decision_comment'] = ''
		return data


class LeaveTypeSerializer(serializers.ModelSerializer):
	class Meta:
		model = LeaveType
		fields = ['id', 'code', 'name', 'requires_approval', 'employee_requestable', 'requires_note', 'requires_replacement', 'counts_against_balance']


class BalanceSerializer(serializers.Serializer):
	leave_type_id = serializers.IntegerField()
	leave_type = serializers.CharField()
	year = serializers.IntegerField()
	base_days = serializers.DecimalField(max_digits=6, decimal_places=1)
	carry_over_days = serializers.DecimalField(max_digits=6, decimal_places=1)
	manual_adjustment = serializers.DecimalField(max_digits=6, decimal_places=1)
	entitlement = serializers.DecimalField(max_digits=7, decimal_places=1)
	used = serializers.DecimalField(max_digits=7, decimal_places=1)
	pending = serializers.DecimalField(max_digits=7, decimal_places=1)
	remaining = serializers.DecimalField(max_digits=7, decimal_places=1)
	available = serializers.DecimalField(max_digits=7, decimal_places=1)


class ReplacementChoiceSerializer(serializers.Serializer):
	id = serializers.IntegerField()
	name = serializers.CharField()


class LeaveRequestCreateSerializer(serializers.Serializer):
	employee_id = serializers.IntegerField(required=False)
	leave_type_id = serializers.IntegerField()
	start_date = serializers.DateField()
	end_date = serializers.DateField()
	working_days = serializers.DecimalField(max_digits=5, decimal_places=1)
	reason = serializers.CharField(required=False, allow_blank=True, max_length=10000)
	replacement_id = serializers.IntegerField(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
	reason = serializers.CharField(required=False, allow_blank=True, max_length=10000)


class EntitlementChangeSerializer(serializers.Serializer):
	base_days = serializers.DecimalField(max_digits=6, decimal_places=1, required=False)
	carry_over_days = serializers.DecimalField(max_digits=6, decimal_places=1, required=False)
	adjustment_delta = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
	adjustment_set = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
	reason = serializers.CharField(max_length=10000)


class EntitlementCreateSerializer(serializers.Serializer):
	employee_id = serializers.IntegerField()
	leave_type_id = serializers.IntegerField()
	year = serializers.IntegerField(min_value=1900, max_value=2200)
	base_days = serializers.DecimalField(max_digits=6, decimal_places=1, min_value=0)
	carry_over_days = serializers.DecimalField(max_digits=6, decimal_places=1, min_value=0, required=False, default=0)
	reason = serializers.CharField(max_length=10000)