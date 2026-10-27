// SPDX-FileCopyrightText: 2026 Nextcloud GmbH and Nextcloud contributors
// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from 'react'
import DatePicker, { DateObject } from 'react-multi-date-picker'
import gregorian from 'react-date-object/calendars/gregorian'
import persian from 'react-date-object/calendars/persian'
import persianFa from 'react-date-object/locales/persian_fa'
import {
	ArrowDownLeft,
	ArrowUpLeft,
	CalendarDays,
	Check,
	ChevronLeft,
	Clock3,
	FilePlus2,
	LogOut,
	Menu,
	Plus,
	ShieldCheck,
	Sparkles,
	SunMedium,
	X,
} from 'lucide-react'

type Session = {
	username: string
	display_name: string
	profile_id: number | null
	is_superuser: boolean
	is_manager: boolean
	roles: Array<{ company_id: number; role: string }>
}

type Balance = {
	leave_type_id: number
	leave_type: string
	year: number
	base_days: string
	carry_over_days: string
	manual_adjustment: string
	entitlement: string
	used: string
	pending: string
	remaining: string
	available: string
}

type LeaveType = {
	id: number
	code: string
	name: string
	requires_approval: boolean
	employee_requestable: boolean
	requires_note: boolean
	requires_replacement: boolean
	counts_against_balance: boolean
}

type ReplacementChoice = { id: number; name: string }

type LeaveRequest = {
	id: number
	employee_id: number
	employee_name: string
	leave_type_id: number | null
	leave_type_name: string
	start_date: string
	end_date: string
	working_days: string
	status: string
	reason: string
	created_at: string
}

type Paginated<T> = { results: T[]; count: number }
type ApiError = Error & { status?: number }

const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
	const response = await fetch(`/api/v1${path}`, {
		credentials: 'include',
		...init,
		headers: {
			...(init?.body ? { 'Content-Type': 'application/json' } : {}),
			...(init?.headers ?? {}),
		},
	})
	if (!response.ok) {
		let message = 'ارتباط با سامانه ممکن نشد.'
		try {
			const payload = await response.json() as { detail?: string; message?: string; [key: string]: unknown }
			message = payload.detail ?? payload.message ?? Object.values(payload).flat().join(' ')
		} catch {
			message = response.status === 401 || response.status === 403 ? 'نشست شما معتبر نیست یا دسترسی کافی ندارید.' : message
		}
		const error = new Error(message) as ApiError
		error.status = response.status
		throw error
	}
	if (response.status === 204) return undefined as T
	return response.json() as Promise<T>
}

const fetchCsrf = async () => {
	const response = await fetch('/api/v1/auth/csrf', { credentials: 'include' })
	if (!response.ok) throw new Error('دریافت توکن امنیتی ناموفق بود.')
	return (await response.json() as { csrf_token: string }).csrf_token
}

const formatNumber = (value: string | number) => new Intl.NumberFormat('fa-IR', { maximumFractionDigits: 1 }).format(Number(value))
const formatDate = (value: string) => new Intl.DateTimeFormat('fa-IR-u-ca-persian', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(`${value}T12:00:00`))

function Login({ onLogin }: { onLogin: (session: Session) => void }) {
	const [username, setUsername] = useState('')
	const [password, setPassword] = useState('')
	const [error, setError] = useState('')
	const [submitting, setSubmitting] = useState(false)

	const submit = async (event: React.FormEvent) => {
		event.preventDefault()
		setSubmitting(true)
		setError('')
		try {
			const csrf = await fetchCsrf()
			await api('/auth/login', { method: 'POST', headers: { 'X-CSRFToken': csrf }, body: JSON.stringify({ username, password }) })
			onLogin(await api<Session>('/auth/me'))
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : 'ورود انجام نشد.')
		} finally {
			setSubmitting(false)
		}
	}

	return <main className="login-page">
		<div className="login-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="sun-disc"><SunMedium size={72} strokeWidth={1} /></div><span className="art-caption">وقتِ استراحت، حق شماست</span></div>
		<section className="login-panel">
			<div className="brand-mark"><span className="brand-emblem">ز</span><span>زکریا شیمی<small>سامانه مدیریت مرخصی و غیبت</small></span></div>
			<div className="login-copy"><span className="eyebrow">ورود سازمانی</span><h1>خوش آمدید</h1><p>برای ادامه، با حساب کاربری سازمانی خود وارد شوید.</p></div>
			<form onSubmit={submit} className="login-form">
				<label>نام کاربری<input autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required /></label>
				<label>گذرواژه<input type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required /></label>
				{error && <p className="form-error" role="alert">{error}</p>}
				<button className="button button-primary login-button" disabled={submitting}>{submitting ? 'در حال ورود…' : 'ورود به سامانه'}<ArrowUpLeft size={18} /></button>
			</form>
			<p className="login-foot"><ShieldCheck size={15} /> اتصال امن سازمانی</p>
		</section>
	</main>
}

