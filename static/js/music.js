// Lofi-плеер (сейчас скрыт в интерфейсе)

// =============================================
// ===== LOFI MUSIC PLAYER =====
// =============================================

var _actx = null, _lofiNodes = [], _lofiPlaying = false, _lofiMuted = false, _lofiMaster = null, _lofiTimer = null;
var _currentTrack = null, _musicListOpen = false;

var musicTracks = [
    {
        id: 'lofi', name: 'Lofi Chill', desc: '72 bpm · мягкие аккорды', color: 'linear-gradient(135deg,#a040ff,#ff3060)', bpm: 72, wave: 'triangle', filterHz: 1500,
        chords: [[261.6, 329.6, 392, 493.9], [220, 277.2, 329.6, 415.3], [349.2, 440, 523.3, 659.3], [392, 493.9, 587.3, 740]]
    },
    {
        id: 'night', name: 'Night Drive', desc: '80 bpm · минорный синт', color: 'linear-gradient(135deg,#0044cc,#6600aa)', bpm: 80, wave: 'sawtooth', filterHz: 900,
        chords: [[220, 261.6, 329.6, 440], [196, 246.9, 293.7, 392], [174.6, 220, 261.6, 349.2], [196, 246.9, 329.6, 392]]
    },
    {
        id: 'morning', name: 'Morning Coffee', desc: '90 bpm · мажорный пиано', color: 'linear-gradient(135deg,#ff8820,#ffcc00)', bpm: 90, wave: 'triangle', filterHz: 2000,
        chords: [[293.7, 370, 440, 554.4], [261.6, 329.6, 392, 523.3], [349.2, 440, 523.3, 698.5], [392, 493.9, 587.3, 784]]
    },
    {
        id: 'ambient', name: 'Deep Focus', desc: '60 bpm · эмбиент дроны', color: 'linear-gradient(135deg,#004444,#006666)', bpm: 60, wave: 'sine', filterHz: 600,
        chords: [[130.8, 196, 261.6, 392], [146.8, 220, 293.7, 440], [164.8, 246.9, 329.6, 493.9], [130.8, 196, 261.6, 392]]
    },
    {
        id: 'jazz', name: 'Jazz Noir', desc: '68 bpm · джазовые септаккорды', color: 'linear-gradient(135deg,#330022,#880044)', bpm: 68, wave: 'triangle', filterHz: 1200,
        chords: [[261.6, 311.1, 392, 466.2], [293.7, 349.2, 440, 523.3], [349.2, 415.3, 523.3, 622.3], [311.1, 370, 466.2, 554.4]]
    }
];

var _trackBuffers = {};

function lofiCtx() {
    if (!_actx) _actx = new (window.AudioContext || window.webkitAudioContext)();
    if (_actx.state === 'suspended') _actx.resume();
    return _actx;
}

function updatePlayerUI() {
    var playIcon = document.getElementById('mpIconPlay'), pauseIcon = document.getElementById('mpIconPause');
    var playBtn = document.getElementById('mpPlayBtn'), title = document.getElementById('mpTitle'), sub = document.getElementById('mpSub');
    var art = document.getElementById('mpArt');
    if (_currentTrack && art) art.style.background = _currentTrack.color;
    if (_lofiPlaying && _currentTrack) {
        playIcon.classList.add('hidden'); pauseIcon.classList.remove('hidden');
        playBtn.classList.add('active'); title.classList.add('active');
        title.textContent = _currentTrack.name; sub.textContent = 'playing';
    } else {
        playIcon.classList.remove('hidden'); pauseIcon.classList.add('hidden');
        playBtn.classList.remove('active'); title.classList.remove('active');
        title.textContent = _currentTrack ? _currentTrack.name : 'Выбери музыку';
        sub.textContent = _currentTrack ? _currentTrack.desc : 'нажми чтобы открыть';
    }
    renderMusicList();
}

