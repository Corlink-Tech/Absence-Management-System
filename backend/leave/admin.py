# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.contrib import admin

from leave.models import LeaveType


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
	list_display = ['name', 'code', 'company', 'is_active', 'requires_approval', 'employee_requestable', 'confidential']
	list_filter = ['company', 'is_active', 'counts_against_balance', 'confidential']
	search_fields = ['name', 'code']
