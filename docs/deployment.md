<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->
# نصب، استقرار و بازیابی

این سند هدف استقرار را تعریف می‌کند. Compose فعلی فقط توسعه است و از Django `runserver` و کلیدهای توسعه استفاده می‌کند؛ production نیست.

## پیش‌نیازهای محیط

- Docker Engine و Docker Compose سازگار برای توسعه/استقرار اولیه.
- PostgreSQL با volume پایدار و دسترسی شبکه محدود به backend/worker.
- Reverse proxy با TLS معتبر در محیط عملیاتی.
- فضای خصوصی پایدار برای پیوست و backup؛ SMTP سازمانی اختیاری.
- دامنه و گواهی، DNS، timezone سازمان، حساب مدیر اولیه و policyهای مصوب HR.
- پورت PostgreSQL در Compose توسعه فقط روی `127.0.0.1:5432` منتشر می‌شود؛ production به شبکه خصوصی و firewall قواعد خودش نیاز دارد.
- منابع CPU/RAM/storage پس از آزمون بار بر اساس headcount و retention تعیین شوند؛ عدد زیرساختی از اسناد قابل استنتاج نیست.

## پیکربندی

تنظیمات از Environment Variables/secret store خوانده شوند: secretهای Django، DB credentials، allowed hosts/origins، TLS proxy trust، timezone، locale، محل فایل خصوصی، محدودیت upload، SMTP و سطح log. `.env.example` فقط placeholder دارد؛ secret واقعی وارد Git نمی‌شود. حالت production باید debug خاموش و کوکی secure باشد.

## چرخه نصب پیشنهادی

1. دریافت نسخهٔ تأییدشده و بررسی checksum/signature طبق سیاست سازمان.
2. ساخت secretها، DB role حداقل‌دسترسی، volume خصوصی و TLS.
3. اجرای migration و ایجاد نخستین مدیر از فرمان امن/فرایند one-time.
4. ورود شرکت‌ها، واحدها، کاربران، مدیرها، انواع مرخصی، تعطیلات و سهمیه‌های تأییدشده.
5. اجرای dry-run واردسازی و تطبیق تعداد و نمونه؛ سپس commit اتمیک.
6. آزمون حساب کارمند، مدیر، HR و مدیر سامانه در محیط staging.
7. فعال‌کردن Worker و پایش خطا؛ SMTP فقط پس از آزمون دریافت.
8. انتقال به بهره‌برداری با plan rollback و آموزش نقش‌ها.

## Backup و Restore

- پشتیبان سازگار از PostgreSQL و object/file storage لازم است؛ backup DB به‌تنهایی پیوست‌ها را بازیابی نمی‌کند.
- رمزگذاری در مبدأ/مقصد، دسترسی محدود، نگهداری نسخه‌ای و جداسازی از میزبان اصلی لازم است.
- دوره نگهداری و مقصد جغرافیایی تا تصویب سیاست امنیت/حریم خصوصی تعیین نشده است.
- بازیابی در شبکه جدا: DB و فایل‌ها را با یک نقطه زمانی هماهنگ restore، نسخه برنامه و migration را ثبت، health check و نمونه درخواست/پیوست/مانده را تطبیق دهید.
- هر restore drill باید تاریخ، نسخه، مدت، اختلاف، نتیجه و اقدام اصلاحی ثبت کند. تا انجام restore drill، بازیابی تأییدشده تلقی نمی‌شود.

## عملیات روزانه

health live/ready، آخرین اجرای Job، خطای SMTP، فضای storage، pool اتصال DB، خطاهای 5xx، تلاش ورود ناموفق و وضعیت backup پایش شود. log ساختاریافته request id داشته باشد و داده حساس را redaction کند. restart نباید Job را دو بار اعمال کند.