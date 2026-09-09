package org.telegram.ui;

import android.content.Context;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;

import androidx.core.view.ViewCompat;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ContactsController;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.Utilities;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.TLObject;
import org.telegram.tgnet.TLRPC;
import org.telegram.tgnet.tl.TL_account;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BackDrawable;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.RadioColorCell;
import org.telegram.ui.Components.AlertsCreator;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.Components.IconBackgroundColors;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.UItem;
import org.telegram.ui.Components.UniversalAdapter;
import org.telegram.ui.Components.UniversalRecyclerView;

import java.util.ArrayList;

/**
 * The Setup tab: the settings worth touching on a freshly logged-in account, all on one page and
 * each changed where it stands. Telegram spreads these over Account settings, Privacy and Security,
 * and Devices.
 */
public class ChihuahuaSetupActivity extends BaseFragment implements NotificationCenter.NotificationCenterDelegate {

    private static final int ID_BIRTHDAY = 1;
    private static final int ID_TWO_STEP = 2;
    private static final int ID_SESSION_TTL = 3;
    private static final int ID_PRIVACY_LASTSEEN = 4;
    private static final int ID_PRIVACY_BIRTHDAY = 5;
    private static final int ID_PRIVACY_INVITES = 6;
    private static final int ID_DELETE_TTL = 7;
    private static final int ID_CONTACTS = 8;
    private static final int ID_PROMO_GROUP = 9;

    /** A group promoted at the top of this page; set from config.env. Empty = no row. */
    private static final String PROMO_GROUP = "%%PROMO_GROUP%%";
    private static final String PROMO_TITLE = "%%PROMO_TITLE%%";

    /** Sessions self-destruct, in days, in the order the picker shows them. */
    private static final int[] SESSION_TTL_DAYS = {7, 90, 183, 365};
    /** Account self-destruct, in days, in the order the picker shows them. */
    private static final int[] DELETE_TTL_DAYS = {30, 90, 182, 365, 548, 730};

    private UniversalRecyclerView listView;

    private boolean hasMainTabs;
    private int additionNavigationBarHeight;
    private int navigationBarHeight;

    private TLRPC.UserFull userFull;
    private TL_account.TL_birthday birthday;

    private TL_account.Password currentPassword;
    private int authTtlDays;

    public ChihuahuaSetupActivity() {
        super();
    }

    public ChihuahuaSetupActivity(Bundle args) {
        super(args);
    }

    @Override
    public boolean onFragmentCreate() {
        if (arguments != null) {
            hasMainTabs = arguments.getBoolean("hasMainTabs", false);
        }
        additionNavigationBarHeight = hasMainTabs ? AndroidUtilities.dp(DialogsActivity.MAIN_TABS_HEIGHT_WITH_MARGINS) : 0;

        getNotificationCenter().addObserver(this, NotificationCenter.privacyRulesUpdated);
        getNotificationCenter().addObserver(this, NotificationCenter.userInfoDidLoad);
        getNotificationCenter().addObserver(this, NotificationCenter.twoStepPasswordChanged);

        getContactsController().loadPrivacySettings();
        loadUserInfo();
        loadPassword();
        loadSessionTtl();
        return super.onFragmentCreate();
    }

    @Override
    public void onFragmentDestroy() {
        getNotificationCenter().removeObserver(this, NotificationCenter.privacyRulesUpdated);
        getNotificationCenter().removeObserver(this, NotificationCenter.userInfoDidLoad);
        getNotificationCenter().removeObserver(this, NotificationCenter.twoStepPasswordChanged);
        super.onFragmentDestroy();
    }

    @Override
    public void didReceivedNotification(int id, int account, Object... args) {
        if (id == NotificationCenter.userInfoDidLoad) {
            final Long uid = (Long) args[0];
            if (uid == null || uid != getUserConfig().getClientUserId()) {
                return;
            }
            readUserInfo();
            update();
        } else if (id == NotificationCenter.twoStepPasswordChanged) {
            loadPassword();
        } else {
            update();
        }
    }

    @Override
    public View createView(Context context) {
        actionBar.setAllowOverlayTitle(true);
        actionBar.setTitle("Setup");
        if (!hasMainTabs) {
            actionBar.setBackButtonDrawable(new BackDrawable(false));
        }
        actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() {
            @Override
            public void onItemClick(int id) {
                if (id == -1) {
                    finishFragment();
                }
            }
        });

        final FrameLayout contentView = new FrameLayout(context);
        contentView.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray, resourceProvider));

        listView = new UniversalRecyclerView(this, this::fillItems, this::onClick, null);
        listView.setSections();
        listView.setClipToPadding(false);
        contentView.addView(listView, LayoutHelper.createFrame(LayoutHelper.MATCH_PARENT, LayoutHelper.MATCH_PARENT, Gravity.FILL));

        fragmentView = contentView;
        ViewCompat.setOnApplyWindowInsetsListener(fragmentView, this::onInsetsInternal);
        updatePadding();
        readUserInfo();
        return fragmentView;
    }

    @Override
    public boolean isSupportEdgeToEdge() {
        return true;
    }

    @Override
    public void onInsets(int left, int top, int right, int bottom) {
        navigationBarHeight = bottom;
        updatePadding();
    }

    private void updatePadding() {
        if (listView == null) {
            return;
        }
        final int top = ActionBar.getCurrentActionBarHeight()
            + (actionBar != null && actionBar.getOccupyStatusBar() ? AndroidUtilities.statusBarHeight : 0);
        listView.setPadding(0, top, 0, navigationBarHeight + additionNavigationBarHeight + AndroidUtilities.dp(8));
    }

    private void update() {
        if (listView != null && listView.adapter != null) {
            listView.adapter.update(true);
        }
    }

    /* ------------------------------------------------------------------ the page */

    private void fillItems(ArrayList<UItem> items, UniversalAdapter adapter) {
        if (!PROMO_GROUP.isEmpty()) {
            items.add(SettingsActivity.SettingCell.Factory.of(
                ID_PROMO_GROUP, IconBackgroundColors.BLUE_DEEP.top, IconBackgroundColors.BLUE_DEEP.bottom, R.drawable.msg_discussion,
                PROMO_TITLE, null, promoJoined() ? "Open" : "Join"));
            items.add(UItem.asShadow(null));
        }

        items.add(UItem.asHeader("Security"));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_TWO_STEP, IconBackgroundColors.GREEN.top, IconBackgroundColors.GREEN.bottom,
            currentPassword != null && currentPassword.has_password ? R.drawable.menu_2sv_on : R.drawable.menu_2sv,
            LocaleController.getString(R.string.TwoStepVerification), null, twoStepValue()));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_SESSION_TTL, IconBackgroundColors.CYAN.top, IconBackgroundColors.CYAN.bottom, R.drawable.settings_devices,
            "Terminate old sessions", "if inactive for", sessionTtlValue()));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_DELETE_TTL, IconBackgroundColors.RED.top, IconBackgroundColors.RED.bottom, R.drawable.msg_delete,
            "Delete my account", "if away for", deleteTtlValue()));
        items.add(UItem.asShadow("Two-Step Verification asks for a password as well as the SMS code when this account signs in somewhere new. The other two are Telegram's own timers: a session nobody uses is logged out, and an account nobody comes back to is deleted."));

        items.add(UItem.asHeader("Your info"));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_BIRTHDAY, IconBackgroundColors.BLUE.top, IconBackgroundColors.BLUE.bottom, R.drawable.filled_birthday,
            LocaleController.getString(R.string.ContactBirthday), null,
            birthday == null ? LocaleController.getString(R.string.AddBirthday) : UserInfoActivity.birthdayString(birthday)));
        items.add(UItem.asShadow("Saved as soon as you pick it. Who can see it is Date of Birth below."));

        items.add(UItem.asHeader("Privacy"));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_PRIVACY_LASTSEEN, IconBackgroundColors.BLUE_LIGHT.top, IconBackgroundColors.BLUE_LIGHT.bottom, R.drawable.msg_seen,
            LocaleController.getString(R.string.PrivacyLastSeen), null, privacyValue(ContactsController.PRIVACY_RULES_TYPE_LASTSEEN)));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_PRIVACY_BIRTHDAY, IconBackgroundColors.PURPLE.top, IconBackgroundColors.PURPLE.bottom, R.drawable.filled_birthday,
            LocaleController.getString(R.string.PrivacyBirthday), null, privacyValue(ContactsController.PRIVACY_RULES_TYPE_BIRTHDAY)));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_PRIVACY_INVITES, IconBackgroundColors.ORANGE.top, IconBackgroundColors.ORANGE.bottom, R.drawable.msg_groups,
            LocaleController.getString(R.string.PrivacyInvites), null, privacyValue(ContactsController.PRIVACY_RULES_TYPE_INVITE)));
        items.add(UItem.asShadow("Each applies the moment you pick it. Invites decides who may add this account to groups and channels. Exception lists you have already set are kept."));

        items.add(UItem.asHeader("More"));
        items.add(SettingsActivity.SettingCell.Factory.of(
            ID_CONTACTS, IconBackgroundColors.GRAY.top, IconBackgroundColors.GRAY.bottom, R.drawable.msg_contacts,
            LocaleController.getString(R.string.Contacts)));
        items.add(UItem.asShadow("The contact list this tab used to hold. Everything else is in the Settings tab."));
    }

    private void onClick(UItem item, View view, int position, float x, float y) {
        if (item.id == ID_BIRTHDAY) {
            openBirthdayPicker();
        } else if (item.id == ID_TWO_STEP) {
            openTwoStep();
        } else if (item.id == ID_SESSION_TTL) {
            openSessionTtl();
        } else if (item.id == ID_PRIVACY_LASTSEEN) {
            openPrivacy(ContactsController.PRIVACY_RULES_TYPE_LASTSEEN, LocaleController.getString(R.string.PrivacyLastSeen));
        } else if (item.id == ID_PRIVACY_BIRTHDAY) {
            openPrivacy(ContactsController.PRIVACY_RULES_TYPE_BIRTHDAY, LocaleController.getString(R.string.PrivacyBirthday));
        } else if (item.id == ID_PRIVACY_INVITES) {
            openPrivacy(ContactsController.PRIVACY_RULES_TYPE_INVITE, LocaleController.getString(R.string.PrivacyInvites));
        } else if (item.id == ID_DELETE_TTL) {
            openDeleteTtl();
        } else if (item.id == ID_CONTACTS) {
            final Bundle args = new Bundle();
            args.putBoolean("needPhonebook", true);
            presentFragment(new ContactsActivity(args));
        } else if (item.id == ID_PROMO_GROUP) {
            // Opens the group; joining is Telegram's own button at the bottom of the chat.
            getMessagesController().openByUserName(PROMO_GROUP, this, 1);
        }
    }

    /* ------------------------------------------------------------------ the promoted group */

    /** Only true when this account is known to be in the group — never guesses the other way. */
    private boolean promoJoined() {
        if (PROMO_GROUP.isEmpty()) {
            return false;
        }
        final TLObject object = getMessagesController().getUserOrChat(PROMO_GROUP);
        if (!(object instanceof TLRPC.Chat)) {
            return false;
        }
        final TLRPC.Chat chat = (TLRPC.Chat) object;
        return !chat.left && !chat.kicked;
    }

    /* ------------------------------------------------------------------ birthday */

    private void loadUserInfo() {
        final TLRPC.User user = getUserConfig().getCurrentUser();
        if (user != null) {
            getMessagesController().loadFullUser(user, classGuid, true);
        }
        readUserInfo();
    }

    private void readUserInfo() {
        userFull = getMessagesController().getUserFull(getUserConfig().getClientUserId());
        if (userFull != null) {
            birthday = userFull.birthday;
        }
    }

    private void openBirthdayPicker() {
        if (getContext() == null) {
            return;
        }
        showDialog(AlertsCreator.createBirthdayPickerDialog(
            getContext(),
            LocaleController.getString(R.string.EditProfileBirthdayTitle),
            LocaleController.getString(R.string.EditProfileBirthdayButton),
            birthday,
            this::saveBirthday,
            null,
            false, birthday != null, getResourceProvider()
        ).create());
    }

    private void saveBirthday(TL_account.TL_birthday selected) {
        if (userFull == null) {
            userFull = getMessagesController().getUserFull(getUserConfig().getClientUserId());
        }
        final TLRPC.UserFull full = userFull;
        final TL_account.TL_birthday old = birthday;
        final TL_account.updateBirthday req = new TL_account.updateBirthday();
        if (selected != null) {
            req.flags |= 1;
            req.birthday = selected;
        }
        birthday = selected;
        if (full != null) {
            if (selected != null) {
                full.flags2 |= 32;
            } else {
                full.flags2 &= ~32;
            }
            full.birthday = selected;
        }
        update();
        getConnectionsManager().sendRequest(req, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (error != null || response instanceof TLRPC.TL_boolFalse) {
                birthday = old;
                if (full != null) {
                    if (old != null) {
                        full.flags2 |= 32;
                    } else {
                        full.flags2 &= ~32;
                    }
                    full.birthday = old;
                }
                if (error != null && error.text != null && error.text.startsWith("FLOOD_WAIT_") && getContext() != null) {
                    showDialog(new AlertDialog.Builder(getContext(), getResourceProvider())
                        .setTitle(LocaleController.getString(R.string.PrivacyBirthdayTooOftenTitle))
                        .setMessage(LocaleController.getString(R.string.PrivacyBirthdayTooOftenMessage))
                        .setPositiveButton(LocaleController.getString(R.string.OK), null)
                        .create());
                } else if (error != null) {
                    BulletinFactory.showError(error);
                }
                update();
                return;
            }
            if (full != null) {
                getMessagesStorage().updateUserInfo(full, false);
                getNotificationCenter().postNotificationName(NotificationCenter.userInfoDidLoad, getUserConfig().getClientUserId(), full);
            }
            getMessagesController().invalidateContentSettings();
            update();
        }), ConnectionsManager.RequestFlagFailOnServerErrors);
    }

    /* ------------------------------------------------------------------ two-step verification */

    private void loadPassword() {
        getConnectionsManager().sendRequest(new TL_account.getPassword(), (response, error) -> {
            if (response instanceof TL_account.Password) {
                final TL_account.Password password = (TL_account.Password) response;
                AndroidUtilities.runOnUIThread(() -> {
                    currentPassword = password;
                    TwoStepVerificationActivity.initPasswordNewAlgo(currentPassword);
                    update();
                });
            }
        }, ConnectionsManager.RequestFlagFailOnServerErrors | ConnectionsManager.RequestFlagWithoutLogin);
    }

    private String twoStepValue() {
        if (currentPassword == null) {
            return "";
        }
        return LocaleController.getString(currentPassword.has_password ? R.string.PasswordOn : R.string.PasswordOff);
    }

    private void openTwoStep() {
        if (currentPassword == null) {
            loadPassword();
            return;
        }
        if (!TwoStepVerificationActivity.canHandleCurrentPassword(currentPassword, false)) {
            AlertsCreator.showUpdateAppAlert(getParentActivity(), LocaleController.getString(R.string.UpdateAppAlert), true);
            return;
        }
        if (currentPassword.has_password) {
            final TwoStepVerificationActivity fragment = new TwoStepVerificationActivity();
            fragment.setPassword(currentPassword);
            presentFragment(fragment);
        } else {
            final int type = TextUtils.isEmpty(currentPassword.email_unconfirmed_pattern)
                ? TwoStepVerificationSetupActivity.TYPE_INTRO
                : TwoStepVerificationSetupActivity.TYPE_EMAIL_CONFIRM;
            presentFragment(new TwoStepVerificationSetupActivity(type, currentPassword));
        }
    }

    /* ------------------------------------------------------------------ sessions self-destruct */

    private void loadSessionTtl() {
        getConnectionsManager().sendRequest(new TL_account.getAuthorizations(), (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (response instanceof TL_account.authorizations) {
                authTtlDays = ((TL_account.authorizations) response).authorization_ttl_days;
                update();
            }
        }));
    }

    private String sessionTtlValue() {
        if (authTtlDays <= 0) {
            return "";
        }
        if (authTtlDays > 30 && authTtlDays <= 183) {
            return LocaleController.formatPluralString("Months", authTtlDays / 30);
        }
        if (authTtlDays >= 365) {
            return LocaleController.formatPluralString("Years", authTtlDays / 365);
        }
        return LocaleController.formatPluralString("Weeks", authTtlDays / 7);
    }

    private void openSessionTtl() {
        int selected = 3;
        if (authTtlDays <= 7) {
            selected = 0;
        } else if (authTtlDays <= 93) {
            selected = 1;
        } else if (authTtlDays <= 183) {
            selected = 2;
        }
        final String[] items = new String[]{
            LocaleController.formatPluralString("Weeks", 1),
            LocaleController.formatPluralString("Months", 3),
            LocaleController.formatPluralString("Months", 6),
            LocaleController.formatPluralString("Years", 1)
        };
        showChoice(LocaleController.getString(R.string.SessionsSelfDestruct), items, selected, which -> {
            final int value = SESSION_TTL_DAYS[which];
            final int old = authTtlDays;
            authTtlDays = value;
            update();
            final TL_account.setAuthorizationTTL req = new TL_account.setAuthorizationTTL();
            req.authorization_ttl_days = value;
            getConnectionsManager().sendRequest(req, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
                if (error != null) {
                    authTtlDays = old;
                    BulletinFactory.showError(error);
                    update();
                }
            }), ConnectionsManager.RequestFlagFailOnServerErrors);
        });
    }

    /* ------------------------------------------------------------------ account self-destruct */

    private String deleteTtlValue() {
        if (getContactsController().getLoadingDeleteInfo()) {
            return "";
        }
        final int ttl = getContactsController().getDeleteAccountTTL();
        if (ttl <= 182) {
            return LocaleController.formatPluralString("Months", ttl / 30);
        }
        if (ttl == 365) {
            return LocaleController.formatPluralString("Months", 12);
        }
        if (ttl == 548) {
            return LocaleController.formatPluralString("Months", 18);
        }
        if (ttl == 730) {
            return LocaleController.formatPluralString("Months", 24);
        }
        if (ttl > 30) {
            return LocaleController.formatPluralString("Months", (int) Math.round(ttl / 30.0));
        }
        return LocaleController.formatPluralString("Days", ttl);
    }

    private void openDeleteTtl() {
        final int ttl = getContactsController().getDeleteAccountTTL();
        int selected = 3;
        if (ttl <= 31) {
            selected = 0;
        } else if (ttl <= 93) {
            selected = 1;
        } else if (ttl <= 182) {
            selected = 2;
        } else if (ttl == 548) {
            selected = 4;
        } else if (ttl == 730) {
            selected = 5;
        }
        final String[] items = new String[]{
            LocaleController.formatPluralString("Months", 1),
            LocaleController.formatPluralString("Months", 3),
            LocaleController.formatPluralString("Months", 6),
            LocaleController.formatPluralString("Months", 12),
            LocaleController.formatPluralString("Months", 18),
            LocaleController.formatPluralString("Months", 24)
        };
        showChoice(LocaleController.getString(R.string.DeleteAccountTitle), items, selected, which -> {
            final TL_account.setAccountTTL req = new TL_account.setAccountTTL();
            req.ttl = new TLRPC.TL_accountDaysTTL();
            req.ttl.days = DELETE_TTL_DAYS[which];
            getConnectionsManager().sendRequest(req, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
                if (response instanceof TLRPC.TL_boolTrue) {
                    getContactsController().setDeleteAccountTTL(req.ttl.days);
                } else if (error != null) {
                    BulletinFactory.showError(error);
                }
                update();
            }), ConnectionsManager.RequestFlagFailOnServerErrors);
        });
    }

    /* ------------------------------------------------------------------ privacy rules */

    private String privacyValue(int rulesType) {
        if (getContactsController().getLoadingPrivacyInfo(rulesType)) {
            return "";
        }
        return PrivacySettingsActivity.formatRulesString(getAccountInstance(), rulesType);
    }

    /** 0 = everybody, 1 = my contacts, 2 = nobody — which of the three the account is on now. */
    private int privacyChoice(int rulesType) {
        final ArrayList<TLRPC.PrivacyRule> rules = getContactsController().getPrivacyRules(rulesType);
        if (rules == null) {
            return 2;
        }
        for (int a = 0; a < rules.size(); a++) {
            final TLRPC.PrivacyRule rule = rules.get(a);
            if (rule instanceof TLRPC.TL_privacyValueAllowAll) {
                return 0;
            }
            if (rule instanceof TLRPC.TL_privacyValueAllowContacts) {
                return 1;
            }
            if (rule instanceof TLRPC.TL_privacyValueDisallowAll) {
                return 2;
            }
        }
        return 2;
    }

    private void openPrivacy(int rulesType, String title) {
        final String[] items = new String[]{
            LocaleController.getString(R.string.LastSeenEverybody),
            LocaleController.getString(R.string.LastSeenContacts),
            LocaleController.getString(R.string.LastSeenNobody)
        };
        showChoice(title, items, privacyChoice(rulesType), which -> applyPrivacy(rulesType, which));
    }

    private void applyPrivacy(int rulesType, int choice) {
        final TL_account.setPrivacy req = new TL_account.setPrivacy();
        if (rulesType == ContactsController.PRIVACY_RULES_TYPE_LASTSEEN) {
            req.key = new TLRPC.TL_inputPrivacyKeyStatusTimestamp();
        } else if (rulesType == ContactsController.PRIVACY_RULES_TYPE_BIRTHDAY) {
            req.key = new TLRPC.TL_inputPrivacyKeyBirthday();
        } else if (rulesType == ContactsController.PRIVACY_RULES_TYPE_INVITE) {
            req.key = new TLRPC.TL_inputPrivacyKeyChatInvite();
        } else {
            return;
        }
        // Whatever exceptions are already set stay set; only everybody/contacts/nobody changes here.
        boolean premium = false;
        boolean allowBots = false;
        boolean disallowBots = false;
        final ArrayList<TLRPC.PrivacyRule> current = getContactsController().getPrivacyRules(rulesType);
        if (current != null) {
            for (int a = 0; a < current.size(); a++) {
                final TLRPC.PrivacyRule rule = current.get(a);
                if (rule instanceof TLRPC.TL_privacyValueAllowUsers) {
                    final TLRPC.TL_inputPrivacyValueAllowUsers out = new TLRPC.TL_inputPrivacyValueAllowUsers();
                    copyUsers(((TLRPC.TL_privacyValueAllowUsers) rule).users, out.users);
                    if (!out.users.isEmpty()) {
                        req.rules.add(out);
                    }
                } else if (rule instanceof TLRPC.TL_privacyValueDisallowUsers) {
                    final TLRPC.TL_inputPrivacyValueDisallowUsers out = new TLRPC.TL_inputPrivacyValueDisallowUsers();
                    copyUsers(((TLRPC.TL_privacyValueDisallowUsers) rule).users, out.users);
                    if (!out.users.isEmpty()) {
                        req.rules.add(out);
                    }
                } else if (rule instanceof TLRPC.TL_privacyValueAllowChatParticipants) {
                    final TLRPC.TL_inputPrivacyValueAllowChatParticipants out = new TLRPC.TL_inputPrivacyValueAllowChatParticipants();
                    out.chats.addAll(((TLRPC.TL_privacyValueAllowChatParticipants) rule).chats);
                    if (!out.chats.isEmpty()) {
                        req.rules.add(out);
                    }
                } else if (rule instanceof TLRPC.TL_privacyValueDisallowChatParticipants) {
                    final TLRPC.TL_inputPrivacyValueDisallowChatParticipants out = new TLRPC.TL_inputPrivacyValueDisallowChatParticipants();
                    out.chats.addAll(((TLRPC.TL_privacyValueDisallowChatParticipants) rule).chats);
                    if (!out.chats.isEmpty()) {
                        req.rules.add(out);
                    }
                } else if (rule instanceof TLRPC.TL_privacyValueAllowPremium) {
                    premium = true;
                } else if (rule instanceof TLRPC.TL_privacyValueAllowBots) {
                    allowBots = true;
                } else if (rule instanceof TLRPC.TL_privacyValueDisallowBots) {
                    disallowBots = true;
                }
            }
        }
        if (choice == 0) {
            req.rules.add(new TLRPC.TL_inputPrivacyValueAllowAll());
        } else if (choice == 1) {
            req.rules.add(new TLRPC.TL_inputPrivacyValueAllowContacts());
        } else {
            req.rules.add(new TLRPC.TL_inputPrivacyValueDisallowAll());
        }
        if (premium && choice != 0) {
            req.rules.add(new TLRPC.TL_inputPrivacyValueAllowPremium());
        }
        if (choice == 0) {
            if (disallowBots) {
                req.rules.add(new TLRPC.TL_inputPrivacyValueDisallowBots());
            }
        } else if (allowBots) {
            req.rules.add(new TLRPC.TL_inputPrivacyValueAllowBots());
        }
        getConnectionsManager().sendRequest(req, (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (response instanceof TL_account.privacyRules) {
                final TL_account.privacyRules rules = (TL_account.privacyRules) response;
                getMessagesController().putUsers(rules.users, false);
                getMessagesController().putChats(rules.chats, false);
                getContactsController().setPrivacyRules(rules.rules, rulesType);
            } else if (error != null) {
                BulletinFactory.showError(error);
            }
            update();
        }), ConnectionsManager.RequestFlagFailOnServerErrors);
    }

    private void copyUsers(ArrayList<Long> from, ArrayList<TLRPC.InputUser> to) {
        for (int a = 0; a < from.size(); a++) {
            final TLRPC.InputUser inputUser = getMessagesController().getInputUser(from.get(a));
            if (inputUser != null && !(inputUser instanceof TLRPC.TL_inputUserEmpty)) {
                to.add(inputUser);
            }
        }
    }

    /* ------------------------------------------------------------------ the radio-list dialog */

    private void showChoice(String title, String[] items, int selected, Utilities.Callback<Integer> whenChosen) {
        if (getParentActivity() == null) {
            return;
        }
        final AlertDialog.Builder builder = new AlertDialog.Builder(getParentActivity(), getResourceProvider());
        builder.setTitle(title);
        final LinearLayout linearLayout = new LinearLayout(getParentActivity());
        linearLayout.setOrientation(LinearLayout.VERTICAL);
        builder.setView(linearLayout);
        for (int a = 0; a < items.length; a++) {
            final RadioColorCell cell = new RadioColorCell(getParentActivity());
            cell.setPadding(AndroidUtilities.dp(4), 0, AndroidUtilities.dp(4), 0);
            cell.setTag(a);
            cell.setCheckColor(Theme.getColor(Theme.key_radioBackground), Theme.getColor(Theme.key_dialogRadioBackgroundChecked));
            cell.setTextAndValue(items[a], selected == a);
            cell.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), Theme.RIPPLE_MASK_ALL));
            linearLayout.addView(cell);
            cell.setOnClickListener(v -> {
                builder.getDismissRunnable().run();
                whenChosen.run((Integer) v.getTag());
            });
        }
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        showDialog(builder.create());
    }
}
