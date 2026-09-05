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
ICONS = HERE / "icons"

APP_NAME = os.environ.get("APP_NAME", "Chihuahua Telegram").strip()
APP_PACKAGE = os.environ.get("APP_PACKAGE", "com.chihuahua.messenger").strip()
MAX_ACCOUNTS = int(os.environ.get("MAX_ACCOUNTS", "32"))
BUILD_ABI = os.environ.get("BUILD_ABI", "arm64-v8a").strip()
GRADLE_HEAP = os.environ.get("GRADLE_HEAP", "8g").strip()
TG_API_ID = os.environ.get("TG_API_ID", "").strip()
TG_API_HASH = os.environ.get("TG_API_HASH", "").strip()
KEYSTORE_PASSWORD = os.environ.get("KEYSTORE_PASSWORD", "").strip()
KEYSTORE_ALIAS = os.environ.get("KEYSTORE_ALIAS", "chihuahua").strip()
ACTIVATION_CODE = os.environ.get("ACTIVATION_CODE", "").strip()

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
     * Clears a sender out of every group this account manages: their messages and reactions are
     * deleted in all of them and they are reported to Telegram for spam. {@code mode} decides what
     * else happens to them -- nothing, muted in those groups, or banned from them.
     */
    private void chihuahuaWipeEverywhere(MessageObject message, int mode) {
        final TLRPC.User user = chihuahuaQuickBanTarget(message);
        final TLRPC.Chat chat = currentChat;
        if (user == null || chat == null || getParentActivity() == null) {
            return;
        }
        final ArrayList<TLRPC.Chat> chats = chihuahuaManagedGroups();
        if (chats.isEmpty()) {
            return;
        }
        final ArrayList<Integer> reportIds = new ArrayList<>();
        reportIds.add(message.getId());
        final String name = UserObject.getUserName(user);
        final String where = chats.size() + (chats.size() == 1 ? " group" : " groups") + " you manage";
        final String title, question, confirm, done;
        if (mode == CHIHUAHUA_WIPE_BAN) {
            title = "Ban everywhere and wipe";
            question = "Ban **" + name + "** from " + where + ", delete every message and reaction of theirs in them, and report them to Telegram for spam? They are removed and cannot rejoin.";
            confirm = "Ban and wipe";
            done = name + " banned from " + where;
        } else if (mode == CHIHUAHUA_WIPE_MUTE) {
            title = "Mute everywhere and wipe";
            question = "Mute **" + name + "** in " + where + ", delete every message and reaction of theirs in them, and report them to Telegram for spam? They stay in the groups but cannot post or react.";
            confirm = "Mute and wipe";
            done = name + " muted in " + where;
        } else {
            title = "Wipe everywhere";
            question = "Delete every message and reaction of **" + name + "** in " + where + " and report them to Telegram for spam? They are not muted or removed, so they can post again.";
            confirm = "Wipe";
            done = name + " wiped from " + where;
        }
        AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), themeDelegate);
        builder.setTitle(title);
        builder.setMessage(AndroidUtilities.replaceTags(question));
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        builder.setPositiveButton(confirm, (di, i) -> {
            TLRPC.TL_channels_reportSpam report = new TLRPC.TL_channels_reportSpam();
            report.channel = MessagesController.getInputChannel(chat);
            report.participant = MessagesController.getInputPeer(user);
            report.id = reportIds;
            getConnectionsManager().sendRequest(report, null);
            for (TLRPC.Chat group : chats) {
                getMessagesController().deleteUserChannelHistory(group, user, null, 0);
                getMessagesController().deleteUserChannelAllReactions(group, user, null);
                if (mode == CHIHUAHUA_WIPE_MUTE) {
                    getMessagesController().setParticipantBannedRole(group.id, user, null, chihuahuaMuteRights(), false, ChatActivity.this);
                } else if (mode == CHIHUAHUA_WIPE_BAN) {
                    getMessagesController().deleteParticipantFromChat(group.id, user, group, false, false);
                }
            }
            if (BulletinFactory.canShowBulletin(ChatActivity.this)) {
                BulletinFactory.of(ChatActivity.this).createSimpleBulletin(R.raw.ic_ban, done, "Messages and reactions deleted, reported for spam").show();
            }
        });
        AlertDialog wipeDialog = builder.create();
        showDialog(wipeDialog);
        TextView wipeButton = (TextView) wipeDialog.getButton(DialogInterface.BUTTON_POSITIVE);
        if (wipeButton != null) {
            wipeButton.setTextColor(getThemedColor(Theme.key_text_RedBold));
        }
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
    for name, sub in (("ChihuahuaConfig.java", "messenger"), ("ChihuahuaSettingsActivity.java", "ui")):
        p = HERE / "patches" / name
        if not p.exists():
            fail(f"missing {p}")
            continue
        text = p.read_text(encoding="utf-8").replace("%%ACTIVATION_HASH%%", activation_hash)
        (src / sub / name).write_text(text, encoding="utf-8")
    print("  ok  Chihuahua settings classes copied" + (" (activation lock ON)" if activation_hash else " (no activation code set)"))
    # Activation gate: LaunchActivity asks for the code once per device when a code is compiled in.
    on_resume = "    @Override\n    protected void onResume() {\n        super.onResume();\n"
    on_create = "    @Override\n    protected void onCreate(Bundle savedInstanceState) {\n"
    edit("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java", [
        (on_resume, on_resume + "        chihuahuaCheckActivation();\n"
                   "        org.telegram.messenger.ChihuahuaConfig.applyKeepConnected();\n", 1),
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
        # user ID next to the online status under the name (toggle in Settings → Chihuahua)
        (STATUS_ANCHOR,
         STATUS_ANCHOR +
         "                if (org.telegram.messenger.ChihuahuaConfig.showIdInProfile()) {\n"
         "                    newString2 = newString2 + org.telegram.messenger.ChihuahuaConfig.accountAgeSuffix(user.id);\n"
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
         '                SpannableStringBuilder ssb = new SpannableStringBuilder("Chihuahua");\n', 1),
    ])
    patch_glass_header()
    patch_action_mode_icons()
    patch_profile_header()
    patch_per_account_notifications()
    patch_id_row()
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
