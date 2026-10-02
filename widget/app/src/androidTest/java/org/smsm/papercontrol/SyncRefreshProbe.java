package org.smsm.papercontrol;

import android.app.job.*;
import android.appwidget.*;
import android.content.*;
import android.os.*;
import android.widget.TextView;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

/** Real Android scheduler -> selected SAF file -> native widget host readback. */
public class SyncRefreshProbe extends SyncScheduleProbe {
 private int refreshChecks;
 private void verify(boolean pass,String reason){if(!pass)throw new AssertionError(reason);refreshChecks++;}
 private void setTasks(Context c,String text){Bundle data=new Bundle();data.putString("text",text);c.getContentResolver().call(SyncFixtureControl.URI,"setTasks",null,data);}
 private String tasks(int count){StringBuilder text=new StringBuilder("# 할 일\n");for(int i=1;i<=count;i++)text.append("- [ ] 원격 변경 ").append(i).append(" ⏳ ").append(VaultStore.day()).append(" ^task-qa-").append(i).append('\n');return text.toString();}
 private void waitCount(AppWidgetHostView view,String expected,long timeout){long until=SystemClock.elapsedRealtime()+timeout;AtomicReference<String> found=new AtomicReference<>("");while(SystemClock.elapsedRealtime()<until){runOnMainSync(()->{TextView number=view.findViewById(R.id.widget_count);found.set(number==null?"":number.getText().toString().replaceAll("\\s+",""));});if(expected.equals(found.get())){refreshChecks++;return;}SystemClock.sleep(200);}throw new AssertionError("widget count "+found.get()+" expected "+expected);}
 private void waitStep(SharedPreferences pref,long token,int step,long timeout){long until=SystemClock.elapsedRealtime()+timeout;while(SystemClock.elapsedRealtime()<until){if(pref.getLong("sync_refresh_last_token",0)==token&&pref.getInt("sync_refresh_last_step",-1)>=step){refreshChecks++;return;}SystemClock.sleep(200);}throw new AssertionError("OS refresh step "+step+" did not run for current generation");}
 private static void restore(SharedPreferences pref,Map<String,?> saved){SharedPreferences.Editor edit=pref.edit().clear();for(Map.Entry<String,?> entry:saved.entrySet()){Object v=entry.getValue();String k=entry.getKey();if(v instanceof String)edit.putString(k,(String)v);else if(v instanceof Integer)edit.putInt(k,(Integer)v);else if(v instanceof Long)edit.putLong(k,(Long)v);else if(v instanceof Boolean)edit.putBoolean(k,(Boolean)v);else if(v instanceof Float)edit.putFloat(k,(Float)v);else if(v instanceof Set)edit.putStringSet(k,(Set<String>)v);}edit.commit();}
 @Override public void onStart(){Context c=getTargetContext();SharedPreferences pref=VaultStore.prefs(c);Map<String,?> saved=pref.getAll();AppWidgetHost host=new AppWidgetHost(c,71336);int id=0;
  try{
   setTasks(c,tasks(1));pref.edit().clear().putString("tree",SyncFixtureProvider.TREE.toString()).putString("sync","gitsync").putInt("repo_index",2).putInt("auto_sync_minutes",15).commit();
   verify(new TaskDocument(new VaultStore(c).read("Tasks/할 일.md")).today(VaultStore.day()).size()==1,"initial SAF read");
   AppWidgetManager manager=AppWidgetManager.getInstance(c);id=host.allocateAppWidgetId();Bundle options=new Bundle();options.putInt(AppWidgetManager.OPTION_APPWIDGET_MIN_WIDTH,360);options.putInt(AppWidgetManager.OPTION_APPWIDGET_MAX_WIDTH,360);options.putInt(AppWidgetManager.OPTION_APPWIDGET_MIN_HEIGHT,180);options.putInt(AppWidgetManager.OPTION_APPWIDGET_MAX_HEIGHT,180);
   verify(manager.bindAppWidgetIdIfAllowed(id,new ComponentName(c,PaperWidget.class),options),"native widget binding");int widgetId=id;AppWidgetHostView[] view={null};runOnMainSync(()->{host.startListening();view[0]=host.createView(c,widgetId,manager.getAppWidgetInfo(widgetId));});PaperWidget.updateAll(c);waitCount(view[0],"0/1",10000);
   PostSyncRefresh.start(c);JobScheduler jobs=c.getSystemService(JobScheduler.class);JobInfo first=jobs.getPendingJob(PostSyncRefresh.FIRST_JOB);verify(first!=null&&first.isPersisted(),"post-transfer read survives process exit");verify(first.getNetworkType()==JobInfo.NETWORK_TYPE_NONE,"file refresh does not wait for network");
   long generation=pref.getLong("sync_refresh_token",0);waitStep(pref,generation,0,45000);
   setTasks(c,tasks(2));waitStep(pref,generation,1,75000);waitCount(view[0],"0/2",10000);verify(new TaskDocument(new VaultStore(c).read("Tasks/할 일.md")).tasks.size()==2,"late transfer reread and native display match");
   verify(jobs.getPendingJob(PostSyncRefresh.FIRST_JOB)!=null||jobs.getPendingJob(PostSyncRefresh.SECOND_JOB)!=null,"later checks remain after late read");
   PostSyncRefresh.start(c);long token=pref.getLong("sync_refresh_token",0);PostSyncRefresh.start(c);verify(pref.getLong("sync_refresh_token",0)>token,"new handoff invalidates old generation");verify(jobs.getAllPendingJobs().stream().filter(j->j.getId()==PostSyncRefresh.FIRST_JOB||j.getId()==PostSyncRefresh.SECOND_JOB).count()==1,"new requests replace pending reread chain");
   runOnMainSync(()->WidgetFeedback.show(c,"sync","sending","QA animation"));verify(WidgetFeedback.isBusy(),"button feedback active");setTasks(c,tasks(3));PaperWidget.updateAll(c);runOnMainSync(()->WidgetFeedback.show(c,"sync","sent","QA delivered"));waitCount(view[0],"0/3",10000);verify(!pref.contains("git_completed"),"reread never claims remote push success");
   PostSyncRefresh.cancel(c);verify(jobs.getPendingJob(PostSyncRefresh.FIRST_JOB)==null&&jobs.getPendingJob(PostSyncRefresh.SECOND_JOB)==null,"cancel removes both pending IDs");
  }catch(Throwable e){Bundle result=new Bundle();result.putString("stream","FAIL refresh integration: "+e+"\n");finish(-1,result);return;}
  finally{PostSyncRefresh.cancel(c);PeriodicSync.cancel(c);if(id!=0)host.deleteAppWidgetId(id);host.stopListening();host.deleteHost();restore(pref,saved);}
  super.onStart();
 }
 @Override public void finish(int code,Bundle result){result.putString("stream",result.getString("stream","")+"Native SAF/widget refresh integration checks: "+refreshChecks+"\n");super.finish(code,result);}
}
