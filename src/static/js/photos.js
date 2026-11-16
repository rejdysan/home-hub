/**
 * Photo tile: random photos from the family library (day mode, between the
 * calendar and the NHL tile).
 *
 * Smooth changes come from three things:
 *   1. The backend serves display-sized copies (long edge <= PHOTOS_MAX_EDGE,
 *      a few hundred KB from the Pi's disk), never the multi-MB originals.
 *   2. The next photo is loaded into the hidden layer and fully decoded
 *      (img.decode()) long before it is shown, so a change never waits on
 *      the network or on decoding.
 *   3. The change is a compositor-only crossfade: the new photo fades in on
 *      top while the old one stays fully opaque underneath (no dip to dark
 *      halfway), and photos that fill the tile drift slowly (Ken Burns,
 *      transform only).
 *
 * Photos that roughly match the tile's shape fill it (light crop); others
 * (portraits, panoramas) are shown whole over a blurred copy of themselves.
 *
 * Photos come from GET /api/photos/next, a server-side shuffle (every photo
 * once before any repeats). Rotation pauses while the tile is hidden.
 */

const PhotoTile = {
    rotateMs: 20000,
    FADE_MS: 1600,
    MIN_ROTATE_MS: 5000,
    RETRY_MS: 5000,
    // Fill the tile when photo and tile aspect ratios are within this factor; otherwise show it whole
    COVER_MAX_RATIO: 1.3,

    apiBase: '',
    rect: null,
    stage: null,
    layers: [],
    front: -1,          // index of the visible layer, -1 before the first photo
    prepared: null,     // photo loaded + decoded in the back layer, waiting for its turn
    preparing: false,
    wantShow: false,    // show the next photo as soon as it is ready
    timer: null,
    settleTimer: null,

    // ------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------

    init(rotateMs) {
        this.apiBase = `http://${window.location.hostname}:${DefaultConfig.API_PORT}`;
        this.rect = document.getElementById(ElementId.PHOTOS_RECT);
        this.stage = document.getElementById(ElementId.PHOTO_STAGE);
        if (!this.rect || !this.stage) return;
        this.layers = Array.from(this.stage.querySelectorAll('.photo-layer'));
        if (rotateMs > 0) this.rotateMs = Math.max(rotateMs, this.MIN_ROTATE_MS);
        this.applyTiming();
        this.prepare();
        this.schedule(this.RETRY_MS);
    },

    setRotateInterval(ms) {
        if (!(ms > 0)) return;
        ms = Math.max(ms, this.MIN_ROTATE_MS);
        if (ms === this.rotateMs) return;
        this.rotateMs = ms;
        this.applyTiming();
        if (this.front >= 0) this.schedule(this.rotateMs);
    },

    applyTiming() {
        this.stage.style.setProperty('--photo-fade', `${this.FADE_MS}ms`);
        // Drift lasts until the photo has fully faded out again
        this.stage.style.setProperty('--photo-drift', `${this.rotateMs + 2 * this.FADE_MS}ms`);
    },

    /** Called by kiosk.js when the tile becomes visible (day mode starts). */
    onShow() {
        if (!this.rect) return;
        this.wantShow = true;
        if (this.prepared) this.showPrepared();
        else this.prepare();
        this.schedule(this.RETRY_MS);
    },

    isVisible() {
        return !!(this.rect && this.rect.offsetParent !== null);
    },

    schedule(ms) {
        clearTimeout(this.timer);
        this.timer = setTimeout(() => this.tick(), ms);
    },

    tick() {
        if (!this.isVisible()) return; // paused; onShow() restarts it
        this.wantShow = true;
        if (this.prepared) {
            this.showPrepared();
        } else {
            this.prepare();
        }
        // Safety net: if loading fails, try again soon (a successful change reschedules)
        this.schedule(this.RETRY_MS);
    },

    // ------------------------------------------------------------------
    // Loading
    // ------------------------------------------------------------------

    backIndex() {
        return this.front === 0 ? 1 : 0;
    },

    /** Fetch the next photo and load + decode it into the hidden layer. */
    async prepare() {
        if (this.preparing || this.prepared || !this.layers.length) return;
        this.preparing = true;
        try {
            const res = await fetch(this.apiBase + ApiEndpoint.PHOTOS_NEXT, { cache: 'no-store' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            if (!data.photo) {
                this.showStatus(data);
                return;
            }
            await this.load(this.layers[this.backIndex()], data.photo);
            this.prepared = data.photo;
        } catch (err) {
            console.warn('🖼️ Photo tile: loading the next photo failed:', err);
            if (this.front < 0) this.showStatus(null);
        } finally {
            this.preparing = false;
        }
        if (this.prepared && this.wantShow && this.isVisible()) this.showPrepared();
    },

    async load(layer, photo) {
        const img = layer.querySelector('.photo-img');
        const backdrop = layer.querySelector('.photo-backdrop');
        img.src = this.apiBase + photo.url;
        backdrop.src = this.apiBase + photo.backdrop;
        await img.decode(); // rejects if the image can't be loaded
        await backdrop.decode().catch(() => {});
        this.renderCaption(layer.querySelector('.photo-caption'), photo);
    },

    /** Re-check the decode (the browser may drop bitmaps of hidden images), then crossfade. */
    async showPrepared() {
        const layer = this.layers[this.backIndex()];
        const photo = this.prepared;
        await Promise.all(Array.from(layer.querySelectorAll('img'), img => img.decode().catch(() => {})));
        if (this.prepared === photo && this.isVisible()) this.flip();
    },

    // ------------------------------------------------------------------
    // Showing
    // ------------------------------------------------------------------

    flip() {
        const photo = this.prepared;
        const next = this.backIndex();
        const incoming = this.layers[next];
        const outgoing = this.front >= 0 ? this.layers[this.front] : null;

        this.applyFit(incoming, photo);
        this.layers.forEach(layer => layer.classList.remove('is-behind'));
        if (outgoing) {
            outgoing.classList.remove('is-front');
            outgoing.classList.add('is-behind'); // stays opaque under the incoming photo
        }
        incoming.classList.add('is-front');      // fades in on top

        this.front = next;
        this.prepared = null;
        this.wantShow = false;
        this.hideStatus();

        // Once the fade is done, release the old layer and load the following photo into it
        clearTimeout(this.settleTimer);
        this.settleTimer = setTimeout(() => {
            if (outgoing) outgoing.classList.remove('is-behind');
            this.prepare();
        }, this.FADE_MS + 100);

        this.schedule(this.rotateMs);
    },

    /** Fill the tile when the shapes are close; otherwise show the whole photo over its blurred copy. */
    applyFit(layer, photo) {
        const w = this.stage.clientWidth;
        const h = this.stage.clientHeight;
        const tile = w > 0 && h > 0 ? w / h : 1.2;
        const ratio = photo.width / photo.height;
        const cover = Math.max(ratio, tile) / Math.min(ratio, tile) <= this.COVER_MAX_RATIO;
        layer.classList.toggle('photo-cover', cover);
        layer.classList.toggle('photo-contain', !cover);
        // Drift toward a random point so consecutive photos don't all zoom the same way
        const x = 25 + Math.round(Math.random() * 50);
        const y = 25 + Math.round(Math.random() * 50);
        layer.style.setProperty('--photo-origin', `${x}% ${y}%`);
    },

    renderCaption(el, photo) {
        el.textContent = '';
        if (photo.album) {
            const album = document.createElement('span');
            album.className = 'photo-album';
            album.textContent = photo.album;
            el.appendChild(album);
        }
        const when = this.formatTaken(photo.taken);
        if (when) {
            const date = document.createElement('span');
            date.className = 'photo-date';
            date.textContent = when;
            el.appendChild(date);
        }
    },

    /** '2023-06-14' -> 'June 14, 2023 · 3 years ago' */
    formatTaken(iso) {
        if (!iso) return '';
        const [y, m, d] = iso.split('-').map(Number);
        const taken = new Date(y, m - 1, d);
        if (isNaN(taken.getTime())) return '';
        const label = taken.toLocaleDateString(Locale.DATE, { day: 'numeric', month: 'long', year: 'numeric' });
        const ago = this.timeAgo(taken);
        return ago ? `${label} · ${ago}` : label;
    },

    timeAgo(taken) {
        const now = new Date();
        let months = (now.getFullYear() - taken.getFullYear()) * 12 + (now.getMonth() - taken.getMonth());
        if (now.getDate() < taken.getDate()) months -= 1;
        if (months >= 12) {
            const years = Math.floor(months / 12);
            return years === 1 ? '1 year ago' : `${years} years ago`;
        }
        if (months >= 1) return months === 1 ? '1 month ago' : `${months} months ago`;
        return '';
    },

    // ------------------------------------------------------------------
    // Status (before the first photo)
    // ------------------------------------------------------------------

    showStatus(data) {
        if (this.front >= 0) return; // keep showing the last photo instead
        const el = document.getElementById(ElementId.PHOTO_STATUS);
        if (!el) return;
        let title = 'Loading photos…';
        let sub = '';
        if (data && data.loaded) {
            if (data.pending > 0) {
                title = 'Preparing photos…';
                sub = `${data.pending} photo${data.pending === 1 ? '' : 's'} to go`;
            } else {
                title = 'No photos yet';
                sub = 'Add photos to the photos folder on the Pi or to the shared Google Drive folder';
            }
        }
        el.querySelector('.photo-status-title').textContent = title;
        el.querySelector('.photo-status-sub').textContent = sub;
        el.hidden = false;
    },

    hideStatus() {
        const el = document.getElementById(ElementId.PHOTO_STATUS);
        if (el) el.hidden = true;
    }
};

window.PhotoTile = PhotoTile;
