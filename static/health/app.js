// let и contst не мен и мен
// window спец оюъект который привязывает браузер с кодом
const tg = window.Telegram?.WebApp;
tg?.ready() //оворит Telegram "приложение загрузилось, покажи его
tg?.expand() //растянуть на весь экран, а не показывать в маленьком виде снизу.
const tgUser = tg?.initDataUnsafe?.user || null
const TEST_TELEGRAM_ID = 999000111;

const STEP_GOAL = 10000;
let currentUserId = null

async function apiPost(path, data) {
    const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }, // отпровляет браузеру json чтобы прочитал
        body: JSON.stringify(data),
    });
    return res.json();
}
async function apiGet(path) {
    const res = await fetch(path);
    return res.json();
}


async function initUser() {
    const user = await apiPost('/api/users', {
        telegram_id: tgUser?.id || TEST_TELEGRAM_ID,
        first_name: tgUser?.first_name || "Тестовый пользователь",
        username: tgUser?.username || null,
    });
    currentUserId = user.id;
}



function renderSteps(steps) {
    const percent = Math.round((steps / STEP_GOAL) * 100);
    const remaining = Math.max(0, STEP_GOAL - steps);

    document.getElementById('stepsValue').textContent = steps.toLocaleString('ru-RU');
    document.getElementById('stepsPercent').textContent = percent + '%';
    document.getElementById('stepsSub').textContent = remaining > 0
        ? `осталось ${remaining.toLocaleString('ru-RU')} до цели · ${STEP_GOAL.toLocaleString('ru-RU')}`
        : `цель достигнута · ${STEP_GOAL.toLocaleString('ru-RU')}`;
}

async function loadSteps(){
    const data = await apiGet('/api/health/steps/' + currentUserId);
    renderSteps(data.steps);
}

(async function start(){
    await initUser();
    await loadSteps();
    await loadNutrition();
})();

/* ================================================================
   НИЖЕ — код для вкладок Питание/Тренировки/Статистика.
   Добавлено автоматически, код шагов выше не трогали.
   ================================================================ */

const CALORIE_GOAL = 2500;

function escapeHtml(str){
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML;
}

function showHealthTab(name, btn){
    document.querySelectorAll('.health-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
    if(name === 'nutrition') loadNutrition();
    if(name === 'workouts') loadWorkouts();
    if(name === 'stats') loadStats();
}

function renderNutrition(data){
    const percent = Math.round((data.calories / CALORIE_GOAL) * 100);
    const remaining = Math.max(0, CALORIE_GOAL - data.calories);

    ['nutritionValue', 'nutritionValue2'].forEach(id => {
        document.getElementById(id).textContent = data.calories;
    });
    ['nutritionPercent', 'nutritionPercent2'].forEach(id => {
        document.getElementById(id).textContent = percent + '%';
    });
    ['nutritionSub', 'nutritionSub2'].forEach(id => {
        document.getElementById(id).textContent = `из ${CALORIE_GOAL} ккал · осталось ${remaining}`;
    });

    document.getElementById('macroProtein').textContent = data.protein + 'г';
    document.getElementById('macroFat').textContent = data.fat + 'г';
    document.getElementById('macroCarbs').textContent = data.carbs + 'г';
}

async function loadNutrition(){
    const summary = await apiGet('/api/health/nutrition/' + currentUserId);
    renderNutrition(summary);

    const meals = await apiGet('/api/health/meals/' + currentUserId);
    const listEl = document.getElementById('mealsList');
    if(!listEl) return;
    if(meals.length === 0){
        listEl.innerHTML = '<div class="empty-hint">Пока ничего не записано</div>';
        return;
    }
    listEl.innerHTML = meals.map(m => `
        <div class="entry-item">
            <div>
                <div class="entry-name">${escapeHtml(m.description)}</div>
                <div class="entry-sub">Б${m.protein} Ж${m.fat} У${m.carbs}</div>
            </div>
            <div class="entry-val">${m.calories} ккал</div>
        </div>
    `).join('');
}

async function loadWorkouts(){
    const workouts = await apiGet('/api/health/workouts/' + currentUserId);
    const listEl = document.getElementById('workoutsList');
    if(!listEl) return;
    if(workouts.length === 0){
        listEl.innerHTML = '<div class="empty-hint">Пока ничего не записано</div>';
        return;
    }
    listEl.innerHTML = workouts.map(w => `
        <div class="entry-item">
            <div>
                <div class="entry-name">${escapeHtml(w.type)}</div>
                <div class="entry-sub">${escapeHtml(w.description || '')}</div>
            </div>
            <div class="entry-val">${w.duration_min} мин</div>
        </div>
    `).join('');
}

function renderBarChart(containerId, points, valueKey, maxHint){
    const container = document.getElementById(containerId);
    if(!container) return;
    const max = Math.max(maxHint, ...points.map(p => p[valueKey]));
    const dayNames = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];

    container.innerHTML = points.map(p => {
        const value = p[valueKey];
        const heightPct = max > 0 ? Math.max(3, Math.round((value / max) * 100)) : 3;
        const dayLabel = dayNames[new Date(p.date).getDay()];
        return `
            <div class="stats-bar-wrap">
                <div class="stats-bar" style="height:${heightPct}%"></div>
                <div class="stats-bar-label">${dayLabel}</div>
            </div>
        `;
    }).join('');
}

async function loadStats(){
    const points = await apiGet('/api/health/stats/' + currentUserId + '?days=7');
    renderBarChart('stepsChart', points, 'steps', STEP_GOAL);
    renderBarChart('caloriesChart', points, 'calories', CALORIE_GOAL);
}