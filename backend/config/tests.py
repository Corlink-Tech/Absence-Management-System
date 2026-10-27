# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.test import SimpleTestCase
from django.test import TestCase
from rest_framework.test import APIClient
import yaml

from identity.models import User
from identity.models import Company, EmployeeProfile


class HealthCheckTests(SimpleTestCase):
	def test_live_endpoint_returns_ok_without_authentication(self):
		response = APIClient().get('/api/v1/health/live')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json(), {'status': 'ok'})


class OpenApiSchemaTests(SimpleTestCase):
	def test_schema_endpoint_returns_openapi_document(self):
		response = APIClient().get('/api/v1/schema')

		self.assertEqual(response.status_code, 200)
		schema = yaml.safe_load(response.content)
		self.assertEqual(schema['info']['version'], '0.1.0')
		self.assertIn('/api/v1/requests', schema['paths'])


class SessionAuthenticationTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='employee', password='secure-test-password')
		self.client = APIClient(enforce_csrf_checks=True)
		csrf_response = self.client.get('/api/v1/auth/csrf')
		self.csrf_token = csrf_response.json()['csrf_token']

	def test_login_requires_csrf_and_creates_authenticated_session(self):
		without_csrf = self.client.post('/api/v1/auth/login', {
			'username': 'employee',
			'password': 'secure-test-password',
		}, format='json')
		self.assertEqual(without_csrf.status_code, 403)

		response = self.client.post('/api/v1/auth/login', {
			'username': 'employee',
			'password': 'secure-test-password',
		}, format='json', HTTP_X_CSRFTOKEN=self.csrf_token)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.json()['authenticated'])
		self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 200)

	def test_invalid_credentials_do_not_create_session(self):
		response = self.client.post('/api/v1/auth/login', {
			'username': 'employee',
			'password': 'incorrect-password',
		}, format='json', HTTP_X_CSRFTOKEN=self.csrf_token)
		self.assertEqual(response.status_code, 401)
		self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 403)

	def test_session_marks_manager_from_active_direct_reports(self):
		company = Company.objects.create(code='session-test', name='Session test')
		manager_profile = EmployeeProfile.objects.create(user=self.user, company=company, employee_number='1001')
		report_user = User.objects.create_user(username='report', password='test-password')
		EmployeeProfile.objects.create(user=report_user, company=company, employee_number='1002', manager=manager_profile)
		self.client.force_authenticate(self.user)

		response = self.client.get('/api/v1/auth/me')

		self.assertTrue(response.json()['is_manager'])