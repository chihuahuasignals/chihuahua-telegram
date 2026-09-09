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
    public static final String KEY_FLAG_NEW = "flag_new_in_groups";
    public static final String KEY_QUICK_BAN = "quick_ban";
    public static final String KEY_KEEP_CONNECTED = "keep_connected";
    public static final String KEY_AGE_ALWAYS = "age_always_in_groups";
    public static final String KEY_ACCOUNT_DEFAULTS = "account_defaults";
    /** Not a switch: months, stored separately (see flagMonths()). */
    public static final String KEY_FLAG_MONTHS = "flag_new_months";

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
    private static boolean flagNew = true;
    private static boolean quickBan = true;
    private static boolean keepConnected = true;
    private static boolean ageAlways = false;
    private static boolean accountDefaults = true;
    private static int flagMonths = 3;

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
            flagNew = p.getBoolean(KEY_FLAG_NEW, true);
            quickBan = p.getBoolean(KEY_QUICK_BAN, true);
            keepConnected = p.getBoolean(KEY_KEEP_CONNECTED, true);
            ageAlways = p.getBoolean(KEY_AGE_ALWAYS, false);
            accountDefaults = p.getBoolean(KEY_ACCOUNT_DEFAULTS, true);
            flagMonths = p.getInt(KEY_FLAG_MONTHS, 3);
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

    public static int flagMonths() {
        load();
        return flagMonths;
    }

    public static void setFlagMonths(int months) {
        load();
        flagMonths = months;
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putInt(KEY_FLAG_MONTHS, months).apply();
        }
    }

    /** Show the one-tap "Ban, wipe & report" item on group messages. */
    public static boolean quickBan() {
        load();
        return quickBan;
    }

    public static boolean flagNewInGroups() {
        load();
        return flagNew;
    }

    public static boolean ageAlwaysInGroups() {
        load();
        return ageAlways;
    }

    /** Months since the account was (probably) created; -1 when the ID says nothing. */
    public static int accountAgeMonths(long userId) {
        long millis = estimatedCreationMillis(userId);
        if (millis <= 0) {
            return -1;
        }
        long days = (System.currentTimeMillis() - millis) / 86400000L;
        return (int) (Math.max(0, days) / 30.44);
    }

    /** True when this account is younger than the "flag new accounts" threshold. */
    public static boolean isNewAccount(long userId) {
        load();
        int months = accountAgeMonths(userId);
        return months >= 0 && months < flagMonths;
    }

    /**
     * Badge for the sender's name row in a group: "2mo", "new", "3y". Empty when the ID says
     * nothing, or when only new accounts are flagged and this one is not new.
     */
    public static String groupAgeBadge(long userId) {
        load();
        if (!flagNew && !ageAlways) {
            return "";
        }
        int months = accountAgeMonths(userId);
        if (months < 0) {
            return "";
        }
        boolean isNew = months < flagMonths;
        if (!isNew && !ageAlways) {
            return "";
        }
        if (months < 1) {
            return "new";
        }
        if (months < 24) {
            return months + "mo";
        }
        return (months / 12) + "y";
    }

    // ---- phone number with its flag, for the Accounts list ----------------------------------

    /** Calling code -> ISO country, from Telegram's own countries.txt; first entry wins for shared codes. */
    private static volatile java.util.Map<String, String> codeToIso;

    private static void loadCountries() {
        if (codeToIso != null) {
            return;
        }
        final java.util.HashMap<String, String> map = new java.util.HashMap<>();
        try (java.io.BufferedReader reader = new java.io.BufferedReader(new java.io.InputStreamReader(
                ApplicationLoader.applicationContext.getResources().getAssets().open("countries.txt")))) {
            String line;
            while ((line = reader.readLine()) != null) {
                final String[] args = line.split(";");
                if (args.length >= 2 && !map.containsKey(args[0])) {
                    map.put(args[0], args[1]);
                }
            }
        } catch (Exception e) {
            FileLog.e(e);
        }
        codeToIso = map;
    }

    /** Flag emoji for a phone number given as digits without "+", or "" when the code is unknown. */
    public static String flagForPhone(String digits) {
        if (digits == null || digits.isEmpty()) {
            return "";
        }
        loadCountries();
        for (int len = Math.min(4, digits.length()); len >= 1; len--) {
            final String iso = codeToIso.get(digits.substring(0, len));
            if (iso != null) {
                final String flag = LocaleController.getLanguageFlag(iso);
                return flag == null ? "" : flag;
            }
        }
        return "";
    }

    /** "🇸🇬 +65 8835 7983" for an account's number; "" when there is none. */
    public static String phoneWithFlag(TLRPC.User user) {
        if (user == null || user.phone == null || user.phone.isEmpty()) {
            return "";
        }
        final String formatted = org.telegram.PhoneFormat.PhoneFormat.getInstance().format("+" + user.phone);
        final String flag = flagForPhone(user.phone);
        return flag.isEmpty() ? formatted : flag + " " + formatted;
    }

    // ---- account order (drag to arrange on the Settings tab) ---------------------------------
    // Every account list in the app (Settings tab, the account switcher, the auth sheets) sorts by
    // UserConfig.loginTime, which is used for nothing else. So an order chosen by dragging is
    // stored by handing the accounts their loginTime values back in the new order: same values,
    // permuted, made distinct where two were equal. All lists then agree, and an account added
    // later (loginTime = now) still lands at the end.

    /** All logged-in accounts in display order: loginTime ascending, slot number as tie-break. */
    public static java.util.ArrayList<Integer> accountsInOrder() {
        final java.util.ArrayList<Integer> all = new java.util.ArrayList<>();
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (UserConfig.getInstance(a).isClientActivated()) {
                all.add(a);
            }
        }
        java.util.Collections.sort(all, (o1, o2) -> Integer.compare(UserConfig.getInstance(o1).loginTime, UserConfig.getInstance(o2).loginTime));
        return all;
    }

    /**
     * Makes {@code visible} (account slots, as arranged on the Settings tab) the new order. The tab
     * never lists the account it belongs to ({@code current}), so that one keeps its old position
     * among the others; accounts the list did not show follow in their old order.
     */
    public static void applyAccountOrder(java.util.List<Integer> visible, int current) {
        final java.util.ArrayList<Integer> before = accountsInOrder();
        final java.util.ArrayList<Integer> after = new java.util.ArrayList<>();
        for (int a : visible) {
            if (a != current && before.contains(a) && !after.contains(a)) {
                after.add(a);
            }
        }
        for (int a : before) {
            if (a != current && !after.contains(a)) {
                after.add(a);
            }
        }
        final int currentRank = before.indexOf(current);
        if (currentRank >= 0) {
            after.add(Math.min(currentRank, after.size()), current);
        }
        final int[] times = new int[before.size()];
        for (int i = 0; i < before.size(); i++) {
            times[i] = UserConfig.getInstance(before.get(i)).loginTime;
            if (i > 0 && times[i] <= times[i - 1]) {
                times[i] = times[i - 1] + 1;
            }
        }
        for (int i = 0; i < after.size() && i < times.length; i++) {
            final UserConfig config = UserConfig.getInstance(after.get(i));
            if (config.loginTime != times[i]) {
                config.loginTime = times[i];
                config.saveConfig(false);
            }
        }
    }

    // ---- keeping every account connected -----------------------------------------------------
    // This build has no working Firebase push (Telegram's push servers can only deliver to tokens
    // from Telegram's own Firebase project), so notifications depend entirely on Telegram's
    // keep-alive service and its background connection. Two things make that unreliable here:
    //   * Telegram writes the "Keep-Alive Service" switch into the SELECTED account's preferences
    //     but reads it back from account 0's, so turning it on while any other account is selected
    //     silently does nothing;
    //   * "Background Connection" is per account, so with many accounts logged in most of them have
    //     no persistent connection and only deliver when the app is opened.
    // applyKeepConnected() sets both, for every logged-in account, and is called on every start.

    public static boolean keepConnected() {
        load();
        return keepConnected;
    }

    public static void applyKeepConnected() {
        load();
        if (!keepConnected || ApplicationLoader.applicationContext == null) {
            return;
        }
        try {
            MessagesController.getGlobalNotificationsSettings().edit().putBoolean("pushService", true).apply();
            for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
                if (!UserConfig.getInstance(a).isClientActivated()) {
                    continue;
                }
                MessagesController.getNotificationsSettings(a).edit()
                        .putBoolean("pushConnection", true)
                        .putBoolean("pushService", true)
                        .apply();
                org.telegram.tgnet.ConnectionsManager.getInstance(a).setPushConnectionEnabled(true);
            }
            ApplicationLoader.startPushService();
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    /** One line for the settings screen: what the app is actually relying on right now. */
    public static String notificationStatus() {
        if (ApplicationLoader.applicationContext == null) {
            return "";
        }
        int accounts = 0, connected = 0;
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (!UserConfig.getInstance(a).isClientActivated()) {
                continue;
            }
            accounts++;
            if (MessagesController.getNotificationsSettings(a).getBoolean("pushConnection", MessagesController.getInstance(a).backgroundConnection)) {
                connected++;
            }
        }
        boolean keepAlive = MessagesController.getGlobalNotificationsSettings().getBoolean("pushService", false);
        String push;
        String status = SharedConfig.pushStringStatus == null ? "" : SharedConfig.pushStringStatus;
        if (SharedConfig.pushString != null && !SharedConfig.pushString.isEmpty() && !SharedConfig.pushString.startsWith("__")) {
            push = "Google push: working";
        } else if (status.contains("NO_GOOGLE_PLAY_SERVICES")) {
            push = "Google push: no Play Services";
        } else if (status.contains("FAILED")) {
            push = "Google push: unavailable (normal for this build)";
        } else if (status.contains("GENERATING")) {
            push = "Google push: still trying";
        } else {
            push = "Google push: unavailable (normal for this build)";
        }
        return push + "\nKeep-alive service: " + (keepAlive ? "on" : "OFF")
                + "\nBackground connection: " + connected + " of " + accounts + " accounts";
    }

    // ---- defaults applied to an account when it logs in -----------------------------------------
    // Telegram logs a session out after 6 months unused, deletes an account after 18 months away,
    // and shows a birthday to contacts only. With this many accounts, most of them idle most of the
    // time, that is tight, so each account that logs in here is set once to sessions 1 year,
    // account 24 months and birthday visible to everybody. Once per account, keyed by user id, and
    // each setting is marked done only when the server accepts it — so a call lost to a dead
    // connection is retried on the next start, and once it lands the app never sets that account
    // again, which is what makes changing any of them by hand afterwards stick. Accounts that were
    // already logged in are left alone until the button in Settings -> Chihuahua is pressed.

    /** Telegram's longest self-destruct choices, in days. */
    public static final int SESSION_TTL_DAYS = 365;
    public static final int ACCOUNT_TTL_DAYS = 730;

    public static boolean accountDefaults() {
        load();
        return accountDefaults;
    }

    private static String sessionDoneKey(long userId) {
        return "def_session_" + userId;
    }

    private static String accountDoneKey(long userId) {
        return "def_account_" + userId;
    }

    private static String birthdayDoneKey(long userId) {
        return "def_birthday_" + userId;
    }

    /** Set while an account's three calls have not all gone through, so a start can finish them. */
    private static String pendingKey(long userId) {
        return "def_pending_" + userId;
    }

    /** Called the moment an account finishes logging in on this build. */
    public static void onAccountLoggedIn(int account) {
        load();
        if (!accountDefaults || ApplicationLoader.applicationContext == null) {
            return;
        }
        try {
            final long userId = UserConfig.getInstance(account).getClientUserId();
            if (userId == 0) {
                return;
            }
            prefs().edit().putBoolean(pendingKey(userId), true).apply();
            // A couple of seconds in, so the fresh connection has settled.
            AndroidUtilities.runOnUIThread(() -> applyAccountDefaults(account, false), 2000);
        } catch (Throwable e) {
            FileLog.e(e);
        }
        markTwoStepPrompt(account);
        startAutoJoin();
    }

    // ---- the Two-Step Verification offer --------------------------------------------------------
    // Only the marker lives here; the dialog is ChihuahuaOnboarding, which LaunchActivity calls.

    private static String twoStepPromptKey(long userId) {
        return "ask_2fa_" + userId;
    }

    private static void markTwoStepPrompt(int account) {
        if (!PROMPT_2FA || ApplicationLoader.applicationContext == null) {
            return;
        }
        final long userId = UserConfig.getInstance(account).getClientUserId();
        if (userId != 0) {
            prefs().edit().putBoolean(twoStepPromptKey(userId), true).apply();
        }
    }

    public static boolean twoStepPromptPending(int account) {
        if (!PROMPT_2FA || ApplicationLoader.applicationContext == null) {
            return false;
        }
        final long userId = UserConfig.getInstance(account).getClientUserId();
        return userId != 0 && prefs().getBoolean(twoStepPromptKey(userId), false);
    }

    /** Asked and answered, or the account already had a password: do not raise it again. */
    public static void clearTwoStepPrompt(long userId) {
        if (ApplicationLoader.applicationContext != null && userId != 0) {
            prefs().edit().remove(twoStepPromptKey(userId)).apply();
        }
    }

    /** On every start: finish any account whose login-time calls did not get through. */
    public static void retryAccountDefaults() {
        load();
        if (!accountDefaults || ApplicationLoader.applicationContext == null) {
            return;
        }
        try {
            final SharedPreferences p = prefs();
            for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
                final UserConfig config = UserConfig.getInstance(a);
                if (!config.isClientActivated()) {
                    continue;
                }
                final long userId = config.getClientUserId();
                if (userId != 0 && p.getBoolean(pendingKey(userId), false)) {
                    applyAccountDefaults(a, false);
                }
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    /** The Settings button: every logged-in account, spaced out so it is not one burst. */
    public static void applyAccountDefaultsToAll() {
        int delay = 0;
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (!UserConfig.getInstance(a).isClientActivated()) {
                continue;
            }
            final int account = a;
            AndroidUtilities.runOnUIThread(() -> applyAccountDefaults(account, true), delay);
            delay += 1500;
        }
    }

    /** force = the Settings button, which ignores the done marks and sets everything again. */
    private static void applyAccountDefaults(int account, boolean force) {
        if (ApplicationLoader.applicationContext == null) {
            return;
        }
        try {
            final UserConfig config = UserConfig.getInstance(account);
            if (!config.isClientActivated()) {
                return;
            }
            final long userId = config.getClientUserId();
            if (userId == 0) {
                return;
            }
            final SharedPreferences p = prefs();
            if (force || !p.getBoolean(sessionDoneKey(userId), false)) {
                final TL_account.setAuthorizationTTL req = new TL_account.setAuthorizationTTL();
                req.authorization_ttl_days = SESSION_TTL_DAYS;
                send(account, req, sessionDoneKey(userId), userId);
            }
            if (force || !p.getBoolean(accountDoneKey(userId), false)) {
                final TL_account.setAccountTTL req = new TL_account.setAccountTTL();
                req.ttl = new TLRPC.TL_accountDaysTTL();
                req.ttl.days = ACCOUNT_TTL_DAYS;
                send(account, req, accountDoneKey(userId), userId);
            }
            if (force || !p.getBoolean(birthdayDoneKey(userId), false)) {
                final TL_account.setPrivacy req = new TL_account.setPrivacy();
                req.key = new TLRPC.TL_inputPrivacyKeyBirthday();
                req.rules.add(new TLRPC.TL_inputPrivacyValueAllowAll());
                send(account, req, birthdayDoneKey(userId), userId);
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    /** Marks doneKey only when the server accepted the change. */
    private static void send(int account, org.telegram.tgnet.TLObject req, String doneKey, long userId) {
        org.telegram.tgnet.ConnectionsManager.getInstance(account).sendRequest(req, (response, error) -> {
            if (error == null) {
                prefs().edit().putBoolean(doneKey, true).apply();
                clearPending(userId);
                if (response instanceof TL_account.privacyRules) {
                    final TL_account.privacyRules rules = (TL_account.privacyRules) response;
                    AndroidUtilities.runOnUIThread(() -> {
                        MessagesController.getInstance(account).putUsers(rules.users, false);
                        MessagesController.getInstance(account).putChats(rules.chats, false);
                        ContactsController.getInstance(account).setPrivacyRules(rules.rules, ContactsController.PRIVACY_RULES_TYPE_BIRTHDAY);
                    });
                }
            }
        });
    }

    private static void clearPending(long userId) {
        final SharedPreferences p = prefs();
        if (p.getBoolean(sessionDoneKey(userId), false)
                && p.getBoolean(accountDoneKey(userId), false)
                && p.getBoolean(birthdayDoneKey(userId), false)) {
            p.edit().remove(pendingKey(userId)).apply();
        }
    }

    /** How many logged-in accounts have not had all three applied — for the Settings line. */
    public static int accountsPendingDefaults() {
        if (ApplicationLoader.applicationContext == null) {
            return 0;
        }
        final SharedPreferences p = prefs();
        int pending = 0;
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            final UserConfig config = UserConfig.getInstance(a);
            if (!config.isClientActivated()) {
                continue;
            }
            final long userId = config.getClientUserId();
            if (userId != 0 && !(p.getBoolean(sessionDoneKey(userId), false)
                    && p.getBoolean(accountDoneKey(userId), false)
                    && p.getBoolean(birthdayDoneKey(userId), false))) {
                pending++;
            }
        }
        return pending;
    }

    // ---- groups this build joins for a new account ----------------------------------------------
    // Only the third app sets AUTO_JOIN_LIST; for the others it is empty and none of this runs.
    // Joining is paced: one group every few seconds, one account at a time, marked done per
    // (account, group) so nothing is attempted twice and a restart picks up where it stopped.
    // A burst of joins from one device is exactly what Telegram's anti-spam looks for, which is
    // why this crawls instead of firing sixteen requests at once, and why FLOOD_WAIT parks the
    // account until the next start rather than retrying.

    /** Comma-separated usernames without the @, filled in at build time. Empty = feature off. */
    public static final String AUTO_JOIN_LIST = "%%AUTO_JOIN%%";
    /** Whether to offer Two-Step Verification after a login. */
    public static final boolean PROMPT_2FA = %%PROMPT_2FA%%;

    private static final long JOIN_GAP_MS = 6000;
    private static final long JOIN_ERROR_GAP_MS = 20000;
    private static volatile boolean joinRunning;
    /** Accounts that hit a flood wait; left alone until the app is started again. */
    private static final java.util.Set<Integer> joinParked = new java.util.HashSet<>();
    private static String[] joinNames;

    public static String[] autoJoinGroups() {
        if (joinNames == null) {
            final java.util.ArrayList<String> out = new java.util.ArrayList<>();
            for (String part : AUTO_JOIN_LIST.split(",")) {
                final String name = part.trim().replace("@", "");
                if (!name.isEmpty()) {
                    out.add(name);
                }
            }
            joinNames = out.toArray(new String[0]);
        }
        return joinNames;
    }

    private static String joinKey(long userId, String username) {
        return "joined_" + userId + "_" + username;
    }

    /** True once every group has been joined (or permanently failed) for this account. */
    public static boolean autoJoinDone(int account) {
        if (autoJoinGroups().length == 0 || ApplicationLoader.applicationContext == null) {
            return true;
        }
        final long userId = UserConfig.getInstance(account).getClientUserId();
        if (userId == 0) {
            return true;
        }
        final SharedPreferences p = prefs();
        for (String name : autoJoinGroups()) {
            if (!p.getBoolean(joinKey(userId, name), false)) {
                return false;
            }
        }
        return true;
    }

    /** How many of the groups this account still has to join. */
    public static int autoJoinRemaining(int account) {
        if (autoJoinGroups().length == 0 || ApplicationLoader.applicationContext == null) {
            return 0;
        }
        final long userId = UserConfig.getInstance(account).getClientUserId();
        if (userId == 0) {
            return 0;
        }
        final SharedPreferences p = prefs();
        int left = 0;
        for (String name : autoJoinGroups()) {
            if (!p.getBoolean(joinKey(userId, name), false)) {
                left++;
            }
        }
        return left;
    }

    /** One line for the settings screen, so the background crawl is not invisible. */
    public static String autoJoinStatus() {
        final int groups = autoJoinGroups().length;
        if (groups == 0 || ApplicationLoader.applicationContext == null) {
            return "";
        }
        int left = 0, accounts = 0;
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (!UserConfig.getInstance(a).isClientActivated()) {
                continue;
            }
            accounts++;
            left += autoJoinRemaining(a);
        }
        if (left == 0) {
            return groups + " groups \u00b7 all joined on " + accounts + (accounts == 1 ? " account" : " accounts");
        }
        return groups + " groups \u00b7 " + left + " still to join across " + accounts
                + (accounts == 1 ? " account" : " accounts") + (joinParked.isEmpty() ? "" : ", paused by a Telegram rate limit");
    }

    /**
     * The Settings row: forget the rate-limit parking and any half-finished chain, and go again.
     * A chain whose reply never came back would otherwise sit there until the app is restarted.
     */
    public static void resumeAutoJoin() {
        joinParked.clear();
        joinRunning = false;
        startAutoJoin();
    }

    /** Starts the crawl if it is not already running. Safe to call as often as you like. */
    public static void startAutoJoin() {
        if (joinRunning || autoJoinGroups().length == 0 || ApplicationLoader.applicationContext == null) {
            return;
        }
        joinRunning = true;
        AndroidUtilities.runOnUIThread(ChihuahuaConfig::pumpAutoJoin, 3000);
    }

    /** Does one group for one account, then schedules itself again until there is nothing left. */
    private static void pumpAutoJoin() {
        try {
            final SharedPreferences p = prefs();
            for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
                final UserConfig config = UserConfig.getInstance(a);
                if (!config.isClientActivated() || joinParked.contains(a)) {
                    continue;
                }
                final long userId = config.getClientUserId();
                if (userId == 0) {
                    continue;
                }
                for (String name : autoJoinGroups()) {
                    if (!p.getBoolean(joinKey(userId, name), false)) {
                        joinOne(a, userId, name);
                        return;
                    }
                }
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
        joinRunning = false;
    }

    private static void later(long delay) {
        AndroidUtilities.runOnUIThread(ChihuahuaConfig::pumpAutoJoin, delay);
    }

    /** Marks this group done for this account, so it is never attempted again. */
    private static void markJoined(long userId, String username) {
        prefs().edit().putBoolean(joinKey(userId, username), true).apply();
    }

    private static void joinOne(int account, long userId, String username) {
        final TLRPC.TL_contacts_resolveUsername resolve = new TLRPC.TL_contacts_resolveUsername();
        resolve.username = username;
        org.telegram.tgnet.ConnectionsManager.getInstance(account).sendRequest(resolve, (response, error) -> {
            if (error != null) {
                // A username that no longer exists never will: stop trying. A flood wait parks
                // the whole account, because the limit is on the account, not on this group.
                if (error.text != null && error.text.startsWith("FLOOD_WAIT_")) {
                    AndroidUtilities.runOnUIThread(() -> {
                        joinParked.add(account);
                        later(JOIN_ERROR_GAP_MS);
                    });
                } else {
                    markJoined(userId, username);
                    AndroidUtilities.runOnUIThread(() -> later(JOIN_GAP_MS));
                }
                return;
            }
            if (!(response instanceof TLRPC.TL_contacts_resolvedPeer)) {
                markJoined(userId, username);
                AndroidUtilities.runOnUIThread(() -> later(JOIN_GAP_MS));
                return;
            }
            final TLRPC.TL_contacts_resolvedPeer resolved = (TLRPC.TL_contacts_resolvedPeer) response;
            AndroidUtilities.runOnUIThread(() -> {
                MessagesController.getInstance(account).putUsers(resolved.users, false);
                MessagesController.getInstance(account).putChats(resolved.chats, false);
                if (resolved.chats.isEmpty()) {
                    // a user, not a group: nothing to join
                    markJoined(userId, username);
                    later(JOIN_GAP_MS);
                    return;
                }
                final TLRPC.Chat chat = resolved.chats.get(0);
                if (!ChatObject.isChannel(chat)) {
                    markJoined(userId, username);
                    later(JOIN_GAP_MS);
                    return;
                }
                if (!chat.left && !chat.kicked) {
                    // already in it — just make sure it is muted
                    muteChat(account, chat);
                    markJoined(userId, username);
                    later(JOIN_GAP_MS);
                    return;
                }
                final TLRPC.TL_channels_joinChannel join = new TLRPC.TL_channels_joinChannel();
                join.channel = MessagesController.getInputChannel(chat);
                org.telegram.tgnet.ConnectionsManager.getInstance(account).sendRequest(join, (res, err) -> AndroidUtilities.runOnUIThread(() -> {
                    if (err != null && err.text != null && err.text.startsWith("FLOOD_WAIT_")) {
                        joinParked.add(account);
                        later(JOIN_ERROR_GAP_MS);
                        return;
                    }
                    if (res instanceof TLRPC.Updates) {
                        MessagesController.getInstance(account).processUpdates((TLRPC.Updates) res, false);
                    }
                    // Whatever came back — joined, already a member, or a refusal that will not
                    // change on a retry — this group is done for this account.
                    markJoined(userId, username);
                    muteChat(account, chat);
                    later(err == null ? JOIN_GAP_MS : JOIN_ERROR_GAP_MS);
                }));
            });
        });
    }

    /** Muted for good, so sixteen busy groups do not drown the accounts's own chats. */
    private static void muteChat(int account, TLRPC.Chat chat) {
        try {
            NotificationsController.getInstance(account).muteDialog(-chat.id, 0, true);
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    // ---- per-account notifications -----------------------------------------------------------
    // Telegram only has one global "show notifications from all accounts" switch. With many
    // accounts logged in you usually want a handful noisy and the rest silent, so every account
    // gets its own switch (Settings -> Chihuahua -> Notifications). Silenced accounts post no
    // notification, make no sound, and are left out of the launcher badge count.
    //
    // Default: the first account logged in notifies; every account added after it starts silent.
    // The choice is kept per user ID rather than per slot, so an account that logs out does not
    // hand its setting to whoever logs into that slot next. Accounts that were already logged in
    // when this build first ran keep exactly what they had (their old slot setting, else on).
    private static final java.util.concurrent.ConcurrentHashMap<Long, Boolean> notifyByUser = new java.util.concurrent.ConcurrentHashMap<>();
    private static volatile boolean notifyMigrated;

    private static String notifyKey(long userId) {
        return "notify_user_" + userId;
    }

    private static String legacyNotifyKey(int account) {
        return "notify_account_" + account;
    }

    /**
     * Once per install, and only after every slot's config has been read: give each account that
     * is logged in right now an explicit value, so the "new accounts start silent" default can
     * only ever apply to logins made after this build. False while it is too early to know who
     * is logged in (the start-up loop reads the slots one at a time).
     */
    private static boolean migrateNotifySettings(SharedPreferences prefs) {
        if (notifyMigrated) {
            return true;
        }
        if (prefs.getBoolean("notify_migrated", false)) {
            notifyMigrated = true;
            return true;
        }
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (!UserConfig.getInstance(a).isConfigLoaded()) {
                return false;
            }
        }
        final SharedPreferences.Editor editor = prefs.edit();
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            final long userId = UserConfig.getInstance(a).getClientUserId();
            if (userId != 0) {
                editor.putBoolean(notifyKey(userId), prefs.getBoolean(legacyNotifyKey(a), true));
            }
            editor.remove(legacyNotifyKey(a));
        }
        editor.putBoolean("notify_migrated", true).apply();
        notifyMigrated = true;
        return true;
    }

    /** False when this account's notifications are off (switched off, or added after the first account). */
    public static boolean notificationsEnabled(int account) {
        if (ApplicationLoader.applicationContext == null) {
            return true;
        }
        final long userId = UserConfig.getInstance(account).getClientUserId();
        if (userId == 0) {
            return true;
        }
        final Boolean cached = notifyByUser.get(userId);
        if (cached != null) {
            return cached;
        }
        final SharedPreferences prefs = prefs();
        if (!migrateNotifySettings(prefs)) {
            return prefs.getBoolean(legacyNotifyKey(account), true);
        }
        final String key = notifyKey(userId);
        final boolean value;
        if (prefs.contains(key)) {
            value = prefs.getBoolean(key, true);
        } else {
            // A login made after this build's first run: on only while it is the sole account.
            boolean others = false;
            for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
                if (a != account && UserConfig.getInstance(a).isClientActivated()) {
                    others = true;
                    break;
                }
            }
            value = !others;
            prefs.edit().putBoolean(key, value).apply();
        }
        notifyByUser.put(userId, value);
        return value;
    }

    public static void setNotificationsEnabled(int account, boolean enabled) {
        final long userId = UserConfig.getInstance(account).getClientUserId();
        if (userId == 0) {
            return;
        }
        notifyByUser.put(userId, enabled);
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(notifyKey(userId), enabled).apply();
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

    /** Suffix for the profile status line, e.g. " \u00b7 est. Jun 2026"; empty when the switch is off. */
    public static String accountAgeSuffix(long userId) {
        load();
        if (!accountAge) {
            return "";
        }
        String created = estimatedCreation(userId);
        return created.isEmpty() ? "" : " \u00b7 est. " + created;
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
            case KEY_FLAG_NEW:
                return flagNew;
            case KEY_QUICK_BAN:
                return quickBan;
            case KEY_KEEP_CONNECTED:
                return keepConnected;
            case KEY_AGE_ALWAYS:
                return ageAlways;
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
            case KEY_FLAG_NEW:
                flagNew = value;
                break;
            case KEY_QUICK_BAN:
                quickBan = value;
                break;
            case KEY_KEEP_CONNECTED:
                keepConnected = value;
                break;
            case KEY_AGE_ALWAYS:
                ageAlways = value;
                break;
            default:
                return;
        }
        if (ApplicationLoader.applicationContext != null) {
            prefs().edit().putBoolean(key, value).apply();
        }
    }
}
