# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from identity.models import EmployeeProfile, RoleAssignment
from leave.models import LeaveRequest, LeaveType, RequestEvent


def _has_company_role(user, company_id, *roles):
	return user.is_active and RoleAssignment.objects.filter(
		user=user,
		company_id=company_id,
		role__in=roles,
	).exists()


def _record_event(request, actor, event_type, from_status='', to_status=''):
	RequestEvent.objects.create(
		request=request,
		actor=actor,
		event_type=event_type,
		from_status=from_status,
		to_status=to_status,
	)


class RequestService:
	@staticmethod
	@transaction.atomic
	def create_request(*, actor, employee, leave_type, start_date, end_date, working_days, reason='', replacement=None):
		if not actor.is_active or not employee.is_active or not employee.user.is_active:
			raise PermissionDenied('Inactive users cannot create leave requests.')
		is_hr = _has_company_role(actor, employee.company_id, RoleAssignment.Role.HR)
		hr_recording = employee.user_id != actor.pk
		if hr_recording and not is_hr:
			raise PermissionDenied('Only HR may record leave for another employee.')
		if not hr_recording and employee.user_id != actor.pk:
			raise PermissionDenied('Employees may only create requests for themselves.')
		if employee.company_id is None or not employee.company.is_active:
			raise ValidationError('The employee company is not active.')

		leave_type = LeaveType.objects.select_for_update().filter(pk=leave_type.pk, is_active=True).first()
		if leave_type is None:
			raise ValidationError({'leave_type': 'This leave type is not active.'})
		if leave_type.company_id not in (None, employee.company_id):
			raise ValidationError('The leave type is not available in this company.')
		if not is_hr and (not leave_type.employee_requestable or leave_type.confidential):
			raise PermissionDenied('This leave type cannot be requested by employees.')
		if leave_type.confidential and not is_hr:
			raise PermissionDenied('Only HR may record confidential leave.')
		hr_recording = hr_recording or (is_hr and (not leave_type.employee_requestable or leave_type.confidential))

		if start_date > end_date:
			raise ValidationError({'end_date': 'End date cannot precede start date.'})
		if start_date.year != end_date.year:
			raise ValidationError({'end_date': 'Split requests at the year boundary until the annual day allocation policy is configured.'})
		if not is_hr:
			company_today = timezone.localdate(timezone=ZoneInfo(employee.company.timezone))
			if start_date < company_today:
				raise ValidationError({'start_date': 'Employees cannot request leave that starts in the past.'})
		try:
			day_count = Decimal(str(working_days))
		except (InvalidOperation, TypeError, ValueError):
			raise ValidationError({'working_days': 'Enter a valid working-day count.'})
		if not day_count.is_finite() or day_count <= 0 or day_count > 366:
			raise ValidationError({'working_days': 'Working days must be greater than zero and at most 366.'})
		if day_count != day_count.to_integral_value():
			raise ValidationError({'working_days': 'Only full working days are supported.'})
		if day_count > (end_date - start_date).days + 1:
			raise ValidationError({'working_days': 'Working days cannot exceed the calendar date range.'})
		if leave_type.requires_note and not reason.strip():
			raise ValidationError({'reason': 'A reason is required for this leave type.'})
		if leave_type.requires_replacement and not hr_recording and replacement is None:
			raise ValidationError({'replacement': 'A replacement employee is required.'})
		if replacement:
			if not replacement.is_active or not replacement.user.is_active or replacement.company_id != employee.company_id:
				raise ValidationError({'replacement': 'Replacement must be an active employee in the same company.'})
			if replacement.pk == employee.pk:
				raise ValidationError({'replacement': 'An employee cannot replace themselves.'})

		EmployeeProfile.objects.select_for_update().get(pk=employee.pk)
		overlaps = LeaveRequest.objects.filter(
			employee=employee,
			status__in=LeaveRequest.ACTIVE_STATUSES,
			start_date__lte=end_date,
			end_date__gte=start_date,
		)
		if overlaps.exists():
			raise ValidationError('This request overlaps another active leave request.')

		manager = employee.manager
		if manager and (not manager.is_active or not manager.user.is_active or manager.company_id != employee.company_id):
			manager = None
		if hr_recording or not leave_type.requires_approval:
			status = LeaveRequest.Status.APPROVED
		elif manager is None:
			status = LeaveRequest.Status.ESCALATED
		else:
			status = LeaveRequest.Status.PENDING
		request = LeaveRequest.objects.create(
			company=employee.company,
			employee=employee,
			manager=manager,
			leave_type=leave_type,
			start_date=start_date,
			end_date=end_date,
			working_days=day_count,
			reason=reason.strip(),
			replacement=replacement,
			status=status,
			created_by=actor,
			decided_by=actor if status == LeaveRequest.Status.APPROVED else None,
			decided_at=timezone.now() if status == LeaveRequest.Status.APPROVED else None,
		)
		_record_event(request, actor, 'request_created', to_status=status)
		return request

	@staticmethod
	@transaction.atomic
	def decide(*, actor, request_id, approve, reason=''):
		request = LeaveRequest.objects.select_for_update(of=('self',)).select_related('manager', 'employee', 'leave_type').get(pk=request_id)
		if not actor.is_active:
			raise PermissionDenied('Inactive users cannot decide requests.')
		if request.status not in (LeaveRequest.Status.PENDING, LeaveRequest.Status.ESCALATED):
			raise ValidationError('This request is no longer awaiting a decision.')
		is_hr = _has_company_role(actor, request.company_id, RoleAssignment.Role.HR)
		is_manager = request.status == LeaveRequest.Status.PENDING and request.manager_id is not None and request.manager.user_id == actor.pk
		if not (is_hr or is_manager):
			raise PermissionDenied('You may not decide this request.')
		if request.leave_type.confidential and not is_hr:
			raise PermissionDenied('Only HR may decide confidential leave.')
		if not approve and not reason.strip():
			raise ValidationError({'reason': 'A reason is required to reject a request.'})
		previous = request.status
		request.status = LeaveRequest.Status.APPROVED if approve else LeaveRequest.Status.REJECTED
		request.decision_comment = reason.strip()
		request.decided_by = actor
		request.decided_at = timezone.now()
		request.save(update_fields=['status', 'decision_comment', 'decided_by', 'decided_at', 'updated_at'])
		_record_event(request, actor, 'request_approved' if approve else 'request_rejected', previous, request.status)
		return request

	@staticmethod
	@transaction.atomic
	def cancel_pending(*, actor, request_id):
		request = LeaveRequest.objects.select_for_update().select_related('employee').get(pk=request_id)
		if request.employee.user_id != actor.pk or not actor.is_active:
			raise PermissionDenied('Only the active request owner may cancel this request.')
		if request.status not in (LeaveRequest.Status.PENDING, LeaveRequest.Status.ESCALATED):
			raise ValidationError('Only a pending request can be cancelled directly.')
		previous = request.status
		request.status = LeaveRequest.Status.CANCELLED
		request.save(update_fields=['status', 'updated_at'])
		_record_event(request, actor, 'request_cancelled', previous, request.status)
		return request

	@staticmethod
	@transaction.atomic
	def request_withdrawal(*, actor, request_id):
		request = LeaveRequest.objects.select_for_update().select_related('employee').get(pk=request_id)
		if request.employee.user_id != actor.pk or not actor.is_active:
			raise PermissionDenied('Only the active request owner may request withdrawal.')
		if request.status != LeaveRequest.Status.APPROVED:
			raise ValidationError('Only approved leave can be withdrawn.')
		previous = request.status
		request.status = LeaveRequest.Status.WITHDRAWAL_PENDING
		request.save(update_fields=['status', 'updated_at'])
		_record_event(request, actor, 'withdrawal_requested', previous, request.status)
		return request

	@staticmethod
	@transaction.atomic
	def decide_withdrawal(*, actor, request_id, approve, reason=''):
		request = LeaveRequest.objects.select_for_update(of=('self',)).select_related('manager', 'leave_type').get(pk=request_id)
		if not actor.is_active:
			raise PermissionDenied('Inactive users cannot decide withdrawals.')
		if request.status != LeaveRequest.Status.WITHDRAWAL_PENDING:
			raise ValidationError('This request has no pending withdrawal.')
		is_hr = _has_company_role(actor, request.company_id, RoleAssignment.Role.HR)
		is_manager = request.manager_id is not None and request.manager.user_id == actor.pk
		if not (is_hr or is_manager):
			raise PermissionDenied('You may not decide this withdrawal.')
		if request.leave_type.confidential and not is_hr:
			raise PermissionDenied('Only HR may decide confidential withdrawals.')
		if not approve and not reason.strip():
			raise ValidationError({'reason': 'A reason is required to reject a withdrawal.'})
		previous = request.status
		request.status = LeaveRequest.Status.CANCELLED if approve else LeaveRequest.Status.APPROVED
		request.decision_comment = reason.strip()
		request.decided_by = actor
		request.decided_at = timezone.now()
		request.save(update_fields=['status', 'decision_comment', 'decided_by', 'decided_at', 'updated_at'])
		_record_event(request, actor, 'withdrawal_approved' if approve else 'withdrawal_rejected', previous, request.status)
		return request