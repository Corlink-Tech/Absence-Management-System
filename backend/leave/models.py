# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from identity.models import Company, EmployeeProfile


class LeaveType(models.Model):
	company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.PROTECT, related_name='leave_types')
	code = models.SlugField(max_length=64)
	name = models.CharField(max_length=160)
	is_active = models.BooleanField(default=True)
	requires_approval = models.BooleanField(default=True)
	employee_requestable = models.BooleanField(default=True)
	requires_note = models.BooleanField(default=False)
	requires_replacement = models.BooleanField(default=False)
	counts_against_balance = models.BooleanField(default=False)
	confidential = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(fields=['company', 'code'], name='leave_type_company_code_uniq'),
			models.UniqueConstraint(fields=['code'], condition=Q(company__isnull=True), name='leave_type_global_code_uniq'),
		]

	def clean(self):
		from django.core.exceptions import ValidationError

		if self.confidential and self.employee_requestable:
			raise ValidationError({'employee_requestable': _('Confidential leave types cannot be self-requested.')})

	def __str__(self):
		return self.name


class LeaveRequest(models.Model):
	class Status(models.TextChoices):
		PENDING = 'PENDING', _('Pending')
		ESCALATED = 'ESCALATED', _('Escalated')
		APPROVED = 'APPROVED', _('Approved')
		REJECTED = 'REJECTED', _('Rejected')
		CANCELLED = 'CANCELLED', _('Cancelled')
		WITHDRAWAL_PENDING = 'WITHDRAWAL_PENDING', _('Withdrawal pending')

	ACTIVE_STATUSES = (Status.PENDING, Status.ESCALATED, Status.APPROVED, Status.WITHDRAWAL_PENDING)

	company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='leave_requests')
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='leave_requests')
	manager = models.ForeignKey(EmployeeProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='managed_leave_requests')
	leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='requests')
	start_date = models.DateField()
	end_date = models.DateField()
	working_days = models.DecimalField(max_digits=5, decimal_places=1, validators=[MinValueValidator(0.1), MaxValueValidator(366)])
	reason = models.TextField(blank=True)
	replacement = models.ForeignKey(EmployeeProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name='replacement_leave_requests')
	status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING)
	decision_comment = models.TextField(blank=True)
	decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='leave_decisions')
	decided_at = models.DateTimeField(null=True, blank=True)
	supersedes = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='amendments')
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_leave_requests')
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']
		constraints = [
			models.CheckConstraint(condition=Q(start_date__lte=models.F('end_date')), name='leave_request_dates_ordered'),
			models.CheckConstraint(condition=Q(working_days__gt=0) & Q(working_days__lte=366), name='leave_request_days_positive'),
		]
		indexes = [
			models.Index(fields=['employee', 'status'], name='lreq_emp_status_idx'),
			models.Index(fields=['manager', 'status'], name='lreq_mgr_status_idx'),
			models.Index(fields=['company', 'start_date', 'end_date'], name='lreq_co_dates_idx'),
		]


class RequestEvent(models.Model):
	request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name='events')
	actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='leave_request_events')
	event_type = models.CharField(max_length=48)
	from_status = models.CharField(max_length=24, blank=True)
	to_status = models.CharField(max_length=24, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at', 'pk']
		indexes = [models.Index(fields=['request', 'created_at'], name='leave_event_request_time_idx')]


class LeaveEntitlement(models.Model):
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='leave_entitlements')
	leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='entitlements')
	year = models.PositiveSmallIntegerField()
	base_days = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])
	carry_over_days = models.DecimalField(max_digits=6, decimal_places=1, default=0, validators=[MinValueValidator(0)])
	manual_adjustment = models.DecimalField(max_digits=6, decimal_places=1, default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['employee', 'leave_type', 'year'], name='leave_entitlement_emp_type_year_uniq')]
		indexes = [models.Index(fields=['year', 'leave_type'], name='entitle_year_type_idx')]


class EntitlementEvent(models.Model):
	entitlement = models.ForeignKey(LeaveEntitlement, on_delete=models.PROTECT, related_name='events')
	actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='entitlement_events')
	field = models.CharField(max_length=32)
	old_value = models.DecimalField(max_digits=7, decimal_places=1)
	new_value = models.DecimalField(max_digits=7, decimal_places=1)
	reason = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at', 'pk']
		indexes = [models.Index(fields=['entitlement', 'created_at'], name='entitle_event_time_idx')]