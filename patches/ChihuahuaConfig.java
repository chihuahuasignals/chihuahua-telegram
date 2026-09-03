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
    public static final String KEY_ACCOUNT_AGE = "account_age";

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
    private static boolean accountAge = true;

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
            accountAge = p.getBoolean(KEY_ACCOUNT_AGE, true);
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

    // ---- per-account notifications -----------------------------------------------------------
    // Telegram only has one global "show notifications from all accounts" switch. With many
    // accounts logged in you usually want a handful noisy and the rest silent, so every account
    // gets its own switch (Settings -> Chihuahua -> Notifications). Silenced accounts post no
    // notification, make no sound, and are left out of the launcher badge count.
    private static final java.util.concurrent.ConcurrentHashMap<Integer, Boolean> notifyByAccount = new java.util.concurrent.ConcurrentHashMap<>();

    private static String notifyKey(int account) {
        return "notify_account_" + account;
    }

    /** False when this account's notifications were switched off in Settings -> Chihuahua. */
    public static boolean notificationsEnabled(int account) {
        if (ApplicationLoader.applicationContext == null) {
            return true;
        }
        Boolean cached = notifyByAccount.get(account);
        if (cached != null) {
            return cached;
        }
        boolean value = prefs().getBoolean(notifyKey(account), true);
        notifyByAccount.put(account, value);
        return value;
    }

    public static void setNotificationsEnabled(int account, boolean enabled) {
        notifyByAccount.put(account, enabled);
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(notifyKey(account), enabled).apply();
        }
    }

    // ---- account age from the user ID -------------------------------------------------------
    // Telegram hands out user IDs in increasing order, so an ID roughly dates the account.
    // Anchors: the widely used first-seen table for IDs below 2.15e9, the November 2021 jump
    // to 5e9 (64-bit IDs), then the running maximum of first-seen samples from the
    // jobians/telegram-id-age dataset. First-seen dates lag creation a little, so estimates
    // err towards "newer"; expect ±1-2 months for recent accounts, more for 2017-2021.
    private static final long[] ID_ANCHORS = {2768409L, 7679610L, 11538514L, 15835244L, 23646077L, 38015510L, 44634663L, 46145305L, 54845238L, 63263518L, 101260938L, 111220210L, 116812045L, 122600695L, 130029930L, 133909606L, 157242073L, 171295414L, 181783990L, 222021233L, 225034354L, 278941742L, 285253072L, 294851037L, 297621225L, 328594461L, 337808429L, 352940995L, 369669043L, 400169472L, 805158066L, 1974255900L, 2150000000L, 5000000000L, 5031711230L, 5288930461L, 5396515972L, 5505809357L, 5598262640L, 5694365966L, 5721138769L, 5765259845L, 5931294587L, 5983753471L, 6271031786L, 6277658932L, 6326011828L, 6523424924L, 6684986493L, 6827058708L, 6947316117L, 7104310277L, 7242296450L, 7409259451L, 7458668365L, 7832006200L, 8173852075L, 8238766847L, 8369442459L, 8461579295L, 8559682245L};
    /** Days since 1970-01-01, one per ID_ANCHORS entry. */
    private static final int[] DAY_ANCHORS = {16010, 16070, 16102, 16121, 16127, 16130, 16196, 16205, 16333, 16370, 16500, 16546, 16639, 16640, 16681, 16715, 16745, 16869, 16901, 16960, 16970, 17054, 17092, 17124, 17151, 17194, 17218, 17221, 17256, 17378, 18092, 18912, 18946, 18951, 18967, 19019, 19103, 19139, 19154, 19232, 19258, 19295, 19315, 19349, 19400, 19433, 19545, 19571, 19625, 19667, 19706, 19832, 19872, 19894, 19937, 19985, 20140, 20300, 20308, 20342, 20403};
    /** IDs handed out per day between Sep 2024 and Nov 2025, used past the last anchor. */
    private static final double IDS_PER_DAY_RECENT = 1740852;

    /** Approximate creation time (epoch millis) of the account with this ID; 0 when unknown. */
    public static long estimatedCreationMillis(long userId) {
        if (userId <= 0) {
            return 0;
        }
        final int n = ID_ANCHORS.length;
        double day;
        if (userId <= ID_ANCHORS[0]) {
            day = DAY_ANCHORS[0];
        } else if (userId >= ID_ANCHORS[n - 1]) {
            day = DAY_ANCHORS[n - 1] + (userId - ID_ANCHORS[n - 1]) / IDS_PER_DAY_RECENT;
        } else {
            int i = 1;
            while (userId > ID_ANCHORS[i]) {
                i++;
            }
            day = DAY_ANCHORS[i - 1] + (double) (userId - ID_ANCHORS[i - 1]) * (DAY_ANCHORS[i] - DAY_ANCHORS[i - 1]) / (double) (ID_ANCHORS[i] - ID_ANCHORS[i - 1]);
        }
        return Math.min((long) (day * 86400000.0), System.currentTimeMillis());
    }

    /** "Jun 2026", "2013 or earlier", or "" when the ID is not a user ID. */
    public static String estimatedCreation(long userId) {
        long millis = estimatedCreationMillis(userId);
        if (millis <= 0) {
            return "";
        }
        if (userId <= ID_ANCHORS[0]) {
            return "2013 or earlier";
        }
        return new java.text.SimpleDateFormat("MMM yyyy", java.util.Locale.US).format(new java.util.Date(millis));
    }

    /**
     * Compact age for the profile status line, e.g. " \u00b7 3mo old". Kept short because it shares
     * one line with the last-seen text and the ID; the exact month is in the copy-ID toast.
     */
    public static String accountAgeSuffix(long userId) {
        load();
        if (!accountAge) {
            return "";
        }
        long millis = estimatedCreationMillis(userId);
        if (millis <= 0) {
            return "";
        }
        long days = (System.currentTimeMillis() - millis) / 86400000L;
        if (days < 0) {
            days = 0;
        }
        int months = (int) (days / 30.44);
        if (months < 1) {
            return " \u00b7 new";
        }
        if (months < 24) {
            return " \u00b7 " + months + "mo old";
        }
        return " \u00b7 " + (months / 12) + "y old";
    }

    public static boolean showAccountAge() {
        load();
        return accountAge;
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
            case KEY_ACCOUNT_AGE:
                return accountAge;
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
            case KEY_ACCOUNT_AGE:
                accountAge = value;
                break;
            default:
                return;
        }
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(key, value).apply();
        }
    }
}
