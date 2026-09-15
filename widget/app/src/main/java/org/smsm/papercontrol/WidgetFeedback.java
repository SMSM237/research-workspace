package org.smsm.papercontrol;
import android.content.*;
import android.app.*;
import android.appwidget.*;
import android.os.*;
import android.view.View;
import android.widget.*;
import android.animation.ValueAnimator;
import java.util.*;
/** Phase-only IPC: animation frames are played by the launcher itself. */
public final class WidgetFeedback {
 private static final Handler MAIN=new Handler(Looper.getMainLooper());
 private static final Map<String,Run> RUNS=new java.util.concurrent.ConcurrentHashMap<>();
 private static final Map<Integer,Float> RATIOS=new HashMap<>();
 private static final Map<Integer,Long> WAVES=new HashMap<>();
 private static class Run {final long start=SystemClock.uptimeMillis();volatile long resultAt;volatile String outcome="";String last="";int origin;}
 public static boolean isBusy(){return !RUNS.isEmpty();}
 public static synchronized boolean isBusy(String action){return RUNS.containsKey(action);}
 private static int origin(Context c){return c instanceof Activity?((Activity)c).getIntent().getIntExtra("widget",0):0;}
 public static void show(Context c,String action,String state,String message){
  VaultStore.prefs(c).edit().putString("notice",message).apply();Context app=c.getApplicationContext();int id=origin(c);
  Runnable update=()->{Run r=RUNS.get(action);if(state.equals("sending")){if(r!=null)return;r=new Run();r.origin=id;RUNS.put(action,r);tick(app,action,r);}else if(r!=null)r.outcome=state;};if(Looper.myLooper()==Looper.getMainLooper())update.run();else MAIN.post(update);
 }
 private static String phase(Run r){if(r==null)return "";if(r.resultAt>0)return r.outcome;return "waiting";}
 private static void tick(Context c,String action,Run run){
  if(RUNS.get(action)!=run)return;long now=SystemClock.uptimeMillis();boolean reduced=!ValueAnimator.areAnimatorsEnabled();
  if(now-run.start>10000&&run.outcome.isEmpty())run.outcome="error";
  if(!run.outcome.isEmpty()&&run.resultAt==0)run.resultAt=now;
  long hold=reduced||!run.outcome.equals("sent")?2000:3600;
  if(run.resultAt>0&&now-run.resultAt>=hold){RUNS.remove(action);PaperWidget.refresh(c);return;}
  String phase=phase(run)+(reduced?"-reduced":"");
  if(!phase.equals(run.last)){
   run.last=phase;AppWidgetManager m=AppWidgetManager.getInstance(c);
   for(int id:m.getAppWidgetIds(new ComponentName(c,PaperWidget.class))){if(run.origin!=0&&run.origin!=id)continue;RemoteViews v=new RemoteViews(c.getPackageName(),PaperWidget.layout(c,id));draw(c,v,id,action,run);m.partiallyUpdateAppWidget(id,v);}
  }
  // No per-frame bitmap transactions. Waiting polls only the local handoff state.
  long delay=run.resultAt>0?Math.max(20,hold-(now-run.resultAt)):100;
  MAIN.postDelayed(()->tick(c,action,run),delay);
 }
 public static void paint(Context c,RemoteViews v,int id){for(String action:new String[]{"add","open","analyze","sync"}){Run r=RUNS.get(action);draw(c,v,id,action,r!=null&&(r.origin==0||r.origin==id)?r:null);}}
 private static void draw(Context c,RemoteViews v,int id,String action,Run run){
  String phase=phase(run);boolean nativeMotion=ValueAnimator.areAnimatorsEnabled();
  int view=action.equals("add")?R.id.add_task:action.equals("open")?R.id.open_meeting:action.equals("analyze")?R.id.start_analysis:R.id.git_sync;
  boolean animated=action.equals("analyze")||action.equals("sync");int image=view;
  float t=phase.isEmpty()?-1:phase.equals("sent")||phase.equals("error")?1:0;
  if(animated){
   boolean sync=action.equals("sync");int layout=R.layout.widget_button_still;
   if(nativeMotion&&phase.equals("orbit"))layout=sync?R.layout.widget_sync_orbit:R.layout.widget_analyze_orbit;
   else if(nativeMotion&&phase.equals("waiting"))layout=sync?R.layout.widget_sync_wait:R.layout.widget_analyze_wait;
   else if(nativeMotion&&phase.equals("sent"))layout=sync?R.layout.widget_sync_sent:R.layout.widget_analyze_sent;
   RemoteViews child=new RemoteViews(c.getPackageName(),layout);
   if(layout==R.layout.widget_button_still)child.setImageViewBitmap(R.id.widget_button_image,WidgetGraphics.button(c,action,t,phase,PaperWidget.buttonWidth(c,id),PaperWidget.compact(c,id)?40:48));
   // A fresh Animatable per phase also replays correctly on the second tap.
   v.removeAllViews(view);v.addView(view,child);
  }else v.setImageViewBitmap(image,WidgetGraphics.button(c,action,t,phase,PaperWidget.buttonWidth(c,id),PaperWidget.compact(c,id)?40:48));
  v.setContentDescription(view,action.equals("add")?"할 일 추가":action.equals("open")?"현재 탭의 노트 열기":WidgetGraphics.label(action)+(phase.equals("sent")?" 요청 전달됨":phase.equals("error")?" 요청 오류, 다시 시도":run!=null?" 요청 중":" 요청"));
 }
 public static void wave(Context c,int id,float target,float track){MAIN.post(()->{Float previous=RATIOS.put(id,target);long token=SystemClock.uptimeMillis();WAVES.put(id,token);
  if(Build.VERSION.SDK_INT<31||previous==null||previous==target||!ValueAnimator.areAnimatorsEnabled())return;
  float base=Math.min(previous,target),delta=Math.abs(target-previous);boolean growing=target>previous;
  RemoteViews v=new RemoteViews(c.getPackageName(),PaperWidget.layout(c,id));
  v.setImageViewBitmap(R.id.progress_wave,WidgetGraphics.wave(base,-1));
  int moving=R.id.wave_overlay;v.removeAllViews(moving);v.addView(moving,new RemoteViews(c.getPackageName(),growing?R.layout.widget_wave:R.layout.widget_wave_reverse));
  v.setViewLayoutWidth(moving,track*delta,android.util.TypedValue.COMPLEX_UNIT_DIP);
  v.setViewLayoutMargin(moving,RemoteViews.MARGIN_LEFT,track*base,android.util.TypedValue.COMPLEX_UNIT_DIP);
  v.setViewVisibility(moving,View.VISIBLE);AppWidgetManager.getInstance(c).partiallyUpdateAppWidget(id,v);
  MAIN.postDelayed(()->{if(!Objects.equals(WAVES.get(id),token))return;WAVES.remove(id);RemoteViews stop=new RemoteViews(c.getPackageName(),PaperWidget.layout(c,id));stop.setImageViewBitmap(R.id.progress_wave,WidgetGraphics.wave(target,-1));stop.setViewVisibility(R.id.wave_overlay,View.GONE);AppWidgetManager.getInstance(c).partiallyUpdateAppWidget(id,stop);},1000);
 });}
 public static void toast(Context c,String text){MAIN.post(()->Toast.makeText(c,text,Toast.LENGTH_SHORT).show());}
}
