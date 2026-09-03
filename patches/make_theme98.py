#!/usr/bin/env python3
"""Generates chihuahua98.attheme — a Windows 98 colour scheme for Telegram Android.
Keys not listed fall back to Telegram's defaults. Run: python3 make_theme98.py"""
import os

NAVY = "#000080"      # active title bar / highlight
NAVY2 = "#1084D0"     # title bar gradient end (pressed states)
FACE = "#C0C0C0"      # button face / window chrome
SHADOW = "#808080"    # 3D shadow / disabled text
DARK = "#404040"      # dark shadow / secondary text
TEAL = "#008080"      # desktop
WHITE = "#FFFFFF"
BLACK = "#000000"
LINK = "#0000FF"      # classic hyperlink
GREEN = "#008000"
TOOLTIP = "#FFFFE1"   # tooltip yellow
LIGHT = "#E0E0E0"
SKY = "#80D8FF"       # light text on the navy bar (online status)
PRESSED = "#A8A8A8"
FIELD = "#FFFFFF"
# Windows 16-colour palette for avatars / sender names
MAROON, OLIVE, PURPLE, FUCHSIA = "#800000", "#808000", "#800080", "#C000C0"

T = {}
def put(color, *keys):
    for k in keys:
        T[k] = color

# --- action bar (title bar)
put(NAVY, "actionBarDefault", "avatar_backgroundActionBarBlue", "avatar_backgroundInProfileBlue", "actionBarBrowser",
    "chats_menuTopBackground", "chats_menuTopBackgroundCats", "dialogTopBackground", "actionBarDefaultArchived")
put(WHITE, "actionBarDefaultIcon", "actionBarDefaultTitle", "actionBarDefaultSearch", "actionBarTabActiveText", "actionBarTabLine",
    "avatar_actionBarIconBlue", "profile_title", "chats_menuName", "actionBarDefaultArchivedIcon", "actionBarDefaultArchivedTitle",
    "actionBarDefaultArchivedSearch", "chats_tabUnreadActiveBackground")
put(FACE, "actionBarDefaultSubtitle", "actionBarDefaultSearchPlaceholder", "actionBarTabUnactiveText", "avatar_subtitleInProfileBlue",
    "chats_menuPhone", "chats_menuPhoneCats", "chats_tabUnreadUnactiveBackground", "actionBarDefaultSearchArchivedPlaceholder")
put(SKY, "chat_status", "profile_status")   # "online" / "typing…" on the navy chat header and profile header
# profile: navy header (avatar_backgroundActionBarBlue, see customize.py) with grey Win98 button tiles
put(FACE, "profile_actionBackground")
put(PRESSED, "profile_actionPressedBackground")
put(BLACK, "profile_actionIcon")
put(NAVY2, "actionBarDefaultSelector", "actionBarTabSelector", "avatar_actionBarSelectorBlue", "actionBarDefaultArchivedSelector")
put(FACE, "actionBarDefaultSubmenuBackground", "actionBarActionModeDefault")
put(BLACK, "actionBarDefaultSubmenuItem", "actionBarDefaultSubmenuItemIcon", "actionBarActionModeDefaultIcon")
put(SHADOW, "actionBarDefaultSubmenuSeparator", "actionBarActionModeDefaultTop")
put(PRESSED, "actionBarActionModeDefaultSelector", "actionBarWhiteSelector")

# --- windows, lists, text
put(WHITE, "windowBackgroundWhite", "dialogSearchBackground", "chat_emojiSearchBackground", "chat_inBubble", "chat_inBubbleSelected",
    "chat_inAudioProgress", "chat_inFileProgress", "chat_inMediaIcon")
put(FACE, "windowBackgroundGray", "graySection", "dialogBackground", "chats_menuBackground", "chat_messagePanelBackground",
    "chat_topPanelBackground", "chat_emojiPanelBackground", "chat_unreadMessagesStartBackground", "chat_goDownButton",
    "player_background", "inappPlayerBackground", "chat_botKeyboardButtonBackground", "groupcreate_spanBackground",
    "glass_targetMainTabs", "glass_targetMainTopPanel", "chat_outBubble", "chat_outAudioProgress", "chat_outFileProgress",
    "chat_outMediaIcon", "login_progressInner", "contextProgressInner1", "contextProgressInner2", "contextProgressInner3", "contextProgressInner4",
    "chat_attachCheckBoxCheck", "key_sheet_other")
