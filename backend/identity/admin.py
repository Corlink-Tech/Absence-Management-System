# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from identity.models import Company, Department, EmployeeProfile, EmploymentContract, Position, RoleAssignment, User

admin.site.site_header = 'مدیریت سامانه مرخصی زکریا شیمی'
admin.site.site_title = 'مدیریت زکریا شیمی'
admin.site.index_title = 'مدیریت حساب‌ها و ساختار سازمانی'


@admin.register(User)
class EmployeeUserAdmin(UserAdmin):
	list_display = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff']
	search_fields = ['username', 'first_name', 'last_name', 'email']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
	list_display = ['code', 'name', 'timezone', 'is_active']
	search_fields = ['code', 'name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
	list_display = ['name', 'code', 'company', 'parent', 'is_active']
	list_filter = ['company', 'is_active']
	search_fields = ['name', 'code']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
	list_display = ['name', 'code', 'company']
	list_filter = ['company']
	search_fields = ['name', 'code']


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
	list_display = ['employee_number', 'user', 'company', 'department', 'manager', 'is_active']
	list_filter = ['company', 'department', 'is_active']
	search_fields = ['employee_number', 'user__username', 'user__first_name', 'user__last_name']


@admin.register(RoleAssignment)
class RoleAssignmentAdmin(admin.ModelAdmin):
	list_display = ['user', 'role', 'company', 'assigned_by', 'created_at']
	list_filter = ['company', 'role']
	search_fields = ['user__username', 'company__name']
	readonly_fields = ['created_at']


@admin.register(EmploymentContract)
class EmploymentContractAdmin(admin.ModelAdmin):
	list_display = ['employee', 'valid_from', 'valid_until', 'percentage']
	list_filter = ['employee__company']
	search_fields = ['employee__employee_number', 'employee__user__username']
	readonly_fields = ['created_at']