package org.smsm.papercontrol;
import android.content.*;
public class SyncBootReceiver extends BroadcastReceiver {
 @Override public void onReceive(Context c,Intent i){
  String action=i.getAction();
  if(!Intent.ACTION_BOOT_COMPLETED.equals(action)&&!Intent.ACTION_MY_PACKAGE_REPLACED.equals(action))return;
  PendingResult pending=goAsync();
  new Thread(()->{try{PeriodicSync.schedule(c.getApplicationContext());}finally{pending.finish();}},"widget-sync-schedule").start();
 }
}
