# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.apps import AppConfig


class LeaveConfig(AppConfig):
	default_auto_field = 'django.db.models.BigAutoField'
	name = 'leave'