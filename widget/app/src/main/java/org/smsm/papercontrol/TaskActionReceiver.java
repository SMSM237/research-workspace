package org.smsm.papercontrol;
import android.content.*;
import android.os.*;
import android.widget.Toast;
import java.util.concurrent.*;
/** A checkbox changes a file, never creates a window or launches an Activity. */
public class TaskActionReceiver extends BroadcastReceiver {
 private static final ExecutorService WRITES=Executors.newSingleThreadExecutor();
 @Override public void onReceive(Context context,Intent intent){
  String action=intent.getStringExtra("action");Context c=context.getApplicationContext();
  if("tab-tasks".equals(action)||"tab-meetings".equals(action)){int id=intent.getIntExtra("widget",0);if(id>0){VaultStore.prefs(c).edit().putString("tab_"+id,action.equals("tab-meetings")?"meetings":"tasks").apply();PaperWidget.refresh(c);}return;}
  if("meeting-open".equals(action)){String path=intent.getStringExtra("key");if(path!=null&&path.startsWith("Meetings/Schedule/")&&!path.contains("..")&&path.endsWith(".md"))c.startActivity(new Intent(c,WidgetActionActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_MULTIPLE_TASK).putExtra("action",action).putExtra("key",path));return;}
  if("edit".equals(action)){c.startActivity(new Intent(c,TaskEditorActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_MULTIPLE_TASK).putExtra("action","edit").putExtra("key",intent.getStringExtra("key")).putExtra("raw",intent.getStringExtra("raw")));return;}
  if(!"toggle".equals(action)&&!"meeting-toggle".equals(action)&&!"refresh".equals(action))return;
  String key=intent.getStringExtra("key"),raw=intent.getStringExtra("raw");
  if(("toggle".equals(action)||"meeting-toggle".equals(action))&&(key==null||raw==null||key.length()>512||raw.length()>4096))return;
  PendingResult pending=goAsync();
  WRITES.execute(()->{try{if("toggle".equals(action))new VaultStore(c).change("toggle",key,raw,null);else if("meeting-toggle".equals(action))new VaultStore(c).toggleMeeting(key,raw);PaperWidget.updateAll(c);}catch(Exception e){String message=e instanceof SecurityException?"Vault 접근 권한을 다시 연결해 주세요.":e.getMessage();if(message==null)message="저장하지 못했습니다. 다시 확인해 주세요.";VaultStore.prefs(c).edit().putString("notice",message).apply();String shown=message;new Handler(Looper.getMainLooper()).post(()->Toast.makeText(c,shown,Toast.LENGTH_LONG).show());PaperWidget.updateAll(c);}finally{pending.finish();}});
 }
}