function RequestDialog({ leaveTypes, csrf, onClose, onCreated }: {
	leaveTypes: LeaveType[]
	csrf: string
	onClose: () => void
	onCreated: () => void
}) {
	const [typeId, setTypeId] = useState('')
	const [start, setStart] = useState<DateObject | null>(null)
	const [end, setEnd] = useState<DateObject | null>(null)
	const [workingDays, setWorkingDays] = useState('')
	const [replacementId, setReplacementId] = useState('')
	const [replacementChoices, setReplacementChoices] = useState<ReplacementChoice[]>([])
	const [reason, setReason] = useState('')
	const [error, setError] = useState('')
	const [busy, setBusy] = useState(false)
	const selectedType = leaveTypes.find(type => String(type.id) === typeId)

	useEffect(() => {
		if (!selectedType?.requires_replacement) {
			setReplacementChoices([])
			setReplacementId('')
			return
		}
		api<ReplacementChoice[]>('/employees/replacements').then(setReplacementChoices).catch(reason => {
			setError(reason instanceof Error ? reason.message : 'فهرست جانشینان بارگیری نشد.')
		})
	}, [selectedType?.id])

	const submit = async (event: React.FormEvent) => {
		event.preventDefault()
		if (!start || !end || !typeId) return
		setBusy(true)
		setError('')
		try {
			const toIsoDate = (value: DateObject) => value.convert(gregorian).format('YYYY-MM-DD')
			await api('/requests', {
				method: 'POST',
				headers: { 'X-CSRFToken': csrf },
				body: JSON.stringify({
					leave_type_id: Number(typeId),
					start_date: toIsoDate(start),
					end_date: toIsoDate(end),
					working_days: workingDays,
					reason,
					replacement_id: replacementId ? Number(replacementId) : null,
				}),
			})
			onCreated()
			onClose()
		} catch (reason) {
			setError(reason instanceof Error ? reason.message : 'ثبت درخواست ممکن نشد.')
		} finally {
			setBusy(false)
		}
	}

	return <div className="modal-backdrop" onMouseDown={event => event.target === event.currentTarget && onClose()}>
		<section className="request-modal" role="dialog" aria-modal="true" aria-labelledby="request-title">
			<header className="modal-header"><div><span className="eyebrow">درخواست تازه</span><h2 id="request-title">مرخصی جدید</h2></div><button className="icon-button" onClick={onClose} aria-label="بستن"><X size={20} /></button></header>
			<form onSubmit={submit}>
				<label>نوع مرخصی<select value={typeId} onChange={event => setTypeId(event.target.value)} required><option value="">انتخاب کنید</option>{leaveTypes.filter(type => type.employee_requestable).map(type => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>
				<div className="date-fields">
					<label>از تاریخ<DatePicker calendar={persian} locale={persianFa} value={start} onChange={value => setStart(value as DateObject | null)} calendarPosition="bottom-right" inputClass="field-input" format="YYYY/MM/DD" placeholder="انتخاب تاریخ" required /></label>
					<label>تا تاریخ<DatePicker calendar={persian} locale={persianFa} value={end} onChange={value => setEnd(value as DateObject | null)} calendarPosition="bottom-right" inputClass="field-input" format="YYYY/MM/DD" placeholder="انتخاب تاریخ" required /></label>
				</div>
				<label>روز کاری تأییدشده<input type="number" min="1" max="366" step="1" value={workingDays} onChange={event => setWorkingDays(event.target.value)} placeholder="مثلاً ۳" required /></label>
				{selectedType?.requires_replacement && <label>جانشین<select value={replacementId} onChange={event => setReplacementId(event.target.value)} required><option value="">انتخاب همکار</option>{replacementChoices.map(employee => <option key={employee.id} value={employee.id}>{employee.name}</option>)}</select></label>}
				<label>توضیحات{selectedType?.requires_note ? ' (الزامی)' : ' (اختیاری)'}<textarea value={reason} onChange={event => setReason(event.target.value)} rows={3} maxLength={10000} required={selectedType?.requires_note} /></label>
				{error && <p className="form-error" role="alert">{error}</p>}
				<footer className="modal-actions"><button type="button" className="button button-quiet" onClick={onClose}>انصراف</button><button className="button button-primary" disabled={busy}>{busy ? 'در حال ثبت…' : 'ثبت درخواست'}<ArrowUpLeft size={17} /></button></footer>
			</form>
		</section>
	</div>
}

function ApprovalsList({ requests, onDecide }: {
	requests: LeaveRequest[]
	onDecide: (requestId: number, approve: boolean, reason: string) => Promise<void>
}) {
	const [rejectingId, setRejectingId] = useState<number | null>(null)
	const [reason, setReason] = useState('')
	const [busyId, setBusyId] = useState<number | null>(null)
	const [error, setError] = useState('')

	const decide = async (requestId: number, approve: boolean) => {
		setBusyId(requestId)
		setError('')
		try {
			await onDecide(requestId, approve, reason)
			setRejectingId(null)
			setReason('')
		} catch (failure) {
			setError(failure instanceof Error ? failure.message : 'ثبت تصمیم انجام نشد.')
		} finally {
			setBusyId(null)
		}
	}

	if (!requests.length) return <div className="empty-state table-empty"><div className="empty-icon"><Check size={22} /></div><strong>درخواستی برای بررسی ندارید</strong><span>درخواست‌های تازهٔ همکاران در این بخش نمایش داده می‌شود.</span></div>

	return <div className="approval-list">
		{error && <p className="form-error" role="alert">{error}</p>}
		{requests.map(request => <article className="approval-item" key={request.id}>
			<div className="approval-person"><div className="avatar approval-avatar">{request.employee_name.slice(0, 1)}</div><div><strong>{request.employee_name}</strong><span>{request.leave_type_name}</span></div></div>
			<div className="approval-dates"><span>{formatDate(request.start_date)} تا {formatDate(request.end_date)}</span><small>{formatNumber(request.working_days)} روز کاری</small></div>
			<div className="approval-buttons"><button className="icon-action approve-action" title="تأیید درخواست" aria-label={`تأیید درخواست ${request.employee_name}`} disabled={busyId === request.id} onClick={() => void decide(request.id, true)}><Check size={17} /></button><button className="icon-action reject-action" title="رد درخواست" aria-label={`رد درخواست ${request.employee_name}`} disabled={busyId === request.id} onClick={() => { setRejectingId(rejectingId === request.id ? null : request.id); setReason('') }}><X size={17} /></button></div>
			{rejectingId === request.id && <form className="reject-form" onSubmit={event => { event.preventDefault(); if (reason.trim()) void decide(request.id, false) }}><label>دلیل رد درخواست<textarea value={reason} onChange={event => setReason(event.target.value)} rows={2} maxLength={10000} required /></label><button className="button button-primary" disabled={busyId === request.id || !reason.trim()}>{busyId === request.id ? 'در حال ثبت…' : 'ثبت رد درخواست'}</button></form>}
		</article>)}
	</div>
}

function App() {
	const [session, setSession] = useState<Session | null>(null)
	const [csrf, setCsrf] = useState('')
	const [balances, setBalances] = useState<Balance[]>([])
	const [requests, setRequests] = useState<LeaveRequest[]>([])
	const [approvalRequests, setApprovalRequests] = useState<LeaveRequest[]>([])
	const [requestCount, setRequestCount] = useState(0)
	const [pendingCount, setPendingCount] = useState(0)
	const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
	const [loading, setLoading] = useState(true)
	const [error, setError] = useState('')
	const [showRequest, setShowRequest] = useState(false)
	const [activeView, setActiveView] = useState<'overview' | 'requests' | 'approvals'>('overview')
	const [mobileNav, setMobileNav] = useState(false)

	const refresh = async (currentSession: Session) => {
		setLoading(true)
		setError('')
		try {
			const canReview = currentSession.is_manager || currentSession.roles.some(role => role.role === 'hr')
			const isHr = currentSession.roles.some(role => role.role === 'hr')
			const [balanceData, requestData, pendingData, escalatedData, typeData, managerQueue, hrQueue] = await Promise.all([
				currentSession.profile_id ? api<Balance[]>('/balances/me') : Promise.resolve([] as Balance[]),
				api<Paginated<LeaveRequest>>('/requests?limit=8'),
				api<Paginated<LeaveRequest>>('/requests?status=PENDING&limit=1'),
				api<Paginated<LeaveRequest>>('/requests?status=ESCALATED&limit=1'),
				api<LeaveType[]>('/leave-types'),
				canReview ? api<Paginated<LeaveRequest>>('/requests?status=PENDING&limit=100') : Promise.resolve({ results: [], count: 0 }),
				isHr ? api<Paginated<LeaveRequest>>('/requests?status=ESCALATED&limit=100') : Promise.resolve({ results: [], count: 0 }),
			])
			setBalances(balanceData)
			setRequests(requestData.results)
			setApprovalRequests([...managerQueue.results, ...hrQueue.results].filter(item => item.employee_id !== currentSession.profile_id))
			setRequestCount(requestData.count)
			setPendingCount(pendingData.count + escalatedData.count)
			setLeaveTypes(typeData)
			setCsrf(await fetchCsrf())
			setSession(currentSession)
		} catch (reason) {
			const apiError = reason as ApiError
			setError(apiError.message)
			if (apiError.status === 401 || apiError.status === 403) setSession(null)
		} finally {
			setLoading(false)
		}
	}

	useEffect(() => {
		api<Session>('/auth/me').then(user => refresh(user)).catch(() => setLoading(false))
	}, [])

	const signOut = async () => {
		try {
			await api('/auth/logout', { method: 'POST', headers: { 'X-CSRFToken': csrf } })
		} finally {
			setSession(null)
			setBalances([])
			setRequests([])
		}
	}

	const decideRequest = async (requestId: number, approve: boolean, reason: string) => {
		if (!session) throw new Error('نشست شما معتبر نیست.')
		await api(`/requests/${requestId}/${approve ? 'approve' : 'reject'}`, {
			method: 'POST',
			headers: { 'X-CSRFToken': csrf },
			body: JSON.stringify({ reason }),
		})
		await refresh(session)
	}

	if (loading && !session) return <div className="boot-screen"><div className="loader-mark">ز</div><span>در حال بررسی نشست…</span></div>
	if (!session) return <Login onLogin={user => refresh(user)} />

	const totalAvailable = balances.reduce((sum, item) => sum + Number(item.available), 0)
	const upcoming = requests.find(request => request.status === 'APPROVED' && request.start_date >= new Date().toISOString().slice(0, 10))
	const greetingName = session.display_name.split(' ')[0]

	return <div className="app-shell">
		{mobileNav && <button className="nav-scrim" aria-label="بستن منو" onClick={() => setMobileNav(false)} />}
		<aside className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
			<div className="brand-mark sidebar-brand"><span className="brand-emblem">ز</span><span>زکریا شیمی<small>مدیریت مرخصی</small></span></div>
			{session.profile_id && <button className="new-request button button-primary" onClick={() => setShowRequest(true)}><Plus size={18} />درخواست مرخصی</button>}
			<div className="nav-caption">فضای کاری</div>
			<nav className="side-nav" aria-label="ناوبری اصلی">
				<button className={activeView === 'overview' ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveView('overview'); setMobileNav(false) }}><SunMedium size={18} />نمای کلی</button>
				<button className={activeView === 'requests' ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveView('requests'); setMobileNav(false) }}><CalendarDays size={18} />درخواست‌های من<span className="nav-count">{formatNumber(requestCount)}</span></button>
				{(session.is_manager || session.roles.some(role => role.role === 'hr')) && <button className={activeView === 'approvals' ? 'nav-item active' : 'nav-item'} onClick={() => { setActiveView('approvals'); setMobileNav(false) }}><Check size={18} />بررسی درخواست‌ها<small className="nav-count">{formatNumber(approvalRequests.length)}</small></button>}
			</nav>
			<div className="sidebar-bottom">
				<div className="help-strip"><div className="help-icon"><Sparkles size={17} /></div><div><strong>نیاز به راهنمایی دارید؟</strong><span>با منابع انسانی در ارتباط باشید.</span></div><ChevronLeft size={16} /></div>
				<div className="profile-row"><div className="avatar">{greetingName.slice(0, 1)}</div><div className="profile-meta"><strong>{session.display_name}</strong><span>{session.roles.some(role => role.role === 'hr') ? 'منابع انسانی' : 'همکار سازمان'}</span></div><button className="icon-button logout-button" aria-label="خروج از حساب" onClick={signOut}><LogOut size={17} /></button></div>
			</div>
		</aside>
		<main className="main-content">
			<header className="topbar"><button className="icon-button mobile-menu" onClick={() => setMobileNav(true)} aria-label="بازکردن منو"><Menu size={21} /></button><div className="breadcrumb">خانه <ChevronLeft size={14} /> <strong>{activeView === 'overview' ? 'نمای کلی' : activeView === 'requests' ? 'درخواست‌های من' : 'بررسی درخواست‌ها'}</strong></div><div className="topbar-date">{new Intl.DateTimeFormat('fa-IR-u-ca-persian', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())}</div><div className="top-avatar">{greetingName.slice(0, 1)}</div></header>
			<div className="page-wrap">
				<div className="page-heading"><div><span className="eyebrow">سامانه منابع انسانی</span><h1>{activeView === 'overview' ? `روز بخیر، ${greetingName}` : activeView === 'requests' ? 'درخواست‌های مرخصی' : 'بررسی درخواست‌های همکاران'}</h1><p>{activeView === 'overview' ? 'وضعیت مرخصی و برنامه پیش روی شما' : activeView === 'requests' ? 'همه درخواست‌های ثبت‌شده خود را اینجا دنبال کنید.' : 'درخواست‌های نیازمند تصمیم در محدوده مجاز شما'}</p></div><button className="button button-outline" onClick={() => refresh(session)}><ArrowDownLeft size={17} />تازه‌سازی</button></div>
				{error && <div className="error-banner" role="alert">{error}<button className="icon-button" onClick={() => setError('')} aria-label="بستن پیام"><X size={16} /></button></div>}
				{activeView === 'overview' ? <>
					<section className="welcome-banner"><div className="welcome-copy"><span className="banner-kicker">برنامه‌ریزی هوشمند، استراحت آسوده</span><h2>{upcoming ? 'برای استراحت بعدی آماده شوید' : 'برای استراحت بعدی برنامه دارید؟'}</h2><p>{upcoming ? `مرخصی شما از ${formatDate(upcoming.start_date)} آغاز می‌شود.` : 'درخواست مرخصی خود را ثبت کنید تا برنامه‌ریزی روزهای آینده آسان‌تر شود.'}</p>{session.profile_id && <button className="button button-light" onClick={() => setShowRequest(true)}>ثبت درخواست جدید<ArrowUpLeft size={17} /></button>}</div><div className="banner-visual" aria-hidden="true"><div className="banner-sun" /><div className="banner-leaf leaf-a" /><div className="banner-leaf leaf-b" /><div className="banner-leaf leaf-c" /><span className="banner-orbit" /></div><div className="banner-index">۰۱ <span>—</span> مرخصی شما</div></section>
					<section className="stats-grid" aria-label="خلاصه مرخصی">
						<article className="stat-card stat-primary"><div className="stat-top"><span>مانده قابل استفاده</span><div className="stat-icon"><SunMedium size={18} /></div></div><div className="stat-value">{loading ? '…' : formatNumber(totalAvailable)}<small>روز</small></div><div className="stat-bottom"><span>بر اساس سهمیه فعال شما</span><ArrowUpLeft size={15} /></div></article>
						<article className="stat-card"><div className="stat-top"><span>در انتظار تصمیم</span><div className="stat-icon amber"><Clock3 size={18} /></div></div><div className="stat-value">{formatNumber(pendingCount)}<small>درخواست</small></div><div className="stat-bottom"><span>در صف بررسی مدیر یا HR</span><span className="status-dot" /></div></article>
						<article className="stat-card"><div className="stat-top"><span>روزهای استفاده‌شده</span><div className="stat-icon blue"><Check size={18} /></div></div><div className="stat-value">{formatNumber(balances.reduce((sum, item) => sum + Number(item.used), 0))}<small>روز</small></div><div className="stat-bottom"><span>در دوره جاری</span><span className="stat-trend">{formatNumber(balances.reduce((sum, item) => sum + Number(item.entitlement), 0))} روز سهمیه</span></div></article>
					</section>
					<section className="content-grid"><div className="section-panel balance-panel"><div className="panel-heading"><div><span className="eyebrow">تفکیک سهمیه</span><h2>مانده مرخصی شما</h2></div><button className="text-button" onClick={() => setActiveView('requests')}>درخواست‌ها<ChevronLeft size={15} /></button></div>{balances.length ? <div className="balance-list">{balances.map(balance => {
							const entitlement = Number(balance.entitlement)
							const used = Number(balance.used)
							const percent = entitlement > 0 ? Math.min(100, used / entitlement * 100) : 0
							return <div className="balance-row" key={balance.leave_type_id}><div className="balance-title"><span className="type-dot" /><strong>{balance.leave_type}</strong><span>{formatNumber(balance.year)}</span></div><div className="balance-track"><span style={{ width: `${percent}%` }} /></div><div className="balance-numbers"><span><b>{formatNumber(balance.available)}</b> قابل استفاده</span><span>{formatNumber(used)} از {formatNumber(entitlement)} روز</span></div></div>
						})}</div> : <div className="empty-state"><div className="empty-icon"><FilePlus2 size={22} /></div><strong>هنوز سهمیه‌ای برای شما تعریف نشده</strong><span>برای پیگیری، با منابع انسانی تماس بگیرید.</span></div>}</div>
						<aside className="section-panel next-panel"><div className="panel-heading"><div><span className="eyebrow">برنامه نزدیک</span><h2>مرخصی پیش رو</h2></div><CalendarDays size={18} className="muted-icon" /></div>{upcoming ? <div className="upcoming-card"><div className="upcoming-date"><span>{formatDate(upcoming.start_date)}</span><strong>{formatNumber(upcoming.working_days)} روز</strong></div><div className="upcoming-type">{upcoming.leave_type_name}</div><div className="upcoming-range">{formatDate(upcoming.start_date)} تا {formatDate(upcoming.end_date)}</div><span className="status-pill approved">تأیید شده</span></div> : <div className="empty-upcoming"><div className="empty-calendar"><CalendarDays size={24} /></div><strong>مرخصی تأییدشده‌ای ندارید</strong><span>برنامه بعدی‌تان را همین حالا بچینید.</span><button className="text-button" onClick={() => setShowRequest(true)}>درخواست مرخصی<ChevronLeft size={15} /></button></div>}</aside></section>
					<section className="section-panel requests-panel"><div className="panel-heading"><div><span className="eyebrow">پیگیری وضعیت</span><h2>آخرین درخواست‌ها</h2></div><button className="text-button" onClick={() => setActiveView('requests')}>مشاهده همه<ChevronLeft size={15} /></button></div><RequestTable requests={requests.slice(0, 5)} /></section>
				</> : activeView === 'requests' ? <section className="section-panel requests-panel full-list"><div className="panel-heading"><div><span className="eyebrow">تاریخچه</span><h2>همه درخواست‌ها</h2></div>{session.profile_id && <button className="button button-primary" onClick={() => setShowRequest(true)}><Plus size={17} />درخواست تازه</button>}</div><RequestTable requests={requests} /></section> : <section className="section-panel requests-panel full-list"><div className="panel-heading"><div><span className="eyebrow">صف تصمیم‌گیری</span><h2>در انتظار بررسی</h2></div></div><ApprovalsList requests={approvalRequests} onDecide={decideRequest} /></section>}
				<footer className="page-footer"><span>سامانه مدیریت مرخصی و غیبت</span><span>هلدینگ زکریا شیمی</span><span><ShieldCheck size={14} />اطلاعات شما محرمانه است</span></footer>
			</div>
		</main>
		{showRequest && <RequestDialog leaveTypes={leaveTypes} csrf={csrf} onClose={() => setShowRequest(false)} onCreated={() => refresh(session)} />}
	</div>
}

