// Ядро: Telegram WebApp, API-запросы, инициализация пользователя

const tg = window.Telegram?.WebApp;
if (tg?.ready) tg.ready();
if (tg?.expand) tg.expand();

(function fixMobileKeyboard() {
    var vv = window.visualViewport;
    if (!vv) return;
    function onResize() {
        var h = vv.height;
        document.documentElement.style.setProperty('--vv-h', h + 'px');
        document.querySelectorAll('.modal-overlay:not(.hidden) .modal').forEach(function (m) {
            m.style.maxHeight = (h * 0.85) + 'px';
        });
    }
    vv.addEventListener('resize', onResize);
})();

let currentUserId = null;
let initUserPromise = null;
const tgUser = tg?.initDataUnsafe?.user || null;
let habits = [];
let tasks = [];
const API_BASE = window.location.origin;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}

async function apiGet(path) {
    var r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiPost(path, data) {
    var r = await fetch(API_BASE + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiPatch(path, data) {
    var r = await fetch(API_BASE + path, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiDelete(path) {
    var r = await fetch(API_BASE + path, { method: 'DELETE' });
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}

async function getApiErrorMessage(response, fallback) {
    try {
        var contentType = response.headers.get('Content-Type') || '';
        if (contentType.includes('application/json')) {
            var data = await response.json();
            return data.detail || data.error || data.message || fallback;
        }
        var text = (await response.text()).trim();
        return text || fallback;
    } catch (e) {
        return fallback;
    }
}

async function initUser() {
    if (currentUserId) return currentUserId;
    if (initUserPromise) return initUserPromise;
    initUserPromise = (async function () {
        try {
            var savedGuestId = !tgUser?.id ? parseInt(localStorage.getItem('guestUserId') || '', 10) : NaN;
            if (Number.isFinite(savedGuestId)) {
                currentUserId = savedGuestId;
            } else {
                var user = await apiPost('/api/users', { telegram_id: tgUser?.id || 0, first_name: tgUser?.first_name || 'Пользователь', username: tgUser?.username || null });
                currentUserId = user.id;
                if (!tgUser?.id) { try { localStorage.setItem('guestUserId', String(currentUserId)) } catch (e) { } }
            }
            await Promise.all([
                loadFocusStats().catch(function (e) { console.error('loadFocusStats:', e) }),
                loadHabits().catch(function (e) { console.error('loadHabits:', e) }),
                loadTasks().catch(function (e) { console.error('loadTasks:', e) })
            ]);
            renderProfile();
            return currentUserId;
        } catch (e) { console.error('Ошибка инициализации:', e); return null; }
        finally { initUserPromise = null; }
    })();
    return initUserPromise;
}

async function ensureUserReady() {
    if (currentUserId) return true;
    await initUser();
    return currentUserId !== null;
}
