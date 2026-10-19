// Фокус-таймер, категории и сохранение сессий

let running = false, paused = false, isStopwatch = true, totalSec = 0, elapsed = 0, interval = null;
let segmentStart = 0, accumulatedMs = 0;
const FOCUS_STATE_KEY = 'focusTimerState';
let focusCategory = localStorage.getItem('focusCategory') || '💼 Deep Work';

function updateFocusStatsUI(sessions, totalMin, streak) {
    sessions = sessions || 0; totalMin = totalMin || 0; streak = streak || 0;
    document.getElementById('stat-sessions').textContent = sessions;
    if (totalMin >= 60) { document.getElementById('stat-time').textContent = Math.floor(totalMin / 60) + 'ч ' + totalMin % 60 + 'м' }
    else { document.getElementById('stat-time').textContent = totalMin + 'м' }
    document.getElementById('stat-streak').textContent = '🔥 ' + streak;
}

async function loadFocusStats() {
    if (!currentUserId) return;
    try { var d = await apiGet('/api/focus/' + currentUserId + '?t=' + Date.now()); updateFocusStatsUI(d.today_sessions || 0, d.today_min || 0, d.streak || 0) }
    catch (e) { console.error('Ошибка загрузки статистики фокуса:', e) }
}
updateFocusStatsUI(0, 0, 0);

var defaultCategories = [{ name: 'Deep Work', emoji: '💼' }, { name: 'Креатив', emoji: '🎨' }, { name: 'Учёба', emoji: '📚' }, { name: 'Чтение', emoji: '📖' }, { name: 'Тренировка', emoji: '🏋️' }, { name: 'Другое', emoji: '✨' }];

function getSavedCategories() { try { var s = localStorage.getItem('categories'); if (s) return JSON.parse(s) } catch (e) { } return defaultCategories.slice() }
function saveCategories(list) { localStorage.setItem('categories', JSON.stringify(list)) }
function toggleCategory(e) { if (e) e.stopPropagation(); openCategoryPanel() }

function openCategoryPanel() {
    renderCategoryPanel();
    document.getElementById('categoryOverlay').classList.add('open');
    document.querySelector('.content').classList.add('scroll-locked');
    document.getElementById('categoryPanelSearch').value = '';
}
function closeCategoryPanel() {
    document.getElementById('categoryOverlay').classList.remove('open');
    document.querySelector('.content').classList.remove('scroll-locked');
}

function renderCategoryPanel(filter) {
    var cats = getSavedCategories(), q = (filter || '').toLowerCase(), listEl = document.getElementById('categoryPanelList'), html = '';
    cats.forEach(function (c) {
        if (q && !c.name.toLowerCase().includes(q)) return;
        var full = c.emoji + ' ' + c.name, isActive = focusCategory === full;
        html += '<div class="category-item' + (isActive ? ' active' : '') + '" onclick="pickCategory(\'' + escapeHtml(c.emoji) + '\',\'' + escapeHtml(c.name).replace(/'/g, "\\'") + '\')"><span class="category-name">' + escapeHtml(c.name) + '</span><div class="category-actions"><button class="action-mini danger" onclick="removeCategoryItem(event,\'' + escapeHtml(c.name).replace(/'/g, "\\'") + '\')">✕</button></div></div>';
    });
    if (q) { html += '<div class="category-item" style="cursor:pointer;justify-content:center" onclick="addCategoryFromPanel()"><span class="category-name">+ Добавить «' + escapeHtml(q) + '»</span></div>' }
    listEl.innerHTML = html;
}
function filterCategoryPanel() { renderCategoryPanel(document.getElementById('categoryPanelSearch').value.trim()) }
function pickCategory(emoji, name) { var l = emoji + ' ' + name; focusCategory = l; localStorage.setItem('focusCategory', l); document.getElementById('categoryBtn').textContent = l; closeCategoryPanel() }
function addCategoryFromPanel() { var name = document.getElementById('categoryPanelSearch').value.trim(); if (!name) return; var cats = getSavedCategories(); if (!cats.find(function (c) { return c.name === name })) { cats.push({ name: name, emoji: '✨' }); saveCategories(cats) } pickCategory('✨', name) }
function removeCategoryItem(e, name) { e.stopPropagation(); var cats = getSavedCategories().filter(function (c) { return c.name !== name }); saveCategories(cats); if (focusCategory.endsWith(name) && cats.length > 0) pickCategory(cats[0].emoji, cats[0].name); renderCategoryPanel(document.getElementById('categoryPanelSearch').value.trim()) }
document.getElementById('categoryPanelSearch').addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); if (this.value.trim()) addCategoryFromPanel() } });

