/**
 * NHL tile — one panel that follows the whole NHL season (day mode).
 *
 * It rotates through "views" every few seconds (NHL_TILE_ROTATE_INTERVAL):
 *   Regular season: last night → standings (per conference) → scoring leaders
 *                   → goalie leaders → tonight
 *   Playoffs:       bracket → last night → playoff scoring leaders
 *                   → playoff goalie leaders → tonight
 * Playoff mode is decided by the backend: only while the playoffs are on.
 *
 * The playoff bracket ("spider") narrows as the playoffs progress: the full
 * 16-team tree in round 1, 8 teams in round 2, 4 in the conference finals and
 * only the two finalists in the Stanley Cup Final (then the champion).
 *
 * Data arrives over the WebSocket ('nhl' messages + the initial state). Views
 * without data (no games last night, empty leader boards, ...) are skipped.
 * Rotation pauses while the tile is hidden (morning / night modes).
 */

const NHL_ASSETS = 'https://assets.nhle.com/logos/nhl/svg/';

// Official team colors [primary, secondary]. Where the primary is (near) black,
// the brighter brand color goes first so the team still reads on the dark theme.
const NHL_TEAM_COLORS = Object.freeze({
    ANA: ['#FC4C02', '#B9975B'], BOS: ['#FFB81C', '#000000'], BUF: ['#003087', '#FFB81C'],
    CAR: ['#CE1126', '#000000'], CBJ: ['#002654', '#CE1126'], CGY: ['#C8102E', '#F1BE48'],
    CHI: ['#CF0A2C', '#000000'], COL: ['#6F263D', '#236192'], DAL: ['#006847', '#8F8F8C'],
    DET: ['#CE1126', '#FFFFFF'], EDM: ['#FF4C00', '#041E42'], FLA: ['#C8102E', '#B9975B'],
    LAK: ['#A2AAAD', '#111111'], MIN: ['#154734', '#A6192E'], MTL: ['#AF1E2D', '#192168'],
    NJD: ['#CE1126', '#000000'], NSH: ['#FFB81C', '#041E42'], NYI: ['#00539B', '#F47D30'],
    NYR: ['#0038A8', '#CE1126'], OTT: ['#DA1A32', '#B79257'], PHI: ['#F74902', '#000000'],
    PIT: ['#FCB514', '#000000'], SEA: ['#99D9D9', '#001628'], SJS: ['#006D75', '#EA7200'],
    STL: ['#002F87', '#FCB514'], TBL: ['#002868', '#FFFFFF'], TOR: ['#00205B', '#FFFFFF'],
    UTA: ['#6CACE4', '#000000'], VAN: ['#00205B', '#00843D'], VGK: ['#B4975A', '#333F42'],
    WPG: ['#004C97', '#AC162C'], WSH: ['#C8102E', '#041E42']
});

