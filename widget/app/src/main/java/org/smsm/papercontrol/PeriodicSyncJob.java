package org.smsm.papercontrol;
import android.app.job.*;
public class PeriodicSyncJob extends JobService {
 @Override public boolean onStartJob(JobParameters p){new Thread(()->{
  try{if(PeriodicSync.minutes(this)>0&&VaultStore.prefs(this).contains("tree")){boolean sent=SyncBridge.backgroundSync(this);VaultStore.prefs(this).edit().putLong("auto_sync_checked",System.currentTimeMillis()).putBoolean("auto_sync_sent",sent).apply();}}
  finally{PaperWidget.updateAll(this);jobFinished(p,false);}
 },"widget-periodic-sync").start();return true;}
 @Override public boolean onStopJob(JobParameters p){return false;}
}
