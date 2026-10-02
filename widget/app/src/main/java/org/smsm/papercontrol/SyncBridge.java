package org.smsm.papercontrol;
import android.app.Activity;
import android.app.job.*;
import android.content.*;
import android.net.Uri;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
public final class SyncBridge {
  private static void open(Context a,Uri uri){try{a.startActivity(new Intent(Intent.ACTION_VIEW,uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));}catch(ActivityNotFoundException e){throw new IllegalStateException("Obsidian을 설치하고 연구 Vault를 먼저 열어 주세요.");}}
  public static void obsidian(Context a,String action){String vault=VaultStore.prefs(a).getString("vault","Paper Research Vault");Uri uri=new Uri.Builder().scheme("obsidian").authority("paper-analysis").appendQueryParameter("vault",vault).appendQueryParameter("action",action).build();open(a,uri);}
  public static void note(Activity a,String path){String vault=VaultStore.prefs(a).getString("vault","Paper Research Vault");open(a,new Uri.Builder().scheme("obsidian").authority("open").appendQueryParameter("vault",vault).appendQueryParameter("file",path).build());}
  static boolean useGitSync(Context a){
    String provider=VaultStore.prefs(a).getString("sync","auto");if(provider.equals("gitsync"))return true;if(!provider.equals("auto"))return false;
    try{a.getPackageManager().getPackageInfo("com.viscouspot.gitsync",0);return true;}catch(Exception ignored){return false;}
  }
  /** A saved widget edit must request sync without opening a visible window. */
  public static boolean afterWrite(Context a){
    if(!useGitSync(a)){long now=System.currentTimeMillis();VaultStore.prefs(a).edit().putLong("git_requested",now).putLong("git_failed",now).putString("notice","저장됨 · 자동 동기화는 GitSync 연결이 필요합니다.").apply();PaperWidget.refresh(a);return false;}
    try{sync(a);return true;}catch(RuntimeException e){VaultStore.prefs(a).edit().putString("notice","저장됨 · 동기화 요청 실패: "+e.getMessage()).apply();PaperWidget.refresh(a);return false;}
  }
  public static boolean backgroundSync(Context a){
    if(!useGitSync(a))return false;
    // Avoid repeated requests while the previous service dispatch is still fresh.
    long now=System.currentTimeMillis();if(now-VaultStore.prefs(a).getLong("git_dispatched",0)<30000)return true;
    try{sync(a);return true;}catch(RuntimeException e){VaultStore.prefs(a).edit().putString("notice","동기화 요청 실패: "+e.getMessage()).apply();PaperWidget.refresh(a);return false;}
  }
  public static void sync(Context a){
    VaultStore.prefs(a).edit().putLong("git_requested",System.currentTimeMillis()).apply();PaperWidget.refresh(a);
    try {
    if(useGitSync(a)){
      Intent i=new Intent("INTENT_SYNC").setComponent(new ComponentName("com.viscouspot.gitsync","com.viscouspot.gitsync.GitSyncService"));
      int index=VaultStore.prefs(a).getInt("repo_index",-1);if(index>=0)i.putExtra("index",index);i.putExtra("message","research widget sync");
      ComponentName result=a.startService(i);if(result==null)throw new IllegalStateException("GitSync 앱과 저장소 설정을 확인해 주세요.");
      VaultStore.prefs(a).edit().putLong("git_dispatched",System.currentTimeMillis()).apply();
    }else obsidian(a,"sync");
    VaultStore.prefs(a).edit().putString("notice","동기화 요청 "+LocalTime.now().format(DateTimeFormatter.ofPattern("HH:mm"))).apply();
    }catch(RuntimeException e){VaultStore.prefs(a).edit().putLong("git_failed",System.currentTimeMillis()).apply();PaperWidget.refresh(a);throw e;}
    JobScheduler jobs=(JobScheduler)a.getSystemService(Context.JOB_SCHEDULER_SERVICE);
    jobs.schedule(new JobInfo.Builder(71325,new ComponentName(a,RefreshJob.class)).setMinimumLatency(10000).setOverrideDeadline(60000).build());
  }
}
