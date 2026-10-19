// Задачи

async function loadTasks() {
    if (!currentUserId) return;
    try { tasks = await apiGet('/api/tasks/' + currentUserId); renderTasks() } catch (e) { console.error('Ошибка загрузки задач:', e) }
}

async function saveTask() {
    if (!await ensureUserReady()) { alert('Пользователь ещё не инициализирован.'); return }
    var name = document.getElementById('taskName').value.trim(); if (!name) return;
    try {
        var t = await apiPost('/api/tasks', { user_id: currentUserId, name: name, section: selectedSection, priority: selectedPriority, deadline: document.getElementById('taskDeadline').value || null, from_ai: false });
        tasks.unshift(t); renderTasks(); closeModal('modalTask'); document.getElementById('taskName').value = ''; document.getElementById('taskDeadline').value = '';
    } catch (e) { console.error('Ошибка сохранения задачи:', e); alert('Не удалось добавить задачу') }
}

function renderTasks() {
    var workList = document.getElementById('tasks-work'), lifeList = document.getElementById('tasks-life'), empty = document.getElementById('tasks-empty');
    var workTasks = tasks.filter(function (t) { return t.section === 'work' }), lifeTasks = tasks.filter(function (t) { return t.section === 'life' });
    if (tasks.length === 0) empty.classList.remove('hidden'); else empty.classList.add('hidden');
    workList.innerHTML = renderTaskList(workTasks); lifeList.innerHTML = renderTaskList(lifeTasks);
}

function renderTaskList(list) {
    if (list.length === 0) return '';
    return list.map(function (t) {
        var pClass = t.priority === 'high' ? 'p-high' : t.priority === 'low' ? 'p-low' : 'p-mid';
        var dl = 'Без дедлайна';
        if (t.deadline) { var d = new Date(t.deadline); dl = '⏰ ' + d.toLocaleDateString('ru', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) }
        return '<div class="task-card ' + (t.done ? 'done-t' : '') + '" onclick="toggleTask(' + t.id + ')"><div class="checkbox ' + (t.done ? 'checked' : '') + '">' + (t.done ? '✓' : '') + '</div><div class="task-info"><div class="task-top"><span class="task-title">' + escapeHtml(t.name) + '</span>' + (t.from_ai ? '<span class="task-ai">🤖</span>' : '') + '</div><div class="task-meta"><div class="priority ' + pClass + '"></div><span class="task-deadline">' + escapeHtml(dl) + '</span></div></div><button class="task-del-btn" onclick="deleteTaskClick(event,' + t.id + ')">✕</button></div>';
    }).join('');
}

async function deleteTaskClick(e, id) { e.stopPropagation(); if (!confirm('Удалить задачу?')) return; try { await apiDelete('/api/tasks/' + id); tasks = tasks.filter(function (t) { return t.id !== id }); renderTasks() } catch (e) { console.error('Ошибка удаления задачи:', e) } }

async function toggleTask(id) {
    var task = tasks.find(function (t) { return t.id === id }); if (!task) return;
    try { await apiPatch('/api/tasks/' + id, { done: !task.done }); task.done = !task.done; task.done_at = task.done ? new Date().toISOString() : null; renderTasks() }
    catch (e) { console.error('Ошибка обновления задачи:', e) }
}
