#!/usr/bin/env python3
"""
customize.py — turns a clean Telegram-Android checkout into "Chihuahua Telegram".

Run by the GitHub Actions workflow:   python3 customize.py <path-to-telegram-checkout>

Settings come from environment variables (the workflow loads config.env and the
repository secrets):

  APP_NAME           launcher label                       (default: Chihuahua Telegram)
  APP_PACKAGE        Android application id               (default: com.chihuahua.messenger)
  MAX_ACCOUNTS       accounts the app can hold            (default: 32)
  BUILD_ABI          arm64-v8a  |  all                    (default: arm64-v8a)
  GRADLE_HEAP        JVM heap for Gradle, e.g. 8g         (default: 8g)
  TG_API_ID          your api_id   from my.telegram.org   (required, secret)
  TG_API_HASH        your api_hash from my.telegram.org   (required, secret)
  KEYSTORE_PASSWORD  password of the signing keystore     (required, secret)
  KEYSTORE_ALIAS     key alias inside the keystore        (default: chihuahua)

Every edit is anchored on an exact piece of upstream text and the script aborts
if an anchor is not found exactly the expected number of times — so if Telegram
changes its code, the build fails loudly instead of producing a half-patched app.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "telegram").resolve()
HERE = Path(__file__).resolve().parent
ICONS = HERE / os.environ.get("ICONS_DIR", "icons").strip()

APP_NAME = os.environ.get("APP_NAME", "Chihuahua 1").strip()
APP_PACKAGE = os.environ.get("APP_PACKAGE", "com.chihuahua.messenger").strip()
MAX_ACCOUNTS = int(os.environ.get("MAX_ACCOUNTS", "32"))
BUILD_ABI = os.environ.get("BUILD_ABI", "arm64-v8a").strip()
GRADLE_HEAP = os.environ.get("GRADLE_HEAP", "8g").strip()
TG_API_ID = os.environ.get("TG_API_ID", "").strip()
TG_API_HASH = os.environ.get("TG_API_HASH", "").strip()
KEYSTORE_PASSWORD = os.environ.get("KEYSTORE_PASSWORD", "").strip()
KEYSTORE_ALIAS = os.environ.get("KEYSTORE_ALIAS", "chihuahua").strip()
# The chat list shows this in place of Telegram's wordmark: the app name without a trailing
# "Telegram", so "Chihuahua Telegram" -> "Chihuahua" and "Chihuahua 2" stays as it is.
CHAT_LIST_TITLE = re.sub(r"\s*Telegram$", "", APP_NAME).strip() or APP_NAME
ACTIVATION_CODE = os.environ.get("ACTIVATION_CODE", "").strip()
# A group promoted by a row at the top of the Setup tab. Empty username = no row.
PROMO_GROUP = os.environ.get("PROMO_GROUP", "").strip().lstrip("@")
PROMO_TITLE = os.environ.get("PROMO_TITLE", "").strip() or ("@" + PROMO_GROUP if PROMO_GROUP else "")

DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]

errors = []


def fail(msg):
    errors.append(msg)
    print(f"  !! {msg}")


def check_inputs():
    if not ROOT.is_dir() or not (ROOT / "gradle.properties").exists():
        sys.exit(f"Telegram checkout not found at {ROOT}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", APP_PACKAGE):
        sys.exit(f"APP_PACKAGE '{APP_PACKAGE}' is not a valid Android package name")
    if not (2 <= MAX_ACCOUNTS <= 256):
        sys.exit("MAX_ACCOUNTS must be between 2 and 256")
    if not TG_API_ID.isdigit():
        sys.exit("TG_API_ID secret is missing or not a number — add it in GitHub → Settings → Secrets → Actions")
    if not re.fullmatch(r"[0-9a-f]{32}", TG_API_HASH):
        sys.exit("TG_API_HASH secret is missing or not a 32-char hex string — add it in GitHub → Settings → Secrets → Actions")
    if not KEYSTORE_PASSWORD:
        sys.exit("KEYSTORE_PASSWORD secret is missing — add it in GitHub → Settings → Secrets → Actions")
    if BUILD_ABI not in ("arm64-v8a", "armeabi-v7a", "x86_64", "x86", "all"):
        sys.exit("BUILD_ABI must be arm64-v8a, armeabi-v7a, x86_64, x86 or all")
    if not ICONS.is_dir():
        sys.exit(f"icons folder missing at {ICONS}")


def edit(relpath, replacements):
    """replacements: list of (old, new, expected_count). Applies in order, verifies counts."""
    path = ROOT / relpath
    if not path.exists():
        fail(f"missing file {relpath}")
        return
    text = path.read_text(encoding="utf-8")
    for old, new, expected in replacements:
        n = text.count(old)
        if n != expected:
            fail(f"{relpath}: anchor found {n}x, expected {expected}x: {old.strip()[:70]!r}")
            continue
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  ok  {relpath}")


def java_escape(s):
    """For a Java string literal (the app name reaching source code, not resources)."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "\\'"))


def patch_gradle_properties():
    edit("gradle.properties", [
        ("APP_PACKAGE=org.telegram.messenger\n", f"APP_PACKAGE={APP_PACKAGE}\n", 1),
        ("RELEASE_KEY_PASSWORD=android\n", f"RELEASE_KEY_PASSWORD={KEYSTORE_PASSWORD}\n", 1),
        ("RELEASE_KEY_ALIAS=androidkey\n", f"RELEASE_KEY_ALIAS={KEYSTORE_ALIAS}\n", 1),
        ("RELEASE_STORE_PASSWORD=android\n", f"RELEASE_STORE_PASSWORD={KEYSTORE_PASSWORD}\n", 1),
        ("org.gradle.jvmargs=-Xmx8g -XX:MaxMetaspaceSize=1g\n",
         f"org.gradle.jvmargs=-Xmx{GRADLE_HEAP} -XX:MaxMetaspaceSize=1g\n", 1),
    ])


def patch_account_limit():
    edit("TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java", [
        ("public final static int MAX_ACCOUNT_DEFAULT_COUNT = 3;",
         f"public final static int MAX_ACCOUNT_DEFAULT_COUNT = {MAX_ACCOUNTS};", 1),
        ("public final static int MAX_ACCOUNT_COUNT = 4;",
         f"public final static int MAX_ACCOUNT_COUNT = {MAX_ACCOUNTS};", 1),
        ("return hasPremiumOnAccounts() ? 5 : 3;",
         "return MAX_ACCOUNT_COUNT;", 1),
    ])


NATIVE_GETINSTANCE_OLD = (
    "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
    "    switch (instanceNum) {\n"
    "        case 0:\n"
    "            static ConnectionsManager instance0(0);\n"
    "            return instance0;\n"
    "        case 1:\n"
    "            static ConnectionsManager instance1(1);\n"
    "            return instance1;\n"
    "        case 2:\n"
    "            static ConnectionsManager instance2(2);\n"
    "            return instance2;\n"
    "        case 3:\n"
    "            static ConnectionsManager instance3(3);\n"
    "            return instance3;\n"
    "        case 4:\n"
    "        default:\n"
    "            static ConnectionsManager instance4(4);\n"
    "            return instance4;\n"
    "    }\n"
    "}\n"
)

NATIVE_GETINSTANCE_NEW = (
    "ConnectionsManager& ConnectionsManager::getInstance(int32_t instanceNum) {\n"
    "    // Chihuahua: one native instance per account slot. Upstream had a fixed switch of 5,\n"
    "    // so every account beyond slot 4 shared instance 4 and re-ran init() on it (crash at start).\n"
    "    static std::atomic<ConnectionsManager*> instances[MAX_ACCOUNT_COUNT];\n"
    "    static std::mutex instancesMutex;\n"
    "    if (instanceNum < 0 || instanceNum >= MAX_ACCOUNT_COUNT) {\n"
    "        instanceNum = MAX_ACCOUNT_COUNT - 1;\n"
    "    }\n"
    "    ConnectionsManager *instance = instances[instanceNum].load(std::memory_order_acquire);\n"
    "    if (instance == nullptr) {\n"
    "        std::lock_guard<std::mutex> lock(instancesMutex);\n"
    "        instance = instances[instanceNum].load(std::memory_order_relaxed);\n"
    "        if (instance == nullptr) {\n"
    "            instance = new ConnectionsManager(instanceNum);\n"
    "            instances[instanceNum].store(instance, std::memory_order_release);\n"
    "        }\n"
    "    }\n"
    "    return *instance;\n"
    "}\n"
)


def patch_native_account_limit():
    """The C++ network layer (tgnet) only had room for 5 accounts, in two places:
    MAX_ACCOUNT_COUNT (sizes the per-account JNIEnv array and the delegate loop — slot 5+
    wrote past the end of that array and corrupted neighbouring globals) and the fixed
    switch in ConnectionsManager::getInstance(). Give both MAX_ACCOUNTS."""
    edit("TMessagesProj/jni/tgnet/Defines.h", [
        ("#define MAX_ACCOUNT_COUNT 5\n", f"#define MAX_ACCOUNT_COUNT {MAX_ACCOUNTS}\n", 1),
    ])
    edit("TMessagesProj/jni/tgnet/ConnectionsManager.cpp", [
        ('#include "ConnectionsManager.h"\n',
         '#include <atomic>\n#include <mutex>\n#include "ConnectionsManager.h"\n', 1),
        (NATIVE_GETINSTANCE_OLD, NATIVE_GETINSTANCE_NEW, 1),
    ])


def patch_build_vars():
    edit("TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java", [
        ("public static int APP_ID = 4;", f"public static int APP_ID = {TG_API_ID};", 1),
        ('public static String APP_HASH = "014b35b6184100b085b0d0572f9b5103";',
         f'public static String APP_HASH = "{TG_API_HASH}";', 1),
        ('public static String SAFETYNET_KEY = "AIzaSyDqt8P-7F7CPCseMkOiVRgb1LY8RN1bvH8";',
         'public static String SAFETYNET_KEY = "";', 1),
        ("public static boolean SUPPORTS_PASSKEYS = true;",
         "public static boolean SUPPORTS_PASSKEYS = false;", 1),
    ])


def patch_app_name():
    edit("TMessagesProj/src/main/res/values/strings.xml", [
        ('<string name="AppName">Telegram</string>',
         f'<string name="AppName">{xml_escape(APP_NAME)}</string>', 1),
        ('<string name="AppNameBeta">Telegram Beta</string>',
         f'<string name="AppNameBeta">{xml_escape(APP_NAME)} Beta</string>', 1),
    ])


def patch_abis():
    if BUILD_ABI == "all":
        print("  --  building all ABIs (slow)")
        return
    edit("TMessagesProj_App/build.gradle", [
        ('abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"',
         f'abiFilters "{BUILD_ABI}"', 3),
    ])
    # The library module compiles the native code; without a filter it builds all four ABIs.
    edit("TMessagesProj/build.gradle", [
        ("    defaultConfig {\n        minSdkVersion 21\n        targetSdkVersion 36\n",
         "    defaultConfig {\n        minSdkVersion 21\n        targetSdkVersion 36\n"
         f'        ndk {{ abiFilters "{BUILD_ABI}" }}\n', 1),
    ])


def patch_google_services():
    # The google-services Gradle plugin refuses to build unless the JSON lists our package.
    # Push notifications through Firebase will not work with these placeholder entries
    # (the app falls back to its own background connection); see README for the fix.
    for rel in ("TMessagesProj/google-services.json", "TMessagesProj_App/google-services.json"):
        path = ROOT / rel
        if not path.exists():
            fail(f"missing file {rel}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        clients = data.get("client", [])
        if not clients:
            fail(f"{rel}: no client entries")
            continue
        existing = {c["client_info"]["android_client_info"]["package_name"] for c in clients}
        for pkg in (APP_PACKAGE, APP_PACKAGE + ".beta", APP_PACKAGE + ".web"):
            if pkg in existing:
                continue
            new = json.loads(json.dumps(clients[0]))
            new["client_info"]["android_client_info"]["package_name"] = pkg
            clients.append(new)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  ok  {rel}")


def patch_account_type():
    """Give the app its own Android account type / contact mime types so it can live
    next to the official app instead of fighting it for 'org.telegram.messenger'."""
    old_mime = "vnd.org.telegram.messenger.android"
    new_mime = f"vnd.{APP_PACKAGE}.android"
    edit("TMessagesProj/src/main/res/xml/auth.xml", [
        ('android:accountType="org.telegram.messenger"', f'android:accountType="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/sync_contacts.xml", [
        ('android:accountType="org.telegram.messenger"', f'android:accountType="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/auth_menu.xml", [
        ('android:targetPackage="org.telegram.messenger"', f'android:targetPackage="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/contacts.xml", [(old_mime, new_mime, 3)])
    edit("TMessagesProj/src/main/AndroidManifest.xml", [(old_mime, new_mime, 3)])
    edit("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java", [(old_mime, new_mime, 2)])
    edit("TMessagesProj/src/main/java/org/telegram/messenger/ContactsController.java", [
        (old_mime, new_mime, 3),
        ('"org.telegram.messenger"', 'ApplicationLoader.applicationContext.getPackageName()', 5),
    ])


# ---------------------------------------------------------------------------------------
# Feature: "Add to group" in a user's profile menu (like BGram). Upstream only offers it
# for bots; this adds the same flow for people: pick one of your groups, confirm, add.
ADD_TO_GROUP_HANDLER = (
    "                } else if (id == chihuahua_add_to_group) {\n"
    "                    final TLRPC.User user = getMessagesController().getUser(userId);\n"
    "                    if (user == null) {\n"
    "                        return;\n"
    "                    }\n"
    "                    Bundle args = new Bundle();\n"
    "                    args.putBoolean(\"onlySelect\", true);\n"
    "                    args.putInt(\"dialogsType\", DialogsActivity.DIALOGS_TYPE_ADD_USERS_TO);\n"
    "                    args.putBoolean(\"resetDelegate\", false);\n"
    "                    args.putBoolean(\"closeFragment\", false);\n"
    "                    DialogsActivity fragment = new DialogsActivity(args);\n"
    "                    fragment.setDelegate((fragment1, dids, message, param, notify, scheduleDate, scheduleRepeatPeriod, topicsFragment) -> {\n"
    "                        long did = dids.get(0).dialogId;\n"
    "                        TLRPC.Chat chat = getMessagesController().getChat(-did);\n"
    "                        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), resourcesProvider);\n"
    "                        builder.setTitle(LocaleController.getString(R.string.AddToGroup));\n"
    "                        String chatName = chat == null ? \"\" : chat.title;\n"
    "                        builder.setMessage(AndroidUtilities.replaceTags(formatString(\"AddMembersAlertNamesText\", R.string.AddMembersAlertNamesText, UserObject.getUserName(user), chatName)));\n"
    "                        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);\n"
    "                        builder.setPositiveButton(LocaleController.getString(R.string.Add), (di, i) -> {\n"
    "                            disableProfileAnimation = true;\n"
    "                            Bundle args1 = new Bundle();\n"
    "                            args1.putBoolean(\"scrollToTopOnResume\", true);\n"
    "                            args1.putLong(\"chat_id\", -did);\n"
    "                            if (!getMessagesController().checkCanOpenChat(args1, fragment1)) {\n"
    "                                return;\n"
    "                            }\n"
    "                            ChatActivity chatActivity = new ChatActivity(args1);\n"
    "                            getNotificationCenter().removeObserver(ProfileActivity.this, NotificationCenter.closeChats);\n"
    "                            getNotificationCenter().postNotificationName(NotificationCenter.closeChats);\n"
    "                            getMessagesController().addUserToChat(-did, user, 0, null, chatActivity, true, null, null);\n"
    "                            presentFragment(chatActivity, true);\n"
    "                        });\n"
    "                        showDialog(builder.create());\n"
    "                        return true;\n"
    "                    });\n"
    "                    presentFragment(fragment);\n"
)

CONTACT_SHORTCUT_ANCHOR = (
    "                if (!isBot && getContactsController().contactsDict.get(userId) != null) {\n"
    "                    otherItem.addSubItem(add_shortcut, R.drawable.msg_home, LocaleController.getString(R.string.AddShortcut));\n"
)
CHAT_MENU_ANCHOR = (
    "        } else if (chatId != 0) {\n"
    "            TLRPC.Chat chat = getMessagesController().getChat(chatId);\n"
    "            hasVoiceChatItem = false;\n"
)
STATUS_ANCHOR = "                newString2 = LocaleController.formatUserStatus(currentAccount, user, isOnline, shortStatus ? new boolean[1] : null);\n"
STATUS_SET_ANCHOR = "                } else {\n                    onlineTextView[a].setText(newString2);\n                }\n"

COPY_ID_HANDLER = (
    "                } else if (id == chihuahua_copy_id) {\n"
    "                    String idText;\n"
    "                    if (userId != 0) {\n"
    "                        idText = String.valueOf(userId);\n"
    "                    } else {\n"
    "                        TLRPC.Chat chat = getMessagesController().getChat(chatId);\n"
    "                        idText = (ChatObject.isChannel(chat) ? \"-100\" : \"-\") + chatId;\n"
    "                    }\n"
    "                    AndroidUtilities.addToClipboard(idText);\n"
    "                    if (BulletinFactory.canShowBulletin(ProfileActivity.this)) {\n"
    "                        BulletinFactory.of(ProfileActivity.this).createCopyBulletin(\"ID \" + idText + \" copied\").show();\n"
    "                    }\n"
)

BAN_EVERYWHERE_HANDLER = (
    "                } else if (id == chihuahua_ban_everywhere) {\n"
    "                    final TLRPC.User user = getMessagesController().getUser(userId);\n"
    "                    if (user == null) {\n"
    "                        return;\n"
    "                    }\n"
    "                    final ArrayList<TLRPC.Chat> chats = new ArrayList<>();\n"
    "                    for (TLRPC.Dialog dialog : getMessagesController().getAllDialogs()) {\n"
    "                        if (dialog.id >= 0) {\n"
    "                            continue;\n"
    "                        }\n"
    "                        TLRPC.Chat chat = getMessagesController().getChat(-dialog.id);\n"
    "                        if (chat == null || chat.left || chat.kicked || ChatObject.isChannelAndNotMegaGroup(chat) || !ChatObject.canBlockUsers(chat)) {\n"
    "                            continue;\n"
    "                        }\n"
    "                        chats.add(chat);\n"
    "                    }\n"
    "                    if (chats.isEmpty()) {\n"
    "                        if (BulletinFactory.canShowBulletin(ProfileActivity.this)) {\n"
    "                            BulletinFactory.of(ProfileActivity.this).createSimpleBulletin(R.raw.error, \"You are not an admin with ban rights in any group.\").show();\n"
    "                        }\n"
    "                        return;\n"
    "                    }\n"
    "                    final String groupsWord = chats.size() == 1 ? \" group\" : \" groups\";\n"
    "                    AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), resourcesProvider);\n"
    "                    builder.setTitle(\"Ban from all my groups\");\n"
    "                    builder.setMessage(AndroidUtilities.replaceTags(\"Ban **\" + UserObject.getUserName(user) + \"** from \" + chats.size() + groupsWord + \" you manage? They will be removed and cannot rejoin.\"));\n"
    "                    builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);\n"
    "                    builder.setPositiveButton(\"Ban\", (di, i) -> {\n"
    "                        for (TLRPC.Chat chat : chats) {\n"
    "                            getMessagesController().deleteParticipantFromChat(chat.id, user, chat, false, false);\n"
    "                        }\n"
    "                        if (BulletinFactory.canShowBulletin(ProfileActivity.this)) {\n"
    "                            BulletinFactory.of(ProfileActivity.this).createSimpleBulletin(R.raw.ic_ban, \"Banned from \" + chats.size() + groupsWord).show();\n"
    "                        }\n"
    "                    });\n"
    "                    AlertDialog banDialog = builder.create();\n"
    "                    showDialog(banDialog);\n"
    "                    TextView banButton = (TextView) banDialog.getButton(DialogInterface.BUTTON_POSITIVE);\n"
    "                    if (banButton != null) {\n"
    "                        banButton.setTextColor(getThemedColor(Theme.key_text_RedBold));\n"
    "                    }\n"
)


ADMINS_HANDLER = (
    "                } else if (id == chihuahua_admins) {\n"
    "                    Bundle adminArgs = new Bundle();\n"
    "                    adminArgs.putLong(\"chat_id\", chatId);\n"
    "                    adminArgs.putInt(\"type\", ChatUsersActivity.TYPE_ADMIN);\n"
    "                    ChatUsersActivity adminFragment = new ChatUsersActivity(adminArgs);\n"
    "                    adminFragment.setInfo(chatInfo);\n"
    "                    presentFragment(adminFragment);\n"
)


ACTIVATION_GATE = (
    "    private android.app.AlertDialog chihuahuaActivationDialog;\n"
    "\n"
    "    private void chihuahuaCheckActivation() {\n"
    "        if (org.telegram.messenger.ChihuahuaConfig.isActivated()) {\n"
    "            return;\n"
    "        }\n"
    "        if (chihuahuaActivationDialog != null && chihuahuaActivationDialog.isShowing()) {\n"
    "            return;\n"
    "        }\n"
    "        final android.widget.EditText input = new android.widget.EditText(this);\n"
    "        input.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD);\n"
    "        input.setHint(\"Activation code\");\n"
    "        final android.widget.FrameLayout wrap = new android.widget.FrameLayout(this);\n"
    "        wrap.setPadding(AndroidUtilities.dp(20), AndroidUtilities.dp(8), AndroidUtilities.dp(20), 0);\n"
    "        wrap.addView(input);\n"
    "        final android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(this)\n"
    "                .setTitle(\"Chihuahua Telegram\")\n"
    "                .setMessage(\"This is a private build. Enter the activation code to continue.\")\n"
    "                .setView(wrap)\n"
    "                .setCancelable(false)\n"
    "                .setPositiveButton(\"Unlock\", null)\n"
    "                .setNegativeButton(\"Quit\", (d, w) -> {\n"
    "                    finishAffinity();\n"
    "                    System.exit(0);\n"
    "                })\n"
    "                .create();\n"
    "        dialog.setOnShowListener(d -> dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {\n"
    "            if (org.telegram.messenger.ChihuahuaConfig.tryActivate(input.getText().toString())) {\n"
    "                dialog.dismiss();\n"
    "            } else {\n"
    "                input.setError(\"Wrong code\");\n"
    "            }\n"
    "        }));\n"
    "        chihuahuaActivationDialog = dialog;\n"
    "        dialog.show();\n"
    "    }\n"
    "\n"
)


# The same row serves user and group profiles. Groups show the ID the way bots
# and the Telegram API want it: -100<id> for supergroups and channels, -<id>
# for basic groups — the same text the old menu item copied.
ID_ROW_BIND = """                    } else if (position == chihuahuaIdRow) {
                        final String chihuahuaId = userId != 0
                                ? String.valueOf(userId)
                                : (ChatObject.isChannel(currentChat) ? "-100" : "-") + chatId;
                        detailCell.setTextAndValue(chihuahuaId, "ID \\u00b7 tap to copy", true);
"""


GROUP_BADGE = """            if (currentUser != null && !currentMessageObject.isOutOwner()) {
                final String chihuahuaAge = org.telegram.messenger.ChihuahuaConfig.groupAgeBadge(currentUser.id);
                if (!chihuahuaAge.isEmpty()) {
                    if (adminString == null) {
                        adminString = new SpannableStringBuilder();
                    } else {
                        adminString.append(" ");
                    }
                    final int chihuahuaStart = adminString.length();
                    adminString.append(chihuahuaAge);
                    if (org.telegram.messenger.ChihuahuaConfig.isNewAccount(currentUser.id)) {
                        adminString.setSpan(new ForegroundColorSpanThemable(Theme.key_text_RedBold), chihuahuaStart, adminString.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
                    }
                }
            }
"""


QUICK_BAN_METHODS = """    private static final int CHIHUAHUA_WIPE_ONLY = 0;
    private static final int CHIHUAHUA_WIPE_MUTE = 1;
    private static final int CHIHUAHUA_WIPE_BAN = 2;

    private static final int OPTION_CHIHUAHUA_NUKE = 900;
    private static final int OPTION_CHIHUAHUA_MUTE = 901;
    private static final int OPTION_CHIHUAHUA_WIPE = 902;

    /** The user this message came from, when this build may moderate them here; null otherwise. */
    private TLRPC.User chihuahuaQuickBanTarget(MessageObject message) {
        if (message == null || currentChat == null || currentEncryptedChat != null) {
            return null;
        }
        if (!ChatObject.isMegagroup(currentChat) || !ChatObject.canBlockUsers(currentChat)) {
            return null;
        }
        if (message.isOut() || message.getId() <= 0 || chatMode != MODE_DEFAULT) {
            return null;
        }
        final long fromId = message.getSenderId();
        if (fromId <= 0 || fromId == getUserConfig().getClientUserId()) {
            return null;
        }
        final TLRPC.User user = getMessagesController().getUser(fromId);
        if (user == null || UserObject.isDeleted(user)) {
            return null;
        }
        return user;
    }

    /** Groups where this account is an admin who can remove or restrict members. */
    private ArrayList<TLRPC.Chat> chihuahuaManagedGroups() {
        final ArrayList<TLRPC.Chat> chats = new ArrayList<>();
        for (TLRPC.Dialog dialog : getMessagesController().getAllDialogs()) {
            if (dialog.id >= 0) {
                continue;
            }
            final TLRPC.Chat chat = getMessagesController().getChat(-dialog.id);
            if (chat == null || chat.left || chat.kicked || !ChatObject.isMegagroup(chat) || !ChatObject.canBlockUsers(chat)) {
                continue;
            }
            chats.add(chat);
        }
        return chats;
    }

    /** Everything a muted member may no longer do: post anything, react, invite, pin, edit info. */
    private TLRPC.TL_chatBannedRights chihuahuaMuteRights() {
        final TLRPC.TL_chatBannedRights rights = new TLRPC.TL_chatBannedRights();
        rights.view_messages = false;
        rights.send_messages = true;
        rights.send_media = true;
        rights.send_stickers = true;
        rights.send_gifs = true;
        rights.send_games = true;
        rights.send_inline = true;
        rights.embed_links = true;
        rights.send_polls = true;
        rights.send_photos = true;
        rights.send_videos = true;
        rights.send_roundvideos = true;
        rights.send_audios = true;
        rights.send_voices = true;
        rights.send_docs = true;
        rights.send_plain = true;
        rights.send_reactions = true;
        rights.invite_users = true;
        rights.change_info = true;
        rights.pin_messages = true;
        rights.until_date = 0;
        return rights;
    }

    /**
     * Clears a sender out of every group this account manages. In each group, in this order:
     * find their messages (messages.search by sender, up to 100), report those to Telegram for
     * spam (channels.reportSpam -- the same call Telegram's own "Report spam" tick makes), and only
     * then delete every message of theirs (channels.deleteParticipantHistory, paged until done) and
     * every reaction (messages.deleteParticipantReactions). Report before delete, because a report
     * names message ids and they must still exist. Then, by {@code mode}: nothing, mute, or ban.
     *
     * Wipe runs the moment it is tapped. Mute and ban still ask first.
     */
    private void chihuahuaWipeEverywhere(MessageObject message, int mode) {
        final TLRPC.User user = chihuahuaQuickBanTarget(message);
        final TLRPC.Chat chat = currentChat;
        if (user == null || chat == null) {
            return;
        }
        final ArrayList<TLRPC.Chat> chats = chihuahuaManagedGroups();
        if (chats.isEmpty()) {
            return;
        }
        final int knownId = message.getId();
        final String name = UserObject.getUserName(user);
        final String where = chats.size() + (chats.size() == 1 ? " group" : " groups") + " you manage";
        final Runnable run = () -> {
            for (TLRPC.Chat group : chats) {
                chihuahuaWipeInGroup(group, user, mode, group.id == chat.id ? knownId : 0);
            }
            if (BulletinFactory.canShowBulletin(ChatActivity.this)) {
                final String done = mode == CHIHUAHUA_WIPE_BAN ? name + " banned from " + where
                        : mode == CHIHUAHUA_WIPE_MUTE ? name + " muted in " + where
                        : name + " wiped from " + where;
                BulletinFactory.of(ChatActivity.this).createSimpleBulletin(R.raw.ic_ban, done, "Reporting, then deleting every message and reaction of theirs").show();
            }
        };
        if (mode == CHIHUAHUA_WIPE_ONLY) {
            run.run();
            return;
        }
        if (getParentActivity() == null) {
            return;
        }
        final String title, question, confirm;
        if (mode == CHIHUAHUA_WIPE_BAN) {
            title = "Ban everywhere and wipe";
            question = "Ban **" + name + "** from " + where + ", delete every message and reaction of theirs in them, and report them to Telegram for spam? They are removed and cannot rejoin.";
            confirm = "Ban and wipe";
        } else {
            title = "Mute everywhere and wipe";
            question = "Mute **" + name + "** in " + where + ", delete every message and reaction of theirs in them, and report them to Telegram for spam? They stay in the groups but cannot post or react.";
            confirm = "Mute and wipe";
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), themeDelegate);
        builder.setTitle(title);
        builder.setMessage(AndroidUtilities.replaceTags(question));
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        builder.setPositiveButton(confirm, (di, i) -> run.run());
        AlertDialog wipeDialog = builder.create();
        showDialog(wipeDialog);
        TextView wipeButton = (TextView) wipeDialog.getButton(DialogInterface.BUTTON_POSITIVE);
        if (wipeButton != null) {
            wipeButton.setTextColor(getThemedColor(Theme.key_text_RedBold));
        }
    }

    /** One group: search their messages -> report them -> delete history and reactions -> mute/ban. */
    private void chihuahuaWipeInGroup(TLRPC.Chat group, TLRPC.User user, int mode, int knownMessageId) {
        final Runnable wipe = () -> {
            getMessagesController().deleteUserChannelHistory(group, user, null, 0);
            getMessagesController().deleteUserChannelAllReactions(group, user, null);
            if (mode == CHIHUAHUA_WIPE_MUTE) {
                getMessagesController().setParticipantBannedRole(group.id, user, null, chihuahuaMuteRights(), false, ChatActivity.this);
            } else if (mode == CHIHUAHUA_WIPE_BAN) {
                getMessagesController().deleteParticipantFromChat(group.id, user, group, false, false);
            }
        };
        final TLRPC.TL_messages_search search = new TLRPC.TL_messages_search();
        search.peer = MessagesController.getInputPeer(group);
        search.q = "";
        search.from_id = MessagesController.getInputPeer(user);
        search.flags |= 1;
        search.filter = new TLRPC.TL_inputMessagesFilterEmpty();
        search.limit = 100;
        getConnectionsManager().sendRequest(search, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            final ArrayList<Integer> ids = new ArrayList<>();
            if (response instanceof TLRPC.messages_Messages) {
                for (TLRPC.Message m : ((TLRPC.messages_Messages) response).messages) {
                    ids.add(m.id);
                }
            }
            if (knownMessageId > 0 && !ids.contains(knownMessageId)) {
                ids.add(knownMessageId);
            }
            if (ids.isEmpty()) {
                wipe.run();
                return;
            }
            final TLRPC.TL_channels_reportSpam report = new TLRPC.TL_channels_reportSpam();
            report.channel = MessagesController.getInputChannel(group);
            report.participant = MessagesController.getInputPeer(user);
            report.id = ids;
            // Delete only once the report has been answered, so the ids it names still exist.
            getConnectionsManager().sendRequest(report, (r, e) -> AndroidUtilities.runOnUIThread(wipe));
        }));
    }

"""

QUICK_BAN_MENU_ANCHOR = """        if (showWelcomeMessageRevertOption(primaryMessage)) {
            items.add(getString(R.string.WelcomeMessageRevert));
            options.add(OPTION_WELCOME_REVERT);
            icons.add(R.drawable.outline_revert_24);
        }
    }
"""

QUICK_BAN_HANDLER_ANCHOR = """            case OPTION_DELETE: {
                if (getParentActivity() == null) {
"""


def patch_foreground_connection():
    """Without Google push, notifications only arrive while the app's own connection is up, and
    Telegram's "Keep-Alive Service" is a plain background Service that Android 8+ kills a minute
    after the app leaves the screen. Turn it into a real foreground service (quiet ongoing
    notification), start it the way Android 8+ requires, and declare it "specialUse" so Android 15's
    six-hour daily cap on "dataSync" services does not apply."""
    shutil.copy(HERE / "patches" / "NotificationsService.java",
                ROOT / "TMessagesProj/src/main/java/org/telegram/messenger/NotificationsService.java")
    print("  ok  NotificationsService.java (foreground service)")

    edit("TMessagesProj/src/main/AndroidManifest.xml", [
        ('    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />\n',
         '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />\n'
         '    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />\n'
         '    <uses-permission android:name="android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" />\n', 1),
        ('        <service\n'
         '            android:name=".NotificationsService"\n'
         '            android:enabled="true"\n'
         '            android:exported="true"\n'
         '            android:foregroundServiceType="dataSync"\n'
         '        />\n',
         '        <service\n'
         '            android:name=".NotificationsService"\n'
         '            android:enabled="true"\n'
         '            android:exported="true"\n'
         '            android:foregroundServiceType="specialUse">\n'
         '            <property\n'
         '                android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"\n'
         '                android:value="Holds the Telegram connection open so messages arrive without Google push" />\n'
         '        </service>\n', 1),
    ])

    # Android 8+ refuses startService() from the background; a foreground service must be started as one.
    edit("TMessagesProj/src/main/java/org/telegram/messenger/ApplicationLoader.java", [
        ("                applicationContext.startService(new Intent(applicationContext, NotificationsService.class));\n",
         "                Intent chihuahuaService = new Intent(applicationContext, NotificationsService.class);\n"
         "                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {\n"
         "                    applicationContext.startForegroundService(chihuahuaService);\n"
         "                } else {\n"
         "                    applicationContext.startService(chihuahuaService);\n"
         "                }\n", 1),
    ])


def patch_quick_ban():
    """One menu item on a group message that bans the sender, deletes all of their messages and
    reactions in that group and reports them to Telegram for spam. Telegram can do all four, but
    only as separate checkboxes in the delete sheet, ticked one at a time. Only appears where this
    account is an admin with ban rights in a group."""
    pa = "TMessagesProj/src/main/java/org/telegram/ui/ChatActivity.java"
    menu_item = (
        '        if (org.telegram.messenger.ChihuahuaConfig.quickBan() && chihuahuaQuickBanTarget(selectedObject) != null) {\n'
        '            items.add("Ban, wipe & report");\n'
        '            options.add(OPTION_CHIHUAHUA_NUKE);\n'
        '            icons.add(R.drawable.msg_block2);\n'
        '            items.add("Mute, wipe & report");\n'
        '            options.add(OPTION_CHIHUAHUA_MUTE);\n'
        '            icons.add(R.drawable.msg_mute);\n'
        '            items.add("Wipe & report");\n'
        '            options.add(OPTION_CHIHUAHUA_WIPE);\n'
        '            icons.add(R.drawable.msg_delete);\n'
        '        }\n'
    )
    edit(pa, [
        # the menu entry, appended after every other branch has run
        (QUICK_BAN_MENU_ANCHOR,
         QUICK_BAN_MENU_ANCHOR.rstrip("}\n") + "\n" + menu_item + "    }\n", 1),
        # the two methods, right after the menu builder
        ("    private boolean showWelcomeMessageRevertOption(MessageObject messageObject) {\n",
         QUICK_BAN_METHODS + "    private boolean showWelcomeMessageRevertOption(MessageObject messageObject) {\n", 1),
        # the action
        (QUICK_BAN_HANDLER_ANCHOR,
         "            case OPTION_CHIHUAHUA_NUKE: {\n"
         "                chihuahuaWipeEverywhere(selectedObject, CHIHUAHUA_WIPE_BAN);\n"
         "                break;\n"
         "            }\n"
         "            case OPTION_CHIHUAHUA_MUTE: {\n"
         "                chihuahuaWipeEverywhere(selectedObject, CHIHUAHUA_WIPE_MUTE);\n"
         "                break;\n"
         "            }\n"
         "            case OPTION_CHIHUAHUA_WIPE: {\n"
         "                chihuahuaWipeEverywhere(selectedObject, CHIHUAHUA_WIPE_ONLY);\n"
         "                break;\n"
         "            }\n" + QUICK_BAN_HANDLER_ANCHOR, 1),
    ])


def patch_group_age_badge():
    """Groups show the estimated account age next to the sender's name, in the slot Telegram
    already uses for the "admin" label. Accounts under the threshold (Settings -> Chihuahua)
    are drawn in red, so a throwaway account posting in your group stands out without opening
    its profile."""
    anchor = ("            if (adminString != null) {\n"
              "                StaticLayout staticLayout = new StaticLayout(adminString, Theme.chat_adminPaint, dp(300), Layout.Alignment.ALIGN_NORMAL, 0f, 0f, false);\n")
    edit("TMessagesProj/src/main/java/org/telegram/ui/Cells/ChatMessageCell.java", [
        (anchor, GROUP_BADGE + anchor, 1),
    ])


def patch_id_row():
    """The user ID gets its own row in the profile (same cell style as the phone number), so the
    status line above keeps room for the last-seen text and the estimated creation date. Tapping
    the row copies the ID."""
    pa = "TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java"
    edit(pa, [
        # field + reset, next to the phone row it sits under
        ("    private int phoneRow;\n", "    private int phoneRow;\n    private int chihuahuaIdRow;\n", 1),
        ("        phoneRow = -1;\n", "        phoneRow = -1;\n        chihuahuaIdRow = -1;\n", 1),
        # the row itself, right after the phone row of a user profile
        ("                if (!isBot && (hasPhone || !hasInfo)) {\n                    phoneRow = rowCount++;\n                }\n",
         "                if (!isBot && (hasPhone || !hasInfo)) {\n                    phoneRow = rowCount++;\n                }\n"
         "                if (userId != 0 && org.telegram.messenger.ChihuahuaConfig.showIdInProfile()) {\n"
         "                    chihuahuaIdRow = rowCount++;\n                }\n", 1),
        # same cell type as the phone row
        ("            } else if (position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow) {\n                return VIEW_TYPE_TEXT_DETAIL;\n",
         "            } else if (position == phoneRow || position == locationRow || position == numberRow || position == birthdayRow || position == chihuahuaIdRow) {\n                return VIEW_TYPE_TEXT_DETAIL;\n", 1),
        # contents
        ("                    } else if (position == phoneRow) {\n                        String text;\n",
         ID_ROW_BIND + "                    } else if (position == phoneRow) {\n                        String text;\n", 1),
        # tap copies the ID; for a user it also names the estimated creation month
        ("            listView.stopScroll();\n            if (position == affiliateRow) {\n",
         "            listView.stopScroll();\n"
         "            if (position == chihuahuaIdRow) {\n"
         "                final String chihuahuaId = userId != 0\n"
         "                        ? String.valueOf(userId)\n"
         "                        : (ChatObject.isChannel(currentChat) ? \"-100\" : \"-\") + chatId;\n"
         "                AndroidUtilities.addToClipboard(chihuahuaId);\n"
         "                if (BulletinFactory.canShowBulletin(ProfileActivity.this)) {\n"
         "                    String chihuahuaCreated = userId != 0 ? org.telegram.messenger.ChihuahuaConfig.estimatedCreation(userId) : \"\";\n"
         "                    BulletinFactory.of(ProfileActivity.this).createCopyBulletin(\"ID \" + chihuahuaId + \" copied\" + (chihuahuaCreated.isEmpty() ? \"\" : \" \\u00b7 account created about \" + chihuahuaCreated)).show();\n"
         "                }\n"
         "            } else if (position == affiliateRow) {\n", 1),
        # --- the same row in group and channel profiles, after the invite link ---
        # the info card must exist even for a private group with no description
        ("            if (chatInfo != null && (!TextUtils.isEmpty(chatInfo.about) || chatInfo.location instanceof TLRPC.TL_channelLocation) || ChatObject.isPublic(currentChat)) {\n",
         "            if (org.telegram.messenger.ChihuahuaConfig.showIdInProfile() || chatInfo != null && (!TextUtils.isEmpty(chatInfo.about) || chatInfo.location instanceof TLRPC.TL_channelLocation) || ChatObject.isPublic(currentChat)) {\n", 1),
        ("                if (ChatObject.isPublic(currentChat)) {\n                    usernameRow = rowCount++;\n                }\n            }\n",
         "                if (ChatObject.isPublic(currentChat)) {\n                    usernameRow = rowCount++;\n                }\n"
         "                if (org.telegram.messenger.ChihuahuaConfig.showIdInProfile()) {\n"
         "                    chihuahuaIdRow = rowCount++;\n"
         "                }\n"
         "            }\n", 1),
        # the invite-link cell now has a row under it in group profiles, so give it a divider there
        ("detailCell.setTextAndValue(text, alsoUsernamesString(username, usernames, value), infoEndRowEmpty == -1 && (isTopic || bizHoursRow != -1 || bizLocationRow != -1) && birthdayRow < 0);",
         "detailCell.setTextAndValue(text, alsoUsernamesString(username, usernames, value), infoEndRowEmpty == -1 && (isTopic || bizHoursRow != -1 || bizLocationRow != -1) && birthdayRow < 0 || chatId != 0 && chihuahuaIdRow != -1);", 1),
        # the phone row now has a row under it, so give it a divider
        ("detailCell.setTextAndValue(text, LocaleController.getString(isFragmentPhoneNumber ? R.string.AnonymousNumber : R.string.PhoneMobile), false);",
         "detailCell.setTextAndValue(text, LocaleController.getString(isFragmentPhoneNumber ? R.string.AnonymousNumber : R.string.PhoneMobile), chihuahuaIdRow != -1);", 1),
        # keep list animations happy
        ("            put(++pointer, phoneRow, sparseIntArray);\n",
         "            put(++pointer, phoneRow, sparseIntArray);\n            put(++pointer, chihuahuaIdRow, sparseIntArray);\n", 1),
    ])


def patch_settings_and_toggles():
    """Settings → Chihuahua screen (new classes copied from patches/) plus the switches it controls:
    hide the Stories bar, hide Premium promotions, show IDs in profiles."""
    src = ROOT / "TMessagesProj/src/main/java/org/telegram"
    import hashlib
    activation_hash = hashlib.sha256(("chihuahua:" + ACTIVATION_CODE).encode("utf-8")).hexdigest() if ACTIVATION_CODE else ""
    for name, sub in (("ChihuahuaConfig.java", "messenger"), ("ChihuahuaSettingsActivity.java", "ui"),
                      ("ChihuahuaSetupActivity.java", "ui")):
        p = HERE / "patches" / name
        if not p.exists():
            fail(f"missing {p}")
            continue
        text = (p.read_text(encoding="utf-8")
                .replace("%%ACTIVATION_HASH%%", activation_hash)
                .replace("%%PROMO_GROUP%%", java_escape(PROMO_GROUP))
                .replace("%%PROMO_TITLE%%", java_escape(PROMO_TITLE)))
        (src / sub / name).write_text(text, encoding="utf-8")
    print("  ok  Chihuahua settings classes copied" + (" (activation lock ON)" if activation_hash else " (no activation code set)"))
    # Activation gate: LaunchActivity asks for the code once per device when a code is compiled in.
    on_resume = "    @Override\n    protected void onResume() {\n        super.onResume();\n"
    on_create = "    @Override\n    protected void onCreate(Bundle savedInstanceState) {\n"
    edit("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java", [
        (on_resume, on_resume + "        chihuahuaCheckActivation();\n"
                   "        org.telegram.messenger.ChihuahuaConfig.applyKeepConnected();\n"
                   "        org.telegram.messenger.ChihuahuaConfig.retryTtlDefaults();\n", 1),
        (on_create, ACTIVATION_GATE + on_create, 1),
    ])
    lang_item = ("        items.add(SettingCell.Factory.of(10, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, "
                 "R.drawable.settings_language, getString(R.string.SettingsLanguage), LocaleController.getCurrentLanguageName()));\n")
    lang_case = "            case 10:\n                presentSettingFragment(new LanguageSelectActivity());\n                break;\n"
    edit("TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java", [
        (lang_item, lang_item +
         "        items.add(SettingCell.Factory.of(70, IconBackgroundColors.ORANGE_DEEP.top, IconBackgroundColors.ORANGE_DEEP.bottom, "
         "R.drawable.settings_features, \"Chihuahua\", \"IDs in profiles, Stories bar, Premium promos\"));\n", 1),
        (lang_case, lang_case +
         "            case 70:\n                presentSettingFragment(new ChihuahuaSettingsActivity());\n                break;\n", 1),
    ])
    edit("TMessagesProj/src/main/java/org/telegram/messenger/MessagesController.java", [
        ("    public boolean premiumFeaturesBlocked() {\n        return premiumLocked && !getUserConfig().isPremium();\n    }\n"
         "    public boolean premiumPurchaseBlocked() {\n        return premiumLocked;\n    }\n",
         "    public boolean premiumFeaturesBlocked() {\n        return ChihuahuaConfig.hidePremium() || premiumLocked && !getUserConfig().isPremium();\n    }\n"
         "    public boolean premiumPurchaseBlocked() {\n        return ChihuahuaConfig.hidePremium() || premiumLocked;\n    }\n", 1),
    ])
    header = ("    private void sendRequestInternal(TLObject object, RequestDelegate onComplete, RequestDelegateTimestamp onCompleteTimestamp, "
              "QuickAckDelegate onQuickAck, WriteToSocketDelegate onWriteToSocket, int flags, int datacenterId, int connectionType, boolean immediate, int requestToken) {\n")
    edit("TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java", [
        (header, header +
         "        if (org.telegram.messenger.ChihuahuaConfig.shouldDropRequest(object)) {\n"
         "            // Ghost mode: swallow read receipts / typing / online-status requests.\n"
         "            if (BuildVars.LOGS_ENABLED) {\n"
         "                FileLog.d(\"ghost mode: dropped \" + object);\n"
         "            }\n"
         "            final TLRPC.TL_error ghostError = new TLRPC.TL_error();\n"
         "            ghostError.code = 400;\n"
         "            ghostError.text = \"GHOST_MODE\";\n"
         "            if (onComplete != null) {\n"
         "                onComplete.run(null, ghostError);\n"
         "            } else if (onCompleteTimestamp != null) {\n"
         "                onCompleteTimestamp.run(null, ghostError, System.currentTimeMillis());\n"
         "            }\n"
         "            return;\n"
         "        }\n", 1),
    ])
    edit("TMessagesProj/src/main/java/org/telegram/messenger/voip/VoIPService.java", [
        ("\tprivate boolean isFrontFaceCamera = true;\n",
         "\tprivate boolean isFrontFaceCamera = !org.telegram.messenger.ChihuahuaConfig.backCameraDefault();\n", 1),
    ])
    edit("TMessagesProj/src/main/java/org/telegram/ui/DialogsActivity.java", [
        ("            newVisibility = !getStoriesController().getHiddenList().isEmpty();\n",
         "            newVisibility = !org.telegram.messenger.ChihuahuaConfig.hideStories() && !getStoriesController().getHiddenList().isEmpty();\n", 1),
        ("            newVisibility = !onlySelfStories && getStoriesController().hasStories();\n",
         "            newVisibility = !org.telegram.messenger.ChihuahuaConfig.hideStories() && !onlySelfStories && getStoriesController().hasStories();\n", 1),
    ])



def patch_add_to_group():
    f = "TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java"
    menu_anchor = ("                if (!UserObject.isDeleted(user) && !isBot && currentEncryptedChat == null && !userBlocked"
                   " && userId != 333000 && userId != 777000 && userId != 42777) {\n")
    edit(f, [
        ("    private final static int invite_to_group = 9;\n",
         "    private final static int invite_to_group = 9;\n"
         "    private final static int chihuahua_add_to_group = 90;\n"
         "    private final static int chihuahua_copy_id = 91;\n"
         "    private final static int chihuahua_ban_everywhere = 92;\n"
         "    private final static int chihuahua_admins = 93;\n", 1),
        (menu_anchor,
         menu_anchor +
         "                    otherItem.addSubItem(chihuahua_add_to_group, R.drawable.msg_addbot, LocaleController.getString(R.string.AddToGroup));\n", 1),
        ("                } else if (id == invite_to_group) {\n",
         ADD_TO_GROUP_HANDLER + COPY_ID_HANDLER + BAN_EVERYWHERE_HANDLER + ADMINS_HANDLER + "                } else if (id == invite_to_group) {\n", 1),
        # "Copy ID" + "Ban from all my groups" in a person's profile menu (placed before the contact's Add-to-Home-screen entry)
        (CONTACT_SHORTCUT_ANCHOR,
         "                otherItem.addSubItem(chihuahua_copy_id, R.drawable.msg_copy, \"Copy ID\");\n"
         "                if (!isBot && !UserObject.isDeleted(user) && !UserObject.isUserSelf(user)) {\n"
         "                    otherItem.addSubItem(chihuahua_ban_everywhere, R.drawable.msg_block2, \"Ban from all my groups\").setColors(getThemedColor(Theme.key_text_RedRegular), getThemedColor(Theme.key_text_RedRegular));\n"
         "                }\n" + CONTACT_SHORTCUT_ANCHOR, 1),
        # "Admins" in a group/channel profile menu. (Copy ID used to live here too; the group's
        # ID is now a tap-to-copy row in the profile itself, like a user's.)
        (CHAT_MENU_ANCHOR,
         CHAT_MENU_ANCHOR
         + "            if (chat != null && ChatObject.isChannel(chat)) {\n"
         "                otherItem.addSubItem(chihuahua_admins, R.drawable.msg_admins, \"Admins\");\n"
         "            }\n", 1),
        # estimated creation month next to the online status under the name (toggle in Settings → Chihuahua)
        (STATUS_ANCHOR,
         STATUS_ANCHOR +
         "                if (org.telegram.messenger.ChihuahuaConfig.showIdInProfile()) {\n"
         "                    newString2 = newString2 + org.telegram.messenger.ChihuahuaConfig.accountAgeSuffix(user.id);\n"
         "                }\n", 1),
        # ...and on your own profile, whose status ("online") is built on a separate branch
        ("                    } else {\n"
         "                        newString2 = LocaleController.getString(R.string.Online);\n"
         "                    }\n"
         "                }\n",
         "                    } else {\n"
         "                        newString2 = LocaleController.getString(R.string.Online);\n"
         "                    }\n"
         "                    if (org.telegram.messenger.ChihuahuaConfig.showIdInProfile()) {\n"
         "                        newString2 = newString2 + org.telegram.messenger.ChihuahuaConfig.accountAgeSuffix(user.id);\n"
         "                    }\n"
         "                }\n", 1),
    ])



def patch_theme98():
    """Windows 98 colour theme: bundled as an asset theme, listed in Settings → Chat Settings,
    and applied once on first start of a build that has it. Also the chat-list title."""
    src = HERE / "patches" / "chihuahua98.attheme"
    if not src.exists():
        fail(f"missing {src}")
        return
    shutil.copy(src, ROOT / "TMessagesProj/src/main/assets/chihuahua98.attheme")
    night_reg = '        sortAccents(themeInfo);\n        themes.add(themeInfo);\n        themesDict.put("Night", themeInfo);\n'
    night_pref = '            theme = preferences.getString("nighttheme", null);\n'
    edit("TMessagesProj/src/main/java/org/telegram/ui/ActionBar/Theme.java", [
        (night_reg, night_reg +
         '\n        themeInfo = new ThemeInfo();\n'
         '        themeInfo.name = "Chihuahua 98";\n'
         '        themeInfo.assetName = "chihuahua98.attheme";\n'
         '        themeInfo.previewBackgroundColor = 0xff008080;\n'
         '        themeInfo.previewInColor = 0xffffffff;\n'
         '        themeInfo.previewOutColor = 0xffc0c0c0;\n'
         '        themeInfo.sortIndex = 5;\n'
         '        themes.add(themeInfo);\n'
         '        themesDict.put("Chihuahua 98", themeInfo);\n', 1),
        # ThemeInfo.isDark() only knows the five built-in names; anything else is treated as a
        # file theme and dereferences pathToFile (null for an asset theme) -> NPE at startup.
        ('            } else if ("Blue".equals(name) || "Arctic Blue".equals(name) || "Day".equals(name)) {\n',
         '            } else if ("Blue".equals(name) || "Arctic Blue".equals(name) || "Day".equals(name) || "Chihuahua 98".equals(name)) {\n', 1),
        (night_pref,
         '            if (!themeConfig.getBoolean("chihuahua98_applied", false)) {\n'
         '                ThemeInfo chihuahuaTheme = themesDict.get("Chihuahua 98");\n'
         '                if (chihuahuaTheme != null) {\n'
         '                    applyingTheme = chihuahuaTheme;\n'
         '                    themeConfig.edit().putBoolean("chihuahua98_applied", true).commit();\n'
         '                    preferences.edit().putString("theme", chihuahuaTheme.getKey()).putInt("selectedAutoNightType", AUTO_NIGHT_TYPE_NONE).commit();\n'
         '                }\n'
         '            }\n' + night_pref, 1),
    ])
    # Chat-list title: the official app draws the Telegram wordmark image here; show "Chihuahua" as text instead.
    edit("TMessagesProj/src/main/java/org/telegram/ui/DialogsActivity.java", [
        ('                SpannableStringBuilder ssb = new SpannableStringBuilder(getString(R.string.AppName));\n'
         '                ssb.setSpan(new ImageSpan(logoDrawable), 0, ssb.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);\n',
         '                SpannableStringBuilder ssb = new SpannableStringBuilder("' + java_escape(CHAT_LIST_TITLE) + '");\n', 1),
    ])
    patch_glass_header()
    patch_dialogs_header_icons()
    patch_action_mode_icons()
    patch_profile_header()
    patch_per_account_notifications()
    patch_id_row()
    patch_profile_action_buttons()
    patch_adaptive_header_text()
    patch_hint_contrast()
    patch_phone_copy()
    patch_admin_bio()
    patch_add_account_button()
    patch_sync_contacts_off()
    patch_enter_proceeds()
    patch_no_phonebook_invites()
    patch_profile_qr_icon()
    patch_contacts_select_all()
    patch_stay_on_settings()
    patch_setup_tab()
    patch_account_ttl_defaults()
    patch_account_phone_line()
    patch_account_order()
    patch_group_age_badge()
    patch_quick_ban()
    patch_foreground_connection()


def patch_per_account_notifications():
    """Telegram has one global "show notifications from all accounts" switch. With many accounts
    logged in you want most of them silent, so each account gets its own switch (Settings ->
    Chihuahua -> Notifications). A silenced account posts no notification (the existing one is
    dismissed, exactly as Telegram already does for non-selected accounts), plays no in-app sound,
    and does not count towards the launcher badge."""
    nc = "TMessagesProj/src/main/java/org/telegram/messenger/NotificationsController.java"
    edit(nc, [
        # the one funnel every posted notification goes through
        ("        if (!getUserConfig().isClientActivated() || pushMessages.isEmpty() && storyPushMessages.isEmpty() || !SharedConfig.showNotificationsForAllAccounts && currentAccount != UserConfig.selectedAccount) {\n",
         "        if (!getUserConfig().isClientActivated() || !ChihuahuaConfig.notificationsEnabled(currentAccount) || pushMessages.isEmpty() && storyPushMessages.isEmpty() || !SharedConfig.showNotificationsForAllAccounts && currentAccount != UserConfig.selectedAccount) {\n", 1),
        # launcher badge total
        ("            if (!SharedConfig.showNotificationsForAllAccounts && UserConfig.selectedAccount != a) {\n                continue;\n            }\n",
         "            if (!SharedConfig.showNotificationsForAllAccounts && UserConfig.selectedAccount != a) {\n                continue;\n            }\n"
         "            if (!ChihuahuaConfig.notificationsEnabled(a)) {\n                continue;\n            }\n", 1),
        # sound played while the chat is open
        ("    private void playInChatSound() {\n        if (!inChatSoundEnabled || MediaController.getInstance().isRecordingAudio()) {\n",
         "    private void playInChatSound() {\n        if (!inChatSoundEnabled || !ChihuahuaConfig.notificationsEnabled(currentAccount) || MediaController.getInstance().isRecordingAudio()) {\n", 1),
    ])


def patch_profile_header():
    """Telegram 12.x paints the profile header (avatar, name, status) on windowBackgroundGray but
    colours the name/status/icons with the action-bar keys (profile_title, actionBarDefaultSubtitle,
    actionBarDefaultIcon). With a navy action bar those are white/light grey — invisible on the grey
    header: the "last seen · ID" line disappeared. Paint the header with avatar_backgroundActionBarBlue
    (navy here; white/dark in Telegram's own themes, so those look the same as before) and let the
    Message/Mute/Call/Video tiles take profile_actionBackground on dark action bars."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java", [
        ("topView.setBackgroundColor(getThemedColor(Theme.key_windowBackgroundGray));",
         "topView.setBackgroundColor(getThemedColor(Theme.key_avatar_backgroundActionBarBlue));", 2),
        ("new ThemeDescription(topView, ThemeDescription.FLAG_BACKGROUND, null, null, null, null, Theme.key_windowBackgroundGray)",
         "new ThemeDescription(topView, ThemeDescription.FLAG_BACKGROUND, null, null, null, null, Theme.key_avatar_backgroundActionBarBlue)", 1),
        ("                    btnColor = Theme.multAlpha(Theme.adaptHSV(getThemedColor(Theme.key_actionBarDefault), +0.02f, +0.25f), .35f);\n",
         "                    btnColor = getThemedColor(Theme.key_profile_actionBackground);\n", 1),
    ])
    # The open-from-chat animation ends on getProfileBackColorForId(), which would paint the header
    # grey again once the animation finishes (only used by ProfileActivity).
    edit("TMessagesProj/src/main/java/org/telegram/ui/Components/AvatarDrawable.java", [
        ("    public static int getProfileBackColorForId(long id, Theme.ResourcesProvider resourcesProvider) {\n"
         "        return Theme.getColor(Theme.key_windowBackgroundGray, resourcesProvider);\n",
         "    public static int getProfileBackColorForId(long id, Theme.ResourcesProvider resourcesProvider) {\n"
         "        return Theme.getColor(Theme.key_avatar_backgroundActionBarBlue, resourcesProvider);\n", 1),
    ])


GLASS_HEADER_PROVIDER = '''    // Chihuahua: the chat header pills (title, back, menu) take the action bar colour, so a theme
    // with a coloured action bar and light title/icons stays readable. Telegram's own themes use
    // the same colour for actionBarDefault and chat_topPanelBackground, so they look unchanged.
    private static boolean headerIsDark(Theme.ResourcesProvider r) {
        return org.telegram.messenger.AndroidUtilities.computePerceivedBrightness(Theme.getColor(Theme.key_actionBarDefault, r)) < .721f;
    }

    public static BlurredBackgroundProvider topPanelChatActivityHeader(Theme.ResourcesProvider resourcesProvider) {
        return new BlurredBackgroundProviderBuilder(resourcesProvider)
                .setBackgroundColor((r, isDark) -> {
                    final int colorBg = Theme.getColor(Theme.key_actionBarDefault, r);
                    if (!checkBlurEnabled(resourcesProvider)) {
                        return ColorUtils.setAlphaComponent(colorBg, 255);
                    }
                    final float alpha = LiteMode.isEnabled(LiteMode.FLAG_LIQUID_GLASS) ? 0.85f : 0.76f;
                    return Theme.multAlpha(colorBg, alpha);
                })
                .setStrokeColorTop((r, isDark) -> headerIsDark(r) ? 0x20FFFFFF : 0xFFFFFFFF)
                .setStrokeColorBottom((r, isDark) -> headerIsDark(r) ? 0x14FFFFFF : 0xFFFFFFFF)
                .setShadowColor((r, isDark) -> headerIsDark(r) ? 0 : 0x20000000)
                .setStrokeWidth(dpf2(0.55f), dpf2(0.55f))
                .build();
    }

'''


def patch_dialogs_header_icons():
    """Dark search / menu icons on the chat list's header.

    With the 12.x bottom tabs (hasMainTabs) the chat list's header is a light glass panel and
    Telegram colours its TITLE with key_telegram_color_dialogsLogo (which falls back to
    windowBackgroundWhiteBlackText — black here). The search and menu icons, though, still take
    key_actionBarDefaultIcon, which this theme makes white for the navy chat-screen header. So:
    black title, invisible white icons. Make the icons follow exactly the rule the title follows,
    at every place the colour is set, and give the search field dark text while we are here."""
    da = "TMessagesProj/src/main/java/org/telegram/ui/DialogsActivity.java"
    icon_key = "hasMainTabs ? Theme.key_telegram_color_dialogsLogo : Theme.key_actionBarDefaultIcon"
    edit(da, [
        # initial colour
        ("        actionBar.setItemsColor(getThemedColor(Theme.key_actionBarDefaultIcon), false);\n",
         "        actionBar.setItemsColor(getThemedColor(" + icon_key + "), false);\n", 1),
        # re-applied during the search open/close animation
        ("            int color1 = (folderId != 0 || communityId != 0) ? getThemedColor(Theme.key_actionBarDefaultArchivedIcon) : getThemedColor(Theme.key_actionBarDefaultIcon);\n",
         "            int color1 = (folderId != 0 || communityId != 0) ? getThemedColor(Theme.key_actionBarDefaultArchivedIcon) : getThemedColor(" + icon_key + ");\n", 1),
        # re-applied on theme changes
        ("            arrayList.add(new ThemeDescription(actionBar, ThemeDescription.FLAG_AB_ITEMSCOLOR, null, null, null, cellDelegate, Theme.key_actionBarDefaultIcon));\n",
         "            arrayList.add(new ThemeDescription(actionBar, ThemeDescription.FLAG_AB_ITEMSCOLOR, null, null, null, cellDelegate, " + icon_key + "));\n", 1),
        # typed search text and its placeholder, on the same light header
        ("            actionBar.setTitleColor(getThemedColor(Theme.key_telegram_color_dialogsLogo));\n        }\n",
         "            actionBar.setTitleColor(getThemedColor(Theme.key_telegram_color_dialogsLogo));\n"
         "            actionBar.setSearchTextColor(getThemedColor(Theme.key_windowBackgroundWhiteBlackText), false);\n"
         "            actionBar.setSearchTextColor(getThemedColor(Theme.key_windowBackgroundWhiteGrayText), true);\n"
         "        }\n", 1),
    ])


def patch_profile_action_buttons():
    """Admin tools on the profile button row, in place of the calls-and-stories buttons.

    Groups:   Message · Mute · Admins · Recent Actions      (was: Message · Mute · Video Chat · Add Story · Leave)
    Channels: Mute · Invite Links · Recent Actions          (was: Live Stream · Mute · Add Story)
    Discuss / Gift / Share / Join / Report keep Telegram's own rules. Leave is still in the ⋮ menu.
    The three new buttons follow the same machinery as Telegram's (key -> enum -> availability ->
    per-mode list -> click), and are only offered when the account has the matching rights."""
    pav = "TMessagesProj/src/main/java/org/telegram/ui/Components/ProfileActionsView.java"
    pa = "TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java"
    # Anchor on the root tag: patch_app_name() has already rewritten the AppName line by now.
    edit("TMessagesProj/src/main/res/values/strings.xml", [
        ('<resources>\n',
         '<resources>\n'
         '    <string name="ChihuahuaAdmins">Admins</string>\n'
         '    <string name="ChihuahuaRecentActions">Recent Actions</string>\n'
         '    <string name="ChihuahuaInviteLinks">Invite Links</string>\n', 1),
    ])
    edit(pav, [
        # keys
        ("    public static final int KEY_SETTINGS = 17;\n",
         "    public static final int KEY_SETTINGS = 17;\n"
         "    public static final int KEY_ADMINS = 18;\n"
         "    public static final int KEY_RECENT_ACTIONS = 19;\n"
         "    public static final int KEY_INVITE_LINKS = 20;\n", 1),
        # icon + label
        ("        SETTINGS(R.string.Settings, R.drawable.filled_profile_settings, R.drawable.outline_profile_settings),;\n",
         "        SETTINGS(R.string.Settings, R.drawable.filled_profile_settings, R.drawable.outline_profile_settings),\n"
         "        ADMINS(R.string.ChihuahuaAdmins, R.drawable.msg_admins, R.drawable.msg_admins),\n"
         "        RECENT_ACTIONS(R.string.ChihuahuaRecentActions, R.drawable.msg_log, R.drawable.msg_log),\n"
         "        INVITE_LINKS(R.string.ChihuahuaInviteLinks, R.drawable.msg_link2, R.drawable.msg_link2),;\n", 1),
        # construction
        ("            case KEY_NOTIFICATION:\n                newAction = new Action();\n",
         "            case KEY_ADMINS:\n                newAction = new Action(ActionButton.ADMINS);\n                break;\n"
         "            case KEY_RECENT_ACTIONS:\n                newAction = new Action(ActionButton.RECENT_ACTIONS);\n                break;\n"
         "            case KEY_INVITE_LINKS:\n                newAction = new Action(ActionButton.INVITE_LINKS);\n                break;\n"
         "            case KEY_NOTIFICATION:\n                newAction = new Action();\n", 1),
        # channel row: drop Live Stream...
        ("                } else {\n                    insertIfAvailable(out, KEY_VOICE_CHAT);\n                    insertIfNotAvailable(out, KEY_STREAM, KEY_VOICE_CHAT);\n                }\n                insertIfAvailable(out, KEY_NOTIFICATION);\n",
         "                }\n                insertIfAvailable(out, KEY_NOTIFICATION);\n", 1),
        # ...and Add Story, in favour of Invite Links + Recent Actions
        ("                } else {\n                    insertIfAvailable(out, KEY_STORY);\n                    insertIfNotAvailable(out, KEY_LEAVE, KEY_STORY);\n                }\n                break;\n",
         "                } else {\n"
         "                    // Chihuahua: admin tools instead of Add Story.\n"
         "                    insertIfAvailable(out, KEY_INVITE_LINKS);\n"
         "                    insertIfAvailable(out, KEY_RECENT_ACTIONS);\n"
         "                    insertIfNotAvailable(out, KEY_LEAVE, KEY_STORY);\n"
         "                }\n                break;\n", 1),
        # group row: Admins + Recent Actions instead of Video Chat / Add Story / Leave
        ("                } else {\n                    insertIfAvailable(out, KEY_VOICE_CHAT);\n                    insertIfNotAvailable(out, KEY_STREAM, KEY_VOICE_CHAT);\n                    insertIfAvailable(out, KEY_STORY);\n                    insertIfAvailable(out, KEY_LEAVE);\n                }\n                break;\n",
         "                } else {\n"
         "                    // Chihuahua: admin tools instead of Video Chat / Add Story / Leave (Leave stays in the menu).\n"
         "                    insertIfAvailable(out, KEY_ADMINS);\n"
         "                    insertIfAvailable(out, KEY_RECENT_ACTIONS);\n"
         "                }\n                break;\n", 1),
    ])
    edit(pa, [
        # availability, by rights
        ("            actionsView.set(ProfileActionsView.KEY_STREAM, streamAction);\n",
         "            actionsView.set(ProfileActionsView.KEY_STREAM, streamAction);\n"
         "            actionsView.set(ProfileActionsView.KEY_ADMINS, currentChat != null && ChatObject.isChannel(currentChat) && !ChatObject.isLeftFromChat(currentChat) && !ChatObject.isKickedFromChat(currentChat));\n"
         "            actionsView.set(ProfileActionsView.KEY_RECENT_ACTIONS, currentChat != null && ChatObject.isChannel(currentChat) && ChatObject.hasAdminRights(currentChat));\n"
         "            actionsView.set(ProfileActionsView.KEY_INVITE_LINKS, currentChat != null && ChatObject.isChannel(currentChat) && ChatObject.canUserDoAdminAction(currentChat, ChatObject.ACTION_INVITE));\n", 1),
        # clicks: the same screens Telegram opens from Manage Group
        ("                    case ProfileActionsView.KEY_LEAVE:\n                        leaveChatPressed(false);\n                        break;\n",
         "                    case ProfileActionsView.KEY_ADMINS: {\n"
         "                        Bundle chihuahuaArgs = new Bundle();\n"
         "                        chihuahuaArgs.putLong(\"chat_id\", chatId);\n"
         "                        chihuahuaArgs.putInt(\"type\", ChatUsersActivity.TYPE_ADMIN);\n"
         "                        ChatUsersActivity chihuahuaAdmins = new ChatUsersActivity(chihuahuaArgs);\n"
         "                        chihuahuaAdmins.setInfo(chatInfo);\n"
         "                        presentFragment(chihuahuaAdmins);\n"
         "                        break;\n"
         "                    }\n"
         "                    case ProfileActionsView.KEY_RECENT_ACTIONS:\n"
         "                        if (currentChat != null) {\n"
         "                            presentFragment(new ChannelAdminLogActivity(currentChat));\n"
         "                        }\n"
         "                        break;\n"
         "                    case ProfileActionsView.KEY_INVITE_LINKS: {\n"
         "                        ManageLinksActivity chihuahuaLinks = new ManageLinksActivity(chatId, 0, 0);\n"
         "                        if (chatInfo != null) {\n"
         "                            chihuahuaLinks.setInfo(chatInfo, chatInfo.exported_invite);\n"
         "                        }\n"
         "                        presentFragment(chihuahuaLinks);\n"
         "                        break;\n"
         "                    }\n"
         "                    case ProfileActionsView.KEY_LEAVE:\n                        leaveChatPressed(false);\n                        break;\n", 1),
    ])


def patch_adaptive_header_text():
    """Title and icons that switch with the "adaptive" action bar.

    Telegram 12.x colours the header of ~60 list screens (admins, members, settings pages...) with
    the BODY colour while the list is at the top, blending to actionBarDefault as you scroll. The
    title and icons stay actionBarDefaultTitle/Icon throughout. Fine for Telegram's themes; with a
    navy bar, white text and a light body it means a white title on the grey body until you scroll.
    Blend the text too: dark while the bar shows a light colour, the theme's own colour once it
    has scrolled onto the bar colour. Decided by the actual brightness of the top colour, so dark
    themes and Telegram's own light themes are unaffected."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/ActionBar/ActionBar.java", [
        ("        setBackgroundColor(ColorUtils.blendARGB(lowerColor, topColor, factor));\n"
         "        setShadowAlpha((int) ((1.0f - onTopAnimated) * 0xFF));\n",
         "        setBackgroundColor(ColorUtils.blendARGB(lowerColor, topColor, factor));\n"
         "        // Chihuahua: with a navy bar over a light body the text must switch too - dark while\n"
         "        // the bar shows the body colour, the theme's own colours once scrolled onto navy.\n"
         "        if (adaptive_topColorKey != -1) {\n"
         "            final int barTitle = Theme.getColor(Theme.key_actionBarDefaultTitle, resourcesProvider);\n"
         "            final int barIcon = Theme.getColor(Theme.key_actionBarDefaultIcon, resourcesProvider);\n"
         "            final boolean topIsLight = AndroidUtilities.computePerceivedBrightness(topColor) > 0.72f;\n"
         "            final int topInk = topIsLight ? Theme.getColor(Theme.key_windowBackgroundWhiteBlackText, resourcesProvider) : barTitle;\n"
         "            setTitleColor(ColorUtils.blendARGB(barTitle, topInk, factor));\n"
         "            setItemsColor(ColorUtils.blendARGB(barIcon, topIsLight ? topInk : barIcon, factor), false);\n"
         "        }\n"
         "        setShadowAlpha((int) ((1.0f - onTopAnimated) * 0xFF));\n", 1),
    ])


def patch_admin_bio():
    """One line of each admin's bio in the Administrators list, where Telegram shows
    "Promoted by X". Full user info is fetched lazily per admin and the list refreshes as it
    arrives; admins without a bio keep the promoted-by text."""
    cu = "TMessagesProj/src/main/java/org/telegram/ui/ChatUsersActivity.java"
    edit(cu, [
        ("        getNotificationCenter().addObserver(this, NotificationCenter.dialogDeleted);\n",
         "        getNotificationCenter().addObserver(this, NotificationCenter.dialogDeleted);\n"
         "        getNotificationCenter().addObserver(this, NotificationCenter.userInfoDidLoad);\n", 1),
        ("        getNotificationCenter().removeObserver(this, NotificationCenter.dialogDeleted);\n",
         "        getNotificationCenter().removeObserver(this, NotificationCenter.dialogDeleted);\n"
         "        getNotificationCenter().removeObserver(this, NotificationCenter.userInfoDidLoad);\n", 1),
        ("    public void didReceivedNotification(int id, int account, Object... args) {\n"
         "        if (id == NotificationCenter.chatInfoDidLoad) {\n",
         "    public void didReceivedNotification(int id, int account, Object... args) {\n"
         "        if (id == NotificationCenter.userInfoDidLoad) {\n"
         "            if (type == TYPE_ADMIN && listViewAdapter != null) {\n"
         "                listViewAdapter.notifyDataSetChanged();\n"
         "            }\n"
         "            return;\n"
         "        }\n"
         "        if (id == NotificationCenter.chatInfoDidLoad) {\n", 1),
        ("                            userCell.setData(object, null, role, position != lastRow - 1);\n"
         "                        } else if (type == TYPE_USERS) {\n",
         "                            // Chihuahua: one line of the admin's bio, when they have one.\n"
         "                            if (object instanceof TLRPC.User) {\n"
         "                                final TLRPC.User chihuahuaAdmin = (TLRPC.User) object;\n"
         "                                final TLRPC.UserFull chihuahuaFull = getMessagesController().getUserFull(chihuahuaAdmin.id);\n"
         "                                if (chihuahuaFull == null) {\n"
         "                                    getMessagesController().loadFullUser(chihuahuaAdmin, classGuid, false);\n"
         "                                } else if (!TextUtils.isEmpty(chihuahuaFull.about)) {\n"
         "                                    role = chihuahuaFull.about.replace('\\n', ' ').trim();\n"
         "                                }\n"
         "                            }\n"
         "                            userCell.setData(object, null, role, position != lastRow - 1);\n"
         "                        } else if (type == TYPE_USERS) {\n", 1),
    ])


def patch_add_account_button():
    """"Add Account" at the bottom of the Accounts card on the Settings tab, right above Account.
    Same flow as Telegram's own menu item (free slot -> login screen; none -> the limit sheet).
    Shown even when no other account is logged in yet."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java", [
        ("        if (accountNumbers.size() > 0) {\n"
         "            items.add(UItem.asHeader(getString(R.string.SettingsAccounts)));\n"
         "            for (int i = 0; i < accountNumbers.size(); ++i) {\n"
         "                items.add(AccountCell.Factory.of(i, accountNumbers.get(i)));\n"
         "            }\n"
         "            items.add(UItem.asShadow(null));\n"
         "        }\n",
         "        if (accountNumbers.size() > 0) {\n"
         "            items.add(UItem.asHeader(getString(R.string.SettingsAccounts)));\n"
         "            for (int i = 0; i < accountNumbers.size(); ++i) {\n"
         "                items.add(AccountCell.Factory.of(i, accountNumbers.get(i)));\n"
         "            }\n"
         "        }\n"
         "        // Chihuahua: Add Account right here, above Account.\n"
         "        items.add(UItem.asButton(990, R.drawable.msg_addbot, getString(R.string.AddAccount)).accent());\n"
         "        items.add(UItem.asShadow(null));\n", 1),
        ("        switch (item.id) {\n            case 1:\n                presentSettingFragment(new UserInfoActivity());\n                break;\n",
         "        switch (item.id) {\n"
         "            case 990: {\n"
         "                // Chihuahua: same flow as Telegram's own Add Account menu item.\n"
         "                int chihuahuaFree = 0;\n"
         "                Integer chihuahuaSlot = null;\n"
         "                for (int a = UserConfig.MAX_ACCOUNT_COUNT - 1; a >= 0; a--) {\n"
         "                    if (!UserConfig.getInstance(a).isClientActivated()) {\n"
         "                        chihuahuaFree++;\n"
         "                        if (chihuahuaSlot == null) {\n"
         "                            chihuahuaSlot = a;\n"
         "                        }\n"
         "                    }\n"
         "                }\n"
         "                if (!UserConfig.hasPremiumOnAccounts()) {\n"
         "                    chihuahuaFree -= (UserConfig.MAX_ACCOUNT_COUNT - UserConfig.MAX_ACCOUNT_DEFAULT_COUNT);\n"
         "                }\n"
         "                if (chihuahuaFree > 0 && chihuahuaSlot != null) {\n"
         "                    presentFragment(new LoginActivity(chihuahuaSlot));\n"
         "                } else if (!UserConfig.hasPremiumOnAccounts()) {\n"
         "                    showDialog(new org.telegram.ui.Components.Premium.LimitReachedBottomSheet(this, getContext(), org.telegram.ui.Components.Premium.LimitReachedBottomSheet.TYPE_ACCOUNTS, currentAccount, null));\n"
         "                }\n"
         "                break;\n"
         "            }\n"
         "            case 1:\n                presentSettingFragment(new UserInfoActivity());\n                break;\n", 1),
    ])


def patch_sync_contacts_off():
    """"Sync Contacts" starts unchecked on the login screen (both the field's default and the value
    used when the screen is restored without a saved choice). Every add-account path goes through
    LoginActivity, so this covers all of them; the box can still be ticked by hand."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/LoginActivity.java", [
        ("    private boolean syncContacts = true;\n",
         "    private boolean syncContacts = false; // Chihuahua: off unless ticked\n", 1),
        ('            syncContacts = savedInstanceState.getInt("syncContacts", 1) == 1;\n',
         '            syncContacts = savedInstanceState.getInt("syncContacts", 0) == 1;\n', 1),
    ])


def patch_no_phonebook_invites():
    """No "Invite Friends" list on the Contacts tab. Telegram reads the phone's own address book and
    lists everyone in it who is not on Telegram, which on a phone with a business address book is a
    long list of strangers' numbers under the contacts. The adapter now reads an empty phone book,
    so the invite section and its header disappear; the rest of the screen (including Recent calls,
    and Telegram's own invite screen if you go looking for it) is untouched."""
    ca = "TMessagesProj/src/main/java/org/telegram/ui/Adapters/ContactsAdapter.java"
    edit(ca, [
        ("    private final boolean needPhonebook;\n",
         "    private final boolean needPhonebook;\n"
         "    /** Chihuahua: the device address book, hidden — see chihuahuaPhoneBook(). */\n"
         "    private static final ArrayList<ContactsController.Contact> CHIHUAHUA_NO_PHONEBOOK = new ArrayList<>();\n", 1),
        # every read of the phone book goes through the empty list instead
        ("ContactsController.getInstance(currentAccount).phoneBookContacts",
         "CHIHUAHUA_NO_PHONEBOOK", 10),
    ])


def patch_profile_qr_icon():
    """The QR button on a profile's username row is tinted with actionBarDefaultIcon — white in this
    theme, because that colour is meant for the navy title bar — but the button sits on a light card
    in the list, so it was invisible. Tint it like every other icon on a white card instead."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/ProfileActivity.java", [
        ("                        Drawable drawable = ContextCompat.getDrawable(detailCell.getContext(), R.drawable.header_qr_24);\n"
         "                        drawable.setColorFilter(new PorterDuffColorFilter(dontApplyPeerColor(getThemedColor(Theme.key_actionBarDefaultIcon), false), PorterDuff.Mode.MULTIPLY));\n",
         "                        Drawable drawable = ContextCompat.getDrawable(detailCell.getContext(), R.drawable.header_qr_24);\n"
         "                        // Chihuahua: this one is on a white card, not on the action bar.\n"
         "                        drawable.setColorFilter(new PorterDuffColorFilter(dontApplyPeerColor(getThemedColor(Theme.key_windowBackgroundWhiteGrayIcon), false), PorterDuff.Mode.MULTIPLY));\n", 1),
    ])


def patch_contacts_select_all():
    """A "select all" tick in the Contacts tab's selection bar. Telegram lets you tick contacts one
    by one and delete them; with hundreds of contacts that is not a way to empty the list. The tick
    selects every contact of the account (not only the rows on screen) and the existing Delete
    button then does the rest, with Telegram's own confirmation and its undo bulletin."""
    ca = "TMessagesProj/src/main/java/org/telegram/ui/ContactsActivity.java"
    edit(ca, [
        ("    private final static int delete = 100;\n",
         "    private final static int delete = 100;\n"
         "    private final static int chihuahua_select_all = 101; // Chihuahua: tick every contact\n", 1),
        ("        actionMode.addItemWithWidth(delete, R.drawable.msg_delete, dp(54), getString(R.string.Delete));\n",
         "        actionMode.addItemWithWidth(chihuahua_select_all, R.drawable.msg_select, dp(54), \"Select all\");\n"
         "        actionMode.addItemWithWidth(delete, R.drawable.msg_delete, dp(54), getString(R.string.Delete));\n", 1),
        ("                } else if (id == delete) {\n                    performSelectedContactsDelete();\n",
         "                } else if (id == chihuahua_select_all) {\n"
         "                    chihuahuaSelectAllContacts();\n"
         "                } else if (id == delete) {\n                    performSelectedContactsDelete();\n", 1),
        ("    private void hideActionMode() {\n",
         "    /** Chihuahua: put every contact of this account into the selection, then tick what is on screen. */\n"
         "    private void chihuahuaSelectAllContacts() {\n"
         "        final ArrayList<TLRPC.TL_contact> all = getContactsController().contacts;\n"
         "        for (int a = 0; a < all.size(); a++) {\n"
         "            final TLRPC.User user = getMessagesController().getUser(all.get(a).user_id);\n"
         "            if (user != null && !UserObject.isUserSelf(user) && selectedContacts.indexOfKey(user.id) < 0) {\n"
         "                selectedContacts.put(user.id, user);\n"
         "            }\n"
         "        }\n"
         "        if (selectedContacts.isEmpty()) {\n"
         "            return;\n"
         "        }\n"
         "        if (!actionBar.isActionModeShowed()) {\n"
         "            if (fragmentView != null) {\n"
         "                AndroidUtilities.hideKeyboard(fragmentView.findFocus());\n"
         "            }\n"
         "            actionBar.showActionMode();\n"
         "            backDrawable.setRotation(1, true);\n"
         "        }\n"
         "        selectedContactsCountTextView.setNumber(selectedContacts.size(), true);\n"
         "        // rows further down read the same map when they are bound, so only the visible ones\n"
         "        // need to be ticked by hand\n"
         "        for (int i = 0; i < listView.getChildCount(); i++) {\n"
         "            final View view = listView.getChildAt(i);\n"
         "            if (view instanceof UserCell) {\n"
         "                final UserCell cell = (UserCell) view;\n"
         "                cell.setChecked(selectedContacts.indexOfKey(cell.getDialogId()) >= 0, true);\n"
         "            } else if (view instanceof ProfileSearchCell) {\n"
         "                final ProfileSearchCell cell = (ProfileSearchCell) view;\n"
         "                cell.setChecked(selectedContacts.indexOfKey(cell.getDialogId()) >= 0, true);\n"
         "            }\n"
         "        }\n"
         "    }\n\n"
         "    private void hideActionMode() {\n", 1),
    ])


def patch_enter_proceeds():
    """Login screens: the keyboard's Enter key proceeds. A hardware or IME Enter reaches the
    field as a plain key event with no IME action; Telegram's listeners only answer to
    IME_ACTION_NEXT, so Android's default took over and hopped focus to the next view (the Sync
    Contacts box on the phone screen). Treat Enter like Next on every login field and swallow the
    key-up so focus stays where it is. Runs after patch_sync_contacts_off(): anchors on its output."""
    la = "TMessagesProj/src/main/java/org/telegram/ui/LoginActivity.java"
    edit(la, [
        ("    private boolean syncContacts = false; // Chihuahua: off unless ticked\n",
         "    private boolean syncContacts = false; // Chihuahua: off unless ticked\n\n"
         "    // Chihuahua: a keyboard's Enter key arrives as a key event without an IME action; Android would\n"
         "    // then move focus to the next view. These make every login field treat it as Next.\n"
         "    private static boolean chihuahuaIsEnter(int actionId, KeyEvent event) {\n"
         "        return actionId == EditorInfo.IME_NULL && event != null\n"
         "            && (event.getKeyCode() == KeyEvent.KEYCODE_ENTER || event.getKeyCode() == KeyEvent.KEYCODE_NUMPAD_ENTER);\n"
         "    }\n\n"
         "    private static boolean chihuahuaEnterPressed(int actionId, KeyEvent event) {\n"
         "        return chihuahuaIsEnter(actionId, event) && event.getAction() == KeyEvent.ACTION_DOWN;\n"
         "    }\n\n"
         "    private static boolean chihuahuaEnterReleased(int actionId, KeyEvent event) {\n"
         "        return chihuahuaIsEnter(actionId, event) && event.getAction() != KeyEvent.ACTION_DOWN;\n"
         "    }\n", 1),
        ("                if (i == EditorInfo.IME_ACTION_NEXT) {\n",
         "                if (chihuahuaEnterReleased(i, keyEvent)) {\n"
         "                    return true; // the press already acted; keep the release from moving focus\n"
         "                }\n"
         "                if (i == EditorInfo.IME_ACTION_NEXT || chihuahuaEnterPressed(i, keyEvent)) {\n", 6),
        ("                if (i == EditorInfo.IME_ACTION_DONE || i == EditorInfo.IME_ACTION_NEXT) {\n",
         "                if (chihuahuaEnterReleased(i, keyEvent)) {\n"
         "                    return true;\n"
         "                }\n"
         "                if (i == EditorInfo.IME_ACTION_DONE || i == EditorInfo.IME_ACTION_NEXT || chihuahuaEnterPressed(i, keyEvent)) {\n", 1),
    ])


def patch_stay_on_settings():
    """Switching accounts from the Accounts card keeps you on the Settings tab. switchToAccount()
    rebuilds the tab screen from scratch and MainTabsActivity always opens on Chats; the Settings
    tab now hands it a MainTabsActivity told to open on position 2 (Settings) instead. Accounts
    that show the Calls tab in that slot still start on Chats."""
    ui = "TMessagesProj/src/main/java/org/telegram/ui/"
    edit(ui + "ViewPagerActivity.java", [
        ("    private int initialFragmentPosition = -1;\n",
         "    private int initialFragmentPosition = -1;\n\n"
         "    // Chihuahua: lets a caller choose the page the screen opens on.\n"
         "    public void setInitialFragmentPosition(int position) {\n"
         "        initialFragmentPosition = position;\n"
         "    }\n", 1),
    ])
    edit(ui + "MainTabsActivity.java", [
        ("    public MainTabsActivity() {\n        super();\n",
         "    // Chihuahua: open on the Settings tab (after switching accounts from it).\n"
         "    public void chihuahuaStartOnSettings() {\n"
         "        if (!getUserConfig().showCallsTab) {\n"
         "            setInitialFragmentPosition(POSITION_CALLS_OR_SETTINGS);\n"
         "        }\n"
         "    }\n\n"
         "    public MainTabsActivity() {\n        super();\n", 1),
    ])
    edit(ui + "SettingsActivity.java", [
        ("            if (LaunchActivity.instance != null) {\n"
         "                LaunchActivity.instance.switchToAccount(account, true);\n"
         "            }\n"
         "            return;\n"
         "        } else if (item.instanceOf(SettingsSearchCell.Factory.class)) {\n",
         "            if (LaunchActivity.instance != null) {\n"
         "                // Chihuahua: come back to this tab, not Chats.\n"
         "                LaunchActivity.instance.switchToAccount(account, true, obj -> {\n"
         "                    final MainTabsActivity tabs = new MainTabsActivity();\n"
         "                    tabs.chihuahuaStartOnSettings();\n"
         "                    return tabs;\n"
         "                });\n"
         "            }\n"
         "            return;\n"
         "        } else if (item.instanceOf(SettingsSearchCell.Factory.class)) {\n", 1),
    ])


def patch_account_ttl_defaults():
    """Every account that logs in on this build is set once to Telegram's longest self-destruct
    choices: sessions 1 year, account 24 months. onAuthSuccess is the one funnel every login path
    (code, password, QR, sign-up) goes through."""
    anchor = "        needFinishActivity(afterSignup, res.setup_password_required, res.otherwise_relogin_days);\n"
    edit("TMessagesProj/src/main/java/org/telegram/ui/LoginActivity.java", [
        (anchor,
         "        org.telegram.messenger.ChihuahuaConfig.onAccountLoggedIn(currentAccount);\n" + anchor, 1),
    ])


def patch_setup_tab():
    """Replaces the Contacts tab with the Setup page (ChihuahuaSetupActivity): bio, username,
    birthday, two-step verification, session self-destruct and the three privacy rules on one
    screen. The contact list moves to a row inside that page, and to the tab's long-press menu."""
    ui = "TMessagesProj/src/main/java/org/telegram/ui/"
    # GlassTabView's label is set from a string resource; this build needs a plain string.
    edit(ui + "Components/glass/GlassTabView.java", [
        ("    public static GlassTabView createMainTab(Context context, Theme.ResourcesProvider resourcesProvider, "
         "TabAnimation tabAnimation, @StringRes int stringRes) {\n",
         "    // Chihuahua: rename a tab after it is built.\n"
         "    public void chihuahuaSetLabel(CharSequence text) {\n"
         "        textView.setText(text);\n"
         "    }\n\n"
         "    public static GlassTabView createMainTab(Context context, Theme.ResourcesProvider resourcesProvider, "
         "TabAnimation tabAnimation, @StringRes int stringRes) {\n", 1),
    ])
    contacts_tab = ("        tabs[INDEX_CONTACTS] = GlassTabView.createMainTab(context, resourceProvider, "
                    "GlassTabView.TabAnimation.CONTACTS, R.string.MainTabsContacts);\n")
    badge = ("            if (Build.VERSION.SDK_INT >= 23 && UserConfig.getInstance(currentAccount).syncContacts "
             "&& !hasPermission && MessagesController.getGlobalNotificationsSettings().getBoolean(\"askAboutContacts2\", true)) {\n"
             "                tabs[INDEX_CONTACTS].setCounter(\"!\", true, true);\n"
             "            } else {\n"
             "                tabs[INDEX_CONTACTS].setCounter(null, true, true);\n"
             "            }\n")
    old_fragment = ("        if (position == POSITION_CONTACTS) {\n"
                    "            Bundle args = new Bundle();\n"
                    "            args.putBoolean(\"needPhonebook\", true);\n"
                    "            args.putBoolean(\"needFinishFragment\", false);\n"
                    "            args.putBoolean(\"hasMainTabs\", true);\n"
                    "            return new ContactsActivity(args);\n")
    selector = ("        o.add(R.drawable.msg_contact_add, getString(R.string.NewContact), () -> {\n"
                "            new NewContactBottomSheet(this, getContext()).show();\n"
                "        });\n")
    edit(ui + "MainTabsActivity.java", [
        (contacts_tab,
         "        tabs[INDEX_CONTACTS] = GlassTabView.createMainTab(context, resourceProvider, "
         "GlassTabView.TabAnimation.CHECKLIST, R.string.MainTabsContacts);\n"
         "        tabs[INDEX_CONTACTS].chihuahuaSetLabel(\"Setup\");\n", 1),
        # The "!" badge asked for contacts permission; the tab is not the contact list any more.
        (badge, "            tabs[INDEX_CONTACTS].setCounter(null, true, true);\n", 1),
        (old_fragment,
         "        if (position == POSITION_CONTACTS) {\n"
         "            Bundle args = new Bundle();\n"
         "            args.putBoolean(\"hasMainTabs\", true);\n"
         "            return new ChihuahuaSetupActivity(args);\n", 1),
        # Long-press the tab: the contact list is still one press away.
        (selector,
         "        o.add(R.drawable.msg_contacts, getString(R.string.Contacts), () -> {\n"
         "            Bundle args = new Bundle();\n"
         "            args.putBoolean(\"needPhonebook\", true);\n"
         "            presentFragment(new ContactsActivity(args));\n"
         "        });\n" + selector, 1),
    ])


def patch_account_phone_line():
    """Each row of the Accounts card gets a second line: the account's number, formatted, with the
    flag of its country code (looked up in Telegram's own countries.txt). Row grows 48 -> 58 dp."""
    sa = "TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java"
    column = ("chihuahuaColumn(context)")
    edit(sa, [
        ("        private SimpleTextView textView;\n        private TextView counterView;\n",
         "        private SimpleTextView textView;\n        private SimpleTextView chihuahuaPhoneView;\n        private TextView counterView;\n", 1),
        # name + number stacked where the name alone used to sit (LTR and RTL)
        ("                addView(textView, LayoutHelper.createLinear(0, LayoutHelper.MATCH_PARENT, 1f, Gravity.FILL, 0, 0, 18, 0));\n",
         "                addView(" + column + ", LayoutHelper.createLinear(0, LayoutHelper.MATCH_PARENT, 1f, Gravity.FILL, 0, 0, 18, 0));\n", 1),
        ("                addView(textView, LayoutHelper.createLinear(0, LayoutHelper.MATCH_PARENT, 1f, Gravity.FILL, 18, 0, 0, 0));\n",
         "                addView(" + column + ", LayoutHelper.createLinear(0, LayoutHelper.MATCH_PARENT, 1f, Gravity.FILL, 18, 0, 0, 0));\n", 1),
        # the column builder, placed just before updateColors()
        ("        @Override\n        public void updateColors() {\n            textView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText, resourcesProvider));\n            counterView.setBackground(",
         "        private LinearLayout chihuahuaColumn(Context context) {\n"
         "            chihuahuaPhoneView = new SimpleTextView(context);\n"
         "            chihuahuaPhoneView.setTextSize(13);\n"
         "            chihuahuaPhoneView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText, resourcesProvider));\n"
         "            chihuahuaPhoneView.setGravity(Gravity.CENTER_VERTICAL | (LocaleController.isRTL ? Gravity.RIGHT : Gravity.LEFT));\n"
         "            final LinearLayout column = new LinearLayout(context);\n"
         "            column.setOrientation(VERTICAL);\n"
         "            column.setGravity(Gravity.CENTER_VERTICAL);\n"
         "            column.addView(textView, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 20));\n"
         "            column.addView(chihuahuaPhoneView, LayoutHelper.createLinear(LayoutHelper.MATCH_PARENT, 18));\n"
         "            return column;\n"
         "        }\n\n"
         "        @Override\n        public void updateColors() {\n            textView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteBlackText, resourcesProvider));\n"
         "            chihuahuaPhoneView.setTextColor(Theme.getColor(Theme.key_windowBackgroundWhiteGrayText, resourcesProvider));\n"
         "            counterView.setBackground(", 1),
        ("            textView.setText(UserObject.getUserName(user));\n\n            botDrawable.setCurrentAccount(account);\n",
         "            textView.setText(UserObject.getUserName(user));\n"
         "            chihuahuaPhoneView.setText(Emoji.replaceEmoji(org.telegram.messenger.ChihuahuaConfig.phoneWithFlag(user), chihuahuaPhoneView.getPaint().getFontMetricsInt(), false));\n\n"
         "            botDrawable.setCurrentAccount(account);\n", 1),
        ("                MeasureSpec.makeMeasureSpec(dp(48), MeasureSpec.EXACTLY)\n",
         "                MeasureSpec.makeMeasureSpec(dp(58), MeasureSpec.EXACTLY)\n", 1),
    ])


def patch_account_order():
    """The Accounts card on the Settings tab can be dragged into any order.

    Telegram's UniversalRecyclerView already has drag-to-reorder (ItemTouchHelper behind
    listenReorder/allowReorder, used by Chat Folders, Stickers and Quick Replies); the account rows
    just need to sit in a reorder section. Long-pressing a row starts the drag, and the arrow at
    the row's right end becomes a drag handle that starts one on touch. When the drag ends the new
    order is written back through ChihuahuaConfig.applyAccountOrder(), which permutes the accounts'
    loginTime values - the only thing any account list in the app sorts by - so the switcher menu
    and the auth sheets follow the same order without being touched.
    Runs after patch_add_account_button() and patch_account_phone_line(): anchors on their output."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java", [
        # the list learns to reorder
        ("        listView.adapter.setApplyBackground(false);\n        listView.setSections();\n",
         "        listView.adapter.setApplyBackground(false);\n        listView.setSections();\n"
         "        // Chihuahua: accounts can be dragged into any order (long-press a row, or grab the handle).\n"
         "        listView.listenReorder(this::chihuahuaAccountsReordered);\n"
         "        listView.allowReorder(true);\n", 1),
        # the account rows form the reorder section
        ("        if (accountNumbers.size() > 0) {\n"
         "            items.add(UItem.asHeader(getString(R.string.SettingsAccounts)));\n"
         "            for (int i = 0; i < accountNumbers.size(); ++i) {\n"
         "                items.add(AccountCell.Factory.of(i, accountNumbers.get(i)));\n"
         "            }\n"
         "        }\n",
         "        if (accountNumbers.size() > 0) {\n"
         "            items.add(UItem.asHeader(getString(R.string.SettingsAccounts)));\n"
         "            chihuahuaAccountsOrderId = adapter.reorderSectionStart();\n"
         "            for (int i = 0; i < accountNumbers.size(); ++i) {\n"
         "                items.add(AccountCell.Factory.of(i, accountNumbers.get(i)));\n"
         "            }\n"
         "            adapter.reorderSectionEnd();\n"
         "        }\n", 1),
        # the drop handler
        ("    private boolean onLongClick(UItem item, View view, int position, float x, float y) {\n",
         "    private int chihuahuaAccountsOrderId = -1;\n"
         "    private void chihuahuaAccountsReordered(int id, ArrayList<UItem> items) {\n"
         "        if (id != chihuahuaAccountsOrderId) {\n"
         "            return;\n"
         "        }\n"
         "        final ArrayList<Integer> order = new ArrayList<>();\n"
         "        for (UItem item : items) {\n"
         "            if (item.instanceOf(AccountCell.Factory.class)) {\n"
         "                order.add(item.intValue);\n"
         "            }\n"
         "        }\n"
         "        org.telegram.messenger.ChihuahuaConfig.applyAccountOrder(order, currentAccount);\n"
         "    }\n\n"
         "    private boolean onLongClick(UItem item, View view, int position, float x, float y) {\n", 1),
        # the arrow becomes a drag handle with a 48dp touch target (icon stays centred where the arrow was)
        ("            arrowView.setImageResource(R.drawable.msg_arrowright);\n",
         "            arrowView.setImageResource(R.drawable.list_reorder); // Chihuahua: drag handle\n", 1),
        ("                addView(arrowView, LayoutHelper.createLinear(24, 24, 0, Gravity.CENTER_VERTICAL | Gravity.LEFT, 12, 0, 0, 0));\n",
         "                addView(arrowView, LayoutHelper.createLinear(48, 48, 0, Gravity.CENTER_VERTICAL | Gravity.LEFT, 0, 0, 0, 0));\n", 1),
        ("                addView(arrowView, LayoutHelper.createLinear(24, 24, 0, Gravity.CENTER_VERTICAL | Gravity.RIGHT, 0, 0, 12, 0));\n",
         "                addView(arrowView, LayoutHelper.createLinear(48, 48, 0, Gravity.CENTER_VERTICAL | Gravity.RIGHT, 0, 0, 0, 0));\n", 1),
        ("                return new AccountCell(context, resourcesProvider);\n",
         "                final AccountCell cell = new AccountCell(context, resourcesProvider);\n"
         "                // Chihuahua: touching the handle starts the drag at once; long-pressing the row works too.\n"
         "                cell.arrowView.setClickable(true);\n"
         "                cell.arrowView.setOnTouchListener((v, event) -> {\n"
         "                    if (event.getAction() == MotionEvent.ACTION_DOWN && listView instanceof UniversalRecyclerView) {\n"
         "                        final UniversalRecyclerView universal = (UniversalRecyclerView) listView;\n"
         "                        final RecyclerView.ViewHolder holder = listView.getChildViewHolder(cell);\n"
         "                        if (universal.itemTouchHelper != null && universal.isReorderAllowed() && holder != null) {\n"
         "                            universal.itemTouchHelper.startDrag(holder);\n"
         "                        }\n"
         "                    }\n"
         "                    return false;\n"
         "                });\n"
         "                return cell;\n", 1),
    ])


def patch_phone_copy():
    """A tap on the "+44 7468 350735 • @username" line under the name on the Settings tab copies the
    phone number (formatted as shown) and confirms with Telegram's own "Phone copied" bulletin.
    The line shrinks to its text with a rounded ripple so it reads as tappable."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/SettingsActivity.java", [
        ("        topView.addView(subtitleView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.WRAP_CONTENT, Gravity.CENTER_HORIZONTAL | Gravity.TOP, 0, 168 - 12, 0, 0));\n",
         "        // Chihuahua: a tap on this line copies the phone number.\n"
         "        subtitleView.setPadding(dp(8), dp(4), dp(8), dp(4));\n"
         "        subtitleView.setBackground(Theme.createRadSelectorDrawable(getThemedColor(Theme.key_listSelector), 8, 8));\n"
         "        subtitleView.setOnClickListener(v -> {\n"
         "            final TLRPC.User chihuahuaUser = getUserConfig().getCurrentUser();\n"
         "            if (chihuahuaUser == null || TextUtils.isEmpty(chihuahuaUser.phone)) {\n"
         "                return;\n"
         "            }\n"
         "            AndroidUtilities.addToClipboard(PhoneFormat.getInstance().format(\"+\" + chihuahuaUser.phone));\n"
         "            BulletinFactory.of(this).createCopyBulletin(getString(R.string.PhoneCopied)).show();\n"
         "        });\n"
         "        topView.addView(subtitleView, LayoutHelper.createFrame(LayoutHelper.WRAP_CONTENT, LayoutHelper.WRAP_CONTENT, Gravity.CENTER_HORIZONTAL | Gravity.TOP, 16, 168 - 12 - 4, 16, 0));\n", 1),
    ])


def patch_hint_contrast():
    """Tooltip bubbles (HintView2: "Tap on 📷 to post a story…", the stories Premium hints) hardcode
    white text and a white close button, assuming their default dark bubble. Three of them paint
    undo_background instead — tooltip yellow in this theme — so the text vanished (Sean's screenshot,
    2026-09-06). setBgColor() now picks the ink from the bubble's brightness: black on a light
    bubble, white on a dark one. Bubbles that keep the default dark background are unaffected."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/Stories/recorder/HintView2.java", [
        ("    public HintView2 setBgColor(int color) {\n"
         "        if (backgroundPaint.getColor() != color) {\n"
         "            backgroundPaint.setColor(color);\n"
         "            invalidate();\n"
         "        }\n"
         "        return this;\n"
         "    }\n",
         "    private int chihuahuaCloseColor = 0x7dffffff;\n\n"
         "    public HintView2 setBgColor(int color) {\n"
         "        if (backgroundPaint.getColor() != color) {\n"
         "            backgroundPaint.setColor(color);\n"
         "            // Chihuahua: dark ink on a light bubble (this theme's tooltip yellow), white on a dark one.\n"
         "            final boolean light = AndroidUtilities.computePerceivedBrightness(color) > 0.72f;\n"
         "            setTextColor(light ? 0xff000000 : 0xffffffff);\n"
         "            chihuahuaCloseColor = light ? 0x7d000000 : 0x7dffffff;\n"
         "            if (closeButtonDrawable != null) {\n"
         "                closeButtonDrawable.setColorFilter(new PorterDuffColorFilter(chihuahuaCloseColor, PorterDuff.Mode.MULTIPLY));\n"
         "            }\n"
         "            invalidate();\n"
         "        }\n"
         "        return this;\n"
         "    }\n", 1),
        ("                closeButtonDrawable.setColorFilter(new PorterDuffColorFilter(0x7dffffff, PorterDuff.Mode.MULTIPLY));\n",
         "                closeButtonDrawable.setColorFilter(new PorterDuffColorFilter(chihuahuaCloseColor, PorterDuff.Mode.MULTIPLY));\n", 2),
    ])


def patch_action_mode_icons():
    """Dark icons on the chat list's select-mode bar, because that bar cannot be painted.

    The chat list calls actionBar.setDrawBlurBackground(), which hands the bar's background over to
    the blur system: setBackgroundColor() on the action mode is then overridden to merely RECORD a
    colour, repainted later as a blur scrim at the alpha of chat_BlurAlpha, and setBackground() is
    overwritten by the blur pass too. Two builds spent trying to force it navy proved that. So the
    bar stays as Telegram intends — a light glass panel over the chat list — and the icons on it go
    dark, which is exactly how Telegram's own light themes read.

    Only DialogsActivity is changed. ChatActivity never blurs its action bar, so its select-mode bar
    really is navy and keeps the white icons."""
    edit("TMessagesProj/src/main/java/org/telegram/ui/DialogsActivity.java", [
        ("Theme.key_actionBarActionModeDefaultIcon",
         "Theme.key_windowBackgroundWhiteBlackText", 11),
    ])


def patch_glass_header():
    """Telegram 12.x draws the chat screen's header as translucent "glass" pills coloured by
    chat_topPanelBackground, while the title and icons on them use actionBarDefaultTitle/Icon.
    That works for Telegram's themes (white bar, dark text) but a Windows 98 navy bar with white
    text ends up as white text on a light grey pill. Make the header pills follow actionBarDefault
    (the pinned-message panel and other top panels keep chat_topPanelBackground)."""
    ui = "TMessagesProj/src/main/java/org/telegram/ui/"
    tags_anchor = "    public static BlurredBackgroundProvider topPanelChatActivityTags(Theme.ResourcesProvider resourcesProvider) {\n"
    edit(ui + "Components/blur3/drawable/color/impl/BlurredBackgroundProviderImpl.java", [
        (tags_anchor, GLASS_HEADER_PROVIDER + tags_anchor, 1),
    ])
    edit(ui + "ChatActivity.java", [
        ("            BlurredBackgroundProviderImpl.topPanelChatActivity(themeDelegate),\n            ChatObject.isForum(currentChat));\n",
         "            BlurredBackgroundProviderImpl.topPanelChatActivityHeader(themeDelegate),\n            ChatObject.isForum(currentChat));\n", 1),
    ])
    edit(ui + "ChannelAdminLogActivity.java", [
        ("actionBar.setupGlass(glassBackgroundDrawableFactory, BlurredBackgroundProviderImpl.topPanelChatActivity(resourceProvider));",
         "actionBar.setupGlass(glassBackgroundDrawableFactory, BlurredBackgroundProviderImpl.topPanelChatActivityHeader(resourceProvider));", 1),
    ])
    for rel in ("community/CommunityCreateActivity.java", "community/CommunityEditActivity.java"):
        edit(ui + rel, [
            ("actionBar.setupGlass(factory, BlurredBackgroundProviderImpl.topPanelChatActivity(resourceProvider));",
             "actionBar.setupGlass(factory, BlurredBackgroundProviderImpl.topPanelChatActivityHeader(resourceProvider));", 1),
        ])


def install_icons():
    res = ROOT / "TMessagesProj/src/main/res"
    for d in DENSITIES:
        mip = res / f"mipmap-{d}"
        if not mip.is_dir():
            fail(f"missing {mip}")
            continue
        shutil.copy(ICONS / f"foreground-{d}.png", mip / "icon_foreground.png")
        shutil.copy(ICONS / f"foreground-{d}.png", mip / "icon_foreground_round.png")
        shutil.copy(ICONS / f"launcher-{d}.png", mip / "ic_launcher.png")
        shutil.copy(ICONS / f"launcher_round-{d}.png", mip / "ic_launcher_round.png")
        dr = res / f"drawable-{d}" / "ic_launcher_dr.webp"
        if dr.exists():
            shutil.copy(ICONS / f"dr-{d}.webp", dr)
    # Adaptive icon: gradient bitmap as the background layer, dog sticker as the foreground,
    # and no monochrome (themed-icon) layer, which would be Telegram's paper plane.
    for d in DENSITIES:
        shutil.copy(ICONS / f"background-{d}.png", res / f"mipmap-{d}" / "icon_bg_chihuahua.png")
    edit("TMessagesProj/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", [
        ('<background android:drawable="@drawable/icon_background" />',
         '<background android:drawable="@mipmap/icon_bg_chihuahua" />', 1),
        ('    <monochrome android:drawable="@drawable/icon_plane" />\n', "", 1),
    ])
    edit("TMessagesProj/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", [
        ('<background android:drawable="@drawable/icon_background_round" />',
         '<background android:drawable="@mipmap/icon_bg_chihuahua" />', 1),
        ('    <monochrome android:drawable="@drawable/icon_plane" />\n', "", 1),
    ])
    print("  ok  launcher icons installed")


def write_summary():
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [
        "### Customization applied",
        f"- App name: **{APP_NAME}**",
        f"- Package: `{APP_PACKAGE}`",
        f"- Max accounts: **{MAX_ACCOUNTS}**",
        f"- ABI: `{BUILD_ABI}`",
        f"- api_id: `{TG_API_ID[:2]}…` (hidden)",
    ]
    print("\n".join(lines))
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    print(f"Customizing Telegram source at {ROOT}")
    check_inputs()
    patch_gradle_properties()
    patch_account_limit()
    patch_native_account_limit()
    patch_build_vars()
    patch_app_name()
    patch_abis()
    patch_google_services()
    patch_account_type()
    patch_add_to_group()
    patch_settings_and_toggles()
    patch_theme98()
    install_icons()
    if errors:
        print(f"\n{len(errors)} problem(s) — the Telegram source no longer matches the anchors above.")
        sys.exit(1)
    write_summary()
    print("\nAll customizations applied.")


if __name__ == "__main__":
    main()