function renderTrackBuffer(track, callback) {
    if (_trackBuffers[track.id]) return callback(_trackBuffers[track.id]);
    var sr = 44100, bpm = track.bpm, beatSec = 60 / bpm;
    var totalBeats = 16, dur = totalBeats * beatSec;
    var len = Math.ceil(sr * dur), off = new OfflineAudioContext(2, len, sr);
    var master = off.createGain(); master.gain.value = 0.9; master.connect(off.destination);

    var chords = track.chords;
    for (var b = 0; b < totalBeats; b++) {
        var tStart = b * beatSec, chord = chords[Math.floor(b / 4) % chords.length], bic = b % 4;

        for (var v = 0; v < chord.length; v++) {
            var po = off.createOscillator(); po.type = 'sine'; po.frequency.value = chord[v];
            var pg = off.createGain(); pg.gain.setValueAtTime(0.04, tStart);
            var pf = off.createBiquadFilter(); pf.type = 'lowpass'; pf.frequency.value = track.filterHz * 0.5;
            po.connect(pf); pf.connect(pg); pg.connect(master);
            po.start(tStart); po.stop(tStart + beatSec);
        }

        var melNote = chord[bic % chord.length] * 2;
        var mo = off.createOscillator(); mo.type = track.wave; mo.frequency.value = melNote;
        var me = off.createGain(); me.gain.setValueAtTime(0, tStart);
        me.gain.linearRampToValueAtTime(0.12, tStart + 0.015);
        me.gain.exponentialRampToValueAtTime(0.001, tStart + beatSec * 0.8);
        var mf = off.createBiquadFilter(); mf.type = 'lowpass'; mf.frequency.value = track.filterHz;
        mo.connect(mf); mf.connect(me); me.connect(master);
        mo.start(tStart); mo.stop(tStart + beatSec);

        if (bic === 0 || bic === 2) {
            var ko = off.createOscillator(); ko.type = 'sine';
            ko.frequency.setValueAtTime(150, tStart);
            ko.frequency.exponentialRampToValueAtTime(40, tStart + 0.12);
            var ke = off.createGain(); ke.gain.setValueAtTime(0.25, tStart);
            ke.gain.exponentialRampToValueAtTime(0.001, tStart + 0.3);
            ko.connect(ke); ke.connect(master); ko.start(tStart); ko.stop(tStart + 0.35);
        }

        var hlen = Math.floor(sr * 0.04);
        var hbuf = off.createBuffer(1, hlen, sr), hd = hbuf.getChannelData(0);
        for (var hi = 0; hi < hlen; hi++)hd[hi] = (Math.random() * 2 - 1) * Math.pow(1 - hi / hlen, 4);
        var hs = off.createBufferSource(); hs.buffer = hbuf;
        var hg = off.createGain(); hg.gain.value = 0.06;
        var hp = off.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 8000;
        hs.connect(hp); hp.connect(hg); hg.connect(master); hs.start(tStart + 0.001);

        if (bic === 1 || bic === 3) {
            var h2buf = off.createBuffer(1, hlen, sr), h2d = h2buf.getChannelData(0);
            for (var hi2 = 0; hi2 < hlen; hi2++)h2d[hi2] = (Math.random() * 2 - 1) * Math.pow(1 - hi2 / hlen, 5);
            var h2s = off.createBufferSource(); h2s.buffer = h2buf;
            var h2g = off.createGain(); h2g.gain.value = 0.03;
            var h2p = off.createBiquadFilter(); h2p.type = 'highpass'; h2p.frequency.value = 9000;
            h2s.connect(h2p); h2p.connect(h2g); h2g.connect(master); h2s.start(tStart + beatSec * 0.5);
        }
    }

    off.startRendering().then(function (buf) {
        _trackBuffers[track.id] = buf;
        callback(buf);
    });
}

function stopLofi() {
    _lofiNodes.forEach(function (n) { try { n.stop ? n.stop() : n.disconnect() } catch (e) { } });
    _lofiNodes = []; _lofiPlaying = false; _lofiMaster = null;
    updatePlayerUI();
}

function startLofi(track) {
    stopLofi();
    if (!track) track = _currentTrack || musicTracks[0];
    _currentTrack = track;
    var ctx = lofiCtx();
    renderTrackBuffer(track, function (buf) {
        if (_currentTrack !== track) return;
        var master = ctx.createGain(); master.gain.value = _lofiMuted ? 0 : 0.4;
        master.connect(ctx.destination); _lofiMaster = master; _lofiNodes.push(master);
        var src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
        src.connect(master); src.start(); _lofiNodes.push(src);
        _lofiPlaying = true;
        updatePlayerUI();
    });
}

function toggleMusic(e) {
    if (e) e.stopPropagation();
    if (_lofiPlaying) stopLofi();
    else startLofi(_currentTrack || musicTracks[0]);
}

function toggleMusicVol(e) {
    if (e) e.stopPropagation();
    _lofiMuted = !_lofiMuted;
    var btn = document.getElementById('mpVolBtn');
    if (_lofiMuted) { btn.classList.add('muted'); if (_lofiMaster) _lofiMaster.gain.value = 0 }
    else { btn.classList.remove('muted'); if (_lofiMaster) _lofiMaster.gain.value = 0.35 }
}

function openMusicList() {
    _musicListOpen = !_musicListOpen;
    document.getElementById('musicList').classList.toggle('hidden', !_musicListOpen);
    renderMusicList();
}

function renderMusicList() {
    var el = document.getElementById('musicList');
    if (!el || el.classList.contains('hidden')) return;
    el.innerHTML = musicTracks.map(function (t) {
        var active = _currentTrack && _currentTrack.id === t.id;
        return '<div class="ml-track' + (active ? ' active' : '') + '" onclick="pickTrack(\'' + t.id + '\')">'
            + '<div class="ml-art" style="background:' + t.color + '"></div>'
            + '<div class="ml-info"><div class="ml-name">' + escapeHtml(t.name) + '</div><div class="ml-desc">' + escapeHtml(t.desc) + '</div></div>'
            + '</div>';
    }).join('');
}

function pickTrack(id) {
    var track = musicTracks.find(function (t) { return t.id === id });
    if (!track) return;
    _currentTrack = track;
    startLofi(track);
    _musicListOpen = false;
    document.getElementById('musicList').classList.add('hidden');
}
