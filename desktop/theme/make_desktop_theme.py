#!/usr/bin/env python3
"""
Builds ChihuahuaTelegram98.tdesktop-theme -- the Windows 98 palette from the Android build,
translated to Telegram Desktop's colour keys.

A .tdesktop-theme is a zip holding colors.tdesktop-theme (name: #rrggbb; lines) and optionally a
background image. Desktop's key names have nothing in common with Android's, so the light "Day
Blue" palette that ships with tdesktop is used as the base and the keys that carry the look are
overridden -- anything not listed keeps a sensible light-theme value instead of being missing.

Run: python3 make_desktop_theme.py [path-to-day-blue.tdesktop-theme]
"""
import io
import os
import sys
import zipfile

from PIL import Image

NAVY = "#000080"   # active title bar, selection, accents
NAVY2 = "#1084d0"  # title bar gradient end / hover
FACE = "#c0c0c0"   # button face, window chrome, own bubbles
SHADOW = "#808080"
DARK = "#404040"
TEAL = "#008080"   # desktop background -> chat wallpaper
WHITE = "#ffffff"
BLACK = "#000000"
PAPER = "#f0f0f0"  # list surfaces
BODY = "#d4d0c8"   # background between panels
LIGHT = "#e0e0e0"
LINK = "#0000ff"
TOOLTIP = "#ffffe1"

OVERRIDES = {
    # chrome
    "windowBg": PAPER,
    "windowFg": BLACK,
    "windowBgOver": LIGHT,
    "windowBgRipple": FACE,
    "windowSubTextFg": DARK,
    "windowSubTextFgOver": DARK,
    "windowBoldFg": BLACK,
    "windowBoldFgOver": BLACK,
    "windowBgActive": NAVY,
    "windowFgActive": WHITE,
    "windowActiveTextFg": NAVY,
    # title bar: the Windows 98 blue caption
    "titleBg": NAVY,
    "titleBgActive": NAVY,
    "titleFg": FACE,
    "titleFgActive": WHITE,
    "titleButtonFg": FACE,
    "titleButtonFgActive": WHITE,
    "titleButtonBgOver": NAVY2,
    "titleButtonBgActiveOver": NAVY2,
    "titleButtonFgOver": WHITE,
    "titleButtonFgActiveOver": WHITE,
    # chat list
    "dialogsBg": PAPER,
    "dialogsNameFg": BLACK,
    "dialogsTextFg": DARK,
    "dialogsDateFg": SHADOW,
    "dialogsBgOver": LIGHT,
    "dialogsBgActive": NAVY,
    "dialogsNameFgActive": WHITE,
    "dialogsTextFgActive": FACE,
    "dialogsDateFgActive": FACE,
    "dialogsUnreadBg": NAVY,
    "dialogsUnreadFg": WHITE,
    "dialogsUnreadBgMuted": SHADOW,
    "dialogsSearchBg": WHITE,
    # message bubbles: incoming white paper, outgoing button-face grey
    "msgInBg": WHITE,
    "msgInBgSelected": LIGHT,
    "msgOutBg": FACE,
    "msgOutBgSelected": "#a8a8a8",
    "msgInServiceFg": NAVY,
    "msgOutServiceFg": NAVY,
    "msgInDateFg": SHADOW,
    "msgOutDateFg": DARK,
    "msgServiceBg": NAVY,
    "msgServiceFg": WHITE,
    "msgOutReplyBarColor": NAVY,
    "msgInReplyBarColor": NAVY,
    # chat area
    "historyComposeAreaBg": FACE,
    "historyComposeAreaFg": BLACK,
    "historyComposeIconFg": DARK,
    "historyPeerUserpicFg": WHITE,
    "historyScrollBg": LIGHT,
    "historyTextInFg": BLACK,
    "historyTextOutFg": BLACK,
    "historyLinkInFg": LINK,
    "historyLinkOutFg": LINK,
    "historySendIconFg": NAVY,
    # menus, boxes, buttons
    "menuBg": FACE,
    "menuBgOver": LIGHT,
    "menuIconFg": DARK,
    "menuIconFgOver": BLACK,
    "menuSeparatorFg": SHADOW,
    "boxBg": PAPER,
    "boxTextFg": BLACK,
    "boxTitleFg": BLACK,
    "tooltipBg": TOOLTIP,
    "tooltipFg": BLACK,
    "tooltipBorderFg": SHADOW,
    "sideBarBg": NAVY,
    "sideBarBgActive": NAVY2,
    "sideBarTextFg": WHITE,
    "sideBarIconFg": WHITE,
}


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "day-blue.tdesktop-theme"
    if not os.path.exists(base):
        sys.exit(f"base theme not found: {base} (take it from tdesktop's Telegram/Resources)")
    with zipfile.ZipFile(base) as z:
        text = z.read("colors.tdesktop-theme").decode()

    out, applied = [], set()
    for line in text.split("\n"):
        stripped = line.strip()
        if ":" in stripped and not stripped.startswith("//"):
            key = stripped.split(":")[0].strip()
            if key in OVERRIDES:
                out.append(f"{key}: {OVERRIDES[key]};")
                applied.add(key)
                continue
        out.append(line)
    missing = sorted(set(OVERRIDES) - applied)
    if missing:
        out.append("")
        out.append("// keys this build adds that the base palette does not list")
        for key in missing:
            out.append(f"{key}: {OVERRIDES[key]};")

    # teal desktop as the chat wallpaper
    background = io.BytesIO()
    Image.new("RGB", (64, 64), TEAL).save(background, format="PNG")

    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "ChihuahuaTelegram98.tdesktop-theme")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("colors.tdesktop-theme", "\n".join(out))
        z.writestr("tiled.png", background.getvalue())
    print(f"{os.path.basename(target)}: {len(applied)} keys overridden, {len(missing)} added, teal tiled background")


if __name__ == "__main__":
    main()
