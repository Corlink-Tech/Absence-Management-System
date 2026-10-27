<!--
  - SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->
# راهنمای توسعه و اجرای پروژه روی لپ‌تاپ دیگر

این راهنما برای اجرای **نسخهٔ توسعه** سامانهٔ مستقل مدیریت مرخصی هلدینگ زکریا شیمی نوشته شده است. برنامه برای اجرا به Nextcloud احتیاج ندارد. Compose فعلی از Django `runserver` و Vite development server استفاده می‌کند و **برای production، اینترنت عمومی یا نگهداری اطلاعات واقعی کارکنان مناسب نیست**.

## ۱. پیش‌نیازها

روش پیشنهادی Docker است. روی لپ‌تاپ مقصد نصب کنید:

- Git؛ برای دریافت مخزن.
- Docker Desktop روی Windows/macOS، یا Docker Engine و Docker Compose v2 روی Linux.
- دسترسی شبکه برای دریافت imageهای Docker و packageهای Python/Node در اولین build.
- پورت‌های آزاد `5173` برای رابط، `8000` برای API و `5432` برای PostgreSQL.

برای اجرای محلی بدون Docker علاوه بر Git، Python 3.14، Node.js 24 و npm 11 لازم است. برای نصب و آزمون اولیه، Docker مسیر توصیه‌شده است.

## ۲. دریافت کد

از URL واقعی مخزن سازمان استفاده کنید؛ URL در این راهنما عمداً فرض نشده است:

```bash
git clone <REPOSITORY_URL> zsh-leave
cd zsh-leave
```

در PowerShell نیز همین فرمان‌ها در ترمینال VS Code اجرا می‌شوند. اگر دسترسی مخزن خصوصی است، ابتدا با روش مورد تأیید سازمان به Git احراز هویت کنید؛ گذرواژه یا token را در URL، فایل `.env` عمومی یا کد منبع قرار ندهید.

## ۳. آماده‌کردن تنظیمات محلی

Compose به‌طور خودکار فایل `.env.example` را نمی‌خواند؛ باید آن را به `.env` کپی کنید.

Linux/macOS/Git Bash:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

فایل `.env` را باز کنید و برای `DJANGO_SECRET_KEY` و `DB_PASSWORD` مقدارهای تصادفی و محلی قرار دهید. نمونهٔ ساخت secret تصادفی در Bash:

```bash
openssl rand -hex 32
```

این فرمان را برای هر دو مقدار جداگانه اجرا کنید. مقدارها را فقط در `.env` همین لپ‌تاپ بگذارید؛ `.env` در Git نادیده گرفته می‌شود. از مقدارهای `replace-with-a-random-*` یا defaultهای Compose فقط برای آزمایش موقت روی لپ‌تاپ شخصی استفاده کنید. این پیش‌فرض‌ها secret عملیاتی نیستند.

پیش از اجرا، پیکربندی را بررسی کنید:

```bash
docker compose config -q
```

## ۴. اجرای سرویس‌ها

از ریشهٔ مخزن اجرا کنید:

```bash
docker compose up --build -d
docker compose ps
```

در وضعیت سالم باید سرویس `db` با حالت `healthy`، سرویس `backend` با حالت `Up` و سرویس `frontend` با حالت `Up` دیده شوند. در شروع نخست، build و migration ممکن است چند دقیقه طول بکشد.

آدرس‌ها:

- رابط فارسی: `http://localhost:5173`
- پنل مدیریت Django: `http://localhost:8000/admin/`
- API health: `http://localhost:8000/api/v1/health/live`
- Swagger UI: `http://localhost:8000/api/docs`
- OpenAPI JSON/YAML: `http://localhost:8000/api/v1/schema`

دیتابیس PostgreSQL روی `127.0.0.1:5432` در دسترس لپ‌تاپ محلی است. پورت روی همهٔ interfaceهای شبکه منتشر نمی‌شود.

### دسترسی از GitHub Codespaces

Compose توسعه دامنهٔ `.app.github.dev` را برای `ALLOWED_HOSTS` و originهای forwardشدهٔ `https://*.app.github.dev` و `https://localhost:5174` را برای CSRF trust مجاز می‌کند تا فرم ورود بتواند cookie و CSRF token را به API بفرستد. روی لپ‌تاپ یا استقرار دیگری این wildcard را بی‌دلیل فعال نکنید؛ فقط originهای مورد نیاز همان محیط را در `DJANGO_CSRF_TRUSTED_ORIGINS` تعیین کنید. هنگام بازکردن لینک forwardشده باید در GitHub نیز وارد شده باشید.

## ۵. نام کاربری و گذرواژهٔ ورود

**نام کاربری یا گذرواژهٔ پیش‌فرضی در پروژه وجود ندارد.** هنگام اولین اجرا هیچ حساب آزمایشی، رمز ثابت، کارمند، HR، نوع مرخصی یا سهمیه‌ای seed نمی‌شود.

یک مدیر سامانه برای همین لپ‌تاپ بسازید:

```bash
docker compose exec backend python manage.py createsuperuser
```

Django از شما نام کاربری، ایمیل اختیاری و گذرواژه می‌پرسد. نام کاربری و گذرواژه‌ای که خودتان وارد می‌کنید، حساب ورود محلی شماست؛ این مقادیر بین لپ‌تاپ‌ها منتقل نمی‌شوند و در مخزن ذخیره نشده‌اند. برای ورود به پنل Django از `http://localhost:8000/admin/` استفاده کنید.

حساب superuser به‌تنهایی نقش HR نیست و به‌طور خودکار مجاز به دیدن درخواست‌ها، مانده‌ها یا اطلاعات محرمانهٔ HR از API نمی‌شود. این جداسازی عمدی است.

## ۶. ساخت شرکت و آماده‌سازی اولین کاربر

در ترمینال دیگری، شرکت هلدینگ را با دادهٔ واقعی سازمان بسازید:

```bash
docker compose exec backend python manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی" --timezone Asia/Tehran
```

فرمان idempotent است: اجرای دوباره با همان code و همان مشخصات شرکت موجود را تأیید می‌کند؛ مقدار متفاوت را بی‌صدا بازنویسی نمی‌کند. اگر شرکت با code دیگری ساخته شده، همان code ثبت‌شده را در ادامه به‌کار ببرید.

در پنل `/admin/` با مدیر ساخته‌شده وارد شوید. برای کاربر نخست:

1. در **Users**، یک حساب سازمانی بسازید و برایش گذرواژهٔ شخصی تعیین کنید. گذرواژه را از راه امن به صاحب حساب برسانید؛ آن را در تیکت، Git یا log قرار ندهید.
2. در **Employee profiles**، برای آن User یک پروفایل پرسنلی با شماره پرسنلی یکتا و شرکت هلدینگ بسازید. بدون پروفایل فعال، کاربر نمی‌تواند درخواست شخصی ثبت کند یا ماندهٔ شخصی بگیرد.
3. برای کاربری که باید درخواست‌های دیگران را بررسی کند، پروفایل کارمند زیرمجموعه را به فیلد **Manager** مدیر متصل کنید. تشخیص مدیر از رابطهٔ فعال گزارش مستقیم انجام می‌شود؛ role جداگانه برای مدیر در تصمیم API لازم نیست.
4. برای کارمند منابع انسانی، در **Role assignments** نقش `hr` را همراه شرکت مربوط ثبت کنید. اگر HR باید به درخواست‌های شرکت دیگری دسترسی داشته باشد، انتساب مجزای همان شرکت لازم است.
5. در **Leave types**، فقط نوع‌های تصویب‌شدهٔ سازمان را بسازید. برای نمونهٔ مرخصی سالانه معمولاً `employee_requestable` و `counts_against_balance` روشن و `requires_approval` مطابق policy سازمان تنظیم می‌شود؛ هیچ تعداد روز یا الزام جانشینی را بدون تصویب HR فرض نکنید.
6. برای آزمایش مانده، سهمیه را HR از API ایجاد می‌کند؛ شرح endpoint و نمونه در بخش بعد آمده است. سهمیهٔ فرضی خودکار ساخته نمی‌شود.

کاربر با حسابی که در مرحلهٔ اول ساخته شد، در `http://localhost:5173` وارد می‌شود. این رابط و API روی مرورگر محلی‌اند؛ حساب `/admin/` و حساب برنامه همان مدل کاربر را دارند، اما حساب عملیاتی واقعی را در محیط توسعه استفاده نکنید.

