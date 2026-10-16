import Gio from 'gi://Gio';
import Gtk from 'gi://Gtk';
import Adw from 'gi://Adw';
import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';

const APP_PATH = '/home/iiaiiappa/PatProject/lt104-keyboard-linux/lt104_gtk.py';

export default class LT104Preferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        // Set comfortable default window size without scrollbars
        try {
            window.set_default_size(840, 480);
        } catch (e) {}

        // Automatically launch the full GTK Control Center
        try {
            let proc = Gio.Subprocess.new(['/usr/bin/python3', APP_PATH], Gio.SubprocessFlags.NONE);
            proc.wait_async(null, null);
        } catch (e) {
            console.error(`[LT104] Failed to spawn GTK app: ${e}`);
        }

        const page = new Adw.PreferencesPage();
        const group = new Adw.PreferencesGroup({
            title: 'LT-104 Keyboard Control Center',
            description: 'Native Linux Control Suite for LangTu LT-104 Mechanical Keyboard'
        });

        const row = new Adw.ActionRow({
            title: 'Open Full Control Center',
            subtitle: 'Click below to launch the native GTK4 application'
        });

        const btn = new Gtk.Button({
            label: 'Open App',
            valign: Gtk.Align.CENTER
        });
        btn.add_css_class('suggested-action');
        btn.add_css_class('pill');
        btn.connect('clicked', () => {
            try {
                let proc = Gio.Subprocess.new(['/usr/bin/python3', APP_PATH], Gio.SubprocessFlags.NONE);
                proc.wait_async(null, null);
            } catch (e) {}
        });

        row.add_suffix(btn);
        group.add(row);
        page.add(group);
        window.add(page);
    }
}
