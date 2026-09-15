package org.smsm.papercontrol;
import android.app.Activity;
import android.app.job.*;
import android.content.*;
import android.net.Uri;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
public final class SyncBridge {
  private static void open(Activity a,Uri uri){try{a.startActivity(new Intent(Intent.ACTION_VIEW,uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));}catch(ActivityNotFoundException e){throw new IllegalStateException("Obsidian을 설치하고 연구 Vault를 먼저 열어 주세요.");}}
  public static void obsidian(Activity a,String action){String vault=VaultStore.prefs(a).getString("vault","Paper Research Vault");Uri uri=new Uri.Builder().scheme("obsidian").authority("paper-analysis").appendQueryParameter("vault",vault).appendQueryParameter("action",action).build();open(a,uri);}
  public static void note(Activity a,String path){String vault=VaultStore.prefs(a).getString("vault","Paper Research Vault");open(a,new Uri.Builder().scheme("obsidian").authority("open").appendQueryParameter("vault",vault).appendQueryParameter("file",path).build());}
  public static void sync(Activity a){
    VaultStore.prefs(a).edit().putLong("git_requested",System.currentTimeMillis()).apply();PaperWidget.refresh(a);
    try {
    String provider=VaultStore.prefs(a).getString("sync","auto");boolean installed=false;try{a.getPackageManager().getPackageInfo("com.viscouspot.gitsync",0);installed=true;}catch(Exception ignored){}
    if(provider.equals("gitsync")||(provider.equals("auto")&&installed)){
      Intent i=new Intent("INTENT_SYNC").setComponent(new ComponentName("com.viscouspot.gitsync","com.viscouspot.gitsync.GitSyncService"));
      int index=VaultStore.prefs(a).getInt("repo_index",-1);if(index>=0)i.putExtra("index",index);i.putExtra("message","research widget sync");
      ComponentName result=a.startService(i);if(result==null)throw new IllegalStateException("GitSync 앱과 저장소 설정을 확인해 주세요.");
    }else obsidian(a,"sync");
    VaultStore.prefs(a).edit().putString("notice","동기화 요청 "+LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm"))).apply();
    }catch(RuntimeException e){VaultStore.prefs(a).edit().putLong("git_failed",System.currentTimeMillis()).apply();PaperWidget.refresh(a);throw e;}
    JobScheduler jobs=(JobScheduler)a.getSystemService(Context.JOB_SCHEDULER_SERVICE);
    jobs.schedule(new JobInfo.Builder(71325,new ComponentName(a,RefreshJob.class)).setMinimumLatency(10000).setOverrideDeadline(60000).build());
  }
}
