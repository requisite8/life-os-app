const tg = window.Telegram?.WebApp;
if (tg?.ready) tg.ready();
if (tg?.expand) tg.expand();

(function fixMobileKeyboard(){
    var vv=window.visualViewport;
    if(!vv)return;
    function onResize(){
        var h=vv.height;
        document.documentElement.style.setProperty('--vv-h',h+'px');
        document.querySelectorAll('.modal-overlay:not(.hidden) .modal').forEach(function(m){
            m.style.maxHeight=(h*0.85)+'px';
        });
    }
    vv.addEventListener('resize',onResize);
})();

let currentUserId = null;
let initUserPromise = null;
const tgUser = tg?.initDataUnsafe?.user || null;
let habits = [];
let tasks = [];
const API_BASE = window.location.origin;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, function(c) {
        return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
}

async function apiGet(path) {
    var r = await fetch(API_BASE + path);
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiPost(path, data) {
    var r = await fetch(API_BASE + path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiPatch(path, data) {
    var r = await fetch(API_BASE + path, {method:'PATCH', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    if (!r.ok) throw new Error(await getApiErrorMessage(r, 'Ошибка: ' + path));
    return r.json();
}
async function apiDelete(path) {
    var r = await fetch(API_BASE + path, {method:'DELETE'});
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
    initUserPromise = (async function() {
        try {
            var user = await apiPost('/api/users', {telegram_id: tgUser?.id || 0, first_name: tgUser?.first_name || 'Пользователь', username: tgUser?.username || null});
            currentUserId = user.id;
            await Promise.all([
                loadFocusStats().catch(function(e){console.error('loadFocusStats:',e)}),
                loadHabits().catch(function(e){console.error('loadHabits:',e)}),
                loadTasks().catch(function(e){console.error('loadTasks:',e)})
            ]);
            renderProfile();
            return currentUserId;
        } catch(e) {console.error('Ошибка инициализации:',e); return null;}
        finally {initUserPromise = null;}
    })();
    return initUserPromise;
}

async function ensureUserReady() {
    if (currentUserId) return true;
    await initUser();
    return currentUserId !== null;
}

var bgThemes={
    crimson:{
        name:'Crimson',
        preview:['#ff1414','#a00aff','#dc0a5a'],
        blobs:[
            ['radial-gradient(circle,rgba(255,20,20,1) 0%,rgba(200,10,60,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,60,30,1) 0%,rgba(220,10,40,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(220,10,80,1) 0%,rgba(170,5,100,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,30,50,1) 0%,rgba(200,10,50,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(160,10,255,1) 0%,rgba(100,5,220,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(130,5,240,1) 0%,rgba(90,5,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(180,20,255,1) 0%,rgba(120,5,210,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(150,10,250,1) 0%,rgba(110,5,215,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(220,10,90,1) 0%,rgba(160,5,140,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(240,20,100,1) 0%,rgba(180,5,130,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(200,5,110,1) 0%,rgba(150,5,150,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(230,15,95,1) 0%,rgba(170,5,135,0.6) 45%,transparent 72%)']
        ]
    },
    ocean:{
        name:'Ocean',
        preview:['#0066ff','#00ccbb','#0088dd'],
        blobs:[
            ['radial-gradient(circle,rgba(0,100,255,1) 0%,rgba(0,60,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,130,255,1) 0%,rgba(0,80,220,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,80,240,1) 0%,rgba(0,50,180,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(20,110,255,1) 0%,rgba(10,70,210,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,200,180,1) 0%,rgba(0,150,140,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,220,200,1) 0%,rgba(0,170,160,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,180,160,1) 0%,rgba(0,130,120,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(10,210,190,1) 0%,rgba(5,160,150,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,140,220,1) 0%,rgba(0,90,180,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,160,240,1) 0%,rgba(0,110,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,120,200,1) 0%,rgba(0,80,160,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(10,150,230,1) 0%,rgba(5,100,190,0.6) 45%,transparent 72%)']
        ]
    },
    aurora:{
        name:'Aurora',
        preview:['#00e080','#00bbff','#8840ff'],
        blobs:[
            ['radial-gradient(circle,rgba(0,224,128,1) 0%,rgba(0,180,90,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,240,140,1) 0%,rgba(0,200,100,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,200,110,1) 0%,rgba(0,160,80,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(20,230,130,1) 0%,rgba(10,190,95,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,190,255,1) 0%,rgba(0,140,220,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,210,255,1) 0%,rgba(0,160,240,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,170,240,1) 0%,rgba(0,120,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(10,200,255,1) 0%,rgba(5,150,230,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(136,64,255,1) 0%,rgba(100,30,220,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(150,80,255,1) 0%,rgba(115,45,235,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(120,50,240,1) 0%,rgba(85,20,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(140,70,250,1) 0%,rgba(105,35,225,0.6) 45%,transparent 72%)']
        ]
    },
    sunset:{
        name:'Sunset',
        preview:['#ff6020','#ff2080','#ffaa00'],
        blobs:[
            ['radial-gradient(circle,rgba(255,96,32,1) 0%,rgba(220,60,10,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,120,40,1) 0%,rgba(240,80,20,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(240,80,20,1) 0%,rgba(200,50,5,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,100,30,1) 0%,rgba(230,70,15,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(255,32,128,1) 0%,rgba(220,10,90,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,50,140,1) 0%,rgba(235,20,100,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(240,20,110,1) 0%,rgba(200,5,80,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(250,40,130,1) 0%,rgba(215,15,95,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(255,170,0,1) 0%,rgba(220,140,0,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,190,20,1) 0%,rgba(240,160,10,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(240,150,0,1) 0%,rgba(200,120,0,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,180,10,1) 0%,rgba(230,150,5,0.6) 45%,transparent 72%)']
        ]
    },
    neon:{
        name:'Neon',
        preview:['#ff00aa','#00ffcc','#4400ff'],
        blobs:[
            ['radial-gradient(circle,rgba(255,0,170,1) 0%,rgba(200,0,130,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(255,20,180,1) 0%,rgba(220,10,140,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(240,0,160,1) 0%,rgba(190,0,120,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(250,10,175,1) 0%,rgba(210,5,135,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,255,204,1) 0%,rgba(0,200,160,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,255,220,1) 0%,rgba(0,220,175,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,240,190,1) 0%,rgba(0,190,150,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(10,250,210,1) 0%,rgba(5,210,165,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(68,0,255,1) 0%,rgba(50,0,200,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(80,10,255,1) 0%,rgba(60,5,220,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(55,0,240,1) 0%,rgba(40,0,190,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(70,5,250,1) 0%,rgba(55,2,210,0.6) 45%,transparent 72%)']
        ]
    },
    midnight:{
        name:'Midnight',
        preview:['#1a0050','#000066','#220044'],
        blobs:[
            ['radial-gradient(circle,rgba(26,0,80,1) 0%,rgba(18,0,55,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(35,0,90,1) 0%,rgba(25,0,65,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(20,0,70,1) 0%,rgba(14,0,48,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(30,0,85,1) 0%,rgba(22,0,60,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,0,102,1) 0%,rgba(0,0,70,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,0,120,1) 0%,rgba(0,0,85,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,0,90,1) 0%,rgba(0,0,60,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(0,0,110,1) 0%,rgba(0,0,78,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(34,0,68,1) 0%,rgba(24,0,48,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(42,0,78,1) 0%,rgba(30,0,56,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(28,0,58,1) 0%,rgba(20,0,40,0.6) 45%,transparent 72%)','radial-gradient(circle,rgba(38,0,72,1) 0%,rgba(27,0,52,0.6) 45%,transparent 72%)']
        ]
    }
};

var blobEls=[document.querySelector('.blob1'),document.querySelector('.blob2'),document.querySelector('.blob3')];
var blobData=[];
var blobIntervals=[];

function applyBgTheme(themeKey){
    var theme=bgThemes[themeKey]||bgThemes.crimson;
    blobIntervals.forEach(function(id){clearInterval(id)});
    blobIntervals=[];
    blobData=theme.blobs.map(function(colors,i){return{el:blobEls[i],colors:colors}});
    var delays=[5000,7500,10000];
    blobData.forEach(function(b,i){startBlob(b,delays[i])});
    localStorage.setItem('bgTheme',themeKey);
}

function rndBlob(min,max){return Math.random()*(max-min)+min}
function moveBlob(b){var s=rndBlob(500,680);b.el.style.width=s+'px';b.el.style.height=s+'px';b.el.style.top=rndBlob(0,100)+'%';b.el.style.left=rndBlob(0,100)+'%';b.el.style.opacity=rndBlob(0.55,0.85);b.el.style.background=b.colors[Math.floor(Math.random()*b.colors.length)]}
function startBlob(b,i){moveBlob(b);blobIntervals.push(setInterval(function(){moveBlob(b)},i))}
applyBgTheme(localStorage.getItem('bgTheme')||'crimson');

function showTab(tabName,clickedBtn){
    document.querySelectorAll('.tab-content').forEach(function(t){t.classList.remove('active')});
    document.querySelectorAll('.nav-btn').forEach(function(b){b.classList.remove('active')});
    document.getElementById('tab-'+tabName).classList.add('active');
    clickedBtn.classList.add('active');
    if(tabName==='stats') renderStats();
    if(tabName==='focus') loadFocusStats();
}

let running=false, paused=false, isStopwatch=true, totalSec=0, elapsed=0, interval=null;
let focusCategory = localStorage.getItem('focusCategory') || '💼 Deep Work';

function updateFocusStatsUI(sessions,totalMin,streak){
    sessions=sessions||0; totalMin=totalMin||0; streak=streak||0;
    document.getElementById('stat-sessions').textContent=sessions;
    if(totalMin>=60){document.getElementById('stat-time').textContent=Math.floor(totalMin/60)+'ч '+totalMin%60+'м'}
    else{document.getElementById('stat-time').textContent=totalMin+'м'}
    document.getElementById('stat-streak').textContent='🔥 '+streak;
}

async function loadFocusStats(){
    if(!currentUserId) return;
    try{var d=await apiGet('/api/focus/'+currentUserId+'?t='+Date.now());updateFocusStatsUI(d.today_sessions||0,d.today_min||0,d.streak||0)}
    catch(e){console.error('Ошибка загрузки статистики фокуса:',e)}
}
updateFocusStatsUI(0,0,0);

var defaultCategories=[{name:'Deep Work',emoji:'💼'},{name:'Креатив',emoji:'🎨'},{name:'Учёба',emoji:'📚'},{name:'Чтение',emoji:'📖'},{name:'Тренировка',emoji:'🏋️'},{name:'Другое',emoji:'✨'}];

function getSavedCategories(){try{var s=localStorage.getItem('categories');if(s)return JSON.parse(s)}catch(e){}return defaultCategories.slice()}
function saveCategories(list){localStorage.setItem('categories',JSON.stringify(list))}
function toggleCategory(e){if(e)e.stopPropagation();openCategoryPanel()}

function openCategoryPanel(){
    renderCategoryPanel();
    document.getElementById('categoryOverlay').classList.add('open');
    document.querySelector('.content').classList.add('scroll-locked');
    document.getElementById('categoryPanelSearch').value='';
}
function closeCategoryPanel(){
    document.getElementById('categoryOverlay').classList.remove('open');
    document.querySelector('.content').classList.remove('scroll-locked');
}

function renderCategoryPanel(filter){
    var cats=getSavedCategories(),q=(filter||'').toLowerCase(),listEl=document.getElementById('categoryPanelList'),html='';
    cats.forEach(function(c){
        if(q&&!c.name.toLowerCase().includes(q))return;
        var full=c.emoji+' '+c.name,isActive=focusCategory===full;
        html+='<div class="category-item'+(isActive?' active':'')+'" onclick="pickCategory(\''+escapeHtml(c.emoji)+'\',\''+escapeHtml(c.name).replace(/'/g,"\\'")+'\')"><span class="category-name">'+escapeHtml(c.name)+'</span><div class="category-actions"><button class="action-mini danger" onclick="removeCategoryItem(event,\''+escapeHtml(c.name).replace(/'/g,"\\'")+'\')">✕</button></div></div>';
    });
    if(q){html+='<div class="category-item" style="cursor:pointer;justify-content:center" onclick="addCategoryFromPanel()"><span class="category-name">+ Добавить «'+escapeHtml(q)+'»</span></div>'}
    listEl.innerHTML=html;
}
function filterCategoryPanel(){renderCategoryPanel(document.getElementById('categoryPanelSearch').value.trim())}
function pickCategory(emoji,name){var l=emoji+' '+name;focusCategory=l;localStorage.setItem('focusCategory',l);document.getElementById('categoryBtn').textContent=l;closeCategoryPanel()}
function addCategoryFromPanel(){var name=document.getElementById('categoryPanelSearch').value.trim();if(!name)return;var cats=getSavedCategories();if(!cats.find(function(c){return c.name===name})){cats.push({name:name,emoji:'✨'});saveCategories(cats)}pickCategory('✨',name)}
function removeCategoryItem(e,name){e.stopPropagation();var cats=getSavedCategories().filter(function(c){return c.name!==name});saveCategories(cats);if(focusCategory.endsWith(name)&&cats.length>0)pickCategory(cats[0].emoji,cats[0].name);renderCategoryPanel(document.getElementById('categoryPanelSearch').value.trim())}
document.getElementById('categoryPanelSearch').addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();if(this.value.trim())addCategoryFromPanel()}});

function toggleTimeDropdown(e){e.stopPropagation();document.getElementById('timeDropdown').classList.toggle('open')}
function setTimeButtonLabel(label){document.getElementById('timeBtn').childNodes[0].nodeValue=label+' '}

function selectMode(sec,label,e){
    e.stopPropagation();
    if(sec===-1){
        var input=window.prompt('Сколько минут длится сессия?','30');
        if(input===null){document.getElementById('timeDropdown').classList.remove('open');return}
        var customMinutes=parseInt(input,10);
        if(!Number.isFinite(customMinutes)||customMinutes<=0){alert('Введите количество минут больше 0');document.getElementById('timeDropdown').classList.remove('open');return}
        sec=customMinutes*60;label=customMinutes+' мин';
    }
    isStopwatch=(sec===0);totalSec=sec;elapsed=0;
    setTimeButtonLabel(label+' ▾');
    document.querySelectorAll('#timeDropdown .dropdown-item').forEach(function(i){i.classList.remove('active')});
    e.target.closest('.dropdown-item').classList.add('active');
    if(running||paused) resetTimer();
    document.getElementById('timeDropdown').classList.remove('open');
}
document.addEventListener('click',function(){document.getElementById('timeDropdown').classList.remove('open')});

function toggleTimer(){if(!running&&!paused)startTimer();else if(running)pauseTimer();else resumeTimer()}

function startTimer(){
    if(!isStopwatch&&totalSec>0&&elapsed>=totalSec) elapsed=0;
    running=true;paused=false;
    document.getElementById('trackArc').setAttribute('opacity','1');
    document.getElementById('progressArc').setAttribute('opacity','1');
    document.getElementById('spinG').setAttribute('opacity','1');
    document.getElementById('spinG').classList.remove('paused');
    document.getElementById('startLabel').classList.add('hidden');
    document.getElementById('timerNum').classList.remove('hidden');
    document.getElementById('resetBtn').classList.remove('hidden');
    document.getElementById('circleHint').textContent='нажми для паузы';
    document.getElementById('modeBadge').textContent='🔵 Идёт сессия';
    document.getElementById('timerNum').textContent=isStopwatch?fmt(elapsed):fmt(totalSec-elapsed);
    interval=setInterval(tick,1000);
}

function tick(){
    elapsed++;
    if(isStopwatch){document.getElementById('timerNum').textContent=fmt(elapsed)}
    else{
        var left=totalSec-elapsed;
        if(left<=0){left=0;clearInterval(interval);interval=null;running=false;paused=false;document.getElementById('modeBadge').textContent='✅ Сессия завершена!';document.getElementById('spinG').classList.add('paused');document.getElementById('circleHint').textContent='отличная работа!';saveFocusAndReload(totalSec)}
        document.getElementById('timerNum').textContent=fmt(left);
        document.getElementById('progressArc').setAttribute('stroke-dashoffset',603-(603*(elapsed/totalSec)));
    }
}

async function saveFocusAndReload(durationSec){
    var durationMin=Math.round(durationSec/60);
    if(durationMin<1)return;
    try{if(!currentUserId)await initUser();if(!currentUserId)return;await apiPost('/api/focus',{user_id:currentUserId,duration_min:durationMin,category:focusCategory})}catch(e){console.error('Ошибка сохранения сессии:',e)}
    try{var d=await apiGet('/api/focus/'+currentUserId+'?t='+Date.now());updateFocusStatsUI(d.today_sessions||0,d.today_min||0,d.streak||0)}catch(e){console.error('Ошибка загрузки статистики:',e)}
}

function pauseTimer(){if(!running)return;running=false;paused=true;clearInterval(interval);interval=null;document.getElementById('spinG').classList.add('paused');document.getElementById('circleHint').textContent='нажми чтобы продолжить';document.getElementById('modeBadge').textContent='⏸ Пауза'}
function resumeTimer(){running=true;paused=false;document.getElementById('spinG').classList.remove('paused');document.getElementById('circleHint').textContent='нажми для паузы';document.getElementById('modeBadge').textContent='🔵 Идёт сессия';interval=setInterval(tick,1000)}

function resetTimer(){
    clearInterval(interval);interval=null;
    if(isStopwatch&&elapsed>=60) saveFocusAndReload(elapsed);
    running=false;paused=false;elapsed=0;
    document.getElementById('trackArc').setAttribute('opacity','0');
    document.getElementById('progressArc').setAttribute('opacity','0');
    document.getElementById('spinG').setAttribute('opacity','0');
    document.getElementById('spinG').classList.add('paused');
    document.getElementById('startLabel').classList.remove('hidden');
    document.getElementById('timerNum').classList.add('hidden');
    document.getElementById('resetBtn').classList.add('hidden');
    document.getElementById('timerNum').textContent='00:00';
    document.getElementById('circleHint').textContent='нажми чтобы начать';
    document.getElementById('modeBadge').textContent='выбери режим и нажми';
    document.getElementById('progressArc').setAttribute('stroke-dashoffset','603');
}

function fmt(s){return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}

function switchTrackerPage(name,btn){
    document.querySelectorAll('.tracker-page').forEach(function(p){p.classList.remove('active')});
    document.querySelectorAll('.sw-btn').forEach(function(b){b.classList.remove('active')});
    document.getElementById('page-'+name).classList.add('active');
    btn.classList.add('active');
}

(function setCurrentDate(){
    var days=['ВС','ПН','ВТ','СР','ЧТ','ПТ','СБ'];
    var months=['ЯНВАРЯ','ФЕВРАЛЯ','МАРТА','АПРЕЛЯ','МАЯ','ИЮНЯ','ИЮЛЯ','АВГУСТА','СЕНТЯБРЯ','ОКТЯБРЯ','НОЯБРЯ','ДЕКАБРЯ'];
    var now=new Date();
    document.getElementById('currentDate').textContent=days[now.getDay()]+', '+now.getDate()+' '+months[now.getMonth()];
})();

var selectedEmoji='🏋️', selectedFreq='Каждый день', selectedSection='work', selectedPriority='mid';
var selectedHabitWeekdays=[];
var editingHabitId=null;
function openAddModal(){openModal('modalChoose')}
function openModal(id){
    document.getElementById(id).classList.remove('hidden');
    if(id==='modalHabit'){
        editingHabitId=null;
        var title=document.querySelector('#modalHabit .modal-title');
        if(title) title.textContent='Новая привычка';
        selectedFreq='Каждый день';
        selectedEmoji='🏋️';
        var reminderInput=document.getElementById('habitReminderTime');
        if(reminderInput) reminderInput.value='';
        document.getElementById('habitName').value='';
        selectedHabitWeekdays=[];
        document.querySelectorAll('#modalHabit .emoji-btn').forEach(function(b){b.classList.remove('active')});
        var firstEmoji=document.querySelector('#modalHabit .emoji-btn');
        if(firstEmoji) firstEmoji.classList.add('active');
        document.querySelectorAll('#modalHabit .freq-btns .freq-btn').forEach(function(b){
            if(b.closest('#habitWeekdays')) return;
            b.classList.toggle('active', b.textContent.trim()==='Каждый день');
        });
        document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function(b){b.classList.remove('active')});
    }
}
function closeModal(id){document.getElementById(id).classList.add('hidden')}
function selectEmoji(el){document.querySelectorAll('.emoji-btn').forEach(function(b){b.classList.remove('active')});el.classList.add('active');selectedEmoji=el.textContent}

function selectFreq(el){
    el.parentElement.querySelectorAll('.freq-btn').forEach(function(b){b.classList.remove('active')});
    el.classList.add('active');
    var t=el.textContent.trim();
    if(t.includes('Работа'))selectedSection='work';
    else if(t.includes('Жизнь'))selectedSection='life';
    else if(t.includes('Высокий'))selectedPriority='high';
    else if(t.includes('Средний'))selectedPriority='mid';
    else if(t.includes('Низкий'))selectedPriority='low';
    else{
        selectedFreq=t;
        selectedHabitWeekdays=[];
        document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function(b){b.classList.remove('active')});
    }
}

function toggleHabitWeekday(el){
    var day=parseInt(el.dataset.day,10);
    if(Number.isNaN(day)) return;
    if(selectedHabitWeekdays.includes(day)){
        selectedHabitWeekdays=selectedHabitWeekdays.filter(function(x){return x!==day});
        el.classList.remove('active');
    }else{
        selectedHabitWeekdays.push(day);
        selectedHabitWeekdays.sort();
        el.classList.add('active');
    }
    if(selectedHabitWeekdays.length>0){
        document.querySelectorAll('#modalHabit .freq-btns:not(#habitWeekdays) .freq-btn').forEach(function(b){b.classList.remove('active')});
        selectedFreq='';
    }
}

function weekdaysLabel(days){
    if(!days || !days.length) return '';
    var names=['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
    return ' · ' + days.map(function(d){return names[d]||''}).filter(Boolean).join(', ');
}

async function loadHabits(){
    if(!currentUserId)return;
    try{habits=await apiGet('/api/habits/'+currentUserId);renderHabits()}catch(e){console.error('Ошибка загрузки привычек:',e)}
}

async function saveHabit(){
    if(!await ensureUserReady()){alert('Пользователь ещё не инициализирован.');return}
    var name=document.getElementById('habitName').value.trim();if(!name)return;
    var reminderTime=(document.getElementById('habitReminderTime')?.value||'').trim()||null;
    var freq=selectedFreq;
    if(selectedHabitWeekdays.length>0){
        var dayNames=['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
        freq=selectedHabitWeekdays.map(function(d){return dayNames[d]||''}).filter(Boolean).join(', ');
    }
    if(!freq) freq='Каждый день';
    try{
        if(editingHabitId){
            await apiPatch('/api/habits/'+editingHabitId,{name:name,icon:selectedEmoji,frequency:freq,reminder_time:reminderTime,weekdays:selectedHabitWeekdays});
            await loadHabits();
        }else{
            await apiPost('/api/habits',{user_id:currentUserId,name:name,icon:selectedEmoji,frequency:freq,reminder_time:reminderTime,weekdays:selectedHabitWeekdays});
            await loadHabits();
        }
        closeModal('modalHabit');
        document.getElementById('habitName').value='';
        if(document.getElementById('habitReminderTime'))document.getElementById('habitReminderTime').value='';
        selectedHabitWeekdays=[];
        editingHabitId=null;
    }catch(e){console.error('Ошибка сохранения привычки:',e);alert('Не удалось добавить привычку')}
}

function isHabitActiveToday(freq,weekdays){
    var dow=(new Date().getDay()+6)%7;
    if(weekdays && weekdays.length>0) return weekdays.includes(dow);
    if(!freq||freq==='Каждый день')return true;
    if(freq==='Пн-Пт')return dow<=4;
    if(freq==='Пн, Ср, Пт')return dow===0||dow===2||dow===4;
    return true;
}

function renderHabits(){
    var list=document.getElementById('habits-list');
    if(habits.length===0){list.innerHTML='<div class="empty-state"><div class="empty-icon">✅</div><div class="empty-text">Нет привычек</div><div class="empty-sub">Нажми + чтобы добавить первую</div></div>';return}
    var dayNames=['Пн','Вт','Ср','Чт','Пт','Сб','Вс'],todayIdx=(new Date().getDay()+6)%7;
    list.innerHTML=habits.map(function(h){
        var active=isHabitActiveToday(h.frequency,h.weekdays||[]);
        var reminderText=h.reminder_time?(' · ⏰ '+h.reminder_time):'';
        var weekDaysText=weekdaysLabel(h.weekdays||[]);
        var dots=h.days.map(function(done,i){return'<div class="day-dot '+(i===todayIdx?'today':done?'done':'')+'"></div>'}).join('');
        var labels=dayNames.map(function(d){return'<div class="day-label">'+d+'</div>'}).join('');
        return'<div class="habit-card'+(active?'':' habit-inactive')+'"><div class="habit-top"><div class="habit-left"><span class="habit-icon">'+escapeHtml(h.icon)+'</span><div><div class="habit-name">'+escapeHtml(h.name)+'</div><div class="habit-freq">'+escapeHtml(h.frequency)+weekDaysText+reminderText+(active?'':' · выходной')+'</div></div></div><div class="habit-right"><span class="habit-streak">🔥 '+h.streak+'</span>'+(active?'<div class="check-circle '+(h.doneToday?'done':'')+'" onclick="toggleHabit('+h.id+')">'+(h.doneToday?'✓':'')+'</div>':'')+'<button class="habit-del-btn" onclick="editHabitClick(event,'+h.id+')">Изм</button><button class="habit-del-btn" onclick="deleteHabitClick(event,'+h.id+')">✕</button></div></div><div class="days-row">'+dots+'</div><div class="days-labels">'+labels+'</div></div>';
    }).join('');
}

function editHabitClick(e,id){
    e.stopPropagation();
    var h=habits.find(function(x){return x.id===id});
    if(!h) return;
    openModal('modalHabit');
    editingHabitId=id;
    var title=document.querySelector('#modalHabit .modal-title');
    if(title) title.textContent='Редактировать привычку';
    document.getElementById('habitName').value=h.name||'';
    if(document.getElementById('habitReminderTime'))document.getElementById('habitReminderTime').value=h.reminder_time||'';
    selectedEmoji=h.icon||'✅';
    selectedFreq=h.frequency||'Каждый день';
    selectedHabitWeekdays=(h.weekdays||[]).slice();
    document.querySelectorAll('#modalHabit .emoji-btn').forEach(function(b){b.classList.toggle('active', b.textContent===selectedEmoji)});
    document.querySelectorAll('#modalHabit .freq-btns .freq-btn').forEach(function(b){
        if(b.closest('#habitWeekdays')) return;
        b.classList.toggle('active', b.textContent.trim()===selectedFreq);
    });
    document.querySelectorAll('#habitWeekdays .freq-btn').forEach(function(b){
        var day=parseInt(b.dataset.day,10);
        b.classList.toggle('active', selectedHabitWeekdays.includes(day));
    });
}

async function deleteHabitClick(e,id){e.stopPropagation();if(!confirm('Удалить привычку?'))return;try{await apiDelete('/api/habits/'+id);habits=habits.filter(function(h){return h.id!==id});renderHabits()}catch(e){console.error('Ошибка удаления привычки:',e)}}

async function toggleHabit(id){
    if(!await ensureUserReady()){alert('Пользователь ещё не инициализирован.');return}
    var today=new Date().toISOString().split('T')[0];
    try{
        var result=await apiPost('/api/habits/toggle',{habit_id:id,user_id:currentUserId,date:today});
        var h=habits.find(function(h){return h.id===id});
        if(h){h.doneToday=result.done;h.streak=result.streak;h.days[(new Date().getDay()+6)%7]=result.done}
        renderHabits();
    }catch(e){console.error('Ошибка обновления привычки:',e);alert('Не удалось обновить привычку')}
}

async function loadTasks(){
    if(!currentUserId)return;
    try{tasks=await apiGet('/api/tasks/'+currentUserId);renderTasks()}catch(e){console.error('Ошибка загрузки задач:',e)}
}

async function saveTask(){
    if(!await ensureUserReady()){alert('Пользователь ещё не инициализирован.');return}
    var name=document.getElementById('taskName').value.trim();if(!name)return;
    try{
        var t=await apiPost('/api/tasks',{user_id:currentUserId,name:name,section:selectedSection,priority:selectedPriority,deadline:document.getElementById('taskDeadline').value||null,from_ai:false});
        tasks.unshift(t);renderTasks();closeModal('modalTask');document.getElementById('taskName').value='';document.getElementById('taskDeadline').value='';
    }catch(e){console.error('Ошибка сохранения задачи:',e);alert('Не удалось добавить задачу')}
}

function renderTasks(){
    var workList=document.getElementById('tasks-work'),lifeList=document.getElementById('tasks-life'),empty=document.getElementById('tasks-empty');
    var workTasks=tasks.filter(function(t){return t.section==='work'}),lifeTasks=tasks.filter(function(t){return t.section==='life'});
    if(tasks.length===0)empty.classList.remove('hidden');else empty.classList.add('hidden');
    workList.innerHTML=renderTaskList(workTasks);lifeList.innerHTML=renderTaskList(lifeTasks);
}

function renderTaskList(list){
    if(list.length===0)return'';
    return list.map(function(t){
        var pClass=t.priority==='high'?'p-high':t.priority==='low'?'p-low':'p-mid';
        var dl='Без дедлайна';
        if(t.deadline){var d=new Date(t.deadline);dl='⏰ '+d.toLocaleDateString('ru',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})}
        return'<div class="task-card '+(t.done?'done-t':'')+'" onclick="toggleTask('+t.id+')"><div class="checkbox '+(t.done?'checked':'')+'">'+(t.done?'✓':'')+'</div><div class="task-info"><div class="task-top"><span class="task-title">'+escapeHtml(t.name)+'</span>'+(t.from_ai?'<span class="task-ai">🤖</span>':'')+'</div><div class="task-meta"><div class="priority '+pClass+'"></div><span class="task-deadline">'+escapeHtml(dl)+'</span></div></div><button class="task-del-btn" onclick="deleteTaskClick(event,'+t.id+')">✕</button></div>';
    }).join('');
}

async function deleteTaskClick(e,id){e.stopPropagation();if(!confirm('Удалить задачу?'))return;try{await apiDelete('/api/tasks/'+id);tasks=tasks.filter(function(t){return t.id!==id});renderTasks()}catch(e){console.error('Ошибка удаления задачи:',e)}}

async function toggleTask(id){
    var task=tasks.find(function(t){return t.id===id});if(!task)return;
    try{await apiPatch('/api/tasks/'+id,{done:!task.done});task.done=!task.done;task.done_at=task.done?new Date().toISOString():null;renderTasks()}
    catch(e){console.error('Ошибка обновления задачи:',e)}
}

var weekOffset=0;

function getWeekRange(offset){
    var now=new Date(),day=now.getDay(),diffToMonday=(day===0)?-6:1-day;
    var monday=new Date(now);monday.setDate(now.getDate()+diffToMonday+offset*7);monday.setHours(0,0,0,0);
    var sunday=new Date(monday);sunday.setDate(monday.getDate()+6);sunday.setHours(23,59,59,999);
    return{monday:monday,sunday:sunday};
}

function formatWeekLabel(monday,sunday){
    var m=['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
    return monday.getDate()+' '+m[monday.getMonth()]+' — '+sunday.getDate()+' '+m[sunday.getMonth()];
}

function showChange(elId,diff,isMinutes){
    var el=document.getElementById(elId);if(!el)return;
    if(diff===0){el.textContent='—';el.className='stat-change';return}
    var abs=Math.round(Math.abs(diff)),sign=diff>0?'↑ +':'↓ -';
    var text=isMinutes?(abs>=60?Math.round(abs/60*10)/10+'ч':abs+'м'):String(abs);
    el.textContent=sign+text;el.className='stat-change'+(diff<0?' down':'');
}

async function renderStats(){
    if(!await ensureUserReady())return;
    var range=getWeekRange(weekOffset),monday=range.monday,sunday=range.sunday;
    document.getElementById('weekLabel').textContent=formatWeekLabel(monday,sunday);
    var subText=weekOffset===0?'текущая неделя':weekOffset===-1?'прошлая неделя':Math.abs(weekOffset)+' нед. назад';
    document.getElementById('weekSub').textContent=subText;
    var nextBtn=document.getElementById('weekNextBtn');
    if(weekOffset===0)nextBtn.classList.add('disabled');else nextBtn.classList.remove('disabled');
    try{
        var stats=await apiGet('/api/stats/'+currentUserId+'?week_offset='+weekOffset);
        var focusMin=stats.curr_focus_min;
        document.getElementById('weekFocus').textContent=focusMin>=60?Math.round(focusMin/60*10)/10+'ч':focusMin+'м';
        document.getElementById('weekSessions').textContent=stats.curr_sessions;
        document.getElementById('weekTasks').textContent=stats.curr_tasks_done;
        var activeHabits=habits.filter(function(h){return isHabitActiveToday(h.frequency,h.weekdays||[])});
        var doneTodayCount=activeHabits.filter(function(h){return h.doneToday}).length;
        document.getElementById('weekHabits').textContent=activeHabits.length>0?Math.round((doneTodayCount/activeHabits.length)*100)+'%':'—';
        showChange('focusChange',stats.focus_diff_min||0,true);
        showChange('sessionsChange',stats.sessions_diff||0,false);
        showChange('tasksChange',stats.tasks_diff||0,false);
        renderFocusBars(monday,stats.focus_by_day);
    }catch(e){console.error('Ошибка загрузки статистики:',e)}
    renderHabitsProgress();renderProfile();renderThemePicker();updateThemeBtnDots();
}

function localDateKey(d){
    var y=d.getFullYear(),m=d.getMonth()+1,day=d.getDate();
    return y+'-'+(m<10?'0':'')+m+'-'+(day<10?'0':'')+day;
}

function renderFocusBars(monday,focusByDay){
    var container=document.getElementById('focusBars'),dayNames=['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
    var today=new Date();today.setHours(0,0,0,0);
    var maxMin=0;
    for(var i=0;i<7;i++){var d=new Date(monday);d.setDate(monday.getDate()+i);maxMin=Math.max(maxMin,focusByDay[localDateKey(d)]||0)}
    if(maxMin===0)maxMin=60;
    var html='';
    for(var i=0;i<7;i++){
        var d=new Date(monday);d.setDate(monday.getDate()+i);
        var key=localDateKey(d),minutes=focusByDay[key]||0;
        var isToday=d.getTime()===today.getTime(),isFuture=d>today;
        var heightPct=minutes>0?Math.max(10,(minutes/maxMin)*100):4;
        var valText='—';if(minutes>0)valText=minutes>=60?Math.round(minutes/60*10)/10+'ч':minutes+'м';
        var barClass='bar';if(isToday)barClass+=' is-today';else if(minutes>0)barClass+=' has-data';
        html+='<div class="bar-wrap"><div class="bar-val">'+(isFuture?'':valText)+'</div><div class="'+barClass+'" style="height:'+heightPct+'%"></div><div class="bar-label">'+dayNames[i]+'</div></div>';
    }
    container.innerHTML=html;
}

function getActiveDaysCount(freq,weekdays){
    if(weekdays && weekdays.length>0) return weekdays.length;
    if(!freq||freq==='Каждый день')return 7;
    if(freq==='Пн-Пт')return 5;
    if(freq==='Пн, Ср, Пт')return 3;
    return 7;
}

function renderHabitsProgress(){
    var container=document.getElementById('habitsProgress');
    if(habits.length===0){container.innerHTML='<p style="color:rgba(220,215,240,0.3);font-size:13px;">Нет активных привычек</p>';return}
    var colors=['pf-1','pf-2','pf-3','pf-4','pf-5'];
    container.innerHTML=habits.map(function(h,i){
        var activeDays=getActiveDaysCount(h.frequency,h.weekdays||[]),doneDays=h.days.filter(Boolean).length;
        var pct=Math.min(100,Math.round((doneDays/activeDays)*100)),colorClass=colors[i%colors.length];
        return'<div class="habit-progress-row"><span class="habit-progress-name">'+escapeHtml(h.icon)+' '+escapeHtml(h.name)+'</span><span class="habit-progress-pct">'+pct+'%</span></div><div class="prog-bar"><div class="prog-fill '+colorClass+'" style="width:'+pct+'%"></div></div>';
    }).join('');
}

function renderProfile(){
    var avatarEl=document.getElementById('userAvatar');
    if(tgUser){
        document.getElementById('userName').textContent=tgUser.first_name+(tgUser.last_name?' '+tgUser.last_name:'');
        if(tgUser.photo_url){
            avatarEl.innerHTML='<img src="'+escapeHtml(tgUser.photo_url)+'" style="width:100%;height:100%;border-radius:50%;object-fit:cover">';
            avatarEl.style.overflow='hidden';
        }else{
            avatarEl.textContent=tgUser.first_name[0].toUpperCase();
        }
    }
    var firstUse=localStorage.getItem('firstUseDate');
    if(!firstUse){localStorage.setItem('firstUseDate',new Date().toISOString());document.getElementById('userDays').textContent='Life OS · первый день'}
    else{var days=Math.floor((new Date()-new Date(firstUse))/(1000*60*60*24))+1;document.getElementById('userDays').textContent='Life OS · '+days+' '+dayWord(days)}
}

function dayWord(n){if(n%10===1&&n%100!==11)return'день';if([2,3,4].includes(n%10)&&![12,13,14].includes(n%100))return'дня';return'дней'}
function changeWeek(dir){if(dir===1&&weekOffset===0)return;weekOffset+=dir;renderStats()}

function renderThemePicker(){
    var container=document.getElementById('themePicker');
    if(!container) return;
    var current=localStorage.getItem('bgTheme')||'crimson';
    var html='';
    Object.keys(bgThemes).forEach(function(key){
        var t=bgThemes[key],isActive=key===current;
        html+='<div class="theme-item'+(isActive?' active':'')+'" onclick="pickTheme(\''+key+'\')">';
        html+='<div class="theme-preview">';
        t.preview.forEach(function(c){html+='<div class="theme-dot" style="background:'+c+'"></div>'});
        html+='</div>';
        html+='<div class="theme-name">'+escapeHtml(t.name)+'</div>';
        html+='</div>';
    });
    container.innerHTML=html;
    updateThemeBtnDots();
}

function updateThemeBtnDots(){
    var dotsEl=document.getElementById('themeBtnDots');
    if(!dotsEl) return;
    var current=localStorage.getItem('bgTheme')||'crimson';
    var theme=bgThemes[current]||bgThemes.crimson;
    dotsEl.innerHTML=theme.preview.map(function(c){return'<div class="theme-dot" style="background:'+c+'"></div>'}).join('');
}

function pickTheme(key){
    applyBgTheme(key);
    renderThemePicker();
}

function appendMsg(role,html){
    var area=document.getElementById('chatArea'),div=document.createElement('div');
    if(role==='user'){div.className='msg-user';div.innerHTML='<div class="msg-user-bubble">'+html+'</div>'}
    else{div.className='msg-ai';div.innerHTML='<div class="ai-avatar-sm">R</div><div class="msg-ai-bubble">'+html+'</div>'}
    area.appendChild(div);area.scrollTop=area.scrollHeight;return div;
}

function showTyping(){var area=document.getElementById('chatArea'),div=document.createElement('div');div.className='typing-indicator';div.id='typingIndicator';div.innerHTML='<div class="ai-avatar-sm">R</div><div class="typing-bubble"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';area.appendChild(div);area.scrollTop=area.scrollHeight}
function hideTyping(){var el=document.getElementById('typingIndicator');if(el)el.remove()}

document.getElementById('categoryBtn').textContent=focusCategory;
updateThemeBtnDots();
initUser();
// =============================================
// ===== AI ВКЛАДКА =====
// =============================================

let chatHistory = [];
window._pendingAIItems = window._pendingAIItems || {};

function aiEscape(v){
    return String(v ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
}

function parseAIResponse(text){
    var taskMatch = text.match(/<tasks>([\s\S]*?)<\/tasks>/i);
    var habitMatch = text.match(/<habits>([\s\S]*?)<\/habits>/i);

    var cleanText = text
        .replace(/<tasks>[\s\S]*?<\/tasks>/ig, '')
        .replace(/<habits>[\s\S]*?<\/habits>/ig, '')
        .trim();

    var parsedTasks = [];
    var parsedHabits = [];

    if(taskMatch){
        try { parsedTasks = JSON.parse(taskMatch[1].trim()) || []; } catch(e){ parsedTasks = []; }
    }
    if(habitMatch){
        try { parsedHabits = JSON.parse(habitMatch[1].trim()) || []; } catch(e){ parsedHabits = []; }
    }

    return { cleanText: cleanText, tasks: parsedTasks, habits: parsedHabits };
}

function formatReminderTime(isoDate){
    if(!isoDate) return '';
    var d = new Date(isoDate);
    if(Number.isNaN(d.getTime())) return String(isoDate);
    return d.toLocaleString('ru', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'});
}

function renderAIActions(msgId, tasks, habits){
    var tHtml = (tasks || []).map(function(t){
        return '<div class="action-item">📋 ' + aiEscape(t.name || 'Без названия') +
            '<span class="action-item-time">' + (t.deadline ? aiEscape(formatReminderTime(t.deadline)) : 'без дедлайна') + '</span></div>';
    }).join('');

    var hHtml = (habits || []).map(function(h){
        var time = h.reminder_time ? (' · ⏰ ' + aiEscape(h.reminder_time)) : '';
        var freq = h.frequency ? (' · ' + aiEscape(h.frequency)) : '';
        return '<div class="action-item">✅ ' + aiEscape(h.name || 'Без названия') +
            '<span class="action-item-time">' + freq + time + '</span></div>';
    }).join('');

    return '<div class="action-card">' +
        '<div class="action-card-title">Найдено: задач ' + (tasks||[]).length + ', привычек ' + (habits||[]).length + '</div>' +
        tHtml + hHtml +
        '<div class="action-btns">' +
        '<div class="action-btn" onclick="saveAIItems(\'' + msgId + '\')">✓ Сохранить</div>' +
        '<div class="action-btn secondary" onclick="dismissAIItems(\'' + msgId + '\')">✕ Отклонить</div>' +
        '</div></div>';
}

async function sendMessage(){
    var input = document.getElementById('aiInput');
    var text = (input?.value || '').trim();
    if(!text) return;

    appendMsg('user', aiEscape(text));
    input.value = '';
    autoResize(input);
    showTyping();

    try {
        if(!currentUserId) await initUser();
        var data = await apiPost('/api/ai/chat', {user_id: currentUserId, message: text, history: chatHistory});
        hideTyping();

        var fullText = String(data.reply || '').trim();
        var parsed = parseAIResponse(fullText);

        chatHistory.push({role:'user', content:text});
        chatHistory.push({role:'assistant', content:fullText});

        var hasActions = (parsed.tasks && parsed.tasks.length) || (parsed.habits && parsed.habits.length);
        if(!hasActions){
            appendMsg('ai', aiEscape(parsed.cleanText || fullText));
            return;
        }

        var msgId = 'ai_' + Date.now();
        window._pendingAIItems[msgId] = { tasks: parsed.tasks || [], habits: parsed.habits || [] };

        var html = aiEscape(parsed.cleanText || 'Разобрал твой текст. Сохраняем?');
        html += renderAIActions(msgId, parsed.tasks, parsed.habits);
        appendMsg('ai', html);
    } catch (e){
        hideTyping();
        console.error('AI chat error:', e);
        appendMsg('ai', 'Ошибка AI. Попробуй ещё раз.');
    }
}

async function saveAIItems(msgId){
    var pack = window._pendingAIItems[msgId];
    if(!pack || !currentUserId) return;

    var savedTasks = 0;
    var savedHabits = 0;

    for(var i=0;i<pack.tasks.length;i++){
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
        } catch(err){ console.error('save ai task err', err); }
    }

    for(var j=0;j<pack.habits.length;j++){
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
        } catch(err2){ console.error('save ai habit err', err2); }
    }

    await loadTasks();
    await loadHabits();

    delete window._pendingAIItems[msgId];
    appendMsg('ai', 'Готово: сохранено задач ' + savedTasks + ', привычек ' + savedHabits + '.');
}

function dismissAIItems(msgId){
    if(window._pendingAIItems[msgId]) delete window._pendingAIItems[msgId];
    appendMsg('ai', 'Ок, ничего не сохраняю.');
}

function handleAiKey(e){
    if(e.key === 'Enter' && !e.shiftKey){
        e.preventDefault();
        sendMessage();
    }
}

function autoResize(el){
    if(!el) return;
    el.style.height = '22px';
    el.style.height = Math.min(el.scrollHeight, 80) + 'px';
    var btn = document.getElementById('aiSendBtn');
    if(!btn) return;
    if(el.value.trim()) btn.classList.add('active');
    else btn.classList.remove('active');
}

// =============================================
// ===== LOFI MUSIC PLAYER =====
// =============================================

var _actx=null,_lofiNodes=[],_lofiPlaying=false,_lofiMuted=false,_lofiMaster=null,_lofiTimer=null;
var _currentTrack=null,_musicListOpen=false;

var musicTracks=[
    {id:'lofi',name:'Lofi Chill',desc:'72 bpm · мягкие аккорды',color:'linear-gradient(135deg,#a040ff,#ff3060)',bpm:72,wave:'triangle',filterHz:1500,
     chords:[[261.6,329.6,392,493.9],[220,277.2,329.6,415.3],[349.2,440,523.3,659.3],[392,493.9,587.3,740]]},
    {id:'night',name:'Night Drive',desc:'80 bpm · минорный синт',color:'linear-gradient(135deg,#0044cc,#6600aa)',bpm:80,wave:'sawtooth',filterHz:900,
     chords:[[220,261.6,329.6,440],[196,246.9,293.7,392],[174.6,220,261.6,349.2],[196,246.9,329.6,392]]},
    {id:'morning',name:'Morning Coffee',desc:'90 bpm · мажорный пиано',color:'linear-gradient(135deg,#ff8820,#ffcc00)',bpm:90,wave:'triangle',filterHz:2000,
     chords:[[293.7,370,440,554.4],[261.6,329.6,392,523.3],[349.2,440,523.3,698.5],[392,493.9,587.3,784]]},
    {id:'ambient',name:'Deep Focus',desc:'60 bpm · эмбиент дроны',color:'linear-gradient(135deg,#004444,#006666)',bpm:60,wave:'sine',filterHz:600,
     chords:[[130.8,196,261.6,392],[146.8,220,293.7,440],[164.8,246.9,329.6,493.9],[130.8,196,261.6,392]]},
    {id:'jazz',name:'Jazz Noir',desc:'68 bpm · джазовые септаккорды',color:'linear-gradient(135deg,#330022,#880044)',bpm:68,wave:'triangle',filterHz:1200,
     chords:[[261.6,311.1,392,466.2],[293.7,349.2,440,523.3],[349.2,415.3,523.3,622.3],[311.1,370,466.2,554.4]]}
];

var _trackBuffers={};

function lofiCtx(){
    if(!_actx)_actx=new(window.AudioContext||window.webkitAudioContext)();
    if(_actx.state==='suspended')_actx.resume();
    return _actx;
}

function updatePlayerUI(){
    var playIcon=document.getElementById('mpIconPlay'),pauseIcon=document.getElementById('mpIconPause');
    var playBtn=document.getElementById('mpPlayBtn'),title=document.getElementById('mpTitle'),sub=document.getElementById('mpSub');
    var art=document.getElementById('mpArt');
    if(_currentTrack&&art)art.style.background=_currentTrack.color;
    if(_lofiPlaying&&_currentTrack){
        playIcon.classList.add('hidden');pauseIcon.classList.remove('hidden');
        playBtn.classList.add('active');title.classList.add('active');
        title.textContent=_currentTrack.name;sub.textContent='playing';
    }else{
        playIcon.classList.remove('hidden');pauseIcon.classList.add('hidden');
        playBtn.classList.remove('active');title.classList.remove('active');
        title.textContent=_currentTrack?_currentTrack.name:'Выбери музыку';
        sub.textContent=_currentTrack?_currentTrack.desc:'нажми чтобы открыть';
    }
    renderMusicList();
}

function renderTrackBuffer(track,callback){
    if(_trackBuffers[track.id])return callback(_trackBuffers[track.id]);
    var sr=44100,bpm=track.bpm,beatSec=60/bpm;
    var totalBeats=16,dur=totalBeats*beatSec;
    var len=Math.ceil(sr*dur),off=new OfflineAudioContext(2,len,sr);
    var master=off.createGain();master.gain.value=0.9;master.connect(off.destination);

    var chords=track.chords;
    for(var b=0;b<totalBeats;b++){
        var tStart=b*beatSec,chord=chords[Math.floor(b/4)%chords.length],bic=b%4;

        for(var v=0;v<chord.length;v++){
            var po=off.createOscillator();po.type='sine';po.frequency.value=chord[v];
            var pg=off.createGain();pg.gain.setValueAtTime(0.04,tStart);
            var pf=off.createBiquadFilter();pf.type='lowpass';pf.frequency.value=track.filterHz*0.5;
            po.connect(pf);pf.connect(pg);pg.connect(master);
            po.start(tStart);po.stop(tStart+beatSec);
        }

        var melNote=chord[bic%chord.length]*2;
        var mo=off.createOscillator();mo.type=track.wave;mo.frequency.value=melNote;
        var me=off.createGain();me.gain.setValueAtTime(0,tStart);
        me.gain.linearRampToValueAtTime(0.12,tStart+0.015);
        me.gain.exponentialRampToValueAtTime(0.001,tStart+beatSec*0.8);
        var mf=off.createBiquadFilter();mf.type='lowpass';mf.frequency.value=track.filterHz;
        mo.connect(mf);mf.connect(me);me.connect(master);
        mo.start(tStart);mo.stop(tStart+beatSec);

        if(bic===0||bic===2){
            var ko=off.createOscillator();ko.type='sine';
            ko.frequency.setValueAtTime(150,tStart);
            ko.frequency.exponentialRampToValueAtTime(40,tStart+0.12);
            var ke=off.createGain();ke.gain.setValueAtTime(0.25,tStart);
            ke.gain.exponentialRampToValueAtTime(0.001,tStart+0.3);
            ko.connect(ke);ke.connect(master);ko.start(tStart);ko.stop(tStart+0.35);
        }

        var hlen=Math.floor(sr*0.04);
        var hbuf=off.createBuffer(1,hlen,sr),hd=hbuf.getChannelData(0);
        for(var hi=0;hi<hlen;hi++)hd[hi]=(Math.random()*2-1)*Math.pow(1-hi/hlen,4);
        var hs=off.createBufferSource();hs.buffer=hbuf;
        var hg=off.createGain();hg.gain.value=0.06;
        var hp=off.createBiquadFilter();hp.type='highpass';hp.frequency.value=8000;
        hs.connect(hp);hp.connect(hg);hg.connect(master);hs.start(tStart+0.001);

        if(bic===1||bic===3){
            var h2buf=off.createBuffer(1,hlen,sr),h2d=h2buf.getChannelData(0);
            for(var hi2=0;hi2<hlen;hi2++)h2d[hi2]=(Math.random()*2-1)*Math.pow(1-hi2/hlen,5);
            var h2s=off.createBufferSource();h2s.buffer=h2buf;
            var h2g=off.createGain();h2g.gain.value=0.03;
            var h2p=off.createBiquadFilter();h2p.type='highpass';h2p.frequency.value=9000;
            h2s.connect(h2p);h2p.connect(h2g);h2g.connect(master);h2s.start(tStart+beatSec*0.5);
        }
    }

    off.startRendering().then(function(buf){
        _trackBuffers[track.id]=buf;
        callback(buf);
    });
}

function stopLofi(){
    _lofiNodes.forEach(function(n){try{n.stop?n.stop():n.disconnect()}catch(e){}});
    _lofiNodes=[];_lofiPlaying=false;_lofiMaster=null;
    updatePlayerUI();
}

function startLofi(track){
    stopLofi();
    if(!track)track=_currentTrack||musicTracks[0];
    _currentTrack=track;
    var ctx=lofiCtx();
    renderTrackBuffer(track,function(buf){
        if(_currentTrack!==track)return;
        var master=ctx.createGain();master.gain.value=_lofiMuted?0:0.4;
        master.connect(ctx.destination);_lofiMaster=master;_lofiNodes.push(master);
        var src=ctx.createBufferSource();src.buffer=buf;src.loop=true;
        src.connect(master);src.start();_lofiNodes.push(src);
        _lofiPlaying=true;
        updatePlayerUI();
    });
}

function toggleMusic(e){
    if(e)e.stopPropagation();
    if(_lofiPlaying)stopLofi();
    else startLofi(_currentTrack||musicTracks[0]);
}

function toggleMusicVol(e){
    if(e)e.stopPropagation();
    _lofiMuted=!_lofiMuted;
    var btn=document.getElementById('mpVolBtn');
    if(_lofiMuted){btn.classList.add('muted');if(_lofiMaster)_lofiMaster.gain.value=0}
    else{btn.classList.remove('muted');if(_lofiMaster)_lofiMaster.gain.value=0.35}
}

function openMusicList(){
    _musicListOpen=!_musicListOpen;
    document.getElementById('musicList').classList.toggle('hidden',!_musicListOpen);
    renderMusicList();
}

function renderMusicList(){
    var el=document.getElementById('musicList');
    if(!el||el.classList.contains('hidden'))return;
    el.innerHTML=musicTracks.map(function(t){
        var active=_currentTrack&&_currentTrack.id===t.id;
        return'<div class="ml-track'+(active?' active':'')+'" onclick="pickTrack(\''+t.id+'\')">'
            +'<div class="ml-art" style="background:'+t.color+'"></div>'
            +'<div class="ml-info"><div class="ml-name">'+escapeHtml(t.name)+'</div><div class="ml-desc">'+escapeHtml(t.desc)+'</div></div>'
            +'</div>';
    }).join('');
}

function pickTrack(id){
    var track=musicTracks.find(function(t){return t.id===id});
    if(!track)return;
    _currentTrack=track;
    startLofi(track);
    _musicListOpen=false;
    document.getElementById('musicList').classList.add('hidden');
}