function RequestTable({ requests }: { requests: LeaveRequest[] }) {
	if (!requests.length) return <div className="empty-state table-empty"><div className="empty-icon"><FilePlus2 size={22} /></div><strong>درخواستی ثبت نشده است</strong><span>پس از ثبت، وضعیت درخواست‌ها در همین فهرست نمایش داده می‌شود.</span></div>
	const labels: Record<string, string> = { PENDING: 'در انتظار بررسی', ESCALATED: 'ارجاع به منابع انسانی', APPROVED: 'تأیید شده', REJECTED: 'رد شده', CANCELLED: 'لغو شده', WITHDRAWAL_PENDING: 'درخواست لغو' }
	return <div className="table-scroll"><table><thead><tr><th>نوع مرخصی</th><th>بازه زمانی</th><th>روز کاری</th><th>وضعیت</th><th>ثبت درخواست</th></tr></thead><tbody>{requests.map(request => <tr key={request.id}><td><div className="request-type"><span className="type-dot" />{request.leave_type_name}</div></td><td><span className="date-range">{formatDate(request.start_date)}<span>تا</span>{formatDate(request.end_date)}</span></td><td>{formatNumber(request.working_days)} روز</td><td><span className={`status-pill ${request.status.toLowerCase()}`}>{labels[request.status] ?? request.status}</span></td><td className="date-muted">{formatDate(request.created_at.slice(0, 10))}</td></tr>)}</tbody></table></div>
}

export default App