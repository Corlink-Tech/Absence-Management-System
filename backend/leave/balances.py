# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from identity.models import EmployeeProfile, RoleAssignment
from leave.models import EntitlementEvent, LeaveEntitlement, LeaveRequest


class BalanceService:
	@staticmethod
	def for_employee(*, employee, year):
		entitlements = LeaveEntitlement.objects.filter(
			employee=employee,
			year=year,
			leave_type__counts_against_balance=True,
		).select_related('leave_type')
		result = []
		for entitlement in entitlements:
			requests = LeaveRequest.objects.filter(
				employee=employee,
				leave_type=entitlement.leave_type,
				start_date__year=year,
			)
			used = sum(
				(request.working_days for request in requests if request.status == LeaveRequest.Status.APPROVED),
				Decimal('0'),
			)
			pending = sum(
				(request.working_days for request in requests if request.status in (LeaveRequest.Status.PENDING, LeaveRequest.Status.ESCALATED)),
				Decimal('0'),
			)
			total = entitlement.base_days + entitlement.carry_over_days + entitlement.manual_adjustment
			result.append({
				'leave_type_id': entitlement.leave_type_id,
				'leave_type': entitlement.leave_type.name,
				'year': year,
				'base_days': entitlement.base_days,
				'carry_over_days': entitlement.carry_over_days,
				'manual_adjustment': entitlement.manual_adjustment,
				'entitlement': total,
				'used': used,
				'pending': pending,
				'remaining': total - used,
				'available': total - used - pending,
			})
		return result

	@staticmethod
	@transaction.atomic
	def create(*, actor, employee, leave_type, year, base_days, carry_over_days=0, reason):
		is_hr = actor.is_active and RoleAssignment.objects.filter(
			user=actor,
			company_id=employee.company_id,
			role=RoleAssignment.Role.HR,
		).exists()
		if not is_hr:
			raise PermissionDenied('Only HR may create leave entitlements.')
		if not employee.is_active or not employee.company.is_active:
			raise ValidationError('The employee or company is not active.')
		if leave_type.company_id not in (None, employee.company_id) or not leave_type.is_active or not leave_type.counts_against_balance:
			raise ValidationError({'leave_type': 'The leave type cannot have an entitlement for this employee.'})
		if not reason.strip():
			raise ValidationError({'reason': 'A reason is required when creating an entitlement.'})

		EmployeeProfile.objects.select_for_update().get(pk=employee.pk)
		if LeaveEntitlement.objects.filter(employee=employee, leave_type=leave_type, year=year).exists():
			raise ValidationError('An entitlement already exists for this employee, type and year.')
		entitlement = LeaveEntitlement.objects.create(
			employee=employee,
			leave_type=leave_type,
			year=year,
			base_days=base_days,
			carry_over_days=carry_over_days,
		)
		for field, value in (('base_days', entitlement.base_days), ('carry_over_days', entitlement.carry_over_days)):
			if value:
				EntitlementEvent.objects.create(
					entitlement=entitlement,
					actor=actor,
					field=field,
					old_value=Decimal('0'),
					new_value=value,
					reason=reason.strip(),
				)
		return entitlement

	@staticmethod
	@transaction.atomic
	def adjust(*, actor, entitlement_id, reason, base_days=None, carry_over_days=None, adjustment_delta=None, adjustment_set=None):
		entitlement = LeaveEntitlement.objects.select_for_update().select_related('employee__company').get(pk=entitlement_id)
		is_hr = actor.is_active and RoleAssignment.objects.filter(
			user=actor,
			company_id=entitlement.employee.company_id,
			role=RoleAssignment.Role.HR,
		).exists()
		if not is_hr:
			raise PermissionDenied('Only HR may adjust leave entitlements.')
		if adjustment_delta is not None and adjustment_set is not None:
			raise ValidationError('Use either adjustment_delta or adjustment_set, not both.')
		if not reason.strip():
			raise ValidationError({'reason': 'A reason is required for entitlement changes.'})

		changes = {
			'base_days': base_days,
			'carry_over_days': carry_over_days,
		}
		if adjustment_delta is not None:
			changes['manual_adjustment'] = entitlement.manual_adjustment + Decimal(str(adjustment_delta))
		elif adjustment_set is not None:
			changes['manual_adjustment'] = Decimal(str(adjustment_set))

		updated_fields = []
		for field, proposed_value in changes.items():
			if proposed_value is None:
				continue
			value = Decimal(str(proposed_value))
			if not value.is_finite() or (field in ('base_days', 'carry_over_days') and value < 0):
				raise ValidationError({field: 'Enter a finite, non-negative value.'})
			previous = getattr(entitlement, field)
			if value == previous:
				continue
			setattr(entitlement, field, value)
			updated_fields.append(field)
			EntitlementEvent.objects.create(
				entitlement=entitlement,
				actor=actor,
				field=field,
				old_value=previous,
				new_value=value,
				reason=reason.strip(),
			)
		if updated_fields:
			entitlement.save(update_fields=[*updated_fields, 'updated_at'])
		return entitlement