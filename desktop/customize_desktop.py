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
import re
import shutil
import sys
import textwrap
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
PROFILE_ACTIONS = "Telegram/SourceFiles/info/profile/info_profile_actions.cpp"


def age_anchor_table():
    """Read the ID -> date anchor table out of the Android build's ChihuahuaConfig.

    Telegram hands out user IDs in increasing order, so a table of known
    (id, date) pairs interpolates to a creation month. Both apps read the same
    table from the same file, so their estimates can never drift apart.
    """
    src = HERE.parent / "patches" / "ChihuahuaConfig.java"
    if not src.exists():
        fail(f"missing {src} — needed for the account-age table")
        return None
    text = src.read_text(encoding="utf-8")
    ids = re.search(r"ID_ANCHORS\s*=\s*\{([^}]*)\}", text)
    days = re.search(r"DAY_ANCHORS\s*=\s*\{([^}]*)\}", text)
    rate = re.search(r"IDS_PER_DAY_RECENT\s*=\s*([0-9.]+)", text)
    if not (ids and days and rate):
        fail("ChihuahuaConfig.java: could not read the account-age anchors")
        return None
    id_values = [v.strip().rstrip("Ll") for v in ids.group(1).split(",") if v.strip()]
    day_values = [v.strip() for v in days.group(1).split(",") if v.strip()]
    if len(id_values) != len(day_values) or len(id_values) < 2:
        fail(f"account-age anchors: {len(id_values)} ids vs {len(day_values)} days")
        return None
    return id_values, day_values, rate.group(1)


# Written to Telegram/SourceFiles/chihuahua_age.h and included by both the
# profile rows and the group-message name badge. A header needs no CMake source
# list change, and one copy means the two cannot disagree.
AGE_HEADER = '''/*
Generated by desktop/customize_desktop.py from patches/ChihuahuaConfig.java.
Do not edit here — edit the anchor table in that file, so the Android and
desktop builds keep estimating account age identically.
*/
#pragma once

#include <QtCore/QDate>
#include <QtCore/QLocale>
#include <QtCore/QString>

namespace Chihuahua {

// Telegram hands out user IDs in increasing order, so a table of known
// (id, date) pairs interpolates to a creation month.
inline constexpr auto kAnchors = %(count)d;
inline constexpr quint64 kIdAnchors[kAnchors] = {
%(ids)s
};
// Days since 1970-01-01, one per entry above.
inline constexpr int kDayAnchors[kAnchors] = {
%(days)s
};
// IDs handed out per day past the last anchor.
inline constexpr auto kIdsPerDayRecent = %(rate)s;
// Accounts younger than this many months are flagged in group chats. Matches
// the Android build's default ("flag new accounts", threshold 3 months).
inline constexpr auto kFlagMonths = 3;

// Days since 1970-01-01 when this account was probably made; -1 when unknown.
[[nodiscard]] inline double CreatedDay(quint64 id) {
\tif (!id) {
\t\treturn -1.;
\t} else if (id <= kIdAnchors[0]) {
\t\treturn double(kDayAnchors[0]);
\t} else if (id >= kIdAnchors[kAnchors - 1]) {
\t\treturn kDayAnchors[kAnchors - 1]
\t\t\t+ (id - kIdAnchors[kAnchors - 1]) / kIdsPerDayRecent;
\t}
\tauto i = 1;
\twhile (id > kIdAnchors[i]) {
\t\t++i;
\t}
\treturn kDayAnchors[i - 1]
\t\t+ double(id - kIdAnchors[i - 1])
\t\t\t* (kDayAnchors[i] - kDayAnchors[i - 1])
\t\t\t/ double(kIdAnchors[i] - kIdAnchors[i - 1]);
}

[[nodiscard]] inline QDate CreatedDate(quint64 id) {
\tconst auto day = CreatedDay(id);
\tif (day < 0.) {
\t\treturn QDate();
\t}
\tconst auto date = QDate(1970, 1, 1).addDays(qint64(day));
\tconst auto today = QDate::currentDate();
\treturn (date > today) ? today : date;
}

// "Nov 2025", "2013 or earlier", or empty when the ID says nothing.
[[nodiscard]] inline QString CreatedEstimate(quint64 id) {
\tif (!id) {
\t\treturn QString();
\t} else if (id <= kIdAnchors[0]) {
\t\treturn QStringLiteral("2013 or earlier");
\t}
\tconst auto date = CreatedDate(id);
\treturn date.isValid()
\t\t? QLocale::c().toString(date, QStringLiteral("MMM yyyy"))
\t\t: QString();
}

[[nodiscard]] inline int AgeMonths(quint64 id) {
\tconst auto date = CreatedDate(id);
\tif (!date.isValid()) {
\t\treturn -1;
\t}
\tconst auto days = date.daysTo(QDate::currentDate());
\treturn (days <= 0) ? 0 : int(days / 30.44);
}

// "new" or "2mo" for accounts under the threshold; empty for everyone else, so
// the badge showing up at all is the warning.
[[nodiscard]] inline QString GroupAgeBadge(quint64 id) {
\tconst auto months = AgeMonths(id);
\tif (months < 0 || months >= kFlagMonths) {
\t\treturn QString();
\t}
\treturn (months < 1)
\t\t? QStringLiteral("new")
\t\t: (QString::number(months) + QStringLiteral("mo"));
}

} // namespace Chihuahua
'''


def write_age_header(id_values, day_values, rate):
    wrap = lambda vals: "\n".join(
        "\t" + line for line in textwrap.wrap(", ".join(vals), width=68))
    path = ROOT / "Telegram" / "SourceFiles" / "chihuahua_age.h"
    path.write_text(AGE_HEADER % {
        "count": len(id_values),
        "ids": wrap(id_values),
        "days": wrap(day_values),
        "rate": rate,
    }, encoding="utf-8")
    print(f"  ok  Telegram/SourceFiles/chihuahua_age.h ({len(id_values)} anchors)")


# Two rows under the phone number: the ID (right-click to copy) and the
# estimated creation month, matching what the Android build shows in profiles.
ACCOUNT_ID_ROWS = """\t\t{
\t\t\tconst auto chihuahuaId = peerToUser(user->id).bare;
\t\t\taddInfoOneLine(
\t\t\t\tu"ID"_q,
\t\t\t\trpl::single(TextWithEntities{ QString::number(chihuahuaId) }),
\t\t\t\tu"Copy ID"_q,
\t\t\t\tst::infoProfileLabeledPadding,
\t\t\t\tst::popupMenuWithIcons);
\t\t\tconst auto chihuahuaCreated = Chihuahua::CreatedEstimate(chihuahuaId);
\t\t\tif (!chihuahuaCreated.isEmpty()) {
\t\t\t\taddInfoOneLine(
\t\t\t\t\tu"Account created"_q,
\t\t\t\t\trpl::single(TextWithEntities{
\t\t\t\t\t\tu"est. "_q + chihuahuaCreated }),
\t\t\t\t\tu"Copy"_q);
\t\t\t}
\t\t}
"""


MESSAGE_VIEW = "Telegram/SourceFiles/history/view/history_view_message.cpp"

# The sender's name is built in exactly one place and everything downstream
# measures whatever string it is given, so appending the badge here gets the
# layout for free instead of hand-painting text next to the name.
AGE_BADGE_NAME = """\t\tauto chihuahuaName = from->name();
\t\tif (const auto chihuahuaUser = from->asUser()) {
\t\t\tif (!chihuahuaUser->isBot() && !chihuahuaUser->isSelf()) {
\t\t\t\tconst auto badge = Chihuahua::GroupAgeBadge(
\t\t\t\t\tpeerToUser(chihuahuaUser->id).bare);
\t\t\t\tif (!badge.isEmpty()) {
\t\t\t\t\t// Built from code points, not a literal, so no MSVC
\t\t\t\t\t// source-charset question about the middle dot.
\t\t\t\t\tchihuahuaName += QString(QChar(' '))
\t\t\t\t\t\t+ QChar(0x00B7)
\t\t\t\t\t\t+ QChar(' ')
\t\t\t\t\t\t+ badge;
\t\t\t\t}
\t\t\t}
\t\t}
\t\t_fromName.setText(
\t\t\tst::msgNameStyle,
\t\t\tchihuahuaName,
\t\t\tUi::NameTextOptions());
"""


def patch_age_badge():
    edit(MESSAGE_VIEW, [
        ('#include "history/history.h"\n',
         '#include "history/history.h"\n#include "chihuahua_age.h"\n', 1),
        ('\t\t_fromName.setText(\n'
         '\t\t\tst::msgNameStyle,\n'
         '\t\t\tfrom->name(),\n'
         '\t\t\tUi::NameTextOptions());\n',
         AGE_BADGE_NAME, 1),
    ])


PEER_MENU = "Telegram/SourceFiles/window/window_peer_menu.cpp"

ADMINS_CODE = """void Filler::addChihuahuaAdmins() {
\t// Chihuahua: the admin list in one click, in any group or channel you are
\t// in. Telegram only offers it inside Manage group, which needs admin rights.
\tconst auto channel = _peer ? _peer->asChannel() : nullptr;
\tif (!channel || channel->isMonoforum()) {
\t\treturn;
\t}
\tconst auto navigation = _controller;
\t_addAction(u"Admins"_q, [=] {
\t\tParticipantsBoxController::Start(
\t\t\tnavigation,
\t\t\tchannel,
\t\t\tParticipantsRole::Admins);
\t}, &st::menuIconAdmin);
}

"""


def patch_admins():
    edit(PEER_MENU, [
        ('\tvoid addManageChat();\n',
         '\tvoid addManageChat();\n\tvoid addChihuahuaAdmins();\n', 1),
        ('void Filler::addBoostChat() {\n', ADMINS_CODE + 'void Filler::addBoostChat() {\n', 1),
        ('\taddManageChat();\n\taddSetPersonalChannel();\n',
         '\taddManageChat();\n\taddChihuahuaAdmins();\n\taddSetPersonalChannel();\n', 1),
    ])


def patch_account_id():
    table = age_anchor_table()
    if not table:
        return
    write_age_header(*table)
    edit(PROFILE_ACTIONS, [
        ('#include "lang/lang_keys.h"\n',
         '#include "lang/lang_keys.h"\n#include "chihuahua_age.h"\n', 1),
        ('\t\tauto label = user->isBot()\n\t\t\t? tr::lng_info_about_label()\n\t\t\t: tr::lng_info_bio_label();\n',
         ACCOUNT_ID_ROWS
         + '\t\tauto label = user->isBot()\n\t\t\t? tr::lng_info_about_label()\n\t\t\t: tr::lng_info_bio_label();\n', 1),
    ])
    patch_age_badge()


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
    # --- account ID + estimated creation month in user profiles
    patch_account_id()
    # --- "Admins" in a group or channel menu, without needing admin rights
    patch_admins()
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
