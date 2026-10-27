<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->
# راه‌اندازی محیط توسعه

محصول مستقل است و به Nextcloud نیاز ندارد. راه‌اندازی Compose فعلی فقط توسعه است؛ از Django `runserver`، کلیدهای محلی و بدون TLS استفاده می‌کند و برای production مناسب نیست.

## Docker Compose

پیش‌نیاز: Docker Engine و Docker Compose.

1. در صورت نیاز `.env.example` را به `.env` کپی کنید و secretهای تصادفی مخصوص محیط خود بگذارید.
2. اجرا: `docker compose up --build`.
3. در ترمینال دیگر مدیر اولیه بسازید: `docker compose exec backend python manage.py createsuperuser`.
4. شرکت پایه را ایجاد کنید: `docker compose exec backend python manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی"`.
5. در `/admin/` شرکت، کاربران، پروفایل پرسنلی، نقش HR/مدیر، نوع مرخصی و سهمیه را با دادهٔ مصوب تنظیم کنید.
6. رابط در `http://localhost:5173` و API در `http://localhost:8000/api/v1/health/live` در دسترس است.
7. حسابی که مدیر مستقیم فعال دارد، صفحهٔ «بررسی درخواست‌ها» را می‌بیند؛ تصمیم مدیر در محدودهٔ گزارش مستقیم است و رد، دلیل اجباری دارد.
8. قرارداد اولیهٔ API در `http://localhost:8000/api/docs` و schema در `http://localhost:8000/api/v1/schema` ارائه می‌شود.

هیچ حساب، نوع مرخصی، تعطیلات یا سهمیه ساختگی seed نمی‌شود. ابتدا مقادیر واقعی را با مالک HR تأیید کنید. دادهٔ محلی PostgreSQL در volume `postgres_data` می‌ماند.

## محلی بدون Docker

```bash
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py migrate
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py createsuperuser
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی"
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
npm ci
npm run dev
```

## آزمون و build

```bash
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py check
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py test config identity leave
npm run build
```

Production نیازمند secret management، HTTPS/reverse proxy، worker واقعی، policyهای HR، backup و restore آزموده‌شده است؛ جزئیات اولیه در [راهنمای استقرار](deployment.md) آمده است.