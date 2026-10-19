// Общие элементы интерфейса: дата, модальные окна, выбор значков и частоты

function switchTrackerPage(name, btn) {
    document.querySelectorAll('.tracker-page').forEach(function (p) { p.classList.remove('active') });
    document.querySelectorAll('.sw-btn').forEach(function (b) { b.classList.remove('active') });
    document.getElementById('page-' + name).classList.add('active');
    btn.classList.add('active');
}

(function setCurrentDate() {
    var days = ['ВС', 'ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ'];
    var months = ['ЯНВАРЯ', 'ФЕВРАЛЯ', 'МАРТА', 'АПРЕЛЯ', 'МАЯ', 'ИЮНЯ', 'ИЮЛЯ', 'АВГУСТА', 'СЕНТЯБРЯ', 'ОКТЯБРЯ', 'НОЯБРЯ', 'ДЕКАБРЯ'];
    var now = new Date();
    document.getElementById('currentDate').textContent = days[now.getDay()] + ', ' + now.getDate() + ' ' + months[now.getMonth()];
})();

var selectedEmoji = '🏋️', selectedFreq = 'Каждый день', selectedSection = 'work', selectedPriority = 'mid';
var selectedHabitWeekdays = [];
var editingHabitId = null;
function openAddModal() { openModal('modalChoose') }
function openModal(id) {
    document.getElementById(id).classList.remove('hidden');
    if (id === 'modalHabit') {
        editingHabitId = null;
        var title = document.querySelector('#modalHabit .modal-title');
        if (title) title.textContent = 'Новая привычка';
        selectedFreq = 'Каждый день';
        selectedEmoji = '🏋️';
        var reminderInput = document.getElementById('habitReminderTime');
        if (reminderInput) reminderInput.value = '';
        document.getElementById('habitName').value = '';
        selectedHabitWeekdays = [];
        document.querySelectorAll('#modalHabit .emoji-btn').forEach(function (b) { b.classList.remove('active') });
        var firstEmoji = document.querySelector('#modalHabit .emoji-btn');
        if (firstEmoji) firstEmoji.classList.add('active');
        document.querySelectorAll('#modalHabit .freq-btns .freq-btn').forEach(function (b) {
            if (b.closest('#habitWeekdays')) return;
            b.classList.toggle('active', b.textContent.trim() === 'Каждый день');
        });
        document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function (b) { b.classList.remove('active') });
    }
}
function closeModal(id) { document.getElementById(id).classList.add('hidden') }
function selectEmoji(el) { document.querySelectorAll('.emoji-btn').forEach(function (b) { b.classList.remove('active') }); el.classList.add('active'); selectedEmoji = el.textContent }

function selectFreq(el) {
    el.parentElement.querySelectorAll('.freq-btn').forEach(function (b) { b.classList.remove('active') });
    el.classList.add('active');
    var t = el.textContent.trim();
    if (t.includes('Работа')) selectedSection = 'work';
    else if (t.includes('Жизнь')) selectedSection = 'life';
    else if (t.includes('Высокий')) selectedPriority = 'high';
    else if (t.includes('Средний')) selectedPriority = 'mid';
    else if (t.includes('Низкий')) selectedPriority = 'low';
    else {
        selectedFreq = t;
        selectedHabitWeekdays = [];
        document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function (b) { b.classList.remove('active') });
    }
}
