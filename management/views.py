from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.db.models.fields import DecimalField
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from authentication.models import Role, User
from authentication.settings_context import build_settings_context
from authentication.email_change_context import build_email_change_context
from authentication.users import is_username_taken
from authentication.providers import get_provider
from commissions.commission_config import get_commission_settings, parse_commission_form, save_commission_settings
from commissions.constants import GDT_CURRENT_PRICE_KEY
from commissions.models import SystemConfig
from commissions.services import calculate_headman_commission
from management.decorators import (
    admin_required,
    headman_required,
    member_required,
    reject_locked_headman,
)
from management.models import AuditLog, Investment, Profile
from management.services.backup import create_backup, list_backups, restore_backup
from management.services.dashboard import get_admin_dashboard_context, get_headman_dashboard_context
from management.services.audit import (
    email_settings_snapshot,
    profile_snapshot,
    record_audit,
    record_update_audit,
)
from management.services.email_config import (
    EMAIL_MODE_CONSOLE,
    EMAIL_MODE_SMTP,
    get_email_config,
    get_email_config_for_form,
    get_email_mode_label,
    is_smtp_enabled,
    save_email_config,
    send_test_email,
    validate_email_config,
)

PAGE_SIZE = 20

HEADMAN_LIST_SORTABLE = {
    'username': 'username',
    'name': 'profile__name',
    'member_count': 'member_count',
    'total_investment': 'total_investment',
    'status': 'is_locked',
    'date_joined': 'date_joined',
}

MEMBER_LIST_SORTABLE = {
    'username': 'username',
    'name': 'profile__name',
    'phone': 'profile__phone',
    'total_investment': 'total_investment',
    'date_joined': 'date_joined',
}


def _redirect_by_role(user):
    if user.role == Role.ADMIN:
        return redirect('management:admin_dashboard')
    if user.role == Role.HEADMAN:
        return redirect('management:headman_dashboard')
    return redirect('management:member_dashboard')


