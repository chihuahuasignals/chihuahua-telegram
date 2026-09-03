package org.telegram.messenger;

import android.app.Notification;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;

import androidx.core.app.NotificationCompat;

import org.telegram.ui.LaunchActivity;

/**
 * Keeps this build's own connection to Telegram open, because it cannot use Google push.
 *
 * Telegram ships this as a plain background Service, which Android 8 and later stop within about a
 * minute of the app leaving the screen. That is fine for the official app, which Firebase wakes up,
 * but useless here: with no push, a stopped connection means no notification until the app is
 * opened again. It is a real foreground service now, with a quiet ongoing notification, declared
 * "specialUse" in the manifest so that it escapes the six-hour daily cap Android 15 puts on
 * "dataSync" services.
 */
public class NotificationsService extends Service {

    private static final int NOTIFICATION_ID = 38154;

    @Override
    public void onCreate() {
        super.onCreate();
        ApplicationLoader.postInitApplication();
        startForegroundNotification();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForegroundNotification();
        return START_STICKY;
    }

    private void startForegroundNotification() {
        try {
            Intent open = new Intent(ApplicationLoader.applicationContext, LaunchActivity.class);
            open.addCategory(Intent.CATEGORY_LAUNCHER);
            final PendingIntent contentIntent = PendingIntent.getActivity(
                    ApplicationLoader.applicationContext, 0, open,
                    PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

            NotificationsController.checkOtherNotificationsChannel();
            final NotificationCompat.Builder builder =
                    new NotificationCompat.Builder(this, NotificationsController.OTHER_NOTIFICATIONS_CHANNEL)
                            .setSmallIcon(R.drawable.notification)
                            .setContentTitle(LocaleController.getString(R.string.AppName))
                            .setContentText("Connected — notifications are working")
                            .setContentIntent(contentIntent)
                            .setOngoing(true)
                            .setShowWhen(false)
                            .setPriority(NotificationCompat.PRIORITY_MIN);

            final Notification notification = builder.build();
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        SharedPreferences preferences = MessagesController.getGlobalNotificationsSettings();
        if (preferences.getBoolean("pushService", true)) {
            Intent intent = new Intent("org.telegram.start");
            intent.setPackage(getPackageName());
            sendBroadcast(intent);
        }
    }
}
