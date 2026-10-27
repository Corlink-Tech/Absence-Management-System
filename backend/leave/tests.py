# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from identity.models import Company, EmployeeProfile, RoleAssignment, User
from leave.balances import BalanceService
from leave.models import EntitlementEvent, LeaveEntitlement, LeaveRequest, LeaveType
from leave.services import RequestService


class RequestServiceTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(code='zsh-main', name='Zakaria Shimi')
		self.employee_user = User.objects.create_user(username='employee', password='test-password')
		self.manager_user = User.objects.create_user(username='manager', password='test-password')
		self.employee = EmployeeProfile.objects.create(user=self.employee_user, company=self.company, employee_number='1001')
		self.manager = EmployeeProfile.objects.create(user=self.manager_user, company=self.company, employee_number='1002')
		self.employee.manager = self.manager
		self.employee.save(update_fields=['manager'])
		self.leave_type = LeaveType.objects.create(company=self.company, code='annual', name='Annual leave')

	def create_request(self):
		return RequestService.create_request(
			actor=self.employee_user,
			employee=self.employee,
			leave_type=self.leave_type,
			start_date=date(2026, 11, 2),
			end_date=date(2026, 11, 3),
			working_days='2',
		)

	def test_manager_approval_is_atomic_and_audited(self):
		request = self.create_request()

		approved = RequestService.decide(actor=self.manager_user, request_id=request.pk, approve=True)

		self.assertEqual(approved.status, LeaveRequest.Status.APPROVED)
		self.assertEqual(list(approved.events.values_list('event_type', flat=True)), ['request_created', 'request_approved'])

	def test_rejection_requires_reason_and_keeps_request_pending(self):
		request = self.create_request()

		with self.assertRaises(ValidationError):
			RequestService.decide(actor=self.manager_user, request_id=request.pk, approve=False)

		request.refresh_from_db()
		self.assertEqual(request.status, LeaveRequest.Status.PENDING)

	def test_other_manager_cannot_decide(self):
		request = self.create_request()
		other_user = User.objects.create_user(username='other-manager', password='test-password')

		with self.assertRaises(PermissionDenied):
			RequestService.decide(actor=other_user, request_id=request.pk, approve=True)

	def test_overlapping_active_request_is_rejected(self):
		self.create_request()

		with self.assertRaises(ValidationError):
			self.create_request()

	def test_fractional_working_days_are_rejected_until_half_days_are_supported(self):
		with self.assertRaises(ValidationError):
			RequestService.create_request(
				actor=self.employee_user,
				employee=self.employee,
				leave_type=self.leave_type,
				start_date=date(2026, 11, 5),
				end_date=date(2026, 11, 5),
				working_days='0.5',
			)

	def test_employee_cannot_request_past_leave_but_hr_may_record_it(self):
		with self.assertRaises(ValidationError):
			RequestService.create_request(
				actor=self.employee_user,
				employee=self.employee,
				leave_type=self.leave_type,
				start_date=date(2026, 1, 5),
				end_date=date(2026, 1, 5),
				working_days=1,
			)

		hr_user = User.objects.create_user(username='hr-past', password='test-password')
		RoleAssignment.objects.create(user=hr_user, company=self.company, role=RoleAssignment.Role.HR)
		request = RequestService.create_request(
			actor=hr_user,
			employee=self.employee,
			leave_type=self.leave_type,
			start_date=date(2026, 1, 5),
			end_date=date(2026, 1, 5),
			working_days=1,
		)
		self.assertEqual(request.status, LeaveRequest.Status.APPROVED)

	def test_cross_year_request_is_rejected_until_allocation_policy_exists(self):
		with self.assertRaises(ValidationError):
			RequestService.create_request(
				actor=self.employee_user,
				employee=self.employee,
				leave_type=self.leave_type,
				start_date=date(2026, 12, 31),
				end_date=date(2027, 1, 1),
				working_days=2,
			)

	def test_missing_manager_routes_request_to_escalated(self):
		self.employee.manager = None
		self.employee.save(update_fields=['manager'])

		request = self.create_request()

		self.assertEqual(request.status, LeaveRequest.Status.ESCALATED)

	def test_inactive_or_cross_company_manager_routes_request_to_hr(self):
		other_company = Company.objects.create(code='zsh-other', name='Other company')
		inactive_manager_user = User.objects.create_user(username='inactive-manager', password='test-password', is_active=False)
		inactive_manager = EmployeeProfile.objects.create(user=inactive_manager_user, company=other_company, employee_number='2001')
		self.employee.manager = inactive_manager
		self.employee.save(update_fields=['manager'])

		request = self.create_request()

		self.assertEqual(request.status, LeaveRequest.Status.ESCALATED)
		self.assertIsNone(request.manager_id)

	def test_hr_can_record_non_requestable_leave_directly(self):
		hr_user = User.objects.create_user(username='hr', password='test-password')
		RoleAssignment.objects.create(user=hr_user, company=self.company, role=RoleAssignment.Role.HR)
		sick_type = LeaveType.objects.create(
			company=self.company,
			code='sick',
			name='Sick leave',
			requires_approval=False,
			employee_requestable=False,
		)

		request = RequestService.create_request(
			actor=hr_user,
			employee=self.employee,
			leave_type=sick_type,
			start_date=date(2026, 11, 4),
			end_date=date(2026, 11, 4),
			working_days=1,
		)

		self.assertEqual(request.status, LeaveRequest.Status.APPROVED)
		self.assertEqual(request.created_by, hr_user)

	def test_employee_cannot_request_hr_only_type(self):
		sick_type = LeaveType.objects.create(
			company=self.company,
			code='sick',
			name='Sick leave',
			requires_approval=False,
			employee_requestable=False,
		)

		with self.assertRaises(PermissionDenied):
			RequestService.create_request(
				actor=self.employee_user,
				employee=self.employee,
				leave_type=sick_type,
				start_date=date(2026, 11, 4),
				end_date=date(2026, 11, 4),
				working_days=1,
			)

	def test_manager_cannot_decide_after_request_is_escalated(self):
		request = self.create_request()
		request.status = LeaveRequest.Status.ESCALATED
		request.save(update_fields=['status'])

		with self.assertRaises(PermissionDenied):
			RequestService.decide(actor=self.manager_user, request_id=request.pk, approve=True)

	def test_hr_can_record_own_non_requestable_leave(self):
		RoleAssignment.objects.create(user=self.employee_user, company=self.company, role=RoleAssignment.Role.HR)
		sick_type = LeaveType.objects.create(
			company=self.company,
			code='sick-self',
			name='Sick leave',
			requires_approval=False,
			employee_requestable=False,
		)

		request = RequestService.create_request(
			actor=self.employee_user,
			employee=self.employee,
			leave_type=sick_type,
			start_date=date(2026, 11, 4),
			end_date=date(2026, 11, 4),
			working_days=1,
		)

		self.assertEqual(request.status, LeaveRequest.Status.APPROVED)

	def test_manager_cannot_decide_confidential_withdrawal(self):
		hr_user = User.objects.create_user(username='hr-confidential', password='test-password')
		RoleAssignment.objects.create(user=hr_user, company=self.company, role=RoleAssignment.Role.HR)
		confidential_type = LeaveType.objects.create(
			company=self.company,
			code='medical-confidential',
			name='Confidential leave',
			requires_approval=False,
			employee_requestable=False,
			confidential=True,
		)
		request = RequestService.create_request(
			actor=hr_user,
			employee=self.employee,
			leave_type=confidential_type,
			start_date=date(2026, 11, 4),
			end_date=date(2026, 11, 4),
			working_days=1,
		)
		RequestService.request_withdrawal(actor=self.employee_user, request_id=request.pk)

		with self.assertRaises(PermissionDenied):
			RequestService.decide_withdrawal(actor=self.manager_user, request_id=request.pk, approve=True)


class RequestApiTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(code='zsh-main', name='Zakaria Shimi')
		self.other_company = Company.objects.create(code='zsh-other', name='Other company')
		self.employee_user = User.objects.create_user(username='employee', password='test-password')
		self.other_user = User.objects.create_user(username='other', password='test-password')
		self.employee = EmployeeProfile.objects.create(user=self.employee_user, company=self.company, employee_number='1001')
		self.other_employee = EmployeeProfile.objects.create(user=self.other_user, company=self.other_company, employee_number='2001')
		self.leave_type = LeaveType.objects.create(company=self.company, code='annual', name='Annual leave')
		self.client = APIClient()

	def create_request(self, *, employee=None, leave_type=None, actor=None, date_day=10):
		employee = employee or self.employee
		return RequestService.create_request(
			actor=actor or employee.user,
			employee=employee,
			leave_type=leave_type or self.leave_type,
			start_date=date(2026, 11, date_day),
			end_date=date(2026, 11, date_day),
			working_days=1,
		)

	def test_employee_can_create_real_request_through_api(self):
		self.client.force_authenticate(self.employee_user)

		response = self.client.post('/api/v1/requests', {
			'leave_type_id': self.leave_type.pk,
			'start_date': '2026-11-10',
			'end_date': '2026-11-10',
			'working_days': '1',
		}, format='json')

		self.assertEqual(response.status_code, 201)
		self.assertEqual(LeaveRequest.objects.get().status, LeaveRequest.Status.ESCALATED)

	def test_employee_cannot_read_other_company_request_by_id(self):
		request = self.create_request(employee=self.other_employee, leave_type=LeaveType.objects.create(
			company=self.other_company, code='annual', name='Other annual leave',
		))
		self.client.force_authenticate(self.employee_user)

		response = self.client.get(f'/api/v1/requests/{request.pk}')

		self.assertEqual(response.status_code, 404)

	def test_confidential_category_is_redacted_from_owner_response(self):
		hr_user = User.objects.create_user(username='hr', password='test-password')
		RoleAssignment.objects.create(user=hr_user, company=self.company, role=RoleAssignment.Role.HR)
		confidential_type = LeaveType.objects.create(
			company=self.company,
			code='medical',
			name='Medical leave',
		employee_requestable=False,
			confidential=True,
		)
		request = self.create_request(leave_type=confidential_type, actor=hr_user, date_day=11)
		self.client.force_authenticate(self.employee_user)

		response = self.client.get(f'/api/v1/requests/{request.pk}')

		self.assertEqual(response.status_code, 200)
		self.assertIsNone(response.json()['leave_type_id'])
		self.assertEqual(response.json()['leave_type_name'], 'Absent')
		self.assertEqual(response.json()['reason'], '')

	def test_replacement_picker_is_limited_to_active_peers_and_excludes_self(self):
		peer_user = User.objects.create_user(username='peer', first_name='Peer', password='test-password')
		EmployeeProfile.objects.create(user=peer_user, company=self.company, employee_number='1003')
		inactive_user = User.objects.create_user(username='inactive', password='test-password', is_active=False)
		EmployeeProfile.objects.create(user=inactive_user, company=self.company, employee_number='1004')
		self.client.force_authenticate(self.employee_user)

		response = self.client.get('/api/v1/employees/replacements')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), [{'id': EmployeeProfile.objects.get(employee_number='1003').pk, 'name': 'Peer'}])

	def test_hr_does_not_receive_confidential_type_names_from_another_company(self):
		RoleAssignment.objects.create(user=self.employee_user, company=self.company, role=RoleAssignment.Role.HR)
		LeaveType.objects.create(
			company=self.other_company,
			code='other-medical',
			name='Other company medical category',
			employee_requestable=False,
			confidential=True,
		)
		self.client.force_authenticate(self.employee_user)

		response = self.client.get('/api/v1/leave-types')

		self.assertEqual(response.status_code, 200)
		self.assertFalse(any(item['code'] == 'other-medical' for item in response.json()))

	def test_invalid_request_filters_return_validation_errors(self):
		self.client.force_authenticate(self.employee_user)

		invalid_date = self.client.get('/api/v1/requests?from=not-a-date')
		invalid_status = self.client.get('/api/v1/requests?status=UNKNOWN')

		self.assertEqual(invalid_date.status_code, 400)
		self.assertEqual(invalid_status.status_code, 400)

	def test_missing_request_action_returns_not_found(self):
		self.client.force_authenticate(self.employee_user)

		response = self.client.post('/api/v1/requests/999999/approve', {}, format='json')

		self.assertEqual(response.status_code, 404)

	def test_inactive_leave_type_is_rejected(self):
		self.leave_type.is_active = False
		self.leave_type.save(update_fields=['is_active'])
		self.client.force_authenticate(self.employee_user)

		response = self.client.post('/api/v1/requests', {
			'leave_type_id': self.leave_type.pk,
			'start_date': '2026-11-10',
			'end_date': '2026-11-10',
			'working_days': '1',
		}, format='json')

		self.assertEqual(response.status_code, 400)

	def test_hr_cannot_probe_or_record_an_employee_from_another_company(self):
		RoleAssignment.objects.create(user=self.employee_user, company=self.company, role=RoleAssignment.Role.HR)
		self.client.force_authenticate(self.employee_user)
		payload = {
			'employee_id': self.other_employee.pk,
			'leave_type_id': self.leave_type.pk,
			'start_date': '2026-11-12',
			'end_date': '2026-11-12',
			'working_days': '1',
		}

		response = self.client.post('/api/v1/requests', payload, format='json')

		self.assertEqual(response.status_code, 404)

	def test_system_admin_without_hr_role_cannot_read_employee_requests(self):
		request = self.create_request()
		admin_user = User.objects.create_superuser(username='system-admin', password='test-password')
		self.client.force_authenticate(admin_user)

		self.assertEqual(self.client.get(f'/api/v1/requests/{request.pk}').status_code, 404)
		self.assertEqual(self.client.get('/api/v1/requests').json()['count'], 0)
		self.assertEqual(self.client.get('/api/v1/leave-types').json(), [])

	def test_manager_queue_is_scoped_and_rejection_requires_a_reason(self):
		manager_user = User.objects.create_user(username='manager', password='test-password')
		manager = EmployeeProfile.objects.create(user=manager_user, company=self.company, employee_number='1005')
		self.employee.manager = manager
		self.employee.save(update_fields=['manager'])
		request = RequestService.create_request(
			actor=self.employee_user,
			employee=self.employee,
			leave_type=self.leave_type,
			start_date=date(2026, 11, 12),
			end_date=date(2026, 11, 12),
			working_days=1,
		)
		self.client.force_authenticate(manager_user)

		queue = self.client.get('/api/v1/requests?status=PENDING&limit=100')
		self.assertEqual(queue.status_code, 200)
		self.assertEqual([item['id'] for item in queue.json()['results']], [request.pk])
		missing_reason = self.client.post(f'/api/v1/requests/{request.pk}/reject', {}, format='json')
		self.assertEqual(missing_reason.status_code, 400)

		rejected = self.client.post(f'/api/v1/requests/{request.pk}/reject', {'reason': 'Coverage conflict'}, format='json')
		request.refresh_from_db()
		self.assertEqual(rejected.status_code, 200)
		self.assertEqual(request.status, LeaveRequest.Status.REJECTED)
		self.assertTrue(request.events.filter(event_type='request_rejected', actor=manager_user).exists())


class BalanceServiceTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(code='zsh-main', name='Zakaria Shimi')
		self.employee_user = User.objects.create_user(username='employee', password='test-password')
		self.hr_user = User.objects.create_user(username='hr', password='test-password')
		self.employee = EmployeeProfile.objects.create(user=self.employee_user, company=self.company, employee_number='1001')
		RoleAssignment.objects.create(user=self.hr_user, company=self.company, role=RoleAssignment.Role.HR)
		self.annual = LeaveType.objects.create(company=self.company, code='annual', name='Annual leave', counts_against_balance=True)
		self.entitlement = LeaveEntitlement.objects.create(
			employee=self.employee,
			leave_type=self.annual,
			year=2026,
			base_days=Decimal('20'),
			carry_over_days=Decimal('2'),
		)

	def create_request(self, status, day, working_days):
		return LeaveRequest.objects.create(
			company=self.company,
			employee=self.employee,
			leave_type=self.annual,
			start_date=date(2026, 11, day),
			end_date=date(2026, 11, day),
			working_days=working_days,
			status=status,
			created_by=self.employee_user,
		)

	def test_calculates_entitlement_used_pending_remaining_and_available(self):
		self.create_request(LeaveRequest.Status.APPROVED, 10, '3')
		self.create_request(LeaveRequest.Status.PENDING, 11, '2')
		self.create_request(LeaveRequest.Status.REJECTED, 12, '8')

		balance = BalanceService.for_employee(employee=self.employee, year=2026)[0]

		self.assertEqual(balance['entitlement'], Decimal('22'))
		self.assertEqual(balance['used'], Decimal('3'))
		self.assertEqual(balance['pending'], Decimal('2'))
		self.assertEqual(balance['remaining'], Decimal('19'))
		self.assertEqual(balance['available'], Decimal('17'))

	def test_missing_entitlement_does_not_create_a_synthetic_balance(self):
		LeaveEntitlement.objects.all().delete()

		self.assertEqual(BalanceService.for_employee(employee=self.employee, year=2026), [])

	def test_adjustment_delta_and_absolute_set_are_distinct_and_audited(self):
		BalanceService.adjust(actor=self.hr_user, entitlement_id=self.entitlement.pk, adjustment_delta='3', reason='Approved correction')
		BalanceService.adjust(actor=self.hr_user, entitlement_id=self.entitlement.pk, adjustment_delta='-3', reason='Correction reversed')
		self.entitlement.refresh_from_db()
		self.assertEqual(self.entitlement.manual_adjustment, Decimal('0'))
		self.assertEqual(EntitlementEvent.objects.filter(entitlement=self.entitlement, field='manual_adjustment').count(), 2)

		BalanceService.adjust(actor=self.hr_user, entitlement_id=self.entitlement.pk, adjustment_set='5', reason='Set approved adjustment')
		self.entitlement.refresh_from_db()
		self.assertEqual(self.entitlement.manual_adjustment, Decimal('5'))

	def test_adjustment_requires_reason_and_hr_role(self):
		with self.assertRaises(ValidationError):
			BalanceService.adjust(actor=self.hr_user, entitlement_id=self.entitlement.pk, adjustment_delta='1', reason=' ')
		with self.assertRaises(PermissionDenied):
			BalanceService.adjust(actor=self.employee_user, entitlement_id=self.entitlement.pk, adjustment_delta='1', reason='Not HR')

	def test_rejects_mixing_delta_and_absolute_adjustment(self):
		with self.assertRaises(ValidationError):
			BalanceService.adjust(
				actor=self.hr_user,
				entitlement_id=self.entitlement.pk,
				adjustment_delta='1',
				adjustment_set='2',
				reason='Ambiguous operation',
			)


