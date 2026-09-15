package org.smsm.papercontrol;
import android.app.*;
import android.appwidget.AppWidgetManager;
import android.content.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.view.*;
import android.widget.*;
public class MainActivity extends Activity {
  private EditText vault,source,index;private TextView notice,folder;private Spinner provider;
  private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
  private TextView text(String value,int size,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(Color.rgb(32,55,45));if(bold)t.setTypeface(null,Typeface.BOLD);t.setPadding(0,dp(8),0,dp(8));return t;}
  private Button button(String label,boolean primary){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextSize(16);b.setMinHeight(dp(52));b.setPadding(dp(16),dp(10),dp(16),dp(10));GradientDrawable bg=new GradientDrawable();bg.setColor(Color.parseColor(primary?"#26735E":"#FFFFFF"));bg.setCornerRadius(dp(12));b.setBackground(bg);b.setTextColor(Color.parseColor(primary?"#FFFFFF":"#20372D"));LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=dp(12);b.setLayoutParams(p);return b;}
  private EditText field(LinearLayout root,String title,String value){root.addView(text(title,14,true));EditText e=new EditText(this);e.setSingleLine(true);e.setTextSize(16);e.setMinHeight(dp(48));e.setText(value);root.addView(e);return e;}
  @Override public void onCreate(Bundle saved){super.onCreate(saved);
    getWindow().getDecorView();
    if(android.os.Build.VERSION.SDK_INT>=30)getWindow().getInsetsController().setSystemBarsAppearance(WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS|WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS);
    else getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR);
    SharedPreferences p=VaultStore.prefs(this);if(!p.contains("vault"))p.edit().putString("vault",getPreferences(0).getString("vault","Paper Research Vault")).apply();
    ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(Color.parseColor("#EEECE7"));LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(dp(24),dp(16),dp(24),dp(24));scroll.addView(root);setContentView(scroll);
    scroll.setOnApplyWindowInsetsListener((v,insets)->{if(android.os.Build.VERSION.SDK_INT>=30){android.graphics.Insets b=insets.getInsets(WindowInsets.Type.systemBars());v.setPadding(b.left,b.top,b.right,b.bottom);}else v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
    root.addView(text("연구 위젯",28,true));root.addView(text("오늘 할 일을 홈 화면에서 확인하고 수정하세요.",16,false));
    Button connect=button("Vault 폴더 연결",true);connect.setOnClickListener(v->startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION),71));root.addView(connect);
    folder=text(p.contains("tree")?"연결됨 · "+Uri.decode(Uri.parse(p.getString("tree","")).getLastPathSegment()):".obsidian과 Tasks가 들어 있는 Vault 최상위 폴더를 선택하세요.",13,false);root.addView(folder);
    vault=field(root,"Obsidian Vault 이름",p.getString("vault","Paper Research Vault"));source=field(root,"할 일 노트 경로",p.getString("source","Tasks/할 일.md"));
    root.addView(text("동기화 연결",14,true));provider=new Spinner(this);provider.setMinimumHeight(dp(48));provider.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"자동 선택 · GitSync 우선","GitSync 앱","Obsidian Git 플러그인"}));String sync=p.getString("sync","auto");provider.setSelection(sync.equals("gitsync")?1:sync.equals("obsidian")?2:0);root.addView(provider);
    index=field(root,"GitSync 저장소 번호 · 비우면 앱의 현재 저장소",p.contains("repo_index")&&p.getInt("repo_index",-1)>=0?String.valueOf(p.getInt("repo_index",-1)+1):"");index.setInputType(android.text.InputType.TYPE_CLASS_NUMBER);
    Button save=button("설정 저장 · 연결 확인",true);save.setOnClickListener(v->{if(saveSettings())check();});root.addView(save);
    Button pin=button("홈 화면에 위젯 추가",false);pin.setOnClickListener(v->{if(!saveSettings())return;AppWidgetManager m=getSystemService(AppWidgetManager.class);if(m.isRequestPinAppWidgetSupported())m.requestPinAppWidget(new ComponentName(this,PaperWidget.class),null,null);else notice.setText("홈 화면을 길게 누른 뒤 위젯에서 ‘연구 위젯’을 선택하세요.");});root.addView(pin);
    Button syncButton=button("지금 동기화",false);syncButton.setOnClickListener(v->{if(!saveSettings())return;try{SyncBridge.sync(this);notice.setText("동기화를 요청했습니다. 완료 여부는 동기화 앱에서 확인하세요.");}catch(Exception e){notice.setText("동기화 앱 연결을 확인해 주세요: "+e.getMessage());}});root.addView(syncButton);
    Button status=button("분석 상태 보기",false);status.setOnClickListener(v->{if(!saveSettings())return;try{SyncBridge.obsidian(this,"status");}catch(Exception e){notice.setText(e.getMessage());}});root.addView(status);
    notice=text("체크 버튼은 완료 표시, 항목 이름은 수정·삭제입니다. 목록은 스크롤할 수 있습니다.",14,false);notice.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);root.addView(notice);
    root.addView(text("분석은 켜져 있는 PC의 Inbox 파일을 대상으로 합니다. ‘동기화 요청’은 전송 완료 표시가 아닙니다. GitSync 또는 Obsidian Git에서 동기화가 끝났는지 확인하세요.",13,false));
  }
  private boolean saveSettings(){String v=vault.getText().toString().trim(),s=source.getText().toString().trim();if(v.isEmpty()||v.length()>100){vault.setError("Vault 이름을 입력해 주세요.");return false;}if(s.isEmpty()||s.startsWith("/")||s.contains("\\")||s.contains(":")||java.util.Arrays.asList(s.split("/",-1)).stream().anyMatch(x->x.isEmpty()||x.equals("..")||x.equals("."))){source.setError("Vault 안의 노트 경로를 입력해 주세요.");return false;}int i=-1;try{String n=index.getText().toString().trim();if(!n.isEmpty()){i=Integer.parseInt(n)-1;if(i<0||i>999)throw new Exception();}}catch(Exception e){index.setError("1 이상의 저장소 번호를 입력해 주세요.");return false;}VaultStore.prefs(this).edit().putString("vault",v).putString("source",s).putString("sync",new String[]{"auto","gitsync","obsidian"}[provider.getSelectedItemPosition()]).putInt("repo_index",i).apply();PaperWidget.refresh(this);return true;}
  private void check(){notice.setText("할 일 노트를 확인하고 있습니다…");new Thread(()->{String result;try{VaultStore s=new VaultStore(this);java.util.List<TaskDocument.Task> tasks=new TaskDocument(s.read(s.source())).today(VaultStore.day());result="연결 확인 · 오늘 "+tasks.size()+"개, 완료 "+tasks.stream().filter(t->t.done).count()+"개";}catch(Exception e){result="연결 확인 필요 · "+e.getMessage();}String message=result;runOnUiThread(()->notice.setText(message));},"vault-check").start();}
  @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request!=71||result!=RESULT_OK||data==null||data.getData()==null)return;Uri uri=data.getData();try{int flags=data.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION);if((flags&Intent.FLAG_GRANT_WRITE_URI_PERMISSION)==0)throw new SecurityException("쓰기 권한이 필요합니다.");getContentResolver().takePersistableUriPermission(uri,flags);VaultStore.prefs(this).edit().putString("tree",uri.toString()).apply();folder.setText("연결됨 · "+Uri.decode(uri.getLastPathSegment()));if(saveSettings())check();}catch(Exception e){notice.setText("폴더 연결을 완료하지 못했습니다: "+e.getMessage());}}
  @Override protected void onResume(){super.onResume();PaperWidget.refresh(this);}
}
