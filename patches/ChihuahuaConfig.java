package org.telegram.messenger;

import android.content.Context;
import android.content.SharedPreferences;

/**
 * Chihuahua Telegram options (Settings → Chihuahua). Kept in the "chihuahua" preferences file,
 * cached in static fields so the hot paths (chat list, profile) never touch disk.
 */
public class ChihuahuaConfig {

    public static final String KEY_SHOW_ID = "show_id";
    public static final String KEY_HIDE_STORIES = "hide_stories";
    public static final String KEY_HIDE_PREMIUM = "hide_premium";

    private static volatile boolean loaded;
    private static boolean showId = true;
    private static boolean hideStories = false;
    private static boolean hidePremium = false;

    private static SharedPreferences prefs() {
        return ApplicationLoader.applicationContext.getSharedPreferences("chihuahua", Context.MODE_PRIVATE);
    }

    private static void load() {
        if (loaded || ApplicationLoader.applicationContext == null) {
            return;
        }
        synchronized (ChihuahuaConfig.class) {
            if (loaded) {
                return;
            }
            SharedPreferences p = prefs();
            showId = p.getBoolean(KEY_SHOW_ID, true);
            hideStories = p.getBoolean(KEY_HIDE_STORIES, false);
            hidePremium = p.getBoolean(KEY_HIDE_PREMIUM, false);
            loaded = true;
        }
    }

    public static boolean showIdInProfile() {
        load();
        return showId;
    }

    public static boolean hideStories() {
        load();
        return hideStories;
    }

    public static boolean hidePremium() {
        load();
        return hidePremium;
    }

    public static boolean get(String key) {
        load();
        switch (key) {
            case KEY_SHOW_ID:
                return showId;
            case KEY_HIDE_STORIES:
                return hideStories;
            case KEY_HIDE_PREMIUM:
                return hidePremium;
            default:
                return false;
        }
    }

    public static void set(String key, boolean value) {
        load();
        switch (key) {
            case KEY_SHOW_ID:
                showId = value;
                break;
            case KEY_HIDE_STORIES:
                hideStories = value;
                break;
            case KEY_HIDE_PREMIUM:
                hidePremium = value;
                break;
            default:
                return;
        }
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(key, value).apply();
        }
    }
}
