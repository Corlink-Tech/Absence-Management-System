<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->

# سامانه مدیریت مرخصی و غیبت هلدینگ زکریا شیمی

سامانهٔ مستقل فارسی برای ثبت و بررسی درخواست مرخصی، مدیریت سهمیه و نگهداری سابقهٔ تصمیم‌ها. محصول با Django/DRF، PostgreSQL و React/TypeScript ساخته می‌شود و برای اجرا به Nextcloud وابسته نیست.

> **وضعیت فعلی: نسخهٔ توسعهٔ اولیه، نه production.** هستهٔ حساب/سازمان، ورود، درخواست و تأیید مدیر، سهمیه، API و رابط فارسی پیاده شده‌اند. workerهای یادآوری و ارجاع، پنل کامل HR، گزارش‌ها، import/export، پیوست، تقویم کامل، backup/restore عملیاتی و سخت‌سازی استقرار هنوز تکمیل نشده‌اند.

## اجرای سریع

پیش‌نیاز: Git، Docker Engine و Docker Compose v2.

```bash
git clone <REPOSITORY_URL> zsh-leave
cd zsh-leave
cp .env.example .env
```

در Windows PowerShell به‌جای `cp` اجرا کنید:

```powershell
Copy-Item .env.example .env
```

مقدارهای تصادفی مخصوص محیط خود را در `.env` برای `DJANGO_SECRET_KEY` و `DB_PASSWORD` قرار دهید؛ نمونهٔ `.env.example` را برای production استفاده نکنید. سپس:

```bash
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی" --timezone Asia/Tehran
```

`createsuperuser` از شما username و password می‌گیرد. **حساب یا گذرواژهٔ پیش‌فرضی در پروژه وجود ندارد.** نام کاربری و گذرواژه‌ای که روی این لپ‌تاپ می‌سازید، فقط به دیتابیس همان محیط تعلق دارد. برای ساخت کاربران و نقش HR/مدیر وارد پنل Admin شوید؛ superuser به‌طور خودکار نقش HR نمی‌گیرد.

آدرس‌های محلی:

- رابط فارسی: http://localhost:5173
- پنل مدیریت: http://localhost:8000/admin/
- سلامت API: http://localhost:8000/api/v1/health/live
- مستندات API: http://localhost:8000/api/docs

دستورهای کامل Windows/macOS/Linux، ایجاد کاربر و نقش، ورود اولیه، عیب‌یابی و روش اجرای بدون Docker در [dev-guide.md](dev-guide.md) آمده‌اند.

## وضعیت قابلیت‌ها

در حال حاضر کاربر فعال با EmployeeProfile می‌تواند درخواست ثبت کند و آن را از فهرست خود پیگیری کند. مدیر با گزارش مستقیم فعال، صف درخواست‌های مجاز را می‌بیند و می‌تواند تأیید کند یا با دلیل اجباری رد کند. HR با role شرکتی می‌تواند غیبت ثبت و سهمیه ایجاد/اصلاح کند؛ تغییرهای سهمیه و تصمیم‌های درخواست سابقه دارند. رابط راست‌چین، تاریخ‌گیر شمسی و فونت فارسی دارد.

این قابلیت‌ها هنوز در این نسخه موجود نیستند یا برای بهره‌برداری کامل نشده‌اند: ساختار چندشرکتی کامل و پنل HR مستقل، وظایف زمان‌بندی‌شده، تقویم سازمانی، holiday management، پیوست امن، import/export، گزارش‌های HR، اعلان ایمیل، اتصال LDAP/AD و آزمون بازیابی پشتیبان. نیم‌روز و مرخصی ساعتی هم عمداً خارج از نسخهٔ پایه‌اند. وضعیت تفصیلی در [ماتریس قابلیت‌ها](docs/feature-matrix.md) نگهداری می‌شود.

## آزمون و توسعه

```bash
# بررسی وضعیت کد Django و migrationها
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py check
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py makemigrations --check --dry-run
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py test config identity leave

# ساخت رابط
npm ci
npm run build
```

برای اجرای سرورهای محلی و راه‌اندازی PostgreSQL به [راهنمای توسعه](dev-guide.md) مراجعه کنید. Compose فعلی از Django `runserver` و کلیدهای development استفاده می‌کند؛ برای انتشار سازمانی مناسب نیست. پیش از استفاده از دادهٔ واقعی، TLS/reverse proxy، secret management، worker، پایش، policyهای HR و backup/restore آزموده‌شده باید فراهم شوند.

## اسناد پروژه

- [راهنمای اجرای لپ‌تاپ و ورود](dev-guide.md)
- [نیازمندی‌ها](docs/requirements.md)
- [معماری](docs/architecture.md)
- [مدل داده](docs/data-model.md)
- [ماتریس نقش‌ها و مجوزها](docs/permissions-matrix.md)
- [گردش‌کار و ماشین وضعیت](docs/workflows.md)
- [مدل امنیت](docs/security.md)
- [قرارداد API](docs/api.md)
- [برنامهٔ آزمون](docs/testing.md)
- [استقرار و بازیابی](docs/deployment.md)
- [تصمیم‌ها و فرضیات](docs/decisions.md)

`SPECIFICATION.md`، `CHANGELOG.md` و فایل‌های تحلیل پیوست، اسناد تاریخی محصول Nextcloud هستند و مرجع رفتار سامانهٔ مستقل محسوب نمی‌شوند؛ نیازمندی‌های فعلی و تصمیم‌های باز در `docs/` ثبت شده‌اند.
