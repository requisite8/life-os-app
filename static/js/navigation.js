// Переключение вкладок

function showTab(tabName, clickedBtn) {
    document.querySelectorAll('.tab-content').forEach(function (t) { t.classList.remove('active') });
    document.querySelectorAll('.nav-btn').forEach(function (b) { b.classList.remove('active') });
    document.getElementById('tab-' + tabName).classList.add('active');
    clickedBtn.classList.add('active');
    if (tabName === 'stats') renderStats();
    if (tabName === 'focus') loadFocusStats();
}
