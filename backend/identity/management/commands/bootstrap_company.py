# SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from identity.models import Company


class Command(BaseCommand):
	help = 'Create or verify the initial holding company without applying leave-policy defaults.'

	def add_arguments(self, parser):
		parser.add_argument('--code', required=True)
		parser.add_argument('--name', required=True)
		parser.add_argument('--timezone', default='Asia/Tehran')

	def handle(self, *args, **options):
		try:
			company, created = Company.objects.get_or_create(
				code=options['code'],
				defaults={'name': options['name'], 'timezone': options['timezone']},
			)
		except IntegrityError as error:
			raise CommandError('Company setup conflicted with another operation.') from error
		if not created and (company.name != options['name'] or company.timezone != options['timezone']):
			raise CommandError('Company code already exists with different values; review it in the admin site.')
		self.stdout.write(self.style.SUCCESS(f'{"Created" if created else "Verified"} company {company.code}.'))