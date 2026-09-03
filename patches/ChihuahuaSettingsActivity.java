package org.telegram.ui;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;

import org.telegram.messenger.BuildVars;
import org.telegram.messenger.ChihuahuaConfig;
import org.telegram.messenger.NotificationsController;
import org.telegram.messenger.UserObject;
import org.telegram.messenger.UserConfig;
import org.telegram.tgnet.TLRPC;
import org.telegram.messenger.browser.Browser;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.BackDrawable;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.UItem;
import org.telegram.ui.Components.UniversalAdapter;
import org.telegram.ui.Components.UniversalRecyclerView;

import java.util.ArrayList;

/** Settings → Chihuahua: the switches for this build's extra features. */
public class ChihuahuaSettingsActivity extends BaseFragment {

    private static final int ID_SHOW_ID = 1;
    private static final int ID_HIDE_STORIES = 2;
    private static final int ID_HIDE_PREMIUM = 3;
    private static final int ID_GHOST_READ = 4;
    private static final int ID_GHOST_TYPING = 5;
    private static final int ID_GHOST_OFFLINE = 6;
    private static final int ID_BACK_CAMERA = 7;
    private static final int ID_ACCOUNT_AGE = 8;
    private static final int ID_FLAG_NEW = 20;
    private static final int ID_QUICK_BAN = 22;
    private static final int ID_KEEP_CONNECTED = 23;
    private static final int ID_NOTIF_STATUS = 24;
    private static final int ID_BATTERY = 25;
    private static final int ID_AGE_ALWAYS = 21;
    /** Threshold rows use ID_MONTHS_BASE + months. */
    private static final int ID_MONTHS_BASE = 200;
    private static final int[] MONTH_CHOICES = {1, 3, 6, 12};
    /** Notification rows use ID_NOTIFY_BASE + account index. */
    private static final int ID_NOTIFY_BASE = 100;
    private static final int ID_VERSION = 10;
    private static final int ID_ACCOUNTS = 11;
    private static final int ID_SOURCE = 12;

    private UniversalRecyclerView listView;

    @Override
    public View createView(Context context) {
        actionBar.setBackButtonDrawable(new BackDrawable(false));
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle("Chihuahua");
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        FrameLayout contentView = new FrameLayout(context);
        contentView.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray, resourceProvider));

        listView = new UniversalRecyclerView(this, this::fillItems, this::onClick, this::onLongClick);
        contentView.addView(listView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT, Gravity.FILL));

        return fragmentView = contentView;
    }

    private void fillItems(ArrayList<UItem> items, UniversalAdapter adapter) {
        items.add(UItem.asHeader("Profiles"));
        items.add(UItem.asCheck(ID_SHOW_ID, "Show user ID under the name").setChecked(ChihuahuaConfig.showIdInProfile()));
        items.add(UItem.asCheck(ID_ACCOUNT_AGE, "Show estimated account age").setChecked(ChihuahuaConfig.showAccountAge()));
        items.add(UItem.asShadow("The ID has its own row in the profile; tap it to copy. Telegram hands out IDs in order, so the ID dates an account to within a month or two (\"est. Nov 2025\") — a brand-new account is a common spam sign. Every profile's ⋮ menu also has Copy ID, Add to Group and Ban from all my groups."));

        items.add(UItem.asHeader("Moderation"));
        items.add(UItem.asCheck(ID_QUICK_BAN, "\"Ban, wipe & report\" on group messages").setChecked(ChihuahuaConfig.quickBan()));
        items.add(UItem.asShadow("Long-press any message in a group you admin: one item bans the sender, deletes every message and reaction of theirs in that group, and reports them to Telegram for spam. Asks once before it does it. Only shown where you have ban rights."));

        items.add(UItem.asHeader("New accounts in groups"));
        items.add(UItem.asCheck(ID_FLAG_NEW, "Flag new accounts on their messages").setChecked(ChihuahuaConfig.flagNewInGroups()));
        items.add(UItem.asCheck(ID_AGE_ALWAYS, "Show age for everyone, not just new").setChecked(ChihuahuaConfig.ageAlwaysInGroups()));
        if (ChihuahuaConfig.flagNewInGroups() || ChihuahuaConfig.ageAlwaysInGroups()) {
            items.add(UItem.asShadow("Count as new when younger than:"));
            for (int months : MONTH_CHOICES) {
                String label = months == 12 ? "1 year" : (months + (months == 1 ? " month" : " months"));
                items.add(UItem.asRadio(ID_MONTHS_BASE + months, label).setChecked(ChihuahuaConfig.flagMonths() == months));
            }
        }
        items.add(UItem.asShadow("In group chats the sender's estimated account age appears next to their name, where Telegram shows the admin label. Accounts under the threshold are red. Handy for spotting throwaway accounts posting promos \u2014 the estimate comes from the user ID, so it works even when the profile is empty."));

        int activated = 0;
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (UserConfig.getInstance(a).isClientActivated()) {
                activated++;
            }
        }
        if (activated > 1) {
            items.add(UItem.asHeader("Notifications"));
            items.add(UItem.asCheck(ID_KEEP_CONNECTED, "Keep every account connected").setChecked(ChihuahuaConfig.keepConnected()));
            items.add(UItem.asButton(ID_NOTIF_STATUS, "Re-apply and refresh"));
            if (!chihuahuaBatteryUnrestricted()) {
                items.add(UItem.asButton(ID_BATTERY, "Stop Android sleeping the app"));
            }
            items.add(UItem.asShadow(ChihuahuaConfig.notificationStatus() + "\n\nThis build cannot use Google push (that needs a Firebase project of Telegram's), so notifications come from Telegram's own background connection. Telegram only applies its Keep-Alive switch to the first account and its Background Connection switch to one account at a time \u2014 this turns both on for every account, every start. Android also has to be told not to sleep the app: hold the icon \u2192 App info \u2192 Battery \u2192 no restrictions, and on Xiaomi/Redmi also turn on Autostart."));
            for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
                UserConfig config = UserConfig.getInstance(a);
                if (!config.isClientActivated()) {
                    continue;
                }
                TLRPC.User user = config.getCurrentUser();
                String name = user == null ? ("Account " + (a + 1)) : UserObject.getUserName(user);
                String subtext = ChihuahuaConfig.notificationsEnabled(a) ? "On" : "Off";
                String username = user == null ? null : UserObject.getPublicUsername(user);
                if (username != null && !username.isEmpty()) {
                    subtext = subtext + " \u00b7 @" + username;
                } else if (user != null && user.phone != null && !user.phone.isEmpty()) {
                    subtext = subtext + " \u00b7 +" + user.phone;
                }
                items.add(UItem.asButtonCheck(ID_NOTIFY_BASE + a, name, subtext).setChecked(ChihuahuaConfig.notificationsEnabled(a)));
            }
            items.add(UItem.asShadow("Switch an account off and it posts no notifications, makes no sound and is left out of the badge count \u2014 the other accounts keep notifying. Messages still arrive; you just see them when you open that account."));
        }

        items.add(UItem.asHeader("Chat list"));
        items.add(UItem.asCheck(ID_HIDE_STORIES, "Hide the Stories bar").setChecked(ChihuahuaConfig.hideStories()));
        items.add(UItem.asShadow("Removes the row of story avatars above the chat list. Stories stay reachable from profiles."));

        items.add(UItem.asHeader("Ghost mode"));
        items.add(UItem.asCheck(ID_GHOST_READ, "Don't send read receipts").setChecked(ChihuahuaConfig.ghostRead()));
        items.add(UItem.asCheck(ID_GHOST_TYPING, "Don't show that I'm typing").setChecked(ChihuahuaConfig.ghostTyping()));
        items.add(UItem.asCheck(ID_GHOST_OFFLINE, "Stay offline").setChecked(ChihuahuaConfig.ghostOffline()));
        items.add(UItem.asShadow("Read receipts: senders never see blue ticks, voice messages never show as played, stories stay unseen. Because Telegram's servers are never told you read anything, unread badges can come back after a restart. Stay offline: your last seen freezes at the last time this was off."));

        items.add(UItem.asHeader("Calls"));
        items.add(UItem.asCheck(ID_BACK_CAMERA, "Start video calls with the back camera").setChecked(ChihuahuaConfig.backCameraDefault()));
        items.add(UItem.asShadow("Applies to video calls and video in group calls. The flip-camera button still works as usual."));

        items.add(UItem.asHeader("Telegram Premium"));
        items.add(UItem.asCheck(ID_HIDE_PREMIUM, "Hide Premium promotions").setChecked(ChihuahuaConfig.hidePremium()));
        items.add(UItem.asShadow("Hides the Premium entry in Settings and most upgrade banners. Premium features you already pay for keep working."));

        items.add(UItem.asHeader("About"));
        items.add(UItem.asButton(ID_VERSION, "Telegram version", BuildVars.BUILD_VERSION_STRING));
        items.add(UItem.asButton(ID_ACCOUNTS, "Account slots", String.valueOf(UserConfig.MAX_ACCOUNT_COUNT)));
        items.add(UItem.asButton(ID_SOURCE, "Build recipe on GitHub"));
        items.add(UItem.asShadow("Chihuahua Telegram is an unofficial build of Telegram for Android and is not affiliated with Telegram."));
    }

    /** True when Android is already leaving this app alone in the background. */
    private boolean chihuahuaBatteryUnrestricted() {
        try {
            Context context = getContext();
            if (context == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {
                return true;
            }
            PowerManager pm = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
            return pm == null || pm.isIgnoringBatteryOptimizations(context.getPackageName());
        } catch (Throwable e) {
            return true;
        }
    }

    private void onClick(UItem item, View view, int position, float x, float y) {
        if (item.id == ID_BATTERY) {
            try {
                Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                intent.setData(Uri.parse("package:" + getContext().getPackageName()));
                getContext().startActivity(intent);
            } catch (Throwable e) {
                try {
                    getContext().startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
                } catch (Throwable ignore) {
                }
            }
            return;
        }
        if (item.id == ID_NOTIF_STATUS) {
            ChihuahuaConfig.applyKeepConnected();
            if (listView != null && listView.adapter != null) {
                listView.adapter.update(true);
            }
            return;
        }
        if (item.id > ID_MONTHS_BASE && item.id <= ID_MONTHS_BASE + 12) {
            ChihuahuaConfig.setFlagMonths(item.id - ID_MONTHS_BASE);
            if (listView != null && listView.adapter != null) {
                listView.adapter.update(true);
            }
            return;
        }
        if (item.id >= ID_NOTIFY_BASE && item.id < ID_NOTIFY_BASE + UserConfig.MAX_ACCOUNT_COUNT) {
            final int account = item.id - ID_NOTIFY_BASE;
            final boolean enabled = !ChihuahuaConfig.notificationsEnabled(account);
            ChihuahuaConfig.setNotificationsEnabled(account, enabled);
            // Drops the notification that is already on screen for a freshly silenced account.
            NotificationsController.getInstance(account).showNotifications();
            if (listView != null && listView.adapter != null) {
                listView.adapter.update(true);
            }
            return;
        }
        if (item.viewType == UniversalAdapter.VIEW_TYPE_CHECK) {
            String key;
            if (item.id == ID_SHOW_ID) {
                key = ChihuahuaConfig.KEY_SHOW_ID;
            } else if (item.id == ID_HIDE_STORIES) {
                key = ChihuahuaConfig.KEY_HIDE_STORIES;
            } else if (item.id == ID_HIDE_PREMIUM) {
                key = ChihuahuaConfig.KEY_HIDE_PREMIUM;
            } else if (item.id == ID_GHOST_READ) {
                key = ChihuahuaConfig.KEY_GHOST_READ;
            } else if (item.id == ID_GHOST_TYPING) {
                key = ChihuahuaConfig.KEY_GHOST_TYPING;
            } else if (item.id == ID_GHOST_OFFLINE) {
                key = ChihuahuaConfig.KEY_GHOST_OFFLINE;
            } else if (item.id == ID_BACK_CAMERA) {
                key = ChihuahuaConfig.KEY_BACK_CAMERA;
            } else if (item.id == ID_ACCOUNT_AGE) {
                key = ChihuahuaConfig.KEY_ACCOUNT_AGE;
            } else if (item.id == ID_KEEP_CONNECTED) {
                key = ChihuahuaConfig.KEY_KEEP_CONNECTED;
            } else if (item.id == ID_QUICK_BAN) {
                key = ChihuahuaConfig.KEY_QUICK_BAN;
            } else if (item.id == ID_FLAG_NEW) {
                key = ChihuahuaConfig.KEY_FLAG_NEW;
            } else if (item.id == ID_AGE_ALWAYS) {
                key = ChihuahuaConfig.KEY_AGE_ALWAYS;
            } else {
                return;
            }
            ChihuahuaConfig.set(key, !ChihuahuaConfig.get(key));
            if (ChihuahuaConfig.KEY_KEEP_CONNECTED.equals(key)) {
                ChihuahuaConfig.applyKeepConnected();
            }
            if (listView != null && listView.adapter != null) {
                listView.adapter.update(true);
            }
        } else if (item.id == ID_SOURCE) {
            Browser.openUrl(getParentActivity(), "https://github.com/chihuahuasignals/chihuahua-telegram");
        }
    }

    private boolean onLongClick(UItem item, View view, int position, float x, float y) {
        return false;
    }
}
