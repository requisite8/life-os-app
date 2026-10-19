// Привычки

function toggleHabitWeekday(el) {
    var day = parseInt(el.dataset.day, 10);
    if (Number.isNaN(day)) return;
    if (selectedHabitWeekdays.includes(day)) {
        selectedHabitWeekdays = selectedHabitWeekdays.filter(function (x) { return x !== day });
        el.classList.remove('active');
    } else {
        selectedHabitWeekdays.push(day);
        selectedHabitWeekdays.sort();
        el.classList.add('active');
    }
    if (selectedHabitWeekdays.length > 0) {
        document.querySelectorAll('#modalHabit .freq-btns:not(#habitWeekdays) .freq-btn').forEach(function (b) { b.classList.remove('active') });
        selectedFreq = '';
    }
}

function weekdaysLabel(days) {
    if (!days || !days.length) return '';
    var names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    return ' · ' + days.map(function (d) { return names[d] || '' }).filter(Boolean).join(', ');
}

async function loadHabits() {
    if (!currentUserId) return;
    try { habits = await apiGet('/api/habits/' + currentUserId); renderHabits() } catch (e) { console.error('Ошибка загрузки привычек:', e) }
}

async function saveHabit() {
    if (!await ensureUserReady()) { alert('Пользователь ещё не инициализирован.'); return }
    var name = document.getElementById('habitName').value.trim(); if (!name) return;
    var reminderTime = (document.getElementById('habitReminderTime')?.value || '').trim() || null;
    var freq = selectedFreq;
    if (selectedHabitWeekdays.length > 0) {
        var dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        freq = selectedHabitWeekdays.map(function (d) { return dayNames[d] || '' }).filter(Boolean).join(', ');
    }
    if (!freq) freq = 'Каждый день';
    try {
        if (editingHabitId) {
            await apiPatch('/api/habits/' + editingHabitId, { name: name, icon: selectedEmoji, frequency: freq, reminder_time: reminderTime, weekdays: selectedHabitWeekdays });
            await loadHabits();
        } else {
            await apiPost('/api/habits', { user_id: currentUserId, name: name, icon: selectedEmoji, frequency: freq, reminder_time: reminderTime, weekdays: selectedHabitWeekdays });
            await loadHabits();
        }
        closeModal('modalHabit');
        document.getElementById('habitName').value = '';
        if (document.getElementById('habitReminderTime')) document.getElementById('habitReminderTime').value = '';
        selectedHabitWeekdays = [];
        editingHabitId = null;
    } catch (e) { console.error('Ошибка сохранения привычки:', e); alert('Не удалось добавить привычку') }
}

function isHabitActiveToday(freq, weekdays) {
    var dow = (new Date().getDay() + 6) % 7;
    if (weekdays && weekdays.length > 0) return weekdays.includes(dow);
    if (!freq || freq === 'Каждый день') return true;
    if (freq === 'Пн-Пт') return dow <= 4;
    if (freq === 'Пн, Ср, Пт') return dow === 0 || dow === 2 || dow === 4;
    return true;
}

function renderHabits() {
    var list = document.getElementById('habits-list');
    if (habits.length === 0) { list.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-text">Нет привычек</div><div class="empty-sub">Нажми + чтобы добавить первую</div></div>'; return }
    var dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'], todayIdx = (new Date().getDay() + 6) % 7;
    list.innerHTML = habits.map(function (h) {
        var active = isHabitActiveToday(h.frequency, h.weekdays || []);
        var reminderText = h.reminder_time ? (' · ⏰ ' + h.reminder_time) : '';
        var weekDaysText = weekdaysLabel(h.weekdays || []);
        var dots = h.days.map(function (done, i) { return '<div class="day-dot ' + (i === todayIdx ? 'today' : done ? 'done' : '') + '"></div>' }).join('');
        var labels = dayNames.map(function (d) { return '<div class="day-label">' + d + '</div>' }).join('');
        return '<div class="habit-card' + (active ? '' : ' habit-inactive') + '"><div class="habit-top"><div class="habit-left"><span class="habit-icon">' + escapeHtml(h.icon) + '</span><div><div class="habit-name">' + escapeHtml(h.name) + '</div><div class="habit-freq">' + escapeHtml(h.frequency) + weekDaysText + reminderText + (active ? '' : ' · выходной') + '</div></div></div><div class="habit-right"><span class="habit-streak">🔥 ' + h.streak + '</span>' + (active ? '<div class="check-circle ' + (h.doneToday ? 'done' : '') + '" onclick="toggleHabit(' + h.id + ')">' + (h.doneToday ? '✓' : '') + '</div>' : '') + '<button class="habit-del-btn" onclick="editHabitClick(event,' + h.id + ')">Изм</button><button class="habit-del-btn" onclick="deleteHabitClick(event,' + h.id + ')">✕</button></div></div><div class="days-row">' + dots + '</div><div class="days-labels">' + labels + '</div></div>';
    }).join('');
}

function editHabitClick(e, id) {
    e.stopPropagation();
    var h = habits.find(function (x) { return x.id === id });
    if (!h) return;
    openModal('modalHabit');
    editingHabitId = id;
    var title = document.querySelector('#modalHabit .modal-title');
    if (title) title.textContent = 'Редактировать привычку';
    document.getElementById('habitName').value = h.name || '';
    if (document.getElementById('habitReminderTime')) document.getElementById('habitReminderTime').value = h.reminder_time || '';
    selectedEmoji = h.icon || '✅';
    selectedFreq = h.frequency || 'Каждый день';
    selectedHabitWeekdays = (h.weekdays || []).slice();
    document.querySelectorAll('#modalHabit .emoji-btn').forEach(function (b) { b.classList.toggle('active', b.textContent === selectedEmoji) });
    document.querySelectorAll('#modalHabit .freq-btns .freq-btn').forEach(function (b) {
        if (b.closest('#habitWeekdays')) return;
        b.classList.toggle('active', b.textContent.trim() === selectedFreq);
    });
    document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function (b) {
        var day = parseInt(b.dataset.day, 10);
        b.classList.toggle('active', selectedHabitWeekdays.includes(day));
    });
}

async function deleteHabitClick(e, id) { e.stopPropagation(); if (!confirm('Удалить привычку?')) return; try { await apiDelete('/api/habits/' + id); habits = habits.filter(function (h) { return h.id !== id }); renderHabits() } catch (e) { console.error('Ошибка удаления привычки:', e) } }

async function toggleHabit(id) {
    if (!await ensureUserReady()) { alert('Пользователь ещё не инициализирован.'); return }
    var today = new Date().toISOString().split('T')[0];
    try {
        var result = await apiPost('/api/habits/toggle', { habit_id: id, user_id: currentUserId, date: today });
        var h = habits.find(function (h) { return h.id === id });
        if (h) { h.doneToday = result.done; h.streak = result.streak; h.days[(new Date().getDay() + 6) % 7] = result.done }
        renderHabits();
    } catch (e) { console.error('Ошибка обновления привычки:', e); alert('Не удалось обновить привычку') }
}