class BalanceApiTests(TestCase):
	def setUp(self):
		self.company = Company.objects.create(code='zsh-main', name='Zakaria Shimi')
		self.other_company = Company.objects.create(code='zsh-other', name='Other company')
		self.employee_user = User.objects.create_user(username='employee', password='test-password')
		self.manager_user = User.objects.create_user(username='manager', password='test-password')
		self.hr_user = User.objects.create_user(username='hr', password='test-password')
		self.outsider_user = User.objects.create_user(username='outsider', password='test-password')
		self.employee = EmployeeProfile.objects.create(user=self.employee_user, company=self.company, employee_number='1001')
		self.manager = EmployeeProfile.objects.create(user=self.manager_user, company=self.company, employee_number='1002')
		self.employee.manager = self.manager
		self.employee.save(update_fields=['manager'])
		self.other_employee = EmployeeProfile.objects.create(user=self.outsider_user, company=self.other_company, employee_number='2001')
		self.leave_type = LeaveType.objects.create(company=self.company, code='annual', name='Annual leave', counts_against_balance=True)
		self.entitlement = LeaveEntitlement.objects.create(employee=self.employee, leave_type=self.leave_type, year=2026, base_days=20)
		RoleAssignment.objects.create(user=self.hr_user, company=self.company, role=RoleAssignment.Role.HR)
		self.client = APIClient()

	def test_employee_and_manager_can_read_only_their_scoped_balance(self):
		self.client.force_authenticate(self.employee_user)
		own = self.client.get('/api/v1/balances/me?year=2026')
		self.assertEqual(own.status_code, 200)
		self.assertEqual(str(own.json()[0]['entitlement']), '20.0')
		self.assertEqual(self.client.get(f'/api/v1/employees/{self.other_employee.pk}/balances?year=2026').status_code, 403)

		self.client.force_authenticate(self.manager_user)
		self.assertEqual(self.client.get(f'/api/v1/employees/{self.employee.pk}/balances?year=2026').status_code, 200)
		self.assertEqual(self.client.get(f'/api/v1/employees/{self.other_employee.pk}/balances?year=2026').status_code, 403)

	def test_hr_adjustment_api_requires_reason_and_persists_event(self):
		self.client.force_authenticate(self.hr_user)

		response = self.client.patch(f'/api/v1/entitlements/{self.entitlement.pk}', {
			'adjustment_delta': '2',
			'reason': 'Approved adjustment',
		}, format='json')

		self.assertEqual(response.status_code, 200)
		self.entitlement.refresh_from_db()
		self.assertEqual(self.entitlement.manual_adjustment, Decimal('2'))
		self.assertEqual(self.entitlement.events.count(), 1)

	def test_non_hr_cannot_change_entitlement(self):
		self.client.force_authenticate(self.employee_user)

		response = self.client.patch(f'/api/v1/entitlements/{self.entitlement.pk}', {
			'adjustment_delta': '2',
			'reason': 'Unauthorized adjustment',
		}, format='json')

		self.assertEqual(response.status_code, 403)
		self.entitlement.refresh_from_db()
		self.assertEqual(self.entitlement.manual_adjustment, Decimal('0'))

	def test_hr_can_create_initial_entitlement_with_audited_values(self):
		self.client.force_authenticate(self.hr_user)
		payload = {
			'employee_id': self.employee.pk,
			'leave_type_id': self.leave_type.pk,
			'year': 2027,
			'base_days': '22',
			'carry_over_days': '3',
			'reason': 'Approved annual quota',
		}

		response = self.client.post('/api/v1/entitlements', payload, format='json')

		self.assertEqual(response.status_code, 201)
		created = LeaveEntitlement.objects.get(employee=self.employee, year=2027)
		self.assertEqual(created.events.count(), 2)
		self.assertEqual(self.client.post('/api/v1/entitlements', payload, format='json').status_code, 400)

	def test_non_hr_cannot_create_entitlement(self):
		self.client.force_authenticate(self.employee_user)

		response = self.client.post('/api/v1/entitlements', {
			'employee_id': self.employee.pk,
			'leave_type_id': self.leave_type.pk,
			'year': 2027,
			'base_days': '22',
			'reason': 'Unauthorized',
		}, format='json')

		self.assertEqual(response.status_code, 403)
		self.assertFalse(LeaveEntitlement.objects.filter(employee=self.employee, year=2027).exists())

	def test_system_admin_without_hr_role_cannot_read_or_change_balance(self):
		admin_user = User.objects.create_superuser(username='system-admin', password='test-password')
		self.client.force_authenticate(admin_user)

		self.assertEqual(self.client.get(f'/api/v1/employees/{self.employee.pk}/balances?year=2026').status_code, 403)
		response = self.client.patch(f'/api/v1/entitlements/{self.entitlement.pk}', {
			'adjustment_delta': '2',
			'reason': 'Unauthorized by system admin',
		}, format='json')

		self.assertEqual(response.status_code, 403)