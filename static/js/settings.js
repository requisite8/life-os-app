// Настройки: фон, шрифт, размер букв, будильники

function renderThemePicker() {
    var container = document.getElementById('themePicker');
    if (!container) return;
    var current = localStorage.getItem('bgTheme') || 'midnight';
    var html = '';
    Object.keys(bgThemes).forEach(function (key) {
        var t = bgThemes[key], isActive = key === current;
        html += '<div class="theme-item' + (isActive ? ' active' : '') + '" onclick="pickTheme(\'' + key + '\')">';
        html += '<div class="theme-preview">';
        t.preview.forEach(function (c) { html += '<div class="theme-dot" style="background:' + c + '"></div>' });
        html += '</div>';
        html += '<div class="theme-name">' + escapeHtml(t.name) + '</div>';
        html += '</div>';
    });
    container.innerHTML = html;
    updateThemeBtnDots();
}

function updateThemeBtnDots() {
    var dotsEl = document.getElementById('themeBtnDots');
    if (!dotsEl) return;
    var current = localStorage.getItem('bgTheme') || 'midnight';
    var theme = bgThemes[current] || bgThemes.midnight;
    dotsEl.innerHTML = theme.preview.map(function (c) { return '<div class="theme-dot" style="background:' + c + '"></div>' }).join('');
}

function pickTheme(key) {
    applyBgTheme(key);
    renderThemePicker();
}

var appFonts = {
    system: { name: 'Обычный', css: 'Arial,sans-serif' },
    rounded: { name: 'Круглый', css: "'Trebuchet MS',Verdana,sans-serif" },
    classic: { name: 'Классический', css: "Georgia,'Times New Roman',serif" },
    mono: { name: 'Моно', css: "'Courier New',monospace" }
};

function applyFont(key) {
    if (!appFonts[key]) key = 'system';
    document.documentElement.style.setProperty('--app-font', appFonts[key].css);
    localStorage.setItem('appFont', key);
}

function renderFontPicker() {
    var container = document.getElementById('fontPicker');
    if (!container) return;
    var current = localStorage.getItem('appFont') || 'system';
    var html = '';
    Object.keys(appFonts).forEach(function (key) {
        var isActive = key === current;
        html += '<div class="freq-btn' + (isActive ? ' active' : '') + '" onclick="pickFont(\'' + key + '\')" style="font-family:' + appFonts[key].css + '">' + appFonts[key].name + '</div>';
    });
    container.innerHTML = html;
}

function pickFont(key) {
    applyFont(key);
    renderFontPicker();
}

function setFontScale(value) {
    document.documentElement.style.setProperty('--app-font-scale', value / 100);
    document.getElementById('fontSizeVal').textContent = value + '%';
    localStorage.setItem('appFontScale', value);
}

async function setAlarmOptin(checked) {
    if (!currentUserId) await ensureUserReady();
    if (!currentUserId) return;
    try { await apiPatch('/api/users/' + currentUserId + '/settings', { alarm_optin: checked }); }
    catch (e) { console.error('Ошибка сохранения настройки будильника:', e); }
}

async function loadAlarmOptin() {
    if (!currentUserId) return;
    var toggle = document.getElementById('alarmOptinToggle');
    if (!toggle) return;
    try {
        var data = await apiGet('/api/users/' + currentUserId + '/settings');
        toggle.checked = data.alarm_optin === 1;
    } catch (e) { console.error('Ошибка загрузки настройки будильника:', e); }
}

applyFont(localStorage.getItem('appFont') || 'system');
(function () {
    var savedFontScale = localStorage.getItem('appFontScale') || 100;
    document.documentElement.style.setProperty('--app-font-scale', savedFontScale / 100);
    document.addEventListener('DOMContentLoaded', function () {
        var sizeRange = document.getElementById('fontSizeRange'), sizeVal = document.getElementById('fontSizeVal');
        if (sizeRange) { sizeRange.value = savedFontScale }
        if (sizeVal) { sizeVal.textContent = savedFontScale + '%' }
    });
})();
