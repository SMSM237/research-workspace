package org.smsm.papercontrol;
import android.app.job.*;
import android.content.*;
/** A single OS job; never opens Obsidian or a screen from the background. */
public final class PeriodicSync {
 public static final int JOB_ID=71326;
 public static int minutes(Context c){int n=VaultStore.prefs(c).getInt("auto_sync_minutes",15);return n==0||n==15||n==30||n==60?n:15;}
 public static void schedule(Context c){
  JobScheduler jobs=c.getSystemService(JobScheduler.class);if(jobs==null)return;
  int n=minutes(c);if(n==0||!VaultStore.prefs(c).contains("tree")||!SyncBridge.useGitSync(c)){jobs.cancel(JOB_ID);return;}
  JobInfo old=jobs.getPendingJob(JOB_ID);long interval=n*60000L;
  if(old!=null&&old.getIntervalMillis()==interval)return;
  int result=jobs.schedule(new JobInfo.Builder(JOB_ID,new ComponentName(c,PeriodicSyncJob.class)).setPeriodic(interval,Math.min(interval,5*60000L)).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY).setPersisted(true).build());
  VaultStore.prefs(c).edit().putBoolean("auto_sync_scheduled",result==JobScheduler.RESULT_SUCCESS).apply();
 }
 public static void cancel(Context c){JobScheduler jobs=c.getSystemService(JobScheduler.class);if(jobs!=null)jobs.cancel(JOB_ID);}
}
