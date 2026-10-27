# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.urls import path

from leave.views import (
	ApproveRequestView,
	CancelRequestView,
	DecideWithdrawalView,
	EmployeeBalanceView,
	EntitlementCreateView,
	EntitlementDetailView,
	LeaveTypeListView,
	MyBalanceView,
	RejectRequestView,
	RejectWithdrawalView,
	RequestDetailView,
	RequestListCreateView,
	RequestWithdrawalView,
	ReplacementChoicesView,
)

urlpatterns = [
	path('employees/replacements', ReplacementChoicesView.as_view(), name='replacement-choices'),
	path('leave-types', LeaveTypeListView.as_view(), name='leave-types'),
	path('balances/me', MyBalanceView.as_view(), name='balance-me'),
	path('employees/<int:employee_id>/balances', EmployeeBalanceView.as_view(), name='employee-balances'),
	path('entitlements', EntitlementCreateView.as_view(), name='entitlement-create'),
	path('entitlements/<int:entitlement_id>', EntitlementDetailView.as_view(), name='entitlement-detail'),
	path('requests', RequestListCreateView.as_view(), name='request-list-create'),
	path('requests/<int:request_id>', RequestDetailView.as_view(), name='request-detail'),
	path('requests/<int:request_id>/approve', ApproveRequestView.as_view(), name='request-approve'),
	path('requests/<int:request_id>/reject', RejectRequestView.as_view(), name='request-reject'),
	path('requests/<int:request_id>/cancel', CancelRequestView.as_view(), name='request-cancel'),
	path('requests/<int:request_id>/withdraw', RequestWithdrawalView.as_view(), name='request-withdraw'),
	path('requests/<int:request_id>/withdraw/approve', DecideWithdrawalView.as_view(), name='withdrawal-approve'),
	path('requests/<int:request_id>/withdraw/reject', RejectWithdrawalView.as_view(), name='withdrawal-reject'),
]