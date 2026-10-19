// Фоновые темы и анимация пятен

var bgThemes = {
    crimson: {
        name: 'Crimson',
        preview: ['#ff1414', '#a00aff', '#dc0a5a'],
        blobs: [
            ['radial-gradient(circle,rgba(255,20,20,1) 0%,rgba(200,10,60,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,60,30,1) 0%,rgba(220,10,40,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(220,10,80,1) 0%,rgba(170,5,100,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,30,50,1) 0%,rgba(200,10,50,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(160,10,255,1) 0%,rgba(100,5,220,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(130,5,240,1) 0%,rgba(90,5,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(180,20,255,1) 0%,rgba(120,5,210,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(150,10,250,1) 0%,rgba(110,5,215,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(220,10,90,1) 0%,rgba(160,5,140,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(240,20,100,1) 0%,rgba(180,5,130,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(200,5,110,1) 0%,rgba(150,5,150,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(230,15,95,1) 0%,rgba(170,5,135,0.6) 45%,transparent 72%)']
        ]
    },
    ocean: {
        name: 'Ocean',
        preview: ['#0066ff', '#00ccbb', '#0088dd'],
        blobs: [
            ['radial-gradient(circle,rgba(0,100,255,1) 0%,rgba(0,60,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,130,255,1) 0%,rgba(0,80,220,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,80,240,1) 0%,rgba(0,50,180,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(20,110,255,1) 0%,rgba(10,70,210,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,200,180,1) 0%,rgba(0,150,140,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,220,200,1) 0%,rgba(0,170,160,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,180,160,1) 0%,rgba(0,130,120,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(10,210,190,1) 0%,rgba(5,160,150,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,140,220,1) 0%,rgba(0,90,180,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,160,240,1) 0%,rgba(0,110,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,120,200,1) 0%,rgba(0,80,160,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(10,150,230,1) 0%,rgba(5,100,190,0.6) 45%,transparent 72%)']
        ]
    },
    aurora: {
        name: 'Aurora',
        preview: ['#00e080', '#00bbff', '#8840ff'],
        blobs: [
            ['radial-gradient(circle,rgba(0,224,128,1) 0%,rgba(0,180,90,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,240,140,1) 0%,rgba(0,200,100,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,200,110,1) 0%,rgba(0,160,80,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(20,230,130,1) 0%,rgba(10,190,95,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,190,255,1) 0%,rgba(0,140,220,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,210,255,1) 0%,rgba(0,160,240,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,170,240,1) 0%,rgba(0,120,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(10,200,255,1) 0%,rgba(5,150,230,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(136,64,255,1) 0%,rgba(100,30,220,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(150,80,255,1) 0%,rgba(115,45,235,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(120,50,240,1) 0%,rgba(85,20,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(140,70,250,1) 0%,rgba(105,35,225,0.6) 45%,transparent 72%)']
        ]
    },
    sunset: {
        name: 'Sunset',
        preview: ['#ff6020', '#ff2080', '#ffaa00'],
        blobs: [
            ['radial-gradient(circle,rgba(255,96,32,1) 0%,rgba(220,60,10,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,120,40,1) 0%,rgba(240,80,20,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(240,80,20,1) 0%,rgba(200,50,5,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,100,30,1) 0%,rgba(230,70,15,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(255,32,128,1) 0%,rgba(220,10,90,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,50,140,1) 0%,rgba(235,20,100,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(240,20,110,1) 0%,rgba(200,5,80,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(250,40,130,1) 0%,rgba(215,15,95,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(255,170,0,1) 0%,rgba(220,140,0,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,190,20,1) 0%,rgba(240,160,10,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(240,150,0,1) 0%,rgba(200,120,0,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,180,10,1) 0%,rgba(230,150,5,0.6) 45%,transparent 72%)']
        ]
    },
    neon: {
        name: 'Neon',
        preview: ['#ff00aa', '#00ffcc', '#4400ff'],
        blobs: [
            ['radial-gradient(circle,rgba(255,0,170,1) 0%,rgba(200,0,130,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(255,20,180,1) 0%,rgba(220,10,140,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(240,0,160,1) 0%,rgba(190,0,120,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(250,10,175,1) 0%,rgba(210,5,135,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,255,204,1) 0%,rgba(0,200,160,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,255,220,1) 0%,rgba(0,220,175,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,240,190,1) 0%,rgba(0,190,150,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(10,250,210,1) 0%,rgba(5,210,165,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(68,0,255,1) 0%,rgba(50,0,200,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(80,10,255,1) 0%,rgba(60,5,220,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(55,0,240,1) 0%,rgba(40,0,190,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(70,5,250,1) 0%,rgba(55,2,210,0.6) 45%,transparent 72%)']
        ]
    },
    midnight: {
        name: 'Midnight',
        preview: ['#1a0050', '#000066', '#220044'],
        blobs: [
            ['radial-gradient(circle,rgba(26,0,80,1) 0%,rgba(18,0,55,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(35,0,90,1) 0%,rgba(25,0,65,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(20,0,70,1) 0%,rgba(14,0,48,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(30,0,85,1) 0%,rgba(22,0,60,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(0,0,102,1) 0%,rgba(0,0,70,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,0,120,1) 0%,rgba(0,0,85,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,0,90,1) 0%,rgba(0,0,60,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(0,0,110,1) 0%,rgba(0,0,78,0.6) 45%,transparent 72%)'],
            ['radial-gradient(circle,rgba(34,0,68,1) 0%,rgba(24,0,48,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(42,0,78,1) 0%,rgba(30,0,56,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(28,0,58,1) 0%,rgba(20,0,40,0.6) 45%,transparent 72%)', 'radial-gradient(circle,rgba(38,0,72,1) 0%,rgba(27,0,52,0.6) 45%,transparent 72%)']
        ]
    }
};

var blobEls = [document.querySelector('.blob1'), document.querySelector('.blob2'), document.querySelector('.blob3')];
var blobData = [];
var blobIntervals = [];

function applyBgTheme(themeKey) {
    var theme = bgThemes[themeKey] || bgThemes.midnight;
    blobIntervals.forEach(function (id) { clearInterval(id) });
    blobIntervals = [];
    blobData = theme.blobs.map(function (colors, i) { return { el: blobEls[i], colors: colors } });
    var delays = [5000, 7500, 10000];
    blobData.forEach(function (b, i) { startBlob(b, delays[i]) });
    localStorage.setItem('bgTheme', themeKey);
}

function rndBlob(min, max) { return Math.random() * (max - min) + min }
function moveBlob(b) { var s = rndBlob(500, 680); b.el.style.width = s + 'px'; b.el.style.height = s + 'px'; b.el.style.top = rndBlob(0, 100) + '%'; b.el.style.left = rndBlob(0, 100) + '%'; b.el.style.opacity = rndBlob(0.55, 0.85); b.el.style.background = b.colors[Math.floor(Math.random() * b.colors.length)] }
function startBlob(b, i) { moveBlob(b); blobIntervals.push(setInterval(function () { moveBlob(b) }, i)) }
applyBgTheme(localStorage.getItem('bgTheme') || 'midnight');