## ۷. ساخت سهمیهٔ آزمایشی با API

این قابلیت در UI منابع انسانی هنوز وجود ندارد. برای آزمایش، ابتدا کاربر HR را طبق مرحلهٔ قبل بسازید و از Bash/Git Bash این درخواست‌ها را اجرا کنید. گذرواژه را در فایل یا خط فرمانی که shell history ذخیره می‌کند وارد نکنید؛ در صورت امکان ورود را از UI انجام دهید یا history را طبق سیاست سیستم پاک/غیرفعال کنید.

دریافت CSRF token و ورود با cookie jar:

```bash
COOKIE_JAR="${TMPDIR:-/tmp}/zsh-leave-cookies.txt"
CSRF_TOKEN=$(curl -fsS -c "$COOKIE_JAR" http://localhost:8000/api/v1/auth/csrf \
  | python -c "import json,sys; print(json.load(sys.stdin)['csrf_token'])")
```

درخواست ورود را با username و password حساب HR خود بفرستید:

```bash
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H "X-CSRFToken: $CSRF_TOKEN" -H 'Content-Type: application/json' \
  -d '{"username":"<HR_USERNAME>","password":"<HR_PASSWORD>"}' \
  http://localhost:8000/api/v1/auth/login
```

پاسخ موفق، `authenticated: true` و CSRF token تازه برمی‌گرداند. همان مقدار تازه را برای درخواست‌های تغییردهنده استفاده کنید. `employee_id` و `leave_type_id` را از پنل Admin بگیرید؛ `year` و مقدار سهمیه را فقط از HR بپرسید:

```bash
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H "X-CSRFToken: <CSRF_TOKEN_FROM_LOGIN_RESPONSE>" \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":1,"leave_type_id":1,"year":2026,"base_days":"22","carry_over_days":"0","reason":"سهمیهٔ آزمایشی مورد تأیید HR"}' \
  http://localhost:8000/api/v1/entitlements
```

اعداد بالا صرفاً شکل نمونهٔ درخواست‌اند و به ID یا سیاست واقعی اشاره ندارند. اگر کاربر HR به شرکت موردنظر scope نداشته باشد، پاسخ 403 می‌گیرد. اگر سهمیهٔ همان فرد/نوع/سال قبلاً وجود داشته باشد، رکورد تکراری ایجاد نمی‌شود.

## ۸. بررسی ورود و گردش درخواست

1. با یک کاربر دارای EmployeeProfile فعال وارد رابط شوید.
2. برای نمایش و ثبت درخواست، LeaveType فعال و قابل درخواست برای همان شرکت لازم است.
3. درخواستی که مدیر مستقیم فعال دارد به صف «بررسی درخواست‌ها»ی مدیر می‌رود.
4. اگر مدیر تعریف نشده یا غیرفعال باشد، درخواست به `ESCALATED` می‌رود؛ HR همان شرکت آن را در فهرست درخواست‌ها می‌بیند.
5. رد درخواست از طریق API به دلیل نیاز دارد.
6. کارمند نمی‌تواند تاریخ گذشته، روز کسری یا بازهٔ عبوری از سال ثبت کند. HR می‌تواند ثبت گذشته‌نگر انجام دهد. بازهٔ سالانه را تا تصویب policy به دو درخواست تقسیم کنید.

برای health و قرارداد API:

```bash
curl -fsS http://localhost:8000/api/v1/health/live
```

پاسخ مورد انتظار health: `{"status":"ok"}`. این فقط زنده‌بودن process را نشان می‌دهد، نه آماده‌بودن production یا سلامت backup.

## ۹. توقف، شروع مجدد و داده‌ها

توقف سرویس‌ها بدون حذف دیتابیس:

```bash
docker compose down
```

شروع مجدد:

```bash
docker compose up -d
```

دادهٔ PostgreSQL در volume با نام `postgres_data` می‌ماند. فرمان زیر volume و تمام دیتابیس توسعه را حذف می‌کند؛ فقط برای پاک‌کردن کامل محیط آزمایشی استفاده کنید، نه برای توقف عادی:

```bash
docker compose down -v
```

پشتیبان‌گیری و restore عملیاتی در این نسخه پیاده‌سازی/آزموده نشده است. volume توسعه را backup سازمانی تلقی نکنید.

