# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from datetime import date


class User(AbstractUser):
	pass


class Company(models.Model):
	code = models.SlugField(max_length=64, unique=True)
	name = models.CharField(max_length=200)
	timezone = models.CharField(max_length=64, default='Asia/Tehran')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']
		verbose_name = _('company')
		verbose_name_plural = _('companies')

	def __str__(self):
		return self.name


class Department(models.Model):
	company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='departments')
	parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
	code = models.CharField(max_length=64)
	name = models.CharField(max_length=200)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['company__name', 'name']
		constraints = [models.UniqueConstraint(fields=['company', 'code'], name='identity_department_company_code_uniq')]

	def clean(self):
		if self.parent_id and self.parent.company_id != self.company_id:
			raise ValidationError({'parent': _('Parent department must belong to the same company.')})

	def __str__(self):
		return self.name


class Position(models.Model):
	company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.PROTECT, related_name='positions')
	code = models.CharField(max_length=64)
	name = models.CharField(max_length=200)
	
	class Meta:
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(fields=['company', 'code'], name='identity_position_company_code_uniq'),
			models.UniqueConstraint(fields=['code'], condition=Q(company__isnull=True), name='identity_position_global_code_uniq'),
		]

	def __str__(self):
		return self.name


class EmployeeProfile(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='employee_profile')
	company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='employees')
	department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT, related_name='employees')
	position = models.ForeignKey(Position, null=True, blank=True, on_delete=models.PROTECT, related_name='employees')
	manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='direct_reports')
	employee_number = models.CharField(max_length=64)
	hired_on = models.DateField(null=True, blank=True)
	ended_on = models.DateField(null=True, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['user__last_name', 'user__first_name']
		constraints = [models.UniqueConstraint(fields=['company', 'employee_number'], name='identity_employee_company_number_uniq')]
		indexes = [models.Index(fields=['company', 'is_active'], name='id_emp_company_active_idx')]

	def clean(self):
		if self.hired_on and self.ended_on and self.ended_on < self.hired_on:
			raise ValidationError({'ended_on': _('End date cannot precede hire date.')})
		if self.department_id and self.department.company_id != self.company_id:
			raise ValidationError({'department': _('Department must belong to the employee company.')})
		if self.position_id and self.position.company_id not in (None, self.company_id):
			raise ValidationError({'position': _('Position must be global or belong to the employee company.')})
		if self.manager_id and self.manager_id == self.pk:
			raise ValidationError({'manager': _('An employee cannot manage themselves.')})
		if self.manager_id and self.manager.company_id != self.company_id:
			raise ValidationError({'manager': _('Manager must belong to the employee company.')})

	def __str__(self):
		return f'{self.employee_number}: {self.user}'


class RoleAssignment(models.Model):
	class Role(models.TextChoices):
		EMPLOYEE = 'employee', _('Employee')
		MANAGER = 'manager', _('Line manager')
		HR = 'hr', _('Human resources')
		SYSTEM_ADMIN = 'system_admin', _('System administrator')
		EXECUTIVE = 'executive', _('Executive read-only')

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='role_assignments')
	company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='role_assignments')
	role = models.CharField(max_length=32, choices=Role.choices)
	assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_roles')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=['user', 'company', 'role'], name='identity_user_company_role_uniq')]
		indexes = [models.Index(fields=['company', 'role'], name='identity_role_company_role_idx')]


class EmploymentContract(models.Model):
	employee = models.ForeignKey(EmployeeProfile, on_delete=models.PROTECT, related_name='contracts')
	valid_from = models.DateField()
	valid_until = models.DateField(null=True, blank=True)
	percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
	working_week = models.JSONField(default=list)
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='created_contract_periods')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['employee_id', '-valid_from']
		constraints = [models.UniqueConstraint(fields=['employee', 'valid_from'], name='identity_contract_employee_start_uniq')]
		indexes = [models.Index(fields=['employee', 'valid_from', 'valid_until'], name='identity_contract_period_idx')]

	def clean(self):
		errors = {}
		if self.valid_until and self.valid_until < self.valid_from:
			errors['valid_until'] = _('Contract end date cannot precede its start date.')
		if not isinstance(self.working_week, list) or any(type(day) is not int or day < 0 or day > 6 for day in self.working_week):
			errors['working_week'] = _('Working weekdays must be a list of weekdays from 0 to 6.')
		elif len(set(self.working_week)) != len(self.working_week):
			errors['working_week'] = _('Working weekdays cannot contain duplicates.')
		if self.employee_id:
			latest_start = self.valid_until or date.max
			overlaps = EmploymentContract.objects.filter(
				employee_id=self.employee_id,
				valid_from__lte=latest_start,
			).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=self.valid_from))
			if self.pk:
				overlaps = overlaps.exclude(pk=self.pk)
			if overlaps.exists():
				errors['valid_from'] = _('Contract periods for an employee cannot overlap.')
		if errors:
			raise ValidationError(errors)