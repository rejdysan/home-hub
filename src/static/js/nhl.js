/**
 * NHL Stanley Cup Final panel.
 *
 * Renders the live final series: team crests, the big series score, a
 * game-by-game strip, and the next puck-drop. Data arrives over the
 * WebSocket ('nhl' messages + the initial state). When the payload is null
 * (off-season / no active final) the panel is marked inactive so kiosk.js
 * can drop it from the day-mode layout.
 */

const NhlManager = {
    /**
     * @param {Object|null} data - NhlSeries dict, or null when no final is active
     */
    update(data) {
        const active = !!(data && data.top && data.bottom);
        window.nhlActive = active;

        if (active) {
            this.render(data);
        }

        // Let the kiosk layout add/remove the panel column for the current mode
        if (window.updateNhlSlot) window.updateNhlSlot();
    },

    /**
     * Format a game's UTC start into a short local label.
     * NHL marks date-only future games as midnight UTC — in that case we show
     * just the date (no misleading 02:00 time).
     */
    formatGameWhen(startUtc) {
        if (!startUtc) return '';
        const d = new Date(startUtc);
        if (isNaN(d)) return '';
        const dateStr = d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
        const dateOnly = /T00:00:00Z$/.test(startUtc);
        if (dateOnly) return dateStr;
        const timeStr = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        return `${dateStr} · ${timeStr}`;
    },

    /** Human status line: who leads, tie, or a clinched Cup. */
    statusText(s) {
        const t = s.top, b = s.bottom;
        if (t.wins >= s.needed_to_win) return `${t.place} win the Stanley Cup`;
        if (b.wins >= s.needed_to_win) return `${b.place} win the Stanley Cup`;
        if (t.wins === b.wins) return `Series tied ${t.wins}–${b.wins}`;
        const leader = t.wins > b.wins ? t : b;
        return `${leader.place} lead ${Math.max(t.wins, b.wins)}–${Math.min(t.wins, b.wins)}`;
    },

    /** Build one team's crest + name block. */
    teamBlock(team, side) {
        const champ = team.wins >= 4;
        return `
            <div class="nhl-team nhl-team-${side}${champ ? ' nhl-champ' : ''}">
                <div class="nhl-logo-wrap">
                    <img class="nhl-logo" src="${team.logo}" alt="${team.abbrev}"
                         onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div class="nhl-logo-fallback" style="display:none">${team.abbrev}</div>
                </div>
                <div class="nhl-team-name">
                    <span class="nhl-place">${team.place}</span>
                    <span class="nhl-common">${team.name}</span>
                </div>
            </div>`;
    },

    /** Build the row of per-game pips. */
    gamesStrip(s) {
        return s.games.map(g => {
            if (g.state === 'OFF' && g.winner) {
                const topWon = g.winner === s.top.abbrev;
                const hi = Math.max(g.away_score, g.home_score);
                const lo = Math.min(g.away_score, g.home_score);
                return `<div class="nhl-game nhl-game-done ${topWon ? 'win-top' : 'win-bottom'}">
                            <span class="nhl-game-no">G${g.number}</span>
                            <span class="nhl-game-score">${hi}:${lo}</span>
                            <span class="nhl-game-win">${g.winner}</span>
                        </div>`;
            }
            const live = g.state === 'LIVE' || g.state === 'CRIT';
            return `<div class="nhl-game ${live ? 'nhl-game-live' : 'nhl-game-future'}">
                        <span class="nhl-game-no">G${g.number}</span>
                        <span class="nhl-game-score">${live ? 'LIVE' : '—'}</span>
                    </div>`;
        }).join('');
    },

    render(s) {
        const panel = document.getElementById('nhl-panel');
        if (!panel) return;

        const nextGame = s.games.find(g => g.state === 'FUT' || g.state === 'PRE');
        const live = s.games.find(g => g.state === 'LIVE' || g.state === 'CRIT');

        let footer = '';
        if (live) {
            footer = `<span class="nhl-next-tag nhl-live-tag">● LIVE</span>
                      <span class="nhl-next-main">Game ${live.number} · ${live.away} @ ${live.home}</span>`;
        } else if (nextGame) {
            footer = `<span class="nhl-next-tag">NEXT</span>
                      <span class="nhl-next-main">Game ${nextGame.number} · ${this.formatGameWhen(nextGame.start_utc)}
                      · @ ${nextGame.home}</span>`;
        } else {
            footer = `<span class="nhl-next-tag">SERIES OVER</span>`;
        }

        panel.innerHTML = `
            <div class="nhl-header">
                <span class="nhl-title"><i data-lucide="trophy"></i> ${s.round_label}</span>
                <span class="nhl-updated">Updated: ${s.updated || ''}</span>
            </div>
            <div class="nhl-matchup">
                ${this.teamBlock(s.top, 'left')}
                <div class="nhl-score">
                    <span class="nhl-score-num">${s.top.wins}</span>
                    <span class="nhl-score-dash">:</span>
                    <span class="nhl-score-num">${s.bottom.wins}</span>
                </div>
                ${this.teamBlock(s.bottom, 'right')}
            </div>
            <div class="nhl-status">${this.statusText(s)}</div>
            <div class="nhl-games">${this.gamesStrip(s)}</div>
            <div class="nhl-next">${footer}</div>`;

        if (window.lucide) lucide.createIcons();
    }
};

window.NhlManager = NhlManager;
window.renderNhl = (data) => NhlManager.update(data);
