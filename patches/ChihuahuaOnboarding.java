package org.telegram.ui;

import android.app.Activity;
import android.os.Bundle;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ChihuahuaConfig;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.messenger.UserConfig;
import org.telegram.tgnet.ConnectionsManager;
import org.telegram.tgnet.tl.TL_account;
import org.telegram.ui.ActionBar.AlertDialog;

/**
 * What this build does the first time it sees an account after it logs in. Only the offers that
 * need a screen live here - Two-Step Verification, creating a channel - and a build may make
 * either, both or neither (config.env). The settings applied without asking, and the groups
 * joined in the background, are in ChihuahuaConfig.
 */
public class ChihuahuaOnboarding {

    /**
     * Whether a prompt is already on its way or on screen. This is only here to stop two prompts
     * stacking up — it is NOT the "already asked" record, which is per account and lives in
     * ChihuahuaConfig. An earlier version used a once-per-app-start flag for both jobs, and the
     * second account to log in was never asked.
     */
    private static boolean checking;
    private static AlertDialog showing;

    /** From LaunchActivity.onResume: every offer this build makes, for the account on screen. */
    public static void checkPrompts(Activity activity) {
        checkTwoStepPrompt(activity, UserConfig.selectedAccount);
        checkChannelPrompt(activity, UserConfig.selectedAccount);
    }

    /**
     * Offers Two-Step Verification for one account, if this build asks at all, if that account
     * logged in on this build, and if it does not already have a password. Asked once per
     * account: answering either way, or already having a password, stops it coming back.
     */
    public static void checkTwoStepPrompt(Activity activity, int account) {
        if (!ChihuahuaConfig.PROMPT_2FA || activity == null || activity.isFinishing()) {
            return;
        }
        if (checking || showing != null && showing.isShowing()) {
            return;
        }
        if (account < 0 || account >= UserConfig.MAX_ACCOUNT_COUNT) {
            return;
        }
        final UserConfig config = UserConfig.getInstance(account);
        if (!config.isClientActivated() || !ChihuahuaConfig.twoStepPromptPending(account)) {
            return;
        }
        final long userId = config.getClientUserId();
        checking = true;
        ConnectionsManager.getInstance(account).sendRequest(new TL_account.getPassword(), (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            checking = false;
            if (!(response instanceof TL_account.Password)) {
                // Could not tell: leave it pending, and the next start will ask again.
                return;
            }
            final TL_account.Password password = (TL_account.Password) response;
            TwoStepVerificationActivity.initPasswordNewAlgo(password);
            if (password.has_password) {
                ChihuahuaConfig.clearTwoStepPrompt(userId);
                return;
            }
            if (activity.isFinishing()) {
                return;
            }
            try {
                showing = new AlertDialog.Builder(activity)
                    .setTitle(LocaleController.getString(R.string.TwoStepVerification))
                    .setMessage("Add a password to this account, so signing in somewhere new needs the password as well as the SMS code. Without one, anyone who can read the code can take the account.")
                    .setPositiveButton("Set up now", (dialog, which) -> {
                        ChihuahuaConfig.clearTwoStepPrompt(userId);
                        if (LaunchActivity.instance != null) {
                            LaunchActivity.instance.presentFragment(
                                new TwoStepVerificationSetupActivity(TwoStepVerificationSetupActivity.TYPE_INTRO, password));
                        }
                    })
                    .setNegativeButton("Not now", (dialog, which) -> ChihuahuaConfig.clearTwoStepPrompt(userId))
                    .setOnDismissListener(dialog -> {
                        showing = null;
                        checkChannelPrompt(activity, account);
                    })
                    .show();
            } catch (Throwable e) {
                FileLog.e(e);
                showing = null;
            }
        }), ConnectionsManager.RequestFlagFailOnServerErrors | ConnectionsManager.RequestFlagWithoutLogin);
    }

    /**
     * From LoginActivity, once an account is in. Adding an account happens inside LaunchActivity,
     * so onResume does not necessarily fire again — without this, the second account of a session
     * would wait for the app to be backgrounded and reopened before it was asked.
     */
    public static void afterLogin(int account) {
        if (!ChihuahuaConfig.PROMPT_2FA && !ChihuahuaConfig.PROMPT_CHANNEL) {
            return;
        }
        AndroidUtilities.runOnUIThread(() -> {
            if (ChihuahuaConfig.PROMPT_2FA) {
                // ...and the channel offer follows when that dialog closes.
                checkTwoStepPrompt(LaunchActivity.instance, account);
            } else {
                checkChannelPrompt(LaunchActivity.instance, account);
            }
        }, 2500);
    }

    /**
     * Offers to create a channel for one account, if this build asks at all and that account
     * logged in on this build. Asked once per account: answering either way stops it coming
     * back. "Create" opens Telegram's own New Channel screen for that account.
     */
    public static void checkChannelPrompt(Activity activity, int account) {
        if (!ChihuahuaConfig.PROMPT_CHANNEL || activity == null || activity.isFinishing()) {
            return;
        }
        if (checking || showing != null && showing.isShowing()) {
            return;
        }
        if (account < 0 || account >= UserConfig.MAX_ACCOUNT_COUNT) {
            return;
        }
        final UserConfig config = UserConfig.getInstance(account);
        if (!config.isClientActivated() || !ChihuahuaConfig.channelPromptPending(account)) {
            return;
        }
        final long userId = config.getClientUserId();
        try {
            showing = new AlertDialog.Builder(activity)
                .setTitle(LocaleController.getString(R.string.NewChannel))
                .setMessage("Create a new channel for this account?")
                .setPositiveButton("Create", (dialog, which) -> {
                    ChihuahuaConfig.clearChannelPrompt(userId);
                    if (LaunchActivity.instance != null) {
                        final Bundle args = new Bundle();
                        args.putInt("step", 0);
                        final ChannelCreateActivity fragment = new ChannelCreateActivity(args);
                        fragment.setCurrentAccount(account);
                        LaunchActivity.instance.presentFragment(fragment);
                    }
                })
                .setNegativeButton("Not now", (dialog, which) -> ChihuahuaConfig.clearChannelPrompt(userId))
                .setOnDismissListener(dialog -> showing = null)
                .show();
        } catch (Throwable e) {
            FileLog.e(e);
            showing = null;
        }
    }
}