put(PRESSED, "dialogBackgroundGray", "chat_outBubbleSelected", "chat_emojiPanelStickerPackSelector", "chat_botKeyboardButtonBackgroundPressed",
    "chat_inFileBackground", "chat_outFileBackground", "dialogLineProgressBackground", "dialogCheckboxSquareDisabled", "checkboxSquareDisabled")
put(BLACK, "windowBackgroundWhiteBlackText", "dialogTextBlack", "chats_name", "chats_nameArchived", "key_graySectionText", "chats_menuItemText",
    "chats_menuItemIcon", "chat_messageTextIn", "chat_messageTextOut", "chat_inReplyMessageText", "chat_outReplyMessageText",
    "chat_inContactPhoneText", "chat_outContactPhoneText", "chat_inAudioTitleText", "chat_outAudioTitleText", "chat_inFileNameText",
    "chat_outFileNameText", "chat_messagePanelText", "chat_topPanelMessage", "chat_unreadMessagesStartText", "chat_unreadMessagesStartArrowIcon",
    "chat_emojiPanelTrendingTitle", "player_actionBarTitle", "player_actionBarItems", "player_button",
    "inappPlayerTitle", "dialogSearchText", "chat_botKeyboardButtonText", "groupcreate_spanText", "undo_infoColor",
    "glass_tabUnselected", "chat_emojiSearchIcon")
put(DARK, "chats_message", "chats_messageArchived", "chats_message_threeLines", "chat_outTimeText", "chat_outViews",
    "chat_outReplyMediaMessageText", "chat_outAudioDurationText", "chat_outFileInfoText", "chat_outMenu",
    "chat_messagePanelIcons", "chat_topPanelClose", "chat_emojiPanelIcon", "chat_emojiPanelBackspace", "player_actionBarSubtitle",
    "player_time", "inappPlayerClose", "dialogIcon", "dialogTextGray", "dialogTextGray2", "dialogTextGray3", "dialogTextGray4",
    "windowBackgroundWhiteGrayText", "windowBackgroundWhiteGrayText2", "windowBackgroundWhiteGrayText3", "glass_defaultIcon", "glass_defaultText",
    "chat_attachUnactiveTab", "chat_emojiBottomPanelIcon")
put(SHADOW, "divider", "windowBackgroundGrayShadow", "dialogGrayLine", "dialogShadowLine", "chat_messagePanelShadow", "chat_emojiPanelShadowLine",
    "chat_inTimeText", "chat_inViews", "chat_inReplyMediaMessageText", "chat_inAudioDurationText",
    "chat_inFileInfoText", "chat_inMenu", "chats_date", "chats_pinnedIcon", "chats_muteIcon", "chats_unreadCounterMuted",
    "windowBackgroundWhiteGrayText4", "windowBackgroundWhiteGrayText5", "windowBackgroundWhiteGrayText6", "windowBackgroundWhiteGrayText7",
    "windowBackgroundWhiteGrayText8", "windowBackgroundWhiteHintText", "windowBackgroundWhiteGrayIcon", "windowBackgroundWhiteInputField",
    "dialogTextHint", "dialogInputField", "dialogSearchHint", "dialogSearchIcon", "dialogEmptyImage", "dialogEmptyText",
    "emptyListPlaceholder", "fastScrollInactive", "switchTrack", "switchTrackBlue", "switch2Track", "radioBackground", "dialogRadioBackground",
    "checkboxSquareUnchecked", "dialogCheckboxSquareUnchecked", "windowBackgroundUnchecked", "chat_inAudioSeekbar", "chat_outAudioSeekbar",
    "chat_inVoiceSeekbar", "chat_outVoiceSeekbar", "player_progressBackground", "chat_emojiPanelTrendingDescription", "chat_emojiPanelEmptyText",
    "chat_emojiPanelStickerSetName", "picker_disabledButton", "stickers_menu", "groupcreate_hintText",
    "groupcreate_spanDelete", "groupcreate_sectionShadow", "key_sheet_scrollUp", "profile_tabText", "chats_archiveBackground", "chat_inBubbleShadow",
    "featuredStickers_removeButtonText", "chats_menuTopShadow", "chats_menuTopShadowCats", "dialogScrollGlow")
