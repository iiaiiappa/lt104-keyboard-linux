import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class LT104Extension extends Extension {
    async enable() {
        try {
            // Dynamic import with timestamp parameter forces SpiderMonkey / GJS
            // to bypass module caching and reload cleanly every time.
            const module = await import(`file://${this.path}/indicator.js?t=${Date.now()}`);
            this._impl = new module.LT104IndicatorImpl(this);
            this._impl.enable();
        } catch (e) {
            console.error('[LT104-Extension] Error during enable(): ' + e);
        }
    }

    disable() {
        if (this._impl) {
            try {
                this._impl.disable();
            } catch (e) {
                console.error('[LT104-Extension] Error during disable(): ' + e);
            }
            this._impl = null;
        }
    }
}
