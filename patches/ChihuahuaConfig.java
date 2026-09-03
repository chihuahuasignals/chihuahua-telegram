package org.telegram.messenger;

import android.content.Context;
import android.content.SharedPreferences;

import org.telegram.tgnet.TLObject;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_account;
import org.telegram.tgnet.tl.TL_stories;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Chihuahua Telegram options (Settings → Chihuahua). Kept in the "chihuahua" preferences file,
 * cached in static fields so the hot paths (chat list, profile) never touch disk.
 */
public class ChihuahuaConfig {

    public static final String KEY_SHOW_ID = "show_id";
    public static final String KEY_HIDE_STORIES = "hide_stories";
    public static final String KEY_HIDE_PREMIUM = "hide_premium";
    public static final String KEY_GHOST_READ = "ghost_read";
    public static final String KEY_GHOST_TYPING = "ghost_typing";
    public static final String KEY_GHOST_OFFLINE = "ghost_offline";
    public static final String KEY_BACK_CAMERA = "back_camera";

    /** SHA-256 of ("chihuahua:" + activation code), filled in at build time. Empty = no lock. */
    public static final String ACTIVATION_HASH = "%%ACTIVATION_HASH%%";
    public static final String KEY_ACTIVATED = "activated_" + ACTIVATION_HASH;

    private static volatile boolean loaded;
    private static boolean showId = true;
    private static boolean hideStories = false;
    private static boolean hidePremium = false;
    private static boolean ghostRead = false;
    private static boolean ghostTyping = false;
    private static boolean ghostOffline = false;
    private static boolean backCamera = true;

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
            ghostRead = p.getBoolean(KEY_GHOST_READ, false);
            ghostTyping = p.getBoolean(KEY_GHOST_TYPING, false);
            ghostOffline = p.getBoolean(KEY_GHOST_OFFLINE, false);
            backCamera = p.getBoolean(KEY_BACK_CAMERA, true);
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

    public static boolean ghostRead() {
        load();
        return ghostRead;
    }

    public static boolean ghostTyping() {
        load();
        return ghostTyping;
    }

    public static boolean ghostOffline() {
        load();
        return ghostOffline;
    }

    /** Video calls (and group-call video) start with the back camera instead of the selfie camera. */
    public static boolean backCameraDefault() {
        load();
        return backCamera;
    }

    public static boolean ghostModeActive() {
        load();
        return ghostRead || ghostTyping || ghostOffline;
    }

    /**
     * Ghost mode: called for every outgoing API request. Returns true when the request must
     * not be sent (the caller then gets a synthetic GHOST_MODE error, which every affected
     * call site treats as "nothing happened").
     */
    public static boolean shouldDropRequest(TLObject request) {
        load();
        if (!ghostRead && !ghostTyping && !ghostOffline) {
            return false;
        }
        if (ghostRead) {
            if (request instanceof TLRPC.TL_messages_readHistory
                    || request instanceof TLRPC.TL_channels_readHistory
                    || request instanceof TLRPC.TL_messages_readSavedHistory
                    || request instanceof TLRPC.TL_messages_readEncryptedHistory
                    || request instanceof TLRPC.TL_messages_readMessageContents
                    || request instanceof TLRPC.TL_channels_readMessageContents
                    || request instanceof TLRPC.TL_messages_readMentions
                    || request instanceof TLRPC.TL_messages_readReactions
                    || request instanceof TLRPC.TL_messages_readDiscussion
                    || request instanceof TL_stories.TL_stories_readStories) {
                return true;
            }
        }
        if (ghostTyping && request instanceof TLRPC.TL_messages_setTyping) {
            return true;
        }
        if (ghostOffline && request instanceof TL_account.updateStatus && !((TL_account.updateStatus) request).offline) {
            return true;
        }
        return false;
    }

    /** True when this build has no activation code, or the code was entered on this device. */
    public static boolean isActivated() {
        if (ACTIVATION_HASH.isEmpty() || ApplicationLoader.applicationContext == null) {
            return true;
        }
        return prefs().getBoolean(KEY_ACTIVATED, false);
    }

    public static boolean tryActivate(String code) {
        if (code == null) {
            return false;
        }
        String hash = sha256("chihuahua:" + code.trim());
        if (!ACTIVATION_HASH.equalsIgnoreCase(hash)) {
            return false;
        }
        prefs().edit().putBoolean(KEY_ACTIVATED, true).apply();
        return true;
    }

    public static String sha256(String text) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(text.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
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
            case KEY_GHOST_READ:
                return ghostRead;
            case KEY_GHOST_TYPING:
                return ghostTyping;
            case KEY_GHOST_OFFLINE:
                return ghostOffline;
            case KEY_BACK_CAMERA:
                return backCamera;
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
            case KEY_GHOST_READ:
                ghostRead = value;
                break;
            case KEY_GHOST_TYPING:
                ghostTyping = value;
                break;
            case KEY_GHOST_OFFLINE:
                ghostOffline = value;
                break;
            case KEY_BACK_CAMERA:
                backCamera = value;
                break;
            default:
                return;
        }
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(key, value).apply();
        }
    }
}