put(DARK, "chat_outBubbleShadow")

# --- accents: navy everywhere the official app is blue
put(NAVY, "windowBackgroundWhiteBlueText", "windowBackgroundWhiteBlueText2", "windowBackgroundWhiteBlueText3", "windowBackgroundWhiteBlueText4",
    "windowBackgroundWhiteBlueText5", "windowBackgroundWhiteBlueText6", "windowBackgroundWhiteBlueText7", "windowBackgroundWhiteBlueHeader",
    "windowBackgroundWhiteBlueButton", "windowBackgroundWhiteBlueIcon", "windowBackgroundWhiteValueText", "windowBackgroundWhiteInputFieldActivated",
    "windowBackgroundChecked", "switchTrackChecked", "switchTrackBlueChecked", "switch2TrackChecked", "checkbox", "radioBackgroundChecked",
    "dialogRadioBackgroundChecked", "checkboxSquareBackground", "dialogCheckboxSquareBackground", "dialogRoundCheckBox", "dialogTextBlue",
    "dialogTextBlue2", "dialogTextBlue4", "dialogInputFieldActivated", "dialogButton",
    "dialogLineProgress", "dialogFloatingButton", "chats_nameMessage", "chats_nameMessageArchived", "chats_nameMessage_threeLines",
    "chats_unreadCounter", "chats_actionBackground", "chats_sentCheck", "chats_sentReadCheck", "chats_verifiedBackground", "chats_attachMessage",
    "chats_menuItemCheck", "chat_inReplyLine", "chat_outReplyLine", "chat_inReplyNameText", "chat_outReplyNameText", "chat_inForwardedNameText",
    "chat_outForwardedNameText", "chat_inViaBotNameText", "chat_outViaBotNameText", "chat_inSiteNameText", "chat_outSiteNameText",
    "chat_inContactNameText", "chat_outContactNameText", "chat_inPreviewLine", "chat_outPreviewLine", "chat_inPreviewInstantText",
    "chat_outPreviewInstantText", "chat_inInstant", "chat_outInstant", "chat_inAudioSeekbarFill", "chat_outAudioSeekbarFill",
    "chat_inVoiceSeekbarFill", "chat_outVoiceSeekbarFill", "chat_inLoader", "chat_outLoader", "chat_inLoaderSelected", "chat_outLoaderSelected",
    "chat_outSentCheck", "chat_outSentCheckRead", "chat_outSentCheckSelected", "chat_outSentCheckReadSelected", "chat_outSentClock",
    "chat_outSentClockSelected", "chat_serviceBackground", "chat_messagePanelSend", "chat_messagePanelCursor", "chat_messagePanelVoiceBackground",
    "chat_topPanelTitle", "chat_topPanelLine", "chat_emojiPanelIconSelected", "chat_emojiPanelStickerPackSelectorLine",
    "chat_emojiPanelStickerSetNameHighlight", "chat_goDownButtonCounterBackground", "chat_attachActiveTab",
    "profile_tabSelectedText", "profile_tabSelectedLine", "profile_verifiedBackground", "profile_creatorIcon",
    "fastScrollActive", "progressCircle", "contextProgressOuter1", "contextProgressOuter2", "contextProgressOuter3", "contextProgressOuter4",
    "player_progress", "player_buttonActive", "inappPlayerPerformer", "inappPlayerPlayPause", "groupcreate_sectionText", "groupcreate_cursor",
    "contacts_inviteBackground", "login_progressOuter", "featuredStickers_addButton", "featuredStickers_addedIcon", "featuredStickers_unread",
    "picker_enabledButton", "picker_badge", "undo_cancelColor", "glass_tabSelected", "glass_tabSelectedText", "telegram_color",
    "avatar_backgroundSaved", "avatar_background2Saved", "chat_serviceBackgroundSelected", "chat_inSentClock", "chat_inSentClockSelected",
    "chats_archivePinBackground", "chat_inPollCorrectAnswer", "chat_outPollCorrectAnswer")
put(NAVY2, "chats_actionPressedBackground", "dialogFloatingButtonPressed", "featuredStickers_addButtonPressed",
    "chat_messagePanelVoicePressed")
put(WHITE, "chats_unreadCounterText", "chats_actionIcon", "chats_verifiedCheck", "chats_mentionIcon", "chats_archiveIcon", "chats_archiveText",
    "profile_verifiedCheck", "dialogFloatingIcon", "dialogRoundCheckBoxCheck", "dialogCheckboxSquareCheck",
    "checkboxSquareCheck", "checkboxCheck", "windowBackgroundCheckText", "chat_serviceText", "chat_serviceLink", "chat_serviceIcon",
    "chat_messagePanelVoiceDuration", "chat_goDownButtonCounter", "contacts_inviteText",
    "featuredStickers_buttonText", "featuredStickers_buttonProgress", "picker_badgeText", "avatar_text", "switchTrackBlueThumbChecked",
    "fastScrollText", "chat_botButtonText", "returnToCallText")
put(FACE, "switchTrackBlueThumb")
put(LINK, "windowBackgroundWhiteLinkText", "dialogTextLink", "chat_messageLinkIn", "chat_messageLinkOut")
put(GREEN, "windowBackgroundWhiteGreenText", "windowBackgroundWhiteGreenText2", "chats_secretName", "chats_secretIcon", "chats_onlineCircle",
    "chat_emojiPanelNewTrending", "returnToCallBackground")
put(TEAL, "chat_wallpaper")
put(TOOLTIP, "undo_background")
put(LIGHT, "chats_pinnedOverlay", "chats_tabletSelectedOverlay", "chat_inReactionButtonBackground", "chat_outReactionButtonBackground")
put(NAVY, "chat_inReactionButtonText", "chat_outReactionButtonText", "chat_inReactionButtonTextSelected", "chat_outReactionButtonTextSelected")

# --- Windows 16-colour avatars and sender names
for shade, col in (("Red", MAROON), ("Orange", OLIVE), ("Violet", PURPLE), ("Green", GREEN), ("Cyan", TEAL), ("Blue", NAVY), ("Pink", FUCHSIA)):
    put(col, f"avatar_background{shade}", f"avatar_background2{shade}", f"avatar_nameInMessage{shade}")
put(SHADOW, "avatar_backgroundArchived", "avatar_backgroundArchivedHidden")

# --- selection / ripple (with alpha)
T["listSelectorSDK21"] = "#26000080"
T["chat_selectedBackground"] = "#4D000080"
T["chat_inTextSelectionHighlight"] = "#5A000080"
T["chat_outTextSelectionHighlight"] = "#5A000080"
T["chat_TextSelectionCursor"] = NAVY
T["chat_messagePanelVoiceDelete"] = "#FF0000"
T["actionBarActionModeDefaultSelector"] = "#33000080"
T["chats_draft"] = "#FF0000"
T["text_RedRegular"] = "#FF0000"
T["text_RedBold"] = "#FF0000"

def argb_to_signed(hexstr):
    h = hexstr.lstrip("#")
    if len(h) == 6:
        h = "FF" + h
    v = int(h, 16)
    return v - (1 << 32) if v >= (1 << 31) else v

here = os.path.dirname(os.path.abspath(__file__))
valid = set(open(os.path.join(here, "theme_keys.txt")).read().split())
unknown = sorted(k for k in T if k not in valid)
if unknown:
    raise SystemExit("unknown theme keys: " + ", ".join(unknown))
lines = [f"{k}={argb_to_signed(v)}" for k, v in sorted(T.items())]
open(os.path.join(here, "chihuahua98.attheme"), "w").write("\n".join(lines) + "\n")
print(f"chihuahua98.attheme: {len(lines)} colours")
