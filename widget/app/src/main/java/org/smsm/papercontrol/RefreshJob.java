package org.smsm.papercontrol;
public class RefreshJob extends android.app.job.JobService {
 private final java.util.Map<android.app.job.JobParameters,java.util.concurrent.atomic.AtomicBoolean> runs=new java.util.concurrent.ConcurrentHashMap<>();
 @Override public boolean onStartJob(android.app.job.JobParameters p){java.util.concurrent.atomic.AtomicBoolean stopped=new java.util.concurrent.atomic.AtomicBoolean();runs.put(p,stopped);new Thread(()->{
  try{if(PostSyncRefresh.current(this,p)&&!stopped.get()){
   PaperWidget.updateAll(this);
   if(PostSyncRefresh.current(this,p)&&!stopped.get())VaultStore.prefs(this).edit()
    .putLong("sync_refresh_last_token",p.getExtras().getLong("token",0))
    .putInt("sync_refresh_last_step",p.getExtras().getInt("step",0))
    .putLong("sync_refresh_last_run",System.currentTimeMillis()).apply();
  }}
  finally{runs.remove(p);if(!stopped.get()){jobFinished(p,false);PostSyncRefresh.next(this,p);}}
 },"widget-refresh").start();return true;}
 @Override public boolean onStopJob(android.app.job.JobParameters p){java.util.concurrent.atomic.AtomicBoolean stopped=runs.remove(p);if(stopped!=null)stopped.set(true);return PostSyncRefresh.current(this,p);}
}