const NhlTile = {
    data: null,
    rotateMs: 10000,
    timer: null,
    currentKey: null,
    currentIndex: -1,
    renderedData: null,

    // Layout constants — keep in sync with style.css (.nhl-game height / gap)
    GAME_CARD_H: 92,
    GAME_GAP: 10,

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    init(rotateMs) {
        if (rotateMs > 0) this.rotateMs = rotateMs;
        this.restartTimer();
    },

    setRotateInterval(ms) {
        if (!(ms > 0) || ms === this.rotateMs) return;
        this.rotateMs = ms;
        this.restartTimer();
    },

    restartTimer() {
        clearInterval(this.timer);
        this.timer = setInterval(() => this.advance(), this.rotateMs);
    },

    /** New data from the WebSocket. Shows up on the next rotation (no mid-view flicker). */
    update(data) {
        const first = !this.data;
        this.data = data || null;
        const rect = document.getElementById('nhl-rect');
        if (rect) rect.classList.toggle('nhl-playoffs', !!(this.data && this.data.phase === 'playoffs'));
        if (first || this.currentIndex < 0) this.showAt(0);
    },

    /** Called by kiosk.js when the tile becomes visible (day mode starts). */
    onShow() {
        this.currentKey = null;
        this.currentIndex = -1;
        this.showAt(0);
        this.restartTimer();
    },

    isVisible() {
        const rect = document.getElementById('nhl-rect');
        return !!(rect && rect.offsetParent !== null);
    },

    advance() {
        if (!this.isVisible()) return;
        const views = this.buildViews();
        if (!views.length) return this.renderEmpty();
        const at = views.findIndex(v => v.key === this.currentKey);
        const next = ((at >= 0 ? at : this.currentIndex) + 1) % views.length;
        // A single view only re-renders when its data changed
        if (views.length === 1 && views[0].key === this.currentKey && this.renderedData === this.data) {
            this.restartProgress();
            return;
        }
        this.show(views, next);
    },

    showAt(index) {
        if (!this.isVisible()) return;
        const views = this.buildViews();
        if (!views.length) return this.renderEmpty();
        this.show(views, Math.min(index, views.length - 1));
    },

    show(views, index) {
        const view = views[index];
        this.currentKey = view.key;
        this.currentIndex = index;
        this.renderedData = this.data;

        const title = document.getElementById('nhl-title');
        const sub = document.getElementById('nhl-sub');
        const dots = document.getElementById('nhl-dots');
        const body = document.getElementById('nhl-body');
        if (title) title.textContent = view.title;
        if (sub) sub.textContent = view.sub || '';
        if (dots) dots.innerHTML = views.map((v, i) => `<span class="${i === index ? 'on' : ''}"></span>`).join('');
        if (body) {
            body.innerHTML = `<div class="nhl-view nhl-view-${view.type}">${view.render()}</div>`;
            this.fitLists(body);
        }
        this.restartProgress();
    },

    /** Leader lists render every player we have; drop the rows that don't fit the column. */
    fitLists(root) {
        root.querySelectorAll('.nhl-ld-list').forEach(list => {
            const rows = Array.from(list.children);
            // Use layout positions, not scrollHeight: the rows' slide-in transform
            // temporarily adds overflow that scrollHeight would count
            while (rows.length) {
                const last = rows[rows.length - 1];
                if (last.offsetTop - list.offsetTop + last.offsetHeight <= list.clientHeight + 1) break;
                rows.pop().remove();
            }
        });
    },

    renderEmpty() {
        const body = document.getElementById('nhl-body');
        const sub = document.getElementById('nhl-sub');
        if (body) body.innerHTML = `<div class="nhl-empty">${this.data ? 'No NHL data right now' : 'Loading NHL…'}</div>`;
        if (sub) sub.textContent = '';
        this.currentKey = null;
        this.currentIndex = -1;
    },

    restartProgress() {
        const bar = document.getElementById('nhl-progress-bar');
        if (!bar) return;
        bar.style.animation = 'none';
        void bar.offsetWidth; // force reflow so the animation restarts
        bar.style.animation = `nhl-progress ${this.rotateMs}ms linear forwards`;
    },

    // ------------------------------------------------------------------
    // View list
    // ------------------------------------------------------------------

    buildViews() {
        const d = this.data;
        if (!d) return [];

        const body = document.getElementById('nhl-body');
        const size = { w: body ? body.clientWidth : 0, h: body ? body.clientHeight : 0 };
        const wide = size.w >= 700;
        const playoffs = d.phase === 'playoffs' && d.bracket;
        const views = [];

        if (playoffs) {
            views.push({
                key: 'bracket', type: 'bracket', title: 'Stanley Cup Playoffs',
                sub: this.stageLabel(d.bracket, d.season),
                render: () => this.renderBracket(d)
            });
        }

        const results = d.results || [];
        if (results.length) {
            const pages = this.paginate(results, this.gamesPerPage(size));
            pages.forEach((page, i) => views.push({
                key: `results-${i}`, type: 'games', title: 'Last Night',
                sub: this.formatDate(d.results_date) + (pages.length > 1 ? ` · ${i + 1}/${pages.length}` : ''),
                render: () => this.renderGames(page, {}, size)
            }));
        }

        if (!playoffs && (d.standings || []).length) {
            const conferences = this.groupStandings(d.standings);
            conferences.forEach(conf => {
                if (wide) {
                    views.push({
                        key: `standings-${conf.name}`, type: 'standings', title: 'Standings',
                        sub: `${conf.name} Conference`,
                        render: () => this.renderStandings(conf.divisions)
                    });
                } else {
                    conf.divisions.forEach(div => views.push({
                        key: `standings-${div.name}`, type: 'standings', title: 'Standings',
                        sub: `${div.name} Division`,
                        render: () => this.renderStandings([div])
                    }));
                }
            });
        }

        const season = this.seasonLabel(d.season, playoffs);
        if ((d.skater_leaders || []).some(b => b.leaders.length)) {
            views.push({
                key: 'skaters', type: 'leaders', title: playoffs ? 'Playoff Scoring' : 'Scoring Leaders',
                sub: season, render: () => this.renderLeaders(d.skater_leaders)
            });
        }
        if ((d.goalie_leaders || []).some(b => b.leaders.length)) {
            views.push({
                key: 'goalies', type: 'leaders', title: playoffs ? 'Playoff Goalies' : 'Goalie Leaders',
                sub: season, render: () => this.renderLeaders(d.goalie_leaders)
            });
        }

        const upcoming = d.upcoming || [];
        if (upcoming.length) {
            const records = this.recordsByTeam(d);
            const pages = this.paginate(upcoming, this.gamesPerPage(size));
            pages.forEach((page, i) => views.push({
                key: `tonight-${i}`, type: 'games', title: 'Tonight',
                sub: this.formatDate(d.upcoming_date) + ' · Prague time' + (pages.length > 1 ? ` · ${i + 1}/${pages.length}` : ''),
                render: () => this.renderGames(page, records, size)
            }));
        }

        return views;
    },

    gameCols(width) {
        return width >= 860 ? 3 : width >= 540 ? 2 : 1;
    },

    gamesPerPage(size) {
        const cols = this.gameCols(size.w);
        const rows = Math.max(1, Math.floor((size.h + this.GAME_GAP) / (this.GAME_CARD_H + this.GAME_GAP)));
        return cols * rows;
    },

    /** Split into evenly sized pages (11 games at 8/page → 6 + 5, not 8 + 3). */
    paginate(items, perPage) {
        const pages = Math.max(1, Math.ceil(items.length / Math.max(1, perPage)));
        const size = Math.ceil(items.length / pages);
        const out = [];
        for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
        return out;
    },

    // ------------------------------------------------------------------
    // Small helpers
    // ------------------------------------------------------------------

    esc(value) {
        return String(value ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
    },

    colors(abbrev) {
        return NHL_TEAM_COLORS[abbrev] || ['#64748b', '#94a3b8'];
    },

    teamVars(abbrev) {
        const [c1, c2] = this.colors(abbrev);
        return `--tc1:${c1};--tc2:${c2};`;
    },

    logo(abbrev, cls = 'nhl-logo') {
        if (!abbrev) return `<span class="${cls} nhl-logo-tbd"></span>`;
        const a = this.esc(abbrev);
        return `<img class="${cls}" src="${NHL_ASSETS}${a}_dark.svg" alt="${a}" onerror="this.style.visibility='hidden'">`;
    },

    headshot(url, abbrev, cls = 'nhl-shot') {
        return `<span class="${cls}" style="${this.teamVars(abbrev)}">` +
            `<img src="${this.esc(url)}" alt="" onerror="this.style.visibility='hidden'"></span>`;
    },

    /** "2026-11-05" → "Thu 5 Nov" (noon avoids any timezone date shift). */
    formatDate(isoDate) {
        if (!isoDate) return '';
        const d = new Date(`${isoDate}T12:00:00`);
        return isNaN(d) ? isoDate : d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
    },

    formatTime(startUtc) {
        const d = new Date(startUtc);
        return isNaN(d) ? '' : d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
    },

    /** "20262027" → "Regular season 2026–27" / "2027 Playoffs". */
    seasonLabel(season, playoffs) {
        if (!season || season.length !== 8) return playoffs ? 'Playoffs' : 'Regular season';
        return playoffs ? `${season.slice(4)} Playoffs` : `Regular season ${season.slice(0, 4)}–${season.slice(6)}`;
    },

    stageLabel(bracket, season) {
        const labels = { 1: 'First Round', 2: 'Second Round', 3: 'Conference Finals', 4: 'Stanley Cup Final' };
        if (bracket.stage >= 5) return `${season ? season.slice(4) + ' ' : ''}Stanley Cup Champions`;
        return labels[bracket.stage] || '';
    },

    periodLabel(period, periodType) {
        if (periodType === 'SO') return 'SO';
        if (periodType === 'OT') return period > 4 ? `${period - 3}OT` : 'OT';
        return `P${period}`;
    },

    shortClock(t) {
        return (t || '').replace(/^0(\d:)/, '$1');
    },

    formatLeaderValue(category, value) {
        if (category === 'savePctg') return value.toFixed(3).replace(/^0/, '');
        if (category === 'goalsAgainstAverage') return value.toFixed(2);
        return String(Math.round(value));
    },

    /** Team W-L-OT records from the standings, shown on tonight's cards. */
    recordsByTeam(d) {
        const map = {};
        if (d.phase === 'playoffs') return map;
        (d.standings || []).forEach(t => { map[t.abbrev] = `${t.wins}-${t.losses}-${t.ot_losses}`; });
        return map;
    },

    groupStandings(rows) {
        const confs = {};
        rows.forEach(r => {
            const conf = confs[r.conference] || (confs[r.conference] = {});
            (conf[r.division] || (conf[r.division] = [])).push(r);
        });
        return Object.keys(confs).sort().map(name => ({
            name,
            divisions: Object.keys(confs[name]).sort().map(div => ({
                name: div,
                teams: confs[name][div].slice().sort((a, b) => a.division_rank - b.division_rank)
            }))
        }));
    },

    // ------------------------------------------------------------------
    // Scoreboard (last night / tonight)
    // ------------------------------------------------------------------

    gameStatus(g) {
        if (g.schedule_state === 'PPD') return { label: 'Postponed', cls: 'off' };
        if (g.schedule_state === 'CNCL') return { label: 'Cancelled', cls: 'off' };
        if (g.state === 'OFF' || g.state === 'FINAL') {
            const suffix = g.period_type === 'SO' ? '/SO' : g.period_type === 'OT' ? `/${this.periodLabel(g.period, 'OT')}` : '';
            return { label: `Final${suffix}`, cls: 'final' };
        }
        if (g.state === 'LIVE' || g.state === 'CRIT') {
            const p = this.periodLabel(g.period, g.period_type);
            return { label: g.in_intermission ? `${p} Intermission` : `${p} ${this.shortClock(g.clock)}`, cls: 'live' };
        }
        return { label: this.formatTime(g.start_utc), cls: 'future' };
    },

    gameMeta(g) {
        const parts = [];
        if (g.series_status) parts.push(`${g.series_game ? `G${g.series_game} · ` : ''}${g.series_status}`);
        if (g.decider) {
            parts.push(g.decider_when === 'SO'
                ? `SO winner ${g.decider}`
                : `GWG ${g.decider} · ${g.decider_when.replace(/ 0(\d:)/, ' $1')}`);
        } else if ((g.state === 'LIVE' || g.state === 'CRIT') && g.away.sog != null && g.home.sog != null) {
            parts.push(`Shots ${g.away.sog}–${g.home.sog}`);
        }
        return parts.join(' · ');
    },

    gameParts(g) {
        const st = this.gameStatus(g);
        const final = st.cls === 'final';
        return {
            st,
            hasScore: g.away.score != null && g.home.score != null,
            awayWin: final && g.away.score > g.home.score,
            homeWin: final && g.home.score > g.away.score,
            meta: this.gameMeta(g)
        };
    },

    statusHtml(st) {
        return `${st.cls === 'live' ? '<i class="nhl-live-dot"></i>' : ''}${this.esc(st.label)}`;
    },

    scoreHtml(t, hasScore, records) {
        return hasScore ? String(t.score) : `<small>${this.esc(records[t.abbrev] || '')}</small>`;
    },

    /**
     * Scoreboard page. Cards always fill the body height:
     *   1-3 games → wide "versus" rows, one per line, big logos
     *   4-6 games → cards in 2 columns, scaled up
     *   7+ games  → cards in 3 columns, rows stretched to fit
     */
    renderGames(games, records, size) {
        const n = games.length;
        const versus = n <= 3;
        const cols = versus ? 1 : (n <= 6 && size.w >= 540 ? 2 : this.gameCols(size.w));
        const rows = Math.max(1, Math.ceil(n / cols));
        const fit = (size.h - (rows - 1) * this.GAME_GAP) / rows;
        // Card contents scale with the card (CSS container units), so bigger rows = bigger logos/text
        const rowH = Math.max(this.GAME_CARD_H, Math.floor(Math.min(fit, versus ? 260 : 200)));
        const cards = games.map((g, i) => versus ? this.versusCard(g, i, records) : this.compactCard(g, i, records)).join('');
        return `<div class="nhl-games" style="--cols:${cols};grid-auto-rows:${rowH}px">${cards}</div>`;
    },

    compactCard(g, i, records) {
        const p = this.gameParts(g);
        const team = (t, win, lose) => `
            <div class="nhl-gt${win ? ' win' : ''}${lose ? ' lose' : ''}" style="${this.teamVars(t.abbrev)}">
                ${this.logo(t.abbrev)}
                <span class="nhl-gt-abbr">${this.esc(t.abbrev)}</span>
                <span class="nhl-gt-name">${this.esc(t.name)}</span>
                <span class="nhl-gt-score">${this.scoreHtml(t, p.hasScore, records)}</span>
            </div>`;
        return `
            <div class="nhl-game nhl-game-${p.st.cls}" style="--i:${i}">
                <div class="nhl-game-status">${this.statusHtml(p.st)}</div>
                ${team(g.away, p.awayWin, p.homeWin)}
                ${team(g.home, p.homeWin, p.awayWin)}
                <div class="nhl-game-meta">${this.esc(p.meta)}</div>
            </div>`;
    },

    versusCard(g, i, records) {
        const p = this.gameParts(g);
        const side = (t, win, lose, where) => `
            <div class="nhl-vs-team ${where}${win ? ' win' : ''}${lose ? ' lose' : ''}" style="${this.teamVars(t.abbrev)}">
                ${this.logo(t.abbrev)}
                <span class="nhl-vs-names"><b>${this.esc(t.abbrev)}</b><small>${this.esc(t.name)}</small></span>
                ${p.hasScore
                    ? `<span class="nhl-vs-score">${t.score}</span>`
                    : `<span class="nhl-vs-rec">${this.esc(records[t.abbrev] || '')}</span>`}
            </div>`;
        return `
            <div class="nhl-vs nhl-game-${p.st.cls}" style="--i:${i}">
                ${side(g.away, p.awayWin, p.homeWin, 'away')}
                <div class="nhl-vs-mid">
                    <span class="nhl-vs-status">${this.statusHtml(p.st)}</span>
                    ${p.meta ? `<span class="nhl-vs-meta">${this.esc(p.meta)}</span>` : ''}
                </div>
                ${side(g.home, p.homeWin, p.awayWin, 'home')}
            </div>`;
    },

    // ------------------------------------------------------------------
    // Standings (regular season)
    // ------------------------------------------------------------------

    renderStandings(divisions) {
        const tables = divisions.map(div => {
            const rows = div.teams.map((t, i) => {
                // Wildcards are conference-wide: WC1/WC2 hold the spots, WC3+ are chasing
                const wc = t.wildcard_rank > 0
                    ? `<em class="nhl-wc${t.wildcard_rank > 2 ? ' chase' : ''}">WC${t.wildcard_rank}</em>` : '';
                const clinch = t.clinch ? `<sup class="nhl-clinch">${this.esc(t.clinch)}</sup>` : '';
                const streakCls = (t.streak || '').charAt(0) === 'W' ? 'w' : (t.streak || '').charAt(0) === 'L' ? 'l' : 'ot';
                return `
                    <div class="nhl-st-row${t.division_rank === 3 ? ' nhl-cutline' : ''}" style="${this.teamVars(t.abbrev)}--i:${i}">
                        <span class="nhl-st-rank">${t.division_rank}</span>
                        ${this.logo(t.abbrev)}
                        <span class="nhl-st-team"><span class="nhl-st-line">${clinch}<span class="nhl-st-name">${this.esc(t.name)}</span></span>${wc}</span>
                        <span>${t.games_played}</span>
                        <span>${t.wins}</span>
                        <span>${t.losses}</span>
                        <span>${t.ot_losses}</span>
                        <span class="nhl-st-pts">${t.points}</span>
                        <span class="nhl-c-l10">${this.esc(t.l10)}</span>
                        <span class="nhl-c-stk nhl-stk-${streakCls}">${this.esc(t.streak)}</span>
                    </div>`;
            }).join('');
            return `
                <div class="nhl-div">
                    <div class="nhl-div-title">${this.esc(div.name)}</div>
                    <div class="nhl-st-row nhl-st-head">
                        <span>#</span><span></span><span class="nhl-st-team">Team</span>
                        <span>GP</span><span>W</span><span>L</span><span>OT</span>
                        <span class="nhl-st-pts">PTS</span><span class="nhl-c-l10">L10</span><span class="nhl-c-stk">STK</span>
                    </div>
                    ${rows}
                </div>`;
        }).join('');
        return `<div class="nhl-standings" style="--cols:${divisions.length}">${tables}</div>`;
    },

    // ------------------------------------------------------------------
    // Leader boards (skaters / goalies)
    // ------------------------------------------------------------------

    renderLeaders(boards) {
        const cols = boards.filter(b => b.leaders.length).map(board => {
            const [first, ...rest] = board.leaders;
            const fmt = v => this.formatLeaderValue(board.category, v);
            const list = rest.map((p, i) => `
                <div class="nhl-ld-row" style="${this.teamVars(p.team)}--i:${i + 1}">
                    <span class="nhl-ld-rank">${i + 2}</span>
                    ${this.headshot(p.headshot, p.team, 'nhl-shot nhl-shot-sm')}
                    ${this.logo(p.team, 'nhl-logo nhl-logo-xs')}
                    <span class="nhl-ld-name">${this.esc(p.last_name)}</span>
                    <span class="nhl-ld-val">${fmt(p.value)}</span>
                </div>`).join('');
            return `
                <div class="nhl-ld-col">
                    <div class="nhl-ld-label">${this.esc(board.label)}</div>
                    <div class="nhl-ld-top" style="${this.teamVars(first.team)}--i:0">
                        ${this.headshot(first.headshot, first.team, 'nhl-shot nhl-shot-xl')}
                        <div class="nhl-ld-top-info">
                            <span class="nhl-ld-first">${this.esc(first.first_name)}</span>
                            <span class="nhl-ld-last">${this.esc(first.last_name)}</span>
                            <span class="nhl-ld-team">${this.logo(first.team, 'nhl-logo nhl-logo-xs')}${this.esc(first.team)}${first.number ? ` · #${first.number}` : ''}</span>
                            <span class="nhl-ld-top-val">${fmt(first.value)}</span>
                        </div>
                    </div>
                    <div class="nhl-ld-list">${list}</div>
                </div>`;
        }).join('');
        return `<div class="nhl-leaders">${cols}</div>`;
    },

    // ------------------------------------------------------------------
    // Playoff bracket ("spider")
    // ------------------------------------------------------------------

    seriesMap(bracket) {
        const map = {};
        (bracket.series || []).forEach(s => { map[s.letter] = s; });
        // Stanley Cup Final not created yet → finalists are the conference final winners
        if (!map.O && (map.M || map.N)) {
            const finalist = s => (s && s.winner ? { abbrev: s.winner, name: '', seed: '', wins: 0 } : null);
            map.O = { letter: 'O', round: 4, title: 'Stanley Cup Final', top: finalist(map.M), bottom: finalist(map.N), winner: null, needed_to_win: 4 };
        }
        return map;
    },

    /** One line under a series: live score, result, or who leads + next game. */
    seriesNote(s, d) {
        if (!s || !s.top || !s.bottom) return '';
        const games = [...(d.results || []), ...(d.upcoming || [])].filter(g => g.series_letter === s.letter);
        const live = games.find(g => g.state === 'LIVE' || g.state === 'CRIT');
        if (live) {
            return `<i class="nhl-live-dot"></i>G${live.series_game || ''} ${this.esc(this.gameStatus(live).label)} · ` +
                `${this.esc(live.away.abbrev)} ${live.away.score}–${live.home.score} ${this.esc(live.home.abbrev)}`;
        }
        const t = s.top, b = s.bottom;
        if (s.winner) {
            const w = s.winner === t.abbrev ? t : b;
            const l = w === t ? b : t;
            return `${this.esc(w.abbrev)} wins ${w.wins}–${l.wins}`;
        }
        const lead = t.wins >= b.wins ? t : b;
        const status = t.wins === b.wins ? `Tied ${t.wins}–${b.wins}` : `${this.esc(lead.abbrev)} leads ${Math.max(t.wins, b.wins)}–${Math.min(t.wins, b.wins)}`;
        const next = (d.upcoming || []).find(g => g.series_letter === s.letter && (g.state === 'FUT' || g.state === 'PRE'));
        return next ? `${status} · G${next.series_game || ''} ${this.formatTime(next.start_utc)}` : status;
    },

    bracketCard(s, size, d) {
        const team = t => {
            if (!t) {
                return `<div class="nhl-bt nhl-bt-tbd">${this.logo(null)}<span class="nhl-bt-abbr">TBD</span><span class="nhl-bt-wins"></span></div>`;
            }
            const won = s && s.winner === t.abbrev;
            const out = s && s.winner && !won;
            return `
                <div class="nhl-bt${won ? ' win' : ''}${out ? ' out' : ''}" style="${this.teamVars(t.abbrev)}">
                    ${this.logo(t.abbrev)}
                    <span class="nhl-bt-abbr">${this.esc(t.abbrev)}</span>
                    <span class="nhl-bt-name">${this.esc(t.name)}</span>
                    <span class="nhl-bt-seed">${this.esc(t.seed)}</span>
                    <span class="nhl-bt-wins">${s ? t.wins : ''}</span>
                </div>`;
        };
        const live = s && s.top && s.bottom && !s.winner && (s.top.wins + s.bottom.wins) > 0;
        // Notes only on the bigger cards; always rendered so paired cards keep equal heights
        const note = size === 'sm' ? '' : `<div class="nhl-bnote">${this.seriesNote(s, d) || '&nbsp;'}</div>`;
        return `<div class="nhl-bs nhl-bs-${size}${s && s.winner ? ' done' : ''}${live ? ' active' : ''}">
                    ${team(s && s.top)}${team(s && s.bottom)}${note}
                </div>`;
    },

    bracketSide(map, conf, stage, size, d) {
        const letters = conf === 'east'
            ? { 1: ['A', 'B', 'C', 'D'], 2: ['I', 'J'], 3: ['M'] }
            : { 1: ['E', 'F', 'G', 'H'], 2: ['K', 'L'], 3: ['N'] };
        const cols = [];
        for (let round = stage; round <= 3; round++) {
            const cards = letters[round].map(l => this.bracketCard(map[l], size, d));
            let inner;
            if (cards.length === 1) {
                inner = `<div class="nhl-bsingle">${cards[0]}</div>`;
            } else {
                inner = '';
                for (let i = 0; i < cards.length; i += 2) inner += `<div class="nhl-bpair">${cards[i]}${cards[i + 1]}</div>`;
            }
            cols.push(`<div class="nhl-bcol"><div class="nhl-bcol-label">${['', 'Round 1', 'Round 2', conf === 'east' ? 'East Final' : 'West Final'][round]}</div><div class="nhl-bcol-body">${inner}</div></div>`);
        }
        return `<div class="nhl-bside nhl-bside-${conf}">${cols.join('')}</div>`;
    },

    renderBracket(d) {
        const bracket = d.bracket;
        const map = this.seriesMap(bracket);
        if (bracket.stage >= 4) return this.renderFinal(d, map.O, bracket.stage >= 5);

        // Fewer teams left → bigger cards (round 1: 16 teams, round 2: 8, conference finals: 4)
        const size = { 1: 'sm', 2: 'lg', 3: 'xl' }[bracket.stage] || 'sm';
        return `
            <div class="nhl-bracket nhl-bracket-stage-${bracket.stage}">
                <div class="nhl-bconf"><span>East</span><span>West</span></div>
                <div class="nhl-btree">
                    ${this.bracketSide(map, 'east', bracket.stage, size, d)}
                    <div class="nhl-bcenter">
                        <div class="nhl-bcol-label">Stanley Cup Final</div>
                        <div class="nhl-bcol-body"><div class="nhl-bsingle">${this.bracketCard(map.O, size, d)}</div></div>
                    </div>
                    ${this.bracketSide(map, 'west', bracket.stage, size, d)}
                </div>
            </div>`;
    },

    /** Final / champion view: only the two finalists, big. */
    renderFinal(d, s, decided) {
        if (!s || !s.top || !s.bottom) {
            return `<div class="nhl-empty">Stanley Cup Final — matchup to be decided</div>`;
        }
        const champ = decided ? s.winner : null;
        const side = (t) => `
            <div class="nhl-fteam${champ === t.abbrev ? ' champ' : ''}${champ && champ !== t.abbrev ? ' out' : ''}" style="${this.teamVars(t.abbrev)}">
                <div class="nhl-flogo">${this.logo(t.abbrev, 'nhl-logo')}</div>
                <span class="nhl-fname">${this.esc(t.name)}</span>
                <span class="nhl-fseed">${this.esc(t.abbrev)}${t.seed ? ` · ${this.esc(t.seed)}` : ''}</span>
            </div>`;

        let status;
        if (champ) {
            const w = s.top.abbrev === champ ? s.top : s.bottom;
            const l = w === s.top ? s.bottom : s.top;
            status = `<span class="nhl-cup-tag">🏆 Stanley Cup Champions</span>
                      <span class="nhl-fstatus">${this.esc(w.name || w.abbrev)} win ${w.wins}–${l.wins}</span>`;
        } else {
            const t = s.top, b = s.bottom;
            const text = t.wins === b.wins
                ? `Series tied ${t.wins}–${b.wins}`
                : `${this.esc((t.wins > b.wins ? t : b).name || (t.wins > b.wins ? t : b).abbrev)} lead ${Math.max(t.wins, b.wins)}–${Math.min(t.wins, b.wins)}`;
            status = `<span class="nhl-fstatus">${text}</span>${this.finalNextGame(d, s)}`;
        }

        return `
            <div class="nhl-final${champ ? ' nhl-final-champ' : ''}">
                <div class="nhl-fmatch">
                    ${side(s.top)}
                    <div class="nhl-fscore"><b>${s.top.wins}</b><i>:</i><b>${s.bottom.wins}</b></div>
                    ${side(s.bottom)}
                </div>
                <div class="nhl-fstatus-row">${status}</div>
            </div>`;
    },

    /** "Game 5 · LIVE P2 12:34 · 2–1" or "Game 5 · Tonight 02:00" for the final view. */
    finalNextGame(d, s) {
        const games = [...(d.results || []), ...(d.upcoming || [])].filter(g => g.series_letter === s.letter);
        const live = games.find(g => g.state === 'LIVE' || g.state === 'CRIT');
        if (live) {
            const st = this.gameStatus(live);
            return `<span class="nhl-fnext live"><i class="nhl-live-dot"></i>Game ${live.series_game || ''} · ${this.esc(st.label)} · ${live.away.abbrev} ${live.away.score}–${live.home.score} ${live.home.abbrev}</span>`;
        }
        const next = (d.upcoming || []).find(g => g.series_letter === s.letter && (g.state === 'FUT' || g.state === 'PRE'));
        if (next) {
            return `<span class="nhl-fnext">Game ${next.series_game || ''} · Tonight ${this.formatTime(next.start_utc)} · ${next.away.abbrev} @ ${next.home.abbrev}</span>`;
        }
        return '';
    }
};

window.NhlTile = NhlTile;
