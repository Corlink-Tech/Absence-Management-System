<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->
# مدل داده پیشنهادی

این مدل مفهومی است و جایگزین migration نهایی نیست. شناسه‌ها UUID یا bigint انتخاب می‌شوند؛ تصمیم فیزیکی هنگام پیاده‌سازی ثبت شود. همه زمان‌ها UTC و timezone-aware؛ تاریخ‌های مرخصی date بدون ساعت. حذف کارمند نباید سابقهٔ لازم را پاک کند.

| موجودیت | فیلدهای کلیدی و روابط | محرمانگی |
|---|---|---|
| Company | id، code یکتا، name، active، timezone | داخلی |
| Department | company_id، parent_id اختیاری، code/name، active | داخلی |
| Position | company_id اختیاری، code/name | داخلی |
| User | username یکتا، email، password_hash، active، last_login | محرمانه |
| Role / UserRole | code یکتا؛ user_id، role_id، company scope اختیاری | امنیتی |
| EmployeeProfile | user_id، employee_no یکتا، company_id، department_id، position_id، manager_id، start/end، status، locale/timezone | محرمانه |
| EmploymentContract | employee_id، valid_from/to، percentage، working_week، contract type | HR |
| LeaveType | code یکتا، labels، enabled، requires_approval، requestable، counts_balance، requires_note، requires_replacement، confidential، calendar policy | HR |
| LeavePolicy | company/group/type، effective dates، entitlement/carry rules، deadlines، overlap policy | HR/امنیتی |
| LeaveRequest | employee_id، manager_id snapshot، company_id، type_id، dates، approved_working_days، status، reason، replacement_id، decision metadata، supersedes_id | حساس |
| RequestComment | request_id، author_id، body، created_at | حساس؛ مجوز هر درخواست |
| RequestEvent | request_id، actor_id/snapshot، event_type، sanitized before/after، reason reference، timestamp | حساس، append-only |
| RequestAmendment | original_request_id، replacement_request_id، proposed values، state | حساس |
| LeaveAttachment | request_id، uploader_id، storage_key تصادفی، detected_mime، size، hash، timestamps | بسیار حساس |
| Entitlement | employee_id، type_id، year، base، carry، unique(employee,type,year) | HR/کارمند مجاز |
| EntitlementEvent | entitlement_id، field، old/new/delta، actor، reason، import/run id، timestamp | HR، append-only |
| PublicHoliday | company/region، date، label، source، effective period، created/updated by | عمومی درون‌سازمانی |
| HolidayEvent | holiday_id، actor، before/after، reason، timestamp | مدیریتی |
| Notification | recipient_id، event_id، read_at، safe payload | حساس و حداقلی |
| EmailDeliveryLog | event_id، recipient، status، retry metadata، timestamp | عملیاتی؛ بدون متن حساس |
| AuditEvent | actor، action، entity type/id، company scope، outcome، request id، metadata پالایش‌شده، timestamp | بسیار حساس، append-only |
| ImportBatch / ImportRow | actor، file hash، type/year، dry-run، result/count/errors | HR/حساس |
| JobExecution | job key، idempotency key، started/finished، result، error code، counters | عملیاتی |
| SystemSetting | key، JSON validated value، scope، updated_by/time | مدیریتی |

## قیود مهم

- یکتایی employee number در محدودهٔ سیاست سازمان (سراسری یا شرکت) باید پیش از migration تصویب شود.
- کلیدهای خارجی و check constraint برای بازه تاریخ، روز کاری مثبت، درصد معتبر، وضعیت و بازه قرارداد تعریف شوند.
- درخواست‌ها به شرکت زمان ثبت snapshot می‌شوند تا انتقال کارمند بین شرکت‌ها تاریخ مجوز را از بین نبرد.
- قید idempotency یکتا برای Jobهای دوره‌ای و انتقال مانده لازم است.
- جلوگیری از هم‌پوشانی هم‌زمانی در تراکنش با قفل ردیف کارمند و constraint/قفل سازگار با PostgreSQL انجام شود.
- مانده ترجیحاً از entitlement و درخواست‌های مؤثر/دفترکل محاسبه می‌شود؛ cache فقط با راهبرد invalidation روشن مجاز است.
- درخواست عبوری از سال تا تصویب سیاست تخصیص روزها نباید با قاعده پنهان به سال شروع منتسب شود.
- پیوست هیچ URL عمومی یا path کاربرپذیر ندارد؛ همه دانلودها از authorization جاری عبور می‌کنند.
- Audit شامل رمز، توکن، کلید، متن پزشکی یا متن آزاد کامل نمی‌شود؛ before/after برای داده‌های حساس پالایش می‌شود.