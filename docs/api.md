<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->
# قرارداد API اولیه

این سند پیش‌نویس دامنه است؛ schema زنده در `/api/v1/schema` و Swagger در `/api/docs` فقط endpointهای پیاده‌شده را توصیف می‌کنند. API زیر `/api/v1` و JSON UTF-8 است. فهرست درخواست‌ها pagination محدود دارد.

| مسیر | متد | دسترسی اولیه | خلاصه |
|---|---|---|---|
| `/auth/login` | POST | عمومی + rate limit | ورود حساب داخلی |
| `/auth/logout` | POST | نشست جاری + CSRF | خروج و لغو نشست |
| `/auth/me` | GET | احراز هویت | پروفایل، نقش‌ها و scope مجاز |
| `/users` | GET/POST | مدیر سامانه/HR محدود | جست‌وجو و ایجاد/مدیریت حساب طبق scope |
| `/employees` | GET/POST | HR و مدیر مجاز | کارکنان، جست‌وجو/فیلتر شرکت و واحد |
| `/employees/{id}` | GET/PATCH | خود/مدیر گزارش/HR scope | پروفایل با فیلدهای مجاز |
| `/organization/companies` | GET/POST/PATCH | مدیر سامانه؛ read HR | شرکت‌ها |
| `/organization/departments` | CRUD | مدیر سامانه؛ read HR | ساختار واحدها |
| `/employees/{id}/contracts` | GET/PUT | HR scope؛ read محدود | دوره‌های قرارداد و الگوی کار |
| `/leave-types` | GET | احراز هویت؛ خروجی پالایش‌شده | انواع مجاز کاربر |
| `/leave-types` | POST | HR/admin | تعریف نوع و policy |
| `/requests` | GET | خود/گزارش مستقیم/HR scope | فهرست درخواست با فیلتر وضعیت/تاریخ/نوع |
| `/requests` | POST | کارمند یا HR نیابتی | ایجاد، اعتبارسنجی و ارسال برای تصمیم |
| `/requests/{id}` | GET/PATCH | مالک/تصمیم‌گیر/HR scope | جزئیات؛ PATCH فقط قواعد وضعیت مجاز |
| `/requests/{id}/approve` | POST | مدیر مجاز یا HR | تصمیم تأیید |
| `/requests/{id}/reject` | POST | مدیر مجاز یا HR | رد با دلیل اجباری |
| `/requests/{id}/cancel` | POST | مالک طبق وضعیت، تصمیم‌گیر یا HR | لغو/درخواست لغو تأییدشده |
| `/requests/{id}/comments` | GET/POST | شرکت‌کننده مجاز | بحث با پالایش محرمانگی |
| `/requests/{id}/attachments` | GET/POST | HR یا صاحب مجاز | فهرست/بارگذاری؛ multipart محدود |
| `/attachments/{id}` | GET/DELETE | HR/صاحب مجاز یا uploader | دانلود/حذف کنترل‌شده |
| `/balances/me` | GET | خود | سهمیه و ledger فرد |
| `/employees/{id}/balances` | GET | مدیر گزارش یا HR scope | مانده مجاز |
| `/entitlements` | POST | HR scope | ساخت سهمیه اولیه با تاریخچه |
| `/entitlements/{id}` | PATCH | HR scope | اصلاح سهمیه با دلیل و تاریخچه |
| `/entitlements/imports` | POST | HR scope | dry-run/import CSV/XLSX اتمیک |
| `/calendar` | GET | scope شخصی/تیم/شرکت | بازه شمسی ورودی یا ISO؛ خروجی پالایش‌شده |
| `/coverage` | GET | تیم/HR scope | شمارش overlap و هشدار خنثی |
| `/holidays` | GET/POST | همه/read؛ HR write | تعطیلات منطقه/شرکت |
| `/reports/balances` | GET | HR scope/مدیر محدود | گزارش مانده |
| `/reports/absences` | GET | HR scope | غیبت‌ها و وضعیت‌ها |
| `/reports/trends` | GET | HR scope/مدیر ارشد aggregate | شاخص‌های مصوب |
| `/exports/requests` | GET | HR scope | CSV/XLSX با فیلتر مجاز |
| `/exports/balances` | GET | HR scope | CSV/XLSX با کنترل formula injection |
| `/notifications` | GET/PATCH | خود | فهرست/خوانده‌شدن اعلان |
| `/admin/settings` | GET/PATCH | مدیر سامانه/HR برای policyهای مجاز | تنظیمات و ثبت audit |
| `/audit-events` | GET | ممیز/HR scope محدود | جست‌وجوی مجاز، بدون secrets/متن حساس |
| `/health/live` | GET | عمومی کم‌اطلاعات | زنده بودن فرایند |
| `/health/ready` | GET | هنوز پیاده نشده | اتصال وابستگی‌های لازم بدون افشای جزئیات |
| `/api/v1/schema` | GET | عمومی، فقط قرارداد | OpenAPI مسیرهای پیاده‌شده |
| `/api/docs` | GET | عمومی، فقط قرارداد | Swagger UI |

## قراردادهای مشترک

- احراز هویت نشست cookie امن same-origin؛ writeها CSRF دارند. bearer token/API integration نیازمند تصمیم جداگانه است.
- فیلتر `company_id` هرگز scope مجوز را تعیین نمی‌کند؛ Backend scope caller را اعمال می‌کند و تقاطع خالی پاسخ خالی/403 سیاست‌گذاری‌شده می‌دهد.
- pagination با `limit` سقف‌دار و cursor/offset؛ مرتب‌سازی فقط allowlist.
- خطاها قالب ثابت شامل `code`, `message` فارسی، `field_errors`, `request_id`; stack trace به کاربر نشت نمی‌کند.
- write حساس idempotency key/نسخه مورد انتظار دارد؛ تضاد وضعیت 409 و validation 422.
- هر endpoint در OpenAPI نهایی باید مالکیت، نقش، scope شرکتی، فیلدهای حساس، ورودی، پاسخ، pagination و خطاها را تعریف کند.
- مسیرهای users/organization/contracts/comments/attachments/holidays/calendar/reports/exports/notifications/audit و health-ready در جدول دامنه برنامه‌اند، اما هنوز route اجرایی ندارند.