#!/usr/bin/env python3
"""
customize_desktop.py — turns a clean Telegram Desktop (tdesktop) checkout into "Chihuahua Telegram".

Run by the GitHub Actions workflow:   python customize_desktop.py <path-to-tdesktop-checkout>

Settings (environment):
  APP_NAME       window/app name, also the data folder %APPDATA%\\<APP_NAME>   (default: Chihuahua Telegram)
  MAX_ACCOUNTS   accounts the app can hold                                    (default: 32)

api_id / api_hash are passed to CMake by the workflow (TDESKTOP_API_ID / TDESKTOP_API_HASH), not here.
Every edit is anchored on exact upstream text and the script aborts if an anchor is not found
exactly the expected number of times.
"""
import os
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "tdesktop").resolve()
HERE = Path(__file__).resolve().parent
ICONS = HERE.parent / "icons" / "desktop"

APP_NAME = os.environ.get("APP_NAME", "Chihuahua Telegram").strip()
MAX_ACCOUNTS = int(os.environ.get("MAX_ACCOUNTS", "32"))
APP_FILE = "".join(ch for ch in APP_NAME if ch.isalnum()) or "Chihuahua"
# Stable, unique AppUserModelID / installer id so Windows never confuses this app with the official one.
APP_ID = "{" + str(uuid.uuid5(uuid.NAMESPACE_DNS, "chihuahua-telegram.desktop." + APP_NAME)).upper() + "}"

errors = []

# ---------------------------------------------------------------------------
# Moderation actions, ported from the Android build's chihuahuaWipeEverywhere().
# Three one-click items on a message in a group you moderate. All three delete
# every message AND reaction of the sender across every group you manage and
# report them to Telegram for spam; they differ only in what else they do.
# Written straight into history_view_context_menu.cpp (anonymous namespace) so
# that no CMake source list has to be touched.
# ---------------------------------------------------------------------------
MODERATION_INCLUDES = """#include "api/api_report.h"
#include "api/api_chat_participants.h"
#include "data/data_folder.h"
#include "dialogs/dialogs_indexed_list.h"
#include "dialogs/dialogs_main_list.h"
#include "dialogs/dialogs_row.h"
"""

MODERATION_CODE = """// --- Chihuahua: one-click moderation across every group you manage. ---

enum class ChihuahuaMode {
\tWipe, // Delete every message and reaction, report for spam.
\tMute, // ... and silence them everywhere, without removing them.
\tBan,  // ... and remove them everywhere, unable to rejoin.
};

[[nodiscard]] ChatRestrictionsInfo ChihuahuaMuteRights() {
\tusing Flag = ChatRestriction;
\t// Everything except ViewMessages, so they stay in the group and can read.
\treturn ChatRestrictionsInfo(Flag::SendStickers
\t\t| Flag::SendGifs
\t\t| Flag::SendGames
\t\t| Flag::SendInline
\t\t| Flag::SendPolls
\t\t| Flag::SendPhotos
\t\t| Flag::SendVideos
\t\t| Flag::SendVideoMessages
\t\t| Flag::SendMusic
\t\t| Flag::SendVoiceMessages
\t\t| Flag::SendFiles
\t\t| Flag::SendOther
\t\t| Flag::EmbedLinks
\t\t| Flag::ChangeInfo
\t\t| Flag::AddParticipants
\t\t| Flag::PinMessages
\t\t| Flag::CreateTopics
\t\t| Flag::SendReactions, TimeId(0));
}

[[nodiscard]] UserData *ChihuahuaTarget(HistoryItem *item) {
\tif (!item || item->isService() || item->out()) {
\t\treturn nullptr;
\t}
\tconst auto channel = item->history()->peer->asChannel();
\tif (!channel || !channel->isMegagroup() || !channel->canBanMembers()) {
\t\treturn nullptr;
\t}
\tconst auto user = item->from()->asUser();
\tif (!user || user->isSelf()) {
\t\treturn nullptr;
\t}
\treturn user;
}

[[nodiscard]] std::vector<not_null<ChannelData*>> ChihuahuaManagedGroups(
\t\tnot_null<Main::Session*> session,
\t\tChihuahuaMode mode) {
\tauto result = std::vector<not_null<ChannelData*>>();
\tconst auto add = [&](not_null<Dialogs::IndexedList*> list) {
\t\tfor (const auto &row : list->all()) {
\t\t\tconst auto history = row->history();
\t\t\tif (!history) {
\t\t\t\tcontinue;
\t\t\t}
\t\t\tconst auto channel = history->peer->asChannel();
\t\t\tif (!channel || !channel->isMegagroup()) {
\t\t\t\tcontinue;
\t\t\t}
\t\t\tconst auto allowed = (mode == ChihuahuaMode::Wipe)
\t\t\t\t? (channel->canDeleteMessages() || channel->canBanMembers())
\t\t\t\t: channel->canBanMembers();
\t\t\tif (!allowed) {
\t\t\t\tcontinue;
\t\t\t}
\t\t\t// A dialog is in the main list or in the archive, never both.
\t\t\tresult.push_back(channel);
\t\t}
\t};
\tadd(session->data().chatsList()->indexed());
\tif (const auto folder = session->data().folderLoaded(Data::Folder::kId)) {
\t\tadd(folder->chatsList()->indexed());
\t}
\treturn result;
}

void ChihuahuaAct(
\t\tnot_null<Window::SessionController*> controller,
\t\tFullMsgId itemId,
\t\tChihuahuaMode mode) {
\tconst auto session = &controller->session();
\tconst auto owner = &session->data();
\tconst auto item = owner->message(itemId);
\tif (!item) {
\t\treturn;
\t}
\tconst auto user = ChihuahuaTarget(item);
\tif (!user) {
\t\treturn;
\t}
\tconst auto groups = ChihuahuaManagedGroups(session, mode);
\tif (groups.empty()) {
\t\treturn;
\t}
\tconst auto count = int(groups.size());
\tconst auto where = (count == 1)
\t\t? u"1 group"_q
\t\t: (QString::number(count) + u" groups"_q);
\tconst auto text = ((mode == ChihuahuaMode::Ban)
\t\t? u"Ban %1, delete every message and reaction of theirs, and report them for spam in %2 you manage?"_q
\t\t: (mode == ChihuahuaMode::Mute)
\t\t? u"Mute %1 for good, delete every message and reaction of theirs, and report them for spam in %2 you manage?"_q
\t\t: u"Delete every message and reaction of %1 and report them for spam in %2 you manage?"_q
\t\t).arg(user->name(), where);
\tconst auto confirm = (mode == ChihuahuaMode::Ban)
\t\t? u"Ban & wipe"_q
\t\t: (mode == ChihuahuaMode::Mute)
\t\t? u"Mute & wipe"_q
\t\t: u"Wipe"_q;

\t// Report the message that was right-clicked (and its album, if any).
\tauto reportIds = MessageIdsList();
\tif (const auto group = owner->groups().find(item)) {
\t\tfor (const auto &i : group->items) {
\t\t\treportIds.push_back(i->fullId());
\t\t}
\t} else {
\t\treportIds.push_back(itemId);
\t}

\tcontroller->show(Ui::MakeConfirmBox({
\t\t.text = text,
\t\t.confirmed = [=](Fn<void()> close) {
\t\t\tApi::ReportSpam(user, reportIds);
\t\t\tfor (const auto &group : groups) {
\t\t\t\tsession->api().deleteAllFromParticipant(group, user);
\t\t\t\tsession->api().deleteAllReactionsFromParticipant(
\t\t\t\t\tgroup,
\t\t\t\t\tuser,
\t\t\t\t\tMsgId(),
\t\t\t\t\tData::ReactionId());
\t\t\t\tif (mode == ChihuahuaMode::Mute) {
\t\t\t\t\tApi::ChatParticipants::Restrict(
\t\t\t\t\t\tgroup,
\t\t\t\t\t\tuser,
\t\t\t\t\t\tChatRestrictionsInfo(),
\t\t\t\t\t\tChihuahuaMuteRights(),
\t\t\t\t\t\tnullptr,
\t\t\t\t\t\tnullptr);
\t\t\t\t} else if (mode == ChihuahuaMode::Ban) {
\t\t\t\t\tsession->api().chatParticipants().kick(
\t\t\t\t\t\tgroup,
\t\t\t\t\t\tuser,
\t\t\t\t\t\tChatRestrictionsInfo());
\t\t\t\t}
\t\t\t}
\t\t\tcontroller->showToast((mode == ChihuahuaMode::Ban)
\t\t\t\t? (u"Banned and wiped in "_q + where + u"."_q)
\t\t\t\t: (mode == ChihuahuaMode::Mute)
\t\t\t\t? (u"Muted and wiped in "_q + where + u"."_q)
\t\t\t\t: (u"Wiped in "_q + where + u"."_q));
\t\t\tclose();
\t\t},
\t\t.confirmText = confirm,
\t\t.confirmStyle = &st::attentionBoxButton,
\t}));
}

void AddChihuahuaModerationActions(
\t\tnot_null<Ui::PopupMenu*> menu,
\t\tconst ContextMenuRequest &request,
\t\tnot_null<ListWidget*> list) {
\tif (!request.selectedItems.empty()) {
\t\treturn;
\t}
\tconst auto item = request.item;
\tif (!ChihuahuaTarget(item)) {
\t\treturn;
\t}
\tconst auto controller = list->controller();
\tconst auto itemId = item->fullId();
\tconst auto add = [&](
\t\t\tconst QString &text,
\t\t\tChihuahuaMode mode,
\t\t\tconst style::icon *icon) {
\t\tmenu->addAction(text, crl::guard(controller, [=] {
\t\t\tChihuahuaAct(controller, itemId, mode);
\t\t}), icon);
\t};
\tadd(u"Ban, wipe & report"_q, ChihuahuaMode::Ban, &st::menuIconBlockAttention);
\tadd(u"Mute, wipe & report"_q, ChihuahuaMode::Mute, &st::menuIconMute);
\tadd(u"Wipe & report"_q, ChihuahuaMode::Wipe, &st::menuIconDeleteAttention);
}

"""

CONTEXT_MENU = "Telegram/SourceFiles/history/view/history_view_context_menu.cpp"


def patch_moderation():
    edit(CONTEXT_MENU, [
        # Headers the ported code needs that the file does not already pull in.
        ('#include "api/api_report.h"\n', MODERATION_INCLUDES, 1),
        # The code itself, in the file's own anonymous namespace.
        ('void AddReportAction(\n\t\tnot_null<Ui::PopupMenu*> menu,',
         MODERATION_CODE + 'void AddReportAction(\n\t\tnot_null<Ui::PopupMenu*> menu,', 1),
        # Show the items right under Telegram's own Delete entry.
        ('\tAddDeleteAction(menu, request, list);\n\tAddDownloadFilesAction(menu, request, list);\n',
         '\tAddDeleteAction(menu, request, list);\n'
         '\tAddChihuahuaModerationActions(menu, request, list);\n'
         '\tAddDownloadFilesAction(menu, request, list);\n', 1),
    ])


def fail(msg):
    errors.append(msg)
    print(f"  !! {msg}")


def edit(relpath, replacements):
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


def main():
    if not (ROOT / "Telegram" / "CMakeLists.txt").exists():
        sys.exit(f"tdesktop checkout not found at {ROOT}")
    if not (2 <= MAX_ACCOUNTS <= 256):
        sys.exit("MAX_ACCOUNTS must be between 2 and 256")
    if not ICONS.is_dir():
        sys.exit(f"desktop icons missing at {ICONS}")
    print(f"Customizing Telegram Desktop at {ROOT}: name={APP_NAME!r} file={APP_FILE} accounts={MAX_ACCOUNTS} id={APP_ID}")

    # --- account limit (both constants; maxAccounts() = min(premium + kMaxAccounts, kPremiumMaxAccounts))
    edit("Telegram/SourceFiles/main/main_domain.h", [
        ("\tstatic constexpr auto kMaxAccounts = 3;\n\tstatic constexpr auto kPremiumMaxAccounts = 6;\n",
         f"\tstatic constexpr auto kMaxAccounts = {MAX_ACCOUNTS};\n\tstatic constexpr auto kPremiumMaxAccounts = {MAX_ACCOUNTS};\n", 1),
    ])
    # --- identity: name (also the %APPDATA% folder), exe/file name, Windows app id
    edit("Telegram/SourceFiles/core/version.h", [
        ('constexpr auto AppId = "{53F49750-6209-4FBF-9CA8-7A333C87D1ED}"_cs;',
         f'constexpr auto AppId = "{APP_ID}"_cs;', 1),
        ('constexpr auto AppName = "Telegram Desktop"_cs;', f'constexpr auto AppName = "{APP_NAME}"_cs;', 1),
        ('constexpr auto AppFile = "Telegram"_cs;', f'constexpr auto AppFile = "{APP_FILE}"_cs;', 1),
    ])
    # --- exe metadata (what Windows shows in Properties / Task Manager)
    edit("Telegram/Resources/winrc/Telegram.rc", [
        ('VALUE "CompanyName", "Telegram FZ-LLC"', f'VALUE "CompanyName", "{APP_NAME} (unofficial build)"', 1),
        ('VALUE "FileDescription", "Telegram Desktop"', f'VALUE "FileDescription", "{APP_NAME}"', 1),
        ('VALUE "ProductName", "Telegram Desktop"', f'VALUE "ProductName", "{APP_NAME}"', 1),
    ])
    # --- window title
    for rel in ("Telegram/SourceFiles/window/main_window.cpp",
                "Telegram/SourceFiles/window/window_saved_windows.cpp",
                "Telegram/SourceFiles/window/window_restore_shell.cpp"):
        edit(rel, [('u"Telegram"_q', f'u"{APP_NAME}"_q', 1)])
    # --- moderation actions (Ban/Mute/Wipe + report, across every group you manage)
    patch_moderation()
    # --- icons
    art = ROOT / "Telegram" / "Resources" / "art"
    copied = 0
    for f in ICONS.iterdir():
        if f.suffix in (".png", ".ico") and f.name != "preview.png":
            target = art / f.name
            if target.exists():
                shutil.copy(f, target)
                copied += 1
            else:
                print(f"  --  no upstream file for {f.name}, skipped")
    print(f"  ok  {copied} icon files replaced")

    if errors:
        print(f"\n{len(errors)} problem(s) — tdesktop no longer matches the anchors above.")
        sys.exit(1)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Desktop customization applied\n- Name: **{APP_NAME}**\n- Max accounts: **{MAX_ACCOUNTS}**\n- AppId: `{APP_ID}`\n")
    print("\nAll desktop customizations applied.")


if __name__ == "__main__":
    main()
