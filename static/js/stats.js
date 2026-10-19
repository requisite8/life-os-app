// Статистика и профиль

var weekOffset = 0;

function getWeekRange(offset) {
    var now = new Date(), day = now.getDay(), diffToMonday = (day === 0) ? -6 : 1 - day;
    var monday = new Date(now); monday.setDate(now.getDate() + diffToMonday + offset * 7); monday.setHours(0, 0, 0, 0);
    var sunday = new Date(monday); sunday.setDate(monday.getDate() + 6); sunday.setHours(23, 59, 59, 999);
    return { monday: monday, sunday: sunday };
}

function formatWeekLabel(monday, sunday) {
    var m = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];
    return monday.getDate() + ' ' + m[monday.getMonth()] + ' — ' + sunday.getDate() + ' ' + m[sunday.getMonth()];
}

function showChange(elId, diff, isMinutes) {
    var el = document.getElementById(elId); if (!el) return;
    if (diff === 0) { el.textContent = '—'; el.className = 'stat-change'; return }
    var abs = Math.round(Math.abs(diff)), sign = diff > 0 ? '↑ +' : '↓ -';
    var text = isMinutes ? (abs >= 60 ? Math.round(abs / 60 * 10) / 10 + 'ч' : abs + 'м') : String(abs);
    el.textContent = sign + text; el.className = 'stat-change' + (diff < 0 ? ' down' : '');
}

async function renderStats() {
    if (!await ensureUserReady()) return;
    var range = getWeekRange(weekOffset), monday = range.monday, sunday = range.sunday;
    document.getElementById('weekLabel').textContent = formatWeekLabel(monday, sunday);
    var subText = weekOffset === 0 ? 'текущая неделя' : weekOffset === -1 ? 'прошлая неделя' : Math.abs(weekOffset) + ' нед. назад';
    document.getElementById('weekSub').textContent = subText;
    var nextBtn = document.getElementById('weekNextBtn');
    if (weekOffset === 0) nextBtn.classList.add('disabled'); else nextBtn.classList.remove('disabled');
    try {
        var stats = await apiGet('/api/stats/' + currentUserId + '?week_offset=' + weekOffset);
        var focusMin = stats.curr_focus_min;
        document.getElementById('weekFocus').textContent = focusMin >= 60 ? Math.round(focusMin / 60 * 10) / 10 + 'ч' : focusMin + 'м';
        document.getElementById('weekSessions').textContent = stats.curr_sessions;
        document.getElementById('weekTasks').textContent = stats.curr_tasks_done;
        var activeHabits = habits.filter(function (h) { return isHabitActiveToday(h.frequency, h.weekdays || []) });
        var doneTodayCount = activeHabits.filter(function (h) { return h.doneToday }).length;
        document.getElementById('weekHabits').textContent = activeHabits.length > 0 ? Math.round((doneTodayCount / activeHabits.length) * 100) + '%' : '—';
        showChange('focusChange', stats.focus_diff_min || 0, true);
        showChange('sessionsChange', stats.sessions_diff || 0, false);
        showChange('tasksChange', stats.tasks_diff || 0, false);
        renderFocusBars(monday, stats.focus_by_day);
    } catch (e) { console.error('Ошибка загрузки статистики:', e) }
    renderHabitsProgress(); renderProfile(); renderThemePicker(); updateThemeBtnDots(); renderFontPicker(); loadAlarmOptin();
}

function localDateKey(d) {
    var y = d.getFullYear(), m = d.getMonth() + 1, day = d.getDate();
    return y + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
}

function renderFocusBars(monday, focusByDay) {
    var container = document.getElementById('focusBars'), dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var maxMin = 0;
    for (var i = 0; i < 7; i++) { var d = new Date(monday); d.setDate(monday.getDate() + i); maxMin = Math.max(maxMin, focusByDay[localDateKey(d)] || 0) }
    if (maxMin === 0) maxMin = 60;
    var html = '';
    for (var i = 0; i < 7; i++) {
        var d = new Date(monday); d.setDate(monday.getDate() + i);
        var key = localDateKey(d), minutes = focusByDay[key] || 0;
        var isToday = d.getTime() === today.getTime(), isFuture = d > today;
        var heightPct = minutes > 0 ? Math.max(10, (minutes / maxMin) * 100) : 4;
        var valText = '—'; if (minutes > 0) valText = minutes >= 60 ? Math.round(minutes / 60 * 10) / 10 + 'ч' : minutes + 'м';
        var barClass = 'bar'; if (isToday) barClass += ' is-today'; else if (minutes > 0) barClass += ' has-data';
        html += '<div class="bar-wrap"><div class="bar-val">' + (isFuture ? '' : valText) + '</div><div class="' + barClass + '" style="height:' + heightPct + '%"></div><div class="bar-label">' + dayNames[i] + '</div></div>';
    }
    container.innerHTML = html;
}

function getActiveDaysCount(freq, weekdays) {
    if (weekdays && weekdays.length > 0) return weekdays.length;
    if (!freq || freq === 'Каждый день') return 7;
    if (freq === 'Пн-Пт') return 5;
    if (freq === 'Пн, Ср, Пт') return 3;
    return 7;
}

function renderHabitsProgress() {
    var container = document.getElementById('habitsProgress');
    if (habits.length === 0) { container.innerHTML = '<p style="color:rgba(220,215,240,0.3);font-size:13px;">Нет активных привычек</p>'; return }
    var colors = ['pf-1', 'pf-2', 'pf-3', 'pf-4', 'pf-5'];
    container.innerHTML = habits.map(function (h, i) {
        var activeDays = getActiveDaysCount(h.frequency, h.weekdays || []), doneDays = h.days.filter(Boolean).length;
        var pct = Math.min(100, Math.round((doneDays / activeDays) * 100)), colorClass = colors[i % colors.length];
        return '<div class="habit-progress-row"><span class="habit-progress-name">' + escapeHtml(h.icon) + ' ' + escapeHtml(h.name) + '</span><span class="habit-progress-pct">' + pct + '%</span></div><div class="prog-bar"><div class="prog-fill ' + colorClass + '" style="width:' + pct + '%"></div></div>';
    }).join('');
}

function renderProfile() {
    var avatarEl = document.getElementById('userAvatar');
    if (tgUser) {
        document.getElementById('userName').textContent = tgUser.first_name + (tgUser.last_name ? ' ' + tgUser.last_name : '');
        if (tgUser.photo_url) {
            avatarEl.innerHTML = '<img src="' + escapeHtml(tgUser.photo_url) + '" style="width:100%;height:100%;border-radius:50%;object-fit:cover">';
            avatarEl.style.overflow = 'hidden';
        } else {
            avatarEl.textContent = tgUser.first_name[0].toUpperCase();
        }
    }
    var firstUse = localStorage.getItem('firstUseDate');
    if (!firstUse) { localStorage.setItem('firstUseDate', new Date().toISOString()); document.getElementById('userDays').textContent = 'Life OS · первый день' }
    else { var days = Math.floor((new Date() - new Date(firstUse)) / (1000 * 60 * 60 * 24)) + 1; document.getElementById('userDays').textContent = 'Life OS · ' + days + ' ' + dayWord(days) }
}

function dayWord(n) { if (n % 10 === 1 && n % 100 !== 11) return 'день'; if ([2, 3, 4].includes(n % 10) && ![12, 13, 14].includes(n % 100)) return 'дня'; return 'дней' }
function changeWeek(dir) { if (dir === 1 && weekOffset === 0) return; weekOffset += dir; renderStats() }