function toggleTimeDropdown(e) { e.stopPropagation(); document.getElementById('timeDropdown').classList.toggle('open') }
function setTimeButtonLabel(label) { document.getElementById('timeBtn').childNodes[0].nodeValue = label + ' ' }

function selectMode(sec, label, e) {
    e.stopPropagation();
    if (sec === -1) {
        var input = window.prompt('Сколько минут длится сессия?', '30');
        if (input === null) { document.getElementById('timeDropdown').classList.remove('open'); return }
        var customMinutes = parseInt(input, 10);
        if (!Number.isFinite(customMinutes) || customMinutes <= 0) { alert('Введите количество минут больше 0'); document.getElementById('timeDropdown').classList.remove('open'); return }
        sec = customMinutes * 60; label = customMinutes + ' мин';
    }
    isStopwatch = (sec === 0); totalSec = sec; elapsed = 0;
    setTimeButtonLabel(label + ' ▾');
    document.querySelectorAll('#timeDropdown .dropdown-item').forEach(function (i) { i.classList.remove('active') });
    e.target.closest('.dropdown-item').classList.add('active');
    if (running || paused) resetTimer();
    document.getElementById('timeDropdown').classList.remove('open');
}
document.addEventListener('click', function () { document.getElementById('timeDropdown').classList.remove('open') });

function toggleTimer() { if (!running && !paused) startTimer(); else if (running) pauseTimer(); else resumeTimer() }

function currentElapsedSec() {
    return Math.floor((accumulatedMs + (running ? Date.now() - segmentStart : 0)) / 1000);
}

function persistTimerState() {
    try {
        if (!running && !paused) { localStorage.removeItem(FOCUS_STATE_KEY); return }
        localStorage.setItem(FOCUS_STATE_KEY, JSON.stringify({
            isStopwatch: isStopwatch, totalSec: totalSec, accumulatedMs: accumulatedMs,
            segmentStart: running ? segmentStart : null, category: focusCategory,
            label: document.getElementById('timeBtn').childNodes[0].nodeValue.trim(), heartbeat: Date.now()
        }));
    } catch (e) { }
}

function showTimerRunningUI() {
    document.getElementById('trackArc').setAttribute('opacity', '1');
    document.getElementById('progressArc').setAttribute('opacity', '1');
    document.getElementById('spinG').setAttribute('opacity', '1');
    document.getElementById('startLabel').classList.add('hidden');
    document.getElementById('timerNum').classList.remove('hidden');
    document.getElementById('resetBtn').classList.remove('hidden');
}

function startTimer() {
    accumulatedMs = 0; elapsed = 0;
    running = true; paused = false;
    segmentStart = Date.now();
    showTimerRunningUI();
    document.getElementById('spinG').classList.remove('paused');
    document.getElementById('circleHint').textContent = 'нажми для паузы';
    document.getElementById('modeBadge').textContent = '🔵 Идёт сессия';
    document.getElementById('timerNum').textContent = isStopwatch ? fmt(elapsed) : fmt(totalSec - elapsed);
    interval = setInterval(tick, 1000);
    persistTimerState();
}

function finishCountdown() {
    clearInterval(interval); interval = null;
    running = false; paused = false;
    elapsed = totalSec; accumulatedMs = 0;
    document.getElementById('modeBadge').textContent = '✅ Сессия завершена!';
    document.getElementById('spinG').classList.add('paused');
    document.getElementById('circleHint').textContent = 'отличная работа!';
    document.getElementById('timerNum').textContent = fmt(0);
    document.getElementById('progressArc').setAttribute('stroke-dashoffset', '0');
    persistTimerState();
    saveFocusAndReload(totalSec);
}

function tick() {
    elapsed = currentElapsedSec();
    if (isStopwatch) { document.getElementById('timerNum').textContent = fmt(elapsed) }
    else {
        if (totalSec - elapsed <= 0) { finishCountdown(); return }
        document.getElementById('timerNum').textContent = fmt(totalSec - elapsed);
        document.getElementById('progressArc').setAttribute('stroke-dashoffset', 603 - (603 * (elapsed / totalSec)));
    }
    if (elapsed % 5 === 0) persistTimerState();
}

async function saveFocusAndReload(durationSec) {
    var durationMin = Math.round(durationSec / 60);
    if (durationMin < 1) return;
    try { if (!currentUserId) await initUser(); if (!currentUserId) return; await apiPost('/api/focus', { user_id: currentUserId, duration_min: durationMin, category: focusCategory }) } catch (e) { console.error('Ошибка сохранения сессии:', e) }
    try { var d = await apiGet('/api/focus/' + currentUserId + '?t=' + Date.now()); updateFocusStatsUI(d.today_sessions || 0, d.today_min || 0, d.streak || 0) } catch (e) { console.error('Ошибка загрузки статистики:', e) }
}

