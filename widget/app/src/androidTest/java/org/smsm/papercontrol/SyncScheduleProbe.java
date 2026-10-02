package org.smsm.papercontrol;
import android.app.Instrumentation;
import android.app.job.*;
import android.content.*;
import android.os.Bundle;
import java.util.*;
public class SyncScheduleProbe extends Instrumentation {
 private int checks=0;
 private void verify(boolean pass,String message){if(!pass)throw new AssertionError(message);checks++;}
 @Override public void onCreate(Bundle args){super.onCreate(args);start();}
 @Override public void onStart(){
  Bundle result=new Bundle();Context c=getTargetContext();SharedPreferences pref=VaultStore.prefs(c);Map<String,?> saved=pref.getAll();JobScheduler jobs=c.getSystemService(JobScheduler.class);
  try{
   pref.edit().clear().putString("tree","content://qa.documents/tree/vault").putString("sync","gitsync").putInt("repo_index",2).commit();
   verify(PeriodicSync.minutes(c)==15,"default interval");PeriodicSync.schedule(c);JobInfo first=jobs.getPendingJob(PeriodicSync.JOB_ID);
   verify(first!=null&&first.getIntervalMillis()==900000,"real OS job interval");verify(first.isPersisted(),"reboot persistence");verify(first.getNetworkType()==JobInfo.NETWORK_TYPE_ANY,"network constraint");
   PeriodicSync.schedule(c);verify(jobs.getAllPendingJobs().stream().filter(j->j.getId()==PeriodicSync.JOB_ID).count()==1,"unique job");
   pref.edit().putInt("auto_sync_minutes",30).commit();PeriodicSync.schedule(c);verify(jobs.getPendingJob(PeriodicSync.JOB_ID).getIntervalMillis()==1800000,"changed interval");
   pref.edit().putInt("auto_sync_minutes",0).commit();PeriodicSync.schedule(c);verify(jobs.getPendingJob(PeriodicSync.JOB_ID)==null,"disabled cancels");
   final Intent[] sent={null};Context fake=new ContextWrapper(c){@Override public ComponentName startService(Intent i){sent[0]=i;return i.getComponent();}@Override public void startActivity(Intent i){throw new AssertionError("background must not open a screen");}};
   verify(SyncBridge.backgroundSync(fake),"background service dispatch");verify("INTENT_SYNC".equals(sent[0].getAction()),"GitSync action");verify(sent[0].getIntExtra("index",-1)==2,"selected repository");
   verify(!pref.contains("git_completed"),"dispatch never claims Git completion");
   pref.edit().putString("sync","obsidian").putInt("auto_sync_minutes",15).commit();PeriodicSync.schedule(c);verify(jobs.getPendingJob(PeriodicSync.JOB_ID)==null,"no unsupported automatic Obsidian launch");verify(!SyncBridge.backgroundSync(fake),"no foreground fallback");
   pref.edit().putString("sync","gitsync").putLong("git_dispatched",0).commit();Context fail=new ContextWrapper(c){@Override public ComponentName startService(Intent i){throw new IllegalStateException("fixture unavailable");}};
   verify(!SyncBridge.backgroundSync(fail),"dispatch failure reported");verify(pref.getLong("git_failed",0)>0,"failure timestamp persisted");
   result.putString("stream","PASS "+checks+" native scheduler and dispatch checks\n");finish(0,result);
  }catch(Throwable e){result.putString("stream","FAIL "+e+"\n");finish(-1,result);}
  finally{jobs.cancel(PeriodicSync.JOB_ID);PostSyncRefresh.cancel(c);SharedPreferences.Editor edit=pref.edit().clear();for(Map.Entry<String,?> entry:saved.entrySet()){Object v=entry.getValue();String k=entry.getKey();if(v instanceof String)edit.putString(k,(String)v);else if(v instanceof Integer)edit.putInt(k,(Integer)v);else if(v instanceof Long)edit.putLong(k,(Long)v);else if(v instanceof Boolean)edit.putBoolean(k,(Boolean)v);else if(v instanceof Float)edit.putFloat(k,(Float)v);else if(v instanceof Set)edit.putStringSet(k,(Set<String>)v);}edit.commit();}
 }
}
