package org.telegram.ui;

import android.content.Context;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;

import org.telegram.messenger.BuildVars;
import org.telegram.messenger.ChihuahuaConfig;
import org.telegram.messenger.UserConfig;
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
        items.add(UItem.asShadow("Every profile's ⋮ menu also has Copy ID, Add to Group and Ban from all my groups."));

        items.add(UItem.asHeader("Chat list"));
        items.add(UItem.asCheck(ID_HIDE_STORIES, "Hide the Stories bar").setChecked(ChihuahuaConfig.hideStories()));
        items.add(UItem.asShadow("Removes the row of story avatars above the chat list. Stories stay reachable from profiles."));

        items.add(UItem.asHeader("Telegram Premium"));
        items.add(UItem.asCheck(ID_HIDE_PREMIUM, "Hide Premium promotions").setChecked(ChihuahuaConfig.hidePremium()));
        items.add(UItem.asShadow("Hides the Premium entry in Settings and most upgrade banners. Premium features you already pay for keep working."));

        items.add(UItem.asHeader("About"));
        items.add(UItem.asButton(ID_VERSION, "Telegram version", BuildVars.BUILD_VERSION_STRING));
        items.add(UItem.asButton(ID_ACCOUNTS, "Account slots", String.valueOf(UserConfig.MAX_ACCOUNT_COUNT)));
        items.add(UItem.asButton(ID_SOURCE, "Build recipe on GitHub"));
        items.add(UItem.asShadow("Chihuahua Telegram is an unofficial build of Telegram for Android and is not affiliated with Telegram."));
    }

    private void onClick(UItem item, View view, int position, float x, float y) {
        if (item.viewType == UniversalAdapter.VIEW_TYPE_CHECK) {
            String key;
            if (item.id == ID_SHOW_ID) {
                key = ChihuahuaConfig.KEY_SHOW_ID;
            } else if (item.id == ID_HIDE_STORIES) {
                key = ChihuahuaConfig.KEY_HIDE_STORIES;
            } else if (item.id == ID_HIDE_PREMIUM) {
                key = ChihuahuaConfig.KEY_HIDE_PREMIUM;
            } else {
                return;
            }
            ChihuahuaConfig.set(key, !ChihuahuaConfig.get(key));
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
