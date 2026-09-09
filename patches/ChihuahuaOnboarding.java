package org.telegram.ui;

import android.app.Activity;

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
 * What this build does the first time it sees an account after it logs in. Only the offer of
 * Two-Step Verification needs a screen, so only that lives here; the settings applied without
 * asking, and the groups joined in the background, are in ChihuahuaConfig.
 */
public class ChihuahuaOnboarding {

    /** One prompt per app start, however many times LaunchActivity resumes. */
    private static boolean askedThisSession;

    /**
     * Offers Two-Step Verification to the account on screen, if this build asks at all, if that
     * account logged in on this build, and if it does not already have a password. Asked once:
     * answering either way, or already having a password, stops it coming back.
     */
    public static void checkTwoStepPrompt(Activity activity) {
        if (!ChihuahuaConfig.PROMPT_2FA || askedThisSession || activity == null || activity.isFinishing()) {
            return;
        }
        final int account = UserConfig.selectedAccount;
        final UserConfig config = UserConfig.getInstance(account);
        if (!config.isClientActivated() || !ChihuahuaConfig.twoStepPromptPending(account)) {
            return;
        }
        askedThisSession = true;
        final long userId = config.getClientUserId();
        ConnectionsManager.getInstance(account).sendRequest(new TL_account.getPassword(), (response, error) -> AndroidUtilities.runOnUIThread(() -> {
            if (!(response instanceof TL_account.Password)) {
                // Could not tell — leave it pending and try again next start.
                askedThisSession = false;
                return;
            }
            final TL_account.Password password = (TL_account.Password) response;
            TwoStepVerificationActivity.initPasswordNewAlgo(password);
            if (password.has_password) {
                ChihuahuaConfig.clearTwoStepPrompt(userId);
                return;
            }
            if (activity.isFinishing() || UserConfig.selectedAccount != account) {
                askedThisSession = false;
                return;
            }
            try {
                new AlertDialog.Builder(activity)
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
                    .show();
            } catch (Throwable e) {
                FileLog.e(e);
                askedThisSession = false;
            }
        }), ConnectionsManager.RequestFlagFailOnServerErrors | ConnectionsManager.RequestFlagWithoutLogin);
    }
}