def _paginate(request, queryset, page_size=PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    return paginator.get_page(request.GET.get('page'))


def _list_query_string(request, *, sort=None, order=None, sortable=None, preserve=()) -> str:
    from urllib.parse import urlencode

    sortable = sortable or HEADMAN_LIST_SORTABLE
    params = {}
    q = request.GET.get('q', '').strip()
    if q:
        params['q'] = q
    for key in preserve:
        val = request.GET.get(key, '').strip()
        if val:
            params[key] = val
    sort = sort or request.GET.get('sort', 'date_joined')
    order = order or request.GET.get('order', 'desc')
    if sort in sortable:
        params['sort'] = sort
    if order in ('asc', 'desc'):
        params['order'] = order
    return urlencode(params)


def _members_with_totals(queryset):
    gdt_price = SystemConfig.get_gdt_price()
    return queryset.select_related('profile').annotate(
        total_investment=Coalesce(
            Sum('investments__investment_amount'),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
        total_tokens=Coalesce(
            Sum('investments__holding_quantity'),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=18, decimal_places=8),
        ),
    ).annotate(
        total_market_value=ExpressionWrapper(
            F('total_tokens') * Value(gdt_price),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    )


@login_required
def role_dashboard_redirect(request):
    return _redirect_by_role(request.user)


# ── Admin ──────────────────────────────────────────────────────────

@admin_required
def admin_dashboard(request):
    return render(request, 'management/admin/dashboard.html', get_admin_dashboard_context())


@admin_required
def admin_mobile_menu(request):
    return redirect('management:admin_profile')


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_profile(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username},
    )
    if request.method == 'POST':
        before_profile = profile_snapshot(profile)
        profile.phone = request.POST.get('phone', '').strip()
        profile.wechat = request.POST.get('wechat', '').strip()
        profile.save()
        record_update_audit(
            request,
            before=before_profile,
            after=profile_snapshot(profile),
            action='management:admin_profile',
        )
        messages.success(request, '资料已更新。')
        return redirect('management:admin_profile')

    return render(
        request,
        'management/admin/profile.html',
        {
            'profile': profile,
            **build_settings_context(request.user),
            **build_email_change_context(request),
        },
    )


@admin_required
def admin_member_list(request):
    q = request.GET.get('q', '').strip()
    headman_id = request.GET.get('headman', '').strip()
    sort = request.GET.get('sort', 'date_joined')
    order = request.GET.get('order', 'desc')
    if sort not in MEMBER_LIST_SORTABLE:
        sort = 'date_joined'
    if order not in ('asc', 'desc'):
        order = 'desc'

    order_prefix = '' if order == 'asc' else '-'
    headmen = User.objects.filter(role=Role.HEADMAN).select_related('profile').order_by('username')
    members = _members_with_totals(User.objects.filter(role=Role.MEMBER))

    selected_headman = None
    if headman_id.isdigit():
        selected_headman = headmen.filter(pk=int(headman_id)).first()
        if selected_headman:
            members = members.filter(referrer_id=selected_headman.pk)
        else:
            headman_id = ''

    if q:
        members = members.filter(
            Q(username__icontains=q) | Q(profile__name__icontains=q)
        )

    members = members.order_by(f'{order_prefix}{MEMBER_LIST_SORTABLE[sort]}', 'id')
    page_obj = _paginate(request, members)
    return render(request, 'management/admin/member_list.html', {
        'page_obj': page_obj,
        'members': page_obj,
        'headmen': headmen,
        'selected_headman_id': headman_id,
        'selected_headman': selected_headman,
        'q': q,
        'sort': sort,
        'order': order,
        'query': _list_query_string(
            request,
            sort=sort,
            order=order,
            sortable=MEMBER_LIST_SORTABLE,
            preserve=('headman',),
        ),
    })


@admin_required
def admin_member_detail(request, pk):
    member = get_object_or_404(
        _members_with_totals(User.objects.select_related('profile')),
        pk=pk,
        role=Role.MEMBER,
    )
    profile = getattr(member, 'profile', None)
    all_investments = Investment.objects.filter(user=member)
    gdt_price = SystemConfig.get_gdt_price()
    total_market_value = sum((inv.current_market_value for inv in all_investments), Decimal('0'))
    investments = all_investments.order_by('-investment_date')[:50]
    context = {
        'member': member,
        'profile': profile,
        'investments': investments,
        'gdt_price': gdt_price,
        'total_market_value': total_market_value,
        'show_investment_actions': False,
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'management/headman/_member_detail_modal.html', context)
    return redirect('management:admin_member_list')


@admin_required
def admin_headman_list(request):
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'date_joined')
    order = request.GET.get('order', 'desc')
    if sort not in HEADMAN_LIST_SORTABLE:
        sort = 'date_joined'
    if order not in ('asc', 'desc'):
        order = 'desc'

    order_prefix = '' if order == 'asc' else '-'
    headmen = User.objects.filter(role=Role.HEADMAN).select_related('profile').annotate(
        member_count=Count('referred_members', distinct=True),
        total_investment=Coalesce(
            Sum('referred_members__investments__investment_amount'),
            Value(Decimal('0')),
            output_field=DecimalField(max_digits=18, decimal_places=2),
        ),
    ).order_by(f'{order_prefix}{HEADMAN_LIST_SORTABLE[sort]}', 'id')
    if q:
        headmen = headmen.filter(
            Q(username__icontains=q) | Q(profile__name__icontains=q)
        )
    page_obj = _paginate(request, headmen)
    return render(request, 'management/admin/headman_list.html', {
        'page_obj': page_obj,
        'headmen': page_obj,
        'q': q,
        'sort': sort,
        'order': order,
        'query': _list_query_string(request, sort=sort, order=order),
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_headman_detail(request, pk):
    headman = get_object_or_404(
        User.objects.select_related('profile'),
        pk=pk,
        role=Role.HEADMAN,
    )
    profile, _ = Profile.objects.get_or_create(
        user=headman,
        defaults={'name': headman.username},
    )

    if request.method == 'POST' and request.POST.get('action') == 'update_profile':
        if request.POST.get('confirmed') != '1':
            messages.error(request, '请先确认后再保存修改。')
            return redirect('management:admin_headman_detail', pk=pk)

        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, '姓名不能为空。')
            return redirect('management:admin_headman_detail', pk=pk)

        before_profile = profile_snapshot(profile)
        profile.name = name
        profile.phone = request.POST.get('phone', '').strip()
        profile.wechat = request.POST.get('wechat', '').strip()
        profile.email = request.POST.get('email', '').strip()
        profile.save()
        headman.email = profile.email
        headman.save(update_fields=['email'])
        record_update_audit(
            request,
            before=before_profile,
            after=profile_snapshot(profile),
            action='management:admin_headman_detail',
        )
        messages.success(request, f'团长 {headman.username} 的资料已更新。')
        return redirect('management:admin_headman_detail', pk=pk)

    stats = calculate_headman_commission(headman)
    members = (
        headman.referred_members.filter(role=Role.MEMBER)
        .select_related('profile')
        .annotate(
            total_investment=Sum('investments__investment_amount'),
            total_tokens=Sum('investments__holding_quantity'),
        )
        .order_by('-date_joined')
    )
    page_obj = _paginate(request, members)
    return render(request, 'management/admin/headman_detail.html', {
        'headman': headman,
        'profile': profile,
        'stats': stats,
        'page_obj': page_obj,
        'members': page_obj,
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_create_headman(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        wechat = request.POST.get('wechat', '').strip()
        email = request.POST.get('email', '').strip()

        if not username or not password or not name:
            messages.error(request, '用户名、密码、姓名为必填项。')
        elif is_username_taken(username):
            messages.error(request, '用户名已存在。')
        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    role=Role.HEADMAN,
                    is_first_login=True,
                )
                Profile.objects.create(
                    user=user,
                    name=name,
                    phone=phone,
                    wechat=wechat,
                    email=email,
                )
            record_audit(
                request,
                action='management:admin_create_headman',
                after={
                    '用户名': username,
                    '姓名': name,
                    '手机': phone or '—',
                    '微信': wechat or '—',
                    '邮箱': email or '—',
                },
            )
            messages.success(request, f'团长 {username} 开户成功。')
            return redirect('management:admin_headman_detail', pk=user.pk)

    return render(request, 'management/admin/create_headman.html')


@admin_required
@require_http_methods(['POST'])
def admin_toggle_headman_lock(request, pk):
    headman = get_object_or_404(User, pk=pk, role=Role.HEADMAN)
    before_state = '已锁定' if headman.is_locked else '正常'
    headman.is_locked = not headman.is_locked
    headman.save(update_fields=['is_locked'])
    after_state = '已锁定' if headman.is_locked else '正常'
    state = '锁定' if headman.is_locked else '解锁'
    record_update_audit(
        request,
        before={'账号状态': before_state},
        after={'账号状态': after_state},
        action='management:admin_toggle_lock',
    )
    messages.success(request, f'已{state}团长 {headman.username}。')
    redirect_to = request.POST.get('redirect_to', '')
    if redirect_to:
        return redirect(redirect_to)
    page = request.POST.get('page', '')
    if page:
        return redirect(f'/manage/admin/headmen/?page={page}')
    return redirect('management:admin_headman_list')


@admin_required
@require_http_methods(['POST'])
def admin_reset_headman_password(request, pk):
    headman = get_object_or_404(
        User.objects.select_related('profile'),
        pk=pk,
        role=Role.HEADMAN,
    )
    from authentication.password_reset import send_password_reset_email

    try:
        masked = send_password_reset_email(request, headman)
    except ValueError as exc:
        messages.error(request, str(exc))
        redirect_to = request.POST.get('redirect_to', '')
        if redirect_to:
            return redirect(redirect_to)
        return redirect('management:admin_headman_detail', pk=pk)
    except Exception as exc:
        messages.error(request, f'发送失败：{exc}')
        redirect_to = request.POST.get('redirect_to', '')
        if redirect_to:
            return redirect(redirect_to)
        return redirect('management:admin_headman_detail', pk=pk)

    headman.is_first_login = True
    headman.save(update_fields=['is_first_login'])
    record_audit(
        request,
        action='management:admin_reset_headman_password',
        summary=f'向团长 {headman.username} 发送密码重置邮件',
        after={'邮箱': masked, '账号': headman.username},
        note='用户需通过邮件链接设置新密码。',
    )
    messages.success(request, f'密码重置邮件已发送至 {masked}，请提醒团长查收并设置新密码。')
    redirect_to = request.POST.get('redirect_to', '')
    if redirect_to:
        return redirect(redirect_to)
    return redirect('management:admin_headman_detail', pk=pk)


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_settings_price(request):
    current_price = SystemConfig.get_gdt_price()
    if request.method == 'POST':
        raw = request.POST.get('gdt_price', '').strip()
        try:
            price = Decimal(raw)
            if price <= 0:
                raise InvalidOperation
            old_price = current_price
            SystemConfig.set_value(GDT_CURRENT_PRICE_KEY, str(price), 'GDT 当前全局唯一价格')
            record_update_audit(
                request,
                before={'GDT 价格 (USDT)': str(old_price)},
                after={'GDT 价格 (USDT)': str(price)},
                action='management:admin_settings_price',
            )
            messages.success(request, f'GDT 价格已更新为 {price} USDT。')
            return redirect('management:admin_settings_price')
        except (InvalidOperation, ValueError):
            messages.error(request, '请输入有效的正数价格。')

    return render(request, 'management/admin/settings_price.html', {
        'current_price': current_price,
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_settings_commission(request):
    if request.method == 'POST':
        try:
            before_settings = get_commission_settings()
            before_snapshot = {
                '大团长奖励比例': f"{before_settings['base_bonus_rate_percent']}%",
                '奖励币种': before_settings['base_bonus_currency'],
                '阶梯数量': str(len(before_settings['tiers'])),
            }
            tiers, base_bonus_rate, base_bonus_currency = parse_commission_form(request.POST)
            save_commission_settings(tiers, base_bonus_rate, base_bonus_currency)
            after_settings = get_commission_settings()
            after_snapshot = {
                '大团长奖励比例': f"{after_settings['base_bonus_rate_percent']}%",
                '奖励币种': after_settings['base_bonus_currency'],
                '阶梯数量': str(len(after_settings['tiers'])),
            }
            record_update_audit(
                request,
                before=before_snapshot,
                after=after_snapshot,
                action='management:admin_settings_commission',
            )
            messages.success(request, '提成设定已保存，将立即应用于全平台计算。')
            return redirect('management:admin_settings_commission')
        except ValueError as exc:
            messages.error(request, str(exc))

    settings_data = get_commission_settings()
    return render(request, 'management/admin/settings_commission.html', settings_data)


@admin_required
def admin_settings_backup(request):
    backups = list_backups()
    return render(request, 'management/admin/settings_backup.html', {
        'backups': backups,
    })


@admin_required
@require_http_methods(['GET', 'POST'])
def admin_settings_email(request):
    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        if action == 'test':
            test_to = request.POST.get('test_to', '').strip()
            if not test_to:
                messages.error(request, '请填写测试收件邮箱。')
            elif not is_smtp_enabled():
                messages.error(
                    request,
                    '当前为「开发模式（控制台）」，邮件不会真正发出。'
                    '请先将发送方式改为 SMTP，保存后再测试。',
                )
            else:
                try:
                    send_test_email(test_to)
                    record_audit(
                        request,
                        action='management:admin_settings_email',
                        summary='发送测试邮件',
                        after={'收件邮箱': test_to},
                    )
                    messages.success(request, f'测试邮件已发送至 {test_to}，请查收。')
                except Exception as exc:
                    messages.error(request, f'发送失败：{exc}')
            return redirect('management:admin_settings_email')

        form_data = {
            'mode': request.POST.get('mode', EMAIL_MODE_CONSOLE),
            'host': request.POST.get('host', ''),
            'port': request.POST.get('port', '587'),
            'username': request.POST.get('username', ''),
            'password': request.POST.get('password', ''),
            'use_tls': request.POST.get('use_tls') == 'on',
            'from_email': request.POST.get('from_email', ''),
        }
        error = validate_email_config(form_data)
        if error:
            messages.error(request, error)
        else:
            before_config = email_settings_snapshot(get_email_config())
            save_email_config(form_data)
            after_config = email_settings_snapshot(get_email_config())
            record_update_audit(
                request,
                before=before_config,
                after=after_config,
                action='management:admin_settings_email',
            )
            messages.success(request, '邮件服务配置已保存。')
        return redirect('management:admin_settings_email')

    config = get_email_config_for_form()
    return render(request, 'management/admin/settings_email.html', {
        'config': config,
        'mode_label': get_email_mode_label(config['mode']),
        'email_mode_console': EMAIL_MODE_CONSOLE,
        'email_mode_smtp': EMAIL_MODE_SMTP,
        'smtp_active': config['mode'] == EMAIL_MODE_SMTP,
    })


@admin_required
@require_http_methods(['POST'])
def admin_backup(request):
    filepath = create_backup()
    record_audit(
        request,
        action='management:admin_backup',
        after={'备份文件': filepath.name},
    )
    messages.success(request, f'备份成功：{filepath.name}')
    return redirect('management:admin_settings_backup')


@admin_required
@require_http_methods(['POST'])
def admin_restore(request):
    filename = request.POST.get('backup_file', '')
    backups = {b.name: b for b in list_backups()}
    if filename not in backups:
        messages.error(request, '备份文件不存在。')
        return redirect('management:admin_settings_backup')
    try:
        restore_backup(backups[filename])
        record_audit(
            request,
            action='management:admin_restore',
            after={'还原文件': filename},
            note='已用备份覆盖当前数据库。',
        )
        messages.success(request, f'已从 {filename} 还原数据。')
    except Exception as exc:
        messages.error(request, f'还原失败：{exc}')
    return redirect('management:admin_settings_backup')


@admin_required
def admin_settings_audit(request):
    q = request.GET.get('q', '').strip()
    logs = AuditLog.objects.all()
    if q:
        logs = logs.filter(
            Q(username__icontains=q)
            | Q(summary__icontains=q)
            | Q(action__icontains=q)
            | Q(path__icontains=q)
            | Q(ip_address__icontains=q)
        )
    page_obj = _paginate(request, logs, page_size=30)
    return render(request, 'management/admin/settings_audit.html', {
        'page_obj': page_obj,
        'logs': page_obj,
        'q': q,
    })


@admin_required
def admin_settings_audit_detail(request, pk):
    log = get_object_or_404(AuditLog, pk=pk)
    context = {'log': log}
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'management/admin/_audit_detail_modal.html', context)
    return render(request, 'management/admin/settings_audit_detail.html', context)


# ── Headman ────────────────────────────────────────────────────────

@headman_required
def headman_dashboard(request):
    context = get_headman_dashboard_context(request.user)
    context['is_locked'] = request.user.is_locked
    return render(request, 'management/headman/dashboard.html', context)


@headman_required
def headman_member_list(request):
    q = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', 'date_joined')
    order = request.GET.get('order', 'desc')
    if sort not in MEMBER_LIST_SORTABLE:
        sort = 'date_joined'
    if order not in ('asc', 'desc'):
        order = 'desc'

    order_prefix = '' if order == 'asc' else '-'
    members = _members_with_totals(
        request.user.referred_members.filter(role=Role.MEMBER)
    )
    if q:
        members = members.filter(
            Q(username__icontains=q) | Q(profile__name__icontains=q)
        )
    members = members.order_by(f'{order_prefix}{MEMBER_LIST_SORTABLE[sort]}', 'id')
    page_obj = _paginate(request, members)
    return render(request, 'management/headman/member_list.html', {
        'page_obj': page_obj,
        'members': page_obj,
        'q': q,
        'sort': sort,
        'order': order,
        'query': _list_query_string(request, sort=sort, order=order, sortable=MEMBER_LIST_SORTABLE),
        'is_locked': request.user.is_locked,
    })


@headman_required
def headman_member_detail(request, pk):
    member = get_object_or_404(
        _members_with_totals(User.objects.select_related('profile')),
        pk=pk,
        role=Role.MEMBER,
        referrer=request.user,
    )
    profile = getattr(member, 'profile', None)
    all_investments = Investment.objects.filter(user=member)
    gdt_price = SystemConfig.get_gdt_price()
    total_market_value = sum((inv.current_market_value for inv in all_investments), Decimal('0'))
    investments = all_investments.order_by('-investment_date')[:50]
    context = {
        'member': member,
        'profile': profile,
        'investments': investments,
        'gdt_price': gdt_price,
        'total_market_value': total_market_value,
        'is_locked': request.user.is_locked,
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'management/headman/_member_detail_modal.html', context)
    return redirect('management:headman_member_list')


@headman_required
@require_http_methods(['GET', 'POST'])
def headman_profile(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username},
    )
    if request.method == 'POST':
        blocked = reject_locked_headman(request, redirect_to='management:headman_profile')
        if blocked:
            return blocked
        before_profile = profile_snapshot(profile)
        profile.name = request.POST.get('name', profile.name).strip()
        profile.phone = request.POST.get('phone', '').strip()
        profile.wechat = request.POST.get('wechat', '').strip()
        profile.save()
        record_update_audit(
            request,
            before=before_profile,
            after=profile_snapshot(profile),
            action='management:headman_profile',
        )
        messages.success(request, '资料已更新。')
        return redirect('management:headman_profile')

    return render(
        request,
        'management/headman/profile.html',
        {
            'profile': profile,
            **build_settings_context(request.user),
            **build_email_change_context(request),
        },
    )


@headman_required
@require_http_methods(['GET', 'POST'])
def headman_add_member(request):
    blocked = reject_locked_headman(request)
    if blocked:
        return blocked

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        wechat = request.POST.get('wechat', '').strip()
        email = request.POST.get('email', '').strip()
        investment_amount = request.POST.get('investment_amount', '').strip() or '0'
        holding_quantity = request.POST.get('holding_quantity', '').strip() or '0'

        if not all([username, password, name]):
            messages.error(request, '用户名、密码、姓名为必填项。')
        elif is_username_taken(username):
            messages.error(request, '用户名已存在。')
        else:
            try:
                with transaction.atomic():
                    member = User.objects.create_user(
                        username=username,
                        password=password,
                        role=Role.MEMBER,
                        referrer=request.user,
                        is_first_login=True,
                    )
                    Profile.objects.create(
                        user=member,
                        name=name,
                        phone=phone,
                        wechat=wechat,
                        email=email,
                    )
                    amount = Decimal(investment_amount)
                    quantity = Decimal(holding_quantity)
                    if amount > 0 or quantity > 0:
                        Investment.objects.create(
                            user=member,
                            investment_date=timezone.now(),
                            investment_amount=amount,
                            holding_quantity=quantity,
                        )
                record_audit(
                    request,
                    action='management:headman_add_member',
                    after={
                        '用户名': username,
                        '姓名': name,
                        '投资金额 (USDT)': investment_amount,
                        '持有数量 (GDT)': holding_quantity,
                    },
                )
                messages.success(request, f'成员 {username} 录入成功。')
                return redirect('management:headman_member_list')
            except (InvalidOperation, ValueError):
                messages.error(request, '投资金额或持币数量格式无效。')

    return render(request, 'management/headman/add_member.html', {
        'gdt_price': SystemConfig.get_gdt_price(),
    })


@headman_required
@require_http_methods(['GET', 'POST'])
def headman_add_investment(request, pk=None):
    blocked = reject_locked_headman(request)
    if blocked:
        return blocked

    members = (
        request.user.referred_members.filter(role=Role.MEMBER)
        .select_related('profile')
        .order_by('username')
    )
    selected_member = None
    if pk:
        selected_member = get_object_or_404(members, pk=pk)
    elif request.GET.get('member'):
        selected_member = get_object_or_404(members, pk=request.GET.get('member'))

    if request.method == 'POST':
        member_id = request.POST.get('member_id', '').strip() or pk
        member = get_object_or_404(members, pk=member_id)
        profile = getattr(member, 'profile', None)
        investment_amount = request.POST.get('investment_amount', '').strip()
        holding_quantity = request.POST.get('holding_quantity', '').strip()

        if not investment_amount or not holding_quantity:
            messages.error(request, '投资金额与持有数量为必填项。')
        else:
            try:
                amount = Decimal(investment_amount)
                quantity = Decimal(holding_quantity)
                if amount <= 0 and quantity <= 0:
                    messages.error(request, '投资金额或持有数量至少一项大于 0。')
                else:
                    Investment.objects.create(
                        user=member,
                        investment_date=timezone.now(),
                        investment_amount=amount,
                        holding_quantity=quantity,
                    )
                    record_audit(
                        request,
                        action='management:headman_add_investment',
                        after={
                            '成员': member.username,
                            '姓名': profile.name if profile else '—',
                            '投资金额 (USDT)': str(amount),
                            '持有数量 (GDT)': str(int(quantity.to_integral_value())),
                        },
                    )
                    messages.success(
                        request,
                        f'已为 {member.username} 追加投资 {amount} USDT。',
                    )
                    return redirect('management:headman_member_list')
            except (InvalidOperation, ValueError):
                messages.error(request, '投资金额或持币数量格式无效。')

    return render(request, 'management/headman/add_member_investment.html', {
        'members': members,
        'selected_member': selected_member,
        'gdt_price': SystemConfig.get_gdt_price(),
    })


# ── Member ─────────────────────────────────────────────────────────

@member_required
def member_dashboard(request):
    investments = Investment.objects.filter(user=request.user)
    gdt_price = SystemConfig.get_gdt_price()
    total_market_value = sum((i.current_market_value for i in investments), Decimal('0'))
    referrer_profile = None
    if request.user.referrer and hasattr(request.user.referrer, 'profile'):
        referrer_profile = request.user.referrer.profile
    return render(request, 'management/member/dashboard.html', {
        'investment_count': investments.count(),
        'gdt_price': gdt_price,
        'total_market_value': total_market_value,
        'referrer_profile': referrer_profile,
    })


@member_required
def member_investments(request):
    investments = Investment.objects.filter(user=request.user)
    gdt_price = SystemConfig.get_gdt_price()
    page_obj = _paginate(request, investments)
    return render(request, 'management/member/investments.html', {
        'page_obj': page_obj,
        'investments': page_obj,
        'gdt_price': gdt_price,
    })


@member_required
@require_http_methods(['GET', 'POST'])
def member_profile(request):
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={'name': request.user.username},
    )
    if request.method == 'POST':
        before_profile = profile_snapshot(profile)
        profile.phone = request.POST.get('phone', '').strip()
        profile.wechat = request.POST.get('wechat', '').strip()
        profile.save()
        record_update_audit(
            request,
            before=before_profile,
            after=profile_snapshot(profile),
            action='management:member_profile',
        )
        messages.success(request, '资料已更新。')
        return redirect('management:member_profile')

    return render(
        request,
        'management/member/profile.html',
        {
            'profile': profile,
            **build_settings_context(request.user),
            **build_email_change_context(request),
        },
    )


# ── OAuth 预留 ─────────────────────────────────────────────────────

def oauth_provider_info(request, provider):
    try:
        prov = get_provider(provider)
        redirect_uri = request.GET.get('redirect_uri', '/auth/login/')
        return render(request, 'authentication/oauth_placeholder.html', {
            'provider': prov.provider_name,
            'auth_url': prov.get_authorization_url(redirect_uri),
        })
    except ValueError:
        messages.error(request, '未知的 OAuth 提供商。')
        return redirect('authentication:login')
