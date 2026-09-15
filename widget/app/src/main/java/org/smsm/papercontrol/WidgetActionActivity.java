package org.smsm.papercontrol;
import android.app.*;
import android.os.*;
import android.content.*;
import android.widget.*;
public class WidgetActionActivity extends Activity {
  private String action,key,raw;private boolean busy;
  @Override public void onCreate(Bundle state){super.onCreate(state);action=getIntent().getStringExtra("action");key=getIntent().getStringExtra("key");raw=getIntent().getStringExtra("raw");
    if(action==null){finish();return;}if((action.equals("sync")||action.equals("analyze"))&&WidgetFeedback.isBusy(action)){finish();return;}
    switch(action){
      case "toggle":perform(null);break;
      case "edit":case "add":startActivity(new Intent(this,TaskEditorActivity.class).putExtras(getIntent()));finish();break;
      case "sync":WidgetFeedback.show(this,"sync","sending","동기화 요청 전달 중");try{SyncBridge.sync(this);WidgetFeedback.show(this,"sync","sent","동기화 앱에 요청을 전달했습니다");PaperWidget.refresh(this);finish();}catch(Exception e){WidgetFeedback.show(this,"sync","error","동기화 앱 연결을 확인해 주세요");error(e);}break;
      case "analyze":WidgetFeedback.show(this,"analyze","sending","분석 요청 저장 중");new Thread(()->{try{new VaultStore(this).requestAnalysis();runOnUiThread(()->{try{SyncBridge.sync(this);WidgetFeedback.show(this,"analyze","sent","분석 요청 저장 · 동기화 요청 전달됨");PaperWidget.refresh(this);finish();}catch(Exception e){WidgetFeedback.show(this,"analyze","error","요청은 저장됐지만 동기화 연결 확인이 필요합니다");error(e);}});}catch(Exception e){runOnUiThread(()->{WidgetFeedback.show(this,"analyze","error","분석 요청을 저장하지 못했습니다");error(e);});}},"analysis-request").start();break;
      case "connection":new AlertDialog.Builder(this).setTitle("Git 연결").setMessage(new VaultStore(this).gitDetail()).setPositiveButton("닫기",(d,w)->finish()).setNeutralButton("설정",(d,w)->{startActivity(new Intent(this,MainActivity.class));finish();}).setOnCancelListener(d->finish()).show();break;
      case "open":try{int id=getIntent().getIntExtra("widget",0);SyncBridge.note(this,PaperWidget.meetings(this,id)?"Dashboard/Modules/회의 일정.md":new VaultStore(this).source());finish();}catch(Exception e){error(e);}break;
      case "meeting-open":try{VaultStore s=new VaultStore(this);MeetingDocument d=new MeetingDocument(key,s.read(key));String p=d.minutes.startsWith("Meetings/Minutes/")&&!d.minutes.contains("..")&&s.resolve(d.minutes,false,false)!=null?d.minutes:d.path;SyncBridge.note(this,p);finish();}catch(Exception e){error(e);}break;
      case "meeting":try{SyncBridge.note(this,"Dashboard/Modules/회의 일정.md");finish();}catch(Exception e){error(e);}break;
      case "status":try{SyncBridge.obsidian(this,"status");finish();}catch(Exception e){error(e);}break;
      case "refresh":PaperWidget.refresh(this);finish();break;
      case "settings":startActivity(new Intent(this,MainActivity.class));finish();break;
      default:finish();
    }
  }
  private void perform(String title){if(busy)return;busy=true;new Thread(()->{try{new VaultStore(this).change(action,key,raw,title);PaperWidget.updateAll(this);runOnUiThread(this::finish);}catch(Exception e){runOnUiThread(()->{busy=false;error(e);});}},"widget-task-write").start();}
  private void error(Exception e){String message=e instanceof SecurityException?"Vault 접근 권한이 없습니다. 앱에서 폴더를 다시 선택해 주세요.":e.getMessage();if(message==null)message="작업을 완료하지 못했습니다.";VaultStore.prefs(this).edit().putString("notice",message).apply();PaperWidget.refresh(this);new AlertDialog.Builder(this).setTitle("확인이 필요합니다").setMessage(message).setPositiveButton("설정",(d,w)->{startActivity(new Intent(this,MainActivity.class));finish();}).setNegativeButton("닫기",(d,w)->finish()).setOnCancelListener(d->finish()).show();}
}
