# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from identity.models import Company, Department, EmployeeProfile, EmploymentContract, RoleAssignment, User


class OrganizationModelTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(code='zsh-main', name='Zakaria Shimi')
		self.user = User.objects.create_user(username='employee-1', password='test-password')
		self.employee = EmployeeProfile.objects.create(
			user=self.user,
			company=self.company,
			employee_number='1001',
			hired_on=date(2025, 1, 1),
		)

	def test_roles_are_scoped_to_company_and_unique(self):
		RoleAssignment.objects.create(
			user=self.user,
			company=self.company,
			role=RoleAssignment.Role.HR,
		)
		self.assertEqual(self.user.role_assignments.filter(company=self.company, role='hr').count(), 1)

	def test_department_cannot_have_parent_from_another_company(self):
		other_company = Company.objects.create(code='zsh-other', name='Other company')
		parent = Department.objects.create(company=other_company, code='parent', name='Parent')
		child = Department(company=self.company, parent=parent, code='child', name='Child')

		with self.assertRaises(ValidationError):
			child.full_clean()

	def test_contract_rejects_duplicate_or_invalid_weekdays(self):
		contract = EmploymentContract(
			employee=self.employee,
			valid_from=date(2026, 1, 1),
			percentage=75,
			working_week=[0, 0, 8],
		)

		with self.assertRaises(ValidationError):
			contract.full_clean()

	def test_contract_does_not_infer_leave_entitlement(self):
		contract = EmploymentContract.objects.create(
			employee=self.employee,
			valid_from=date(2026, 1, 1),
			percentage=75,
			working_week=[0, 1, 2, 3, 4],
		)

		self.assertEqual(contract.percentage, 75)
		self.assertFalse(hasattr(contract, 'annual_entitlement'))

	def test_employee_manager_must_belong_to_same_company(self):
		other_company = Company.objects.create(code='zsh-other', name='Other company')
		manager_user = User.objects.create_user(username='other-manager', password='test-password')
		other_manager = EmployeeProfile.objects.create(user=manager_user, company=other_company, employee_number='2001')
		self.employee.manager = other_manager

		with self.assertRaises(ValidationError):
			self.employee.full_clean()

	def test_employment_contract_periods_cannot_overlap(self):
		EmploymentContract.objects.create(
			employee=self.employee,
			valid_from=date(2026, 1, 1),
			valid_until=date(2026, 6, 30),
			percentage=100,
			working_week=[0, 1, 2, 3, 4],
		)
		overlapping = EmploymentContract(
			employee=self.employee,
			valid_from=date(2026, 6, 1),
			percentage=80,
			working_week=[0, 1, 2, 3],
		)

		with self.assertRaises(ValidationError):
			overlapping.full_clean()