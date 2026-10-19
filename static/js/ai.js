// Вкладка ИИ: чат, разбор ответов и сохранение найденного

function appendMsg(role, html) {
    var area = document.getElementById('chatArea'), div = document.createElement('div');
    if (role === 'user') { div.className = 'msg-user'; div.innerHTML = '<div class="msg-user-bubble">' + html + '</div>' }
    else { div.className = 'msg-ai'; div.innerHTML = '<div class="ai-avatar-sm">R</div><div class="msg-ai-bubble">' + html + '</div>' }
    area.appendChild(div); area.scrollTop = area.scrollHeight; return div;
}

function showTyping() { var area = document.getElementById('chatArea'), div = document.createElement('div'); div.className = 'typing-indicator'; div.id = 'typingIndicator'; div.innerHTML = '<div class="ai-avatar-sm">R</div><div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>'; area.appendChild(div); area.scrollTop = area.scrollHeight }
function hideTyping() { var el = document.getElementById('typingIndicator'); if (el) el.remove() }

// =============================================
// ===== AI ВКЛАДКА =====
// =============================================

let chatHistory = [];
window._pendingAIItems = window._pendingAIItems || {};

function aiEscape(v) {
    return String(v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}

function parseAIResponse(text) {
    var taskMatch = text.match(/<tasks>([\s\S]*?)<\/tasks>/i);
    var habitMatch = text.match(/<habits>([\s\S]*?)<\/habits>/i);
    var doneMatch = text.match(/<done>([\s\S]*?)<\/done>/i);

    var cleanText = text
        .replace(/<tasks>[\s\S]*?<\/tasks>/ig, '')
        .replace(/<habits>[\s\S]*?<\/habits>/ig, '')
        .replace(/<done>[\s\S]*?<\/done>/ig, '')
        .replace(/<meal>[\s\S]*?<\/meal>/ig, '')
        .replace(/<workout>[\s\S]*?<\/workout>/ig, '')
        .trim();

    var parsedTasks = [];
    var parsedHabits = [];
    var parsedDone = [];

    if (taskMatch) {
        try { parsedTasks = JSON.parse(taskMatch[1].trim()) || []; } catch (e) { parsedTasks = []; }
    }
    if (habitMatch) {
        try { parsedHabits = JSON.parse(habitMatch[1].trim()) || []; } catch (e) { parsedHabits = []; }
    }
    if (doneMatch) {
        try { parsedDone = JSON.parse(doneMatch[1].trim()) || []; } catch (e) { parsedDone = []; }
    }

    return { cleanText: cleanText, tasks: parsedTasks, habits: parsedHabits, done: parsedDone };
}

function findDoneMatch(item) {
    var name = String(item.name || '').trim().toLowerCase();
    if (!name) return null;
    if (item.type === 'habit') {
        return habits.find(function (h) { return !h.doneToday && h.name.toLowerCase().indexOf(name) !== -1; }) || null;
    }
    if (item.type === 'task') {
        return tasks.find(function (t) { return !t.done && t.name.toLowerCase().indexOf(name) !== -1; }) || null;
    }
    return null;
}

function formatReminderTime(isoDate) {
    if (!isoDate) return '';
    var d = new Date(isoDate);
    if (Number.isNaN(d.getTime())) return String(isoDate);
    return d.toLocaleString('ru', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function renderAIActions(msgId, tasks, habits, done) {
    var tHtml = (tasks || []).map(function (t) {
        return '<div class="action-item">📋 ' + aiEscape(t.name || 'Без названия') +
            '<span class="action-item-time">' + (t.deadline ? aiEscape(formatReminderTime(t.deadline)) : 'без дедлайна') + '</span></div>';
    }).join('');

    var hHtml = (habits || []).map(function (h) {
        var time = h.reminder_time ? (' · ⏰ ' + aiEscape(h.reminder_time)) : '';
        var freq = h.frequency ? (' · ' + aiEscape(h.frequency)) : '';
        return '<div class="action-item">✅ ' + aiEscape(h.name || 'Без названия') +
            '<span class="action-item-time">' + freq + time + '</span></div>';
    }).join('');

    var dHtml = (done || []).map(function (d) {
        var match = findDoneMatch(d);
        var status = match ? '' : ' · не найдено';
        return '<div class="action-item">☑️ ' + aiEscape(d.name || 'Без названия') +
            '<span class="action-item-time">' + (d.type === 'habit' ? 'привычка' : 'задача') + status + '</span></div>';
    }).join('');

    var parts = [];
    if ((tasks || []).length) parts.push('задач ' + tasks.length);
    if ((habits || []).length) parts.push('привычек ' + habits.length);
    if ((done || []).length) parts.push('выполнено ' + done.length);

    return '<div class="action-card">' +
        '<div class="action-card-title">Найдено: ' + parts.join(', ') + '</div>' +
        tHtml + hHtml + dHtml +
        '<div class="action-btns">' +
        '<div class="action-btn" onclick="saveAIItems(\'' + msgId + '\')">✓ Сохранить</div>' +
        '<div class="action-btn secondary" onclick="dismissAIItems(\'' + msgId + '\')">✕ Отклонить</div>' +
        '</div></div>';
}

async function sendMessage() {
    var input = document.getElementById('aiInput');
    var text = (input?.value || '').trim();
    if (!text) return;

    appendMsg('user', aiEscape(text));
    input.value = '';
    autoResize(input);
    showTyping();

    try {
        if (!currentUserId) await initUser();
        var data = await apiPost('/api/ai/chat', { user_id: currentUserId, message: text, history: chatHistory });
        hideTyping();

        var fullText = String(data.reply || '').trim();
        var parsed = parseAIResponse(fullText);

        chatHistory.push({ role: 'user', content: text });
        chatHistory.push({ role: 'assistant', content: fullText });

        var hasActions = (parsed.tasks && parsed.tasks.length) || (parsed.habits && parsed.habits.length) || (parsed.done && parsed.done.length);
        if (!hasActions) {
            appendMsg('ai', aiEscape(parsed.cleanText || fullText));
            return;
        }

        var msgId = 'ai_' + Date.now();
        window._pendingAIItems[msgId] = { tasks: parsed.tasks || [], habits: parsed.habits || [], done: parsed.done || [] };

        var html = aiEscape(parsed.cleanText || 'Разобрал твой текст. Сохраняем?');
        html += renderAIActions(msgId, parsed.tasks, parsed.habits, parsed.done);
        appendMsg('ai', html);
    } catch (e) {
        hideTyping();
        console.error('AI chat error:', e);
        appendMsg('ai', 'Ошибка AI. Попробуй ещё раз.');
    }
}

async function saveAIItems(msgId) {
    var pack = window._pendingAIItems[msgId];
    if (!pack || !currentUserId) return;

    var savedTasks = 0;
    var savedHabits = 0;

    for (var i = 0; i < pack.tasks.length; i++) {
        var t = pack.tasks[i];
        try {
            await apiPost('/api/tasks', {
                user_id: currentUserId,
                name: t.name || 'Новая задача',
                section: t.section || 'work',
                priority: t.priority || 'mid',
                deadline: t.deadline || null,
                from_ai: true
            });
            savedTasks++;
        } catch (err) { console.error('save ai task err', err); }
    }

    for (var j = 0; j < pack.habits.length; j++) {
        var h = pack.habits[j];
        try {
            await apiPost('/api/habits', {
                user_id: currentUserId,
                name: h.name || 'Новая привычка',
                icon: h.icon || '✅',
                frequency: h.frequency || 'Каждый день',
                reminder_time: h.reminder_time || null,
                weekdays: Array.isArray(h.weekdays) ? h.weekdays : []
            });
            savedHabits++;
        } catch (err2) { console.error('save ai habit err', err2); }
    }

    await loadTasks();
    await loadHabits();

    var markedDone = 0;
    for (var k = 0; k < (pack.done || []).length; k++) {
        var match = findDoneMatch(pack.done[k]);
        if (!match) continue;
        try {
            if (pack.done[k].type === 'habit') await toggleHabit(match.id);
            else await toggleTask(match.id);
            markedDone++;
        } catch (err3) { console.error('save ai done err', err3); }
    }

    delete window._pendingAIItems[msgId];
    var summary = 'Готово: сохранено задач ' + savedTasks + ', привычек ' + savedHabits;
    if (markedDone) summary += ', отмечено выполненным ' + markedDone;
    appendMsg('ai', summary + '.');
}

function dismissAIItems(msgId) {
    if (window._pendingAIItems[msgId]) delete window._pendingAIItems[msgId];
    appendMsg('ai', 'Ок, ничего не сохраняю.');
}

function handleAiKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    if (!el) return;
    el.style.height = '22px';
    el.style.height = Math.min(el.scrollHeight, 80) + 'px';
    var btn = document.getElementById('aiSendBtn');
    if (!btn) return;
    if (el.value.trim()) btn.classList.add('active');
    else btn.classList.remove('active');
}