## ۱۰. اجرای محلی بدون Docker

پیش‌نیاز: Python 3.14، Node.js 24 و npm 11. در این مسیر Django از SQLite محلی استفاده می‌کند؛ برای بررسی هم‌زمانی و اجرای نزدیک‌تر به Compose، PostgreSQL را با روش Docker اجرا کنید.

### Linux/macOS/Git Bash

از ریشهٔ مخزن:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
export DJANGO_DEBUG=true
backend/.venv/bin/python backend/manage.py migrate
backend/.venv/bin/python backend/manage.py createsuperuser
backend/.venv/bin/python backend/manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی" --timezone Asia/Tehran
```

در ترمینال اول backend را اجرا کنید:

```bash
DJANGO_DEBUG=true backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000
```

در ترمینال دوم:

```bash
npm ci
npm run dev
```

### Windows PowerShell

از ریشهٔ مخزن:

```powershell
py -3.14 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DJANGO_DEBUG = "true"
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py createsuperuser
backend\.venv\Scripts\python.exe backend\manage.py bootstrap_company --code zsh-holding --name "هلدینگ زکریا شیمی" --timezone Asia/Tehran
```

در ترمینال اول backend را اجرا کنید:

```powershell
$env:DJANGO_DEBUG = "true"
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

در ترمینال دوم اجرا کنید:

```powershell
npm ci
npm run dev
```

در هر دو روش، `.venv` و فایل SQLite در لپ‌تاپ محلی ساخته می‌شوند و به‌صورت خودکار با Docker volume یا لپ‌تاپ دیگر مشترک نیستند.

## ۱۱. عیب‌یابی سریع

**پورت اشغال است:** فرایندی را که پورت را گرفته متوقف کنید. Compose فعلی از پورت‌های `5173`, `8000`, `5432` استفاده می‌کند. در صورت تغییر نگاشت، `vite.config.ts` و نشانی API رابط را نیز بررسی کنید.

**Backend بالا نمی‌آید یا migration شکست می‌خورد:**

```bash
docker compose ps
docker compose logs backend
docker compose logs db
```

صبر کنید `db` حالت `healthy` بگیرد؛ سپس `docker compose up -d backend` را اجرا کنید. رمز `DB_PASSWORD` باید در `.env` بین PostgreSQL و Backend یکسان باشد. تغییر رمز بعد از ایجاد volume به‌تنهایی رمز داخل دیتابیس را تغییر نمی‌دهد.

**`403` هنگام login یا POST:** اول `/api/v1/auth/csrf` را بگیرید، cookie را حفظ کنید و همان CSRF token/cookie را برای POST بفرستید. ورود UI این کار را خودکار می‌کند.

**`403` برای اطلاعات HR یا سهمیه:** superuser به‌طور خودکار HR محسوب نمی‌شود. در Django Admin برای User نقش `hr` را به Company درست اختصاص دهید.

**کاربر نمی‌تواند درخواست بسازد:** EmployeeProfile فعال و شرکت فعال لازم است؛ LeaveType نیز باید برای همان شرکت قابل درخواست و فعال باشد.

**مدیر صف تأیید ندارد:** پروفایل کارمند باید در فیلد manager یک گزارش مستقیم فعال در همان شرکت داشته باشد. تغییر رابطه در Admin فوراً در صف‌های بعدی اثر دارد.

**ورود اشتباه:** این پروژه حساب/رمز پیش‌فرض ندارد. از Django Admin حساب بسازید یا اگر هیچ superuserی ندارید، دستور `createsuperuser` را در سرویسی که دیتابیس آن فعال است دوباره اجرا کنید.

## ۱۲. حدود استفاده

Compose و راهنما فقط محیط توسعه را پوشش می‌دهند. پیش از استفاده از اطلاعات واقعی باید دست‌کم TLS و reverse proxy عملیاتی، secret management، ساخت کاربران و نقش‌ها از منبع معتبر، policyهای HR، workerهای زمان‌بندی‌شده، پایش، backup/restore آزموده‌شده، بررسی امنیت و آموزش کاربران تکمیل شوند. برای وضعیت هر قابلیت به [ماتریس قابلیت‌ها](docs/feature-matrix.md) و برای تصمیم‌های باز به [تصمیم‌ها و فرضیات](docs/decisions.md) مراجعه کنید.