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

    /**
     * Whether a prompt is already on its way or on screen. This is only here to stop two prompts
     * stacking up — it is NOT the "already asked" record, which is per account and lives in
     * ChihuahuaConfig. An earlier version used a once-per-app-start flag for both jobs, and the
     * second account to log in was never asked.
     */
    private static boolean checking;
    private static AlertDialog showing;

    /** From LaunchActivity.onResume: the account currently on screen. */
    public static void checkTwoStepPrompt(Activity activity) {
        checkTwoStepPrompt(activity, UserConfig.selectedAccount);
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
                    .setOnDismissListener(dialog -> showing = null)
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
        if (!ChihuahuaConfig.PROMPT_2FA) {
            return;
        }
        AndroidUtilities.runOnUIThread(() -> checkTwoStepPrompt(LaunchActivity.instance, account), 2500);
    }
}