function pauseTimer() {
    if (!running) return;
    accumulatedMs += Date.now() - segmentStart; elapsed = Math.floor(accumulatedMs / 1000);
    running = false; paused = true; clearInterval(interval); interval = null;
    document.getElementById('spinG').classList.add('paused'); document.getElementById('circleHint').textContent = 'нажми чтобы продолжить'; document.getElementById('modeBadge').textContent = '⏸ Пауза';
    persistTimerState();
}
function resumeTimer() {
    segmentStart = Date.now(); running = true; paused = false;
    document.getElementById('spinG').classList.remove('paused'); document.getElementById('circleHint').textContent = 'нажми для паузы'; document.getElementById('modeBadge').textContent = '🔵 Идёт сессия';
    interval = setInterval(tick, 1000);
    persistTimerState();
}

function resetTimer() {
    clearInterval(interval); interval = null;
    var doneSec = (running || paused) ? currentElapsedSec() : 0;
    if (doneSec >= 60) saveFocusAndReload(doneSec);
    running = false; paused = false; elapsed = 0; accumulatedMs = 0;
    persistTimerState();
    document.getElementById('trackArc').setAttribute('opacity', '0');
    document.getElementById('progressArc').setAttribute('opacity', '0');
    document.getElementById('spinG').setAttribute('opacity', '0');
    document.getElementById('spinG').classList.add('paused');
    document.getElementById('startLabel').classList.remove('hidden');
    document.getElementById('timerNum').classList.add('hidden');
    document.getElementById('resetBtn').classList.add('hidden');
    document.getElementById('timerNum').textContent = '00:00';
    document.getElementById('circleHint').textContent = 'нажми чтобы начать';
    document.getElementById('modeBadge').textContent = 'выбери режим и нажми';
    document.getElementById('progressArc').setAttribute('stroke-dashoffset', '603');
}

function fmt(s) { return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0') }

function restoreTimerState() {
    var s = null;
    try { s = JSON.parse(localStorage.getItem(FOCUS_STATE_KEY) || 'null') } catch (e) { s = null }
    try { localStorage.removeItem(FOCUS_STATE_KEY) } catch (e) { }
    if (!s) return;

    isStopwatch = !!s.isStopwatch; totalSec = s.totalSec || 0;
    if (s.category) { focusCategory = s.category; document.getElementById('categoryBtn').textContent = focusCategory }
    if (s.label) setTimeButtonLabel(s.label);

    var accumulated = s.accumulatedMs || 0;
    if (!s.segmentStart) {
        // таймер стоял на паузе — восстанавливаем паузу
        accumulatedMs = accumulated; elapsed = Math.floor(accumulated / 1000);
        running = false; paused = true;
        showTimerRunningUI();
        document.getElementById('spinG').classList.add('paused');
        document.getElementById('circleHint').textContent = 'нажми чтобы продолжить';
        document.getElementById('modeBadge').textContent = '⏸ Пауза';
        document.getElementById('timerNum').textContent = isStopwatch ? fmt(elapsed) : fmt(Math.max(0, totalSec - elapsed));
        if (!isStopwatch && totalSec > 0) document.getElementById('progressArc').setAttribute('stroke-dashoffset', 603 - (603 * (elapsed / totalSec)));
        persistTimerState();
        return;
    }

    if (isStopwatch) {
        // секундомер: страницу закрыли — считаем время до последней отметки и сохраняем
        var sec = Math.floor((accumulated + Math.max(0, (s.heartbeat || s.segmentStart) - s.segmentStart)) / 1000);
        if (sec >= 60) saveFocusAndReload(sec);
        return;
    }

    // обратный отсчёт: считаем по реальному времени, продолжаем или завершаем
    accumulatedMs = accumulated; segmentStart = s.segmentStart; running = true; paused = false;
    showTimerRunningUI();
    document.getElementById('spinG').classList.remove('paused');
    document.getElementById('circleHint').textContent = 'нажми для паузы';
    document.getElementById('modeBadge').textContent = '🔵 Идёт сессия';
    interval = setInterval(tick, 1000);
    tick();
}

document.addEventListener('visibilitychange', function () {
    if (document.hidden) persistTimerState();
    else if (running) tick();
});
window.addEventListener('pagehide', persistTimerState);
restoreTimerState();
