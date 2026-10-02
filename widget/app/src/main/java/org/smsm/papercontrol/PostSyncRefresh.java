package org.smsm.papercontrol;

import android.app.job.*;
import android.content.*;
import android.os.PersistableBundle;

/** Re-read the selected Vault after a handoff, including slow Git transfers. */
public final class PostSyncRefresh {
 public static final int FIRST_JOB=71325, SECOND_JOB=71327;
 private static final long[] OFFSETS={5000,20000,60000,120000,240000};
 private PostSyncRefresh(){}
 public static synchronized void start(Context c){
  JobScheduler jobs=c.getSystemService(JobScheduler.class);if(jobs==null)return;
  long token=VaultStore.prefs(c).getLong("sync_refresh_token",0)+1;
  VaultStore.prefs(c).edit().putLong("sync_refresh_token",token).putLong("sync_refresh_started",System.currentTimeMillis()).commit();
  jobs.cancel(FIRST_JOB);jobs.cancel(SECOND_JOB);schedule(c,jobs,token,0);
 }
 private static void schedule(Context c,JobScheduler jobs,long token,int step){
  if(step>=OFFSETS.length||token!=VaultStore.prefs(c).getLong("sync_refresh_token",0))return;
  long delay=Math.max(1000,VaultStore.prefs(c).getLong("sync_refresh_started",0)+OFFSETS[step]-System.currentTimeMillis());
  PersistableBundle extras=new PersistableBundle();extras.putLong("token",token);extras.putInt("step",step);
  int result=jobs.schedule(new JobInfo.Builder(step%2==0?FIRST_JOB:SECOND_JOB,new ComponentName(c,RefreshJob.class))
   .setExtras(extras).setMinimumLatency(delay).setOverrideDeadline(delay+30000).setPersisted(true).build());
  VaultStore.prefs(c).edit().putBoolean("sync_refresh_scheduled",result==JobScheduler.RESULT_SUCCESS).apply();
 }
 static boolean current(Context c,JobParameters p){long token=p.getExtras().getLong("token",0);return token>0&&token==VaultStore.prefs(c).getLong("sync_refresh_token",0);}
 static synchronized void next(Context c,JobParameters p){
  if(!current(c,p))return;int step=p.getExtras().getInt("step",0)+1;
  if(step>=OFFSETS.length){VaultStore.prefs(c).edit().putBoolean("sync_refresh_scheduled",false).apply();return;}
  JobScheduler jobs=c.getSystemService(JobScheduler.class);if(jobs!=null)schedule(c,jobs,p.getExtras().getLong("token"),step);
 }
 public static synchronized void cancel(Context c){
  VaultStore.prefs(c).edit().putLong("sync_refresh_token",VaultStore.prefs(c).getLong("sync_refresh_token",0)+1).putBoolean("sync_refresh_scheduled",false).commit();
  JobScheduler jobs=c.getSystemService(JobScheduler.class);if(jobs!=null){jobs.cancel(FIRST_JOB);jobs.cancel(SECOND_JOB);}
 }
}
