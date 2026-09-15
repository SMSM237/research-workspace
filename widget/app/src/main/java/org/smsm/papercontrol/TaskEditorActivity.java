package org.smsm.papercontrol;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.*;
import android.content.res.ColorStateList;
import android.view.*;
import android.widget.*;

/** Custom floating card, never a full-screen form or stock AlertDialog. */
public class TaskEditorActivity extends Activity {
 private EditText input;private TextView error;private Button save,remove;private ImageButton close;
 private String action,key,raw;private boolean writing,confirmDelete;
 private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
 private GradientDrawable surface(String fill,String stroke,int radius){GradientDrawable d=new GradientDrawable();d.setColor(Color.parseColor(fill));d.setCornerRadius(dp(radius));if(stroke!=null)d.setStroke(dp(1),Color.parseColor(stroke));return d;}
 private Drawable press(String fill){return new RippleDrawable(ColorStateList.valueOf(Color.parseColor("#3026735E")),surface(fill,null,12),surface("#FFFFFF",null,12));}
 private TextView text(String s,int size,String color,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(Color.parseColor(color));if(bold)t.setTypeface(null,Typeface.BOLD);return t;}
 @Override public void onCreate(Bundle state){super.onCreate(state);action=getIntent().getStringExtra("action");key=getIntent().getStringExtra("key");raw=getIntent().getStringExtra("raw");if(!"add".equals(action)&&!"edit".equals(action)){finish();return;}
  LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(22),dp(14),dp(22),dp(20));card.setBackgroundResource(R.drawable.editor_background);
  LinearLayout heading=new LinearLayout(this);heading.setGravity(Gravity.CENTER_VERTICAL);card.addView(heading);
  heading.addView(text("add".equals(action)?"할 일 추가":"할 일 수정",21,"#20372D",true),new LinearLayout.LayoutParams(0,dp(48),1));
  ((TextView)heading.getChildAt(0)).setGravity(Gravity.CENTER_VERTICAL);
  close=new ImageButton(this);close.setImageResource(R.drawable.ic_close);close.setContentDescription("닫기");close.setPadding(dp(14),dp(14),dp(14),dp(14));close.setStateListAnimator(null);close.setElevation(0);close.setTranslationZ(0);close.setBackground(press("#F6F5F1"));close.setOnClickListener(v->{if(!writing)finish();});heading.addView(close,new LinearLayout.LayoutParams(dp(48),dp(48)));
  TextView subtitle=text("add".equals(action)?"오늘 목록에 바로 담아 두세요.":"내용을 바꿔도 일정과 기록은 유지됩니다.",13,"#63736A",false);LinearLayout.LayoutParams sub=new LinearLayout.LayoutParams(-1,-2);sub.bottomMargin=dp(18);card.addView(subtitle,sub);
  input=new EditText(this);input.setId(android.R.id.edit);input.setTextSize(17);input.setMinLines(2);input.setMaxLines(3);input.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);input.setHorizontallyScrolling(false);input.setGravity(Gravity.TOP|Gravity.START);input.setHint("무엇을 할까요?");input.setHintTextColor(Color.parseColor("#68776E"));input.setTextColor(Color.parseColor("#20372D"));input.setPadding(dp(15),dp(15),dp(15),dp(15));input.setBackground(surface("#FFFFFF","#CAD8CF",12));input.setImeOptions(android.view.inputmethod.EditorInfo.IME_ACTION_DONE);card.addView(input,new LinearLayout.LayoutParams(-1,dp(94)));
  if("edit".equals(action)){try{input.setText(new TaskDocument(raw).tasks.get(0).editable);}catch(Exception e){finish();return;}}
  error=text("",13,"#973B32",false);error.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);error.setPadding(0,dp(10),0,0);error.setVisibility(View.GONE);card.addView(error);
  LinearLayout buttons=new LinearLayout(this);buttons.setGravity(Gravity.CENTER_VERTICAL);LinearLayout.LayoutParams footer=new LinearLayout.LayoutParams(-1,dp(50));footer.topMargin=dp(18);card.addView(buttons,footer);
  if("edit".equals(action)){remove=button("삭제",false);LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(-2,-1);rp.setMarginEnd(dp(10));buttons.addView(remove,rp);remove.setOnClickListener(v->{if(confirmDelete){persist("delete",null);return;}confirmDelete=true;error.setText("이 할 일을 삭제할까요? 한 번 더 누르면 삭제됩니다.");error.setVisibility(View.VISIBLE);remove.setText("삭제 확인");remove.setTextColor(Color.parseColor("#973B32"));});}
  save=button("add".equals(action)?"추가하기":"저장하기",true);buttons.addView(save,new LinearLayout.LayoutParams(0,-1,1));save.setOnClickListener(v->save());
  setContentView(card);getWindow().setLayout(Math.min(dp(420),getResources().getDisplayMetrics().widthPixels-dp(32)),WindowManager.LayoutParams.WRAP_CONTENT);getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE|WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
  input.setOnEditorActionListener((v,id,event)->{if(id==android.view.inputmethod.EditorInfo.IME_ACTION_DONE){save();return true;}return false;});input.requestFocus();
 }
 private Button button(String s,boolean primary){Button b=new Button(this);b.setText(s);b.setAllCaps(false);b.setTextSize(15);b.setTypeface(null,Typeface.BOLD);b.setMinWidth(dp(76));b.setSingleLine(true);b.setMinHeight(dp(48));b.setPadding(dp(16),0,dp(16),0);b.setTextColor(Color.parseColor(primary?"#FFFFFF":"#52675C"));b.setStateListAnimator(null);b.setElevation(0);b.setTranslationZ(0);b.setBackground(press(primary?"#26735E":"#E8EDE7"));return b;}
 private void save(){if(writing)return;try{persist(action,TaskDocument.cleanTitle(input.getText().toString()));}catch(Exception e){error.setText(e.getMessage());error.setVisibility(View.VISIBLE);input.setBackground(surface("#FFFFFF","#B86B62",12));}}
 private void persist(String verb,String title){if(writing)return;writing=true;save.setEnabled(false);save.setText("저장 중…");close.setEnabled(false);if(remove!=null)remove.setEnabled(false);input.setEnabled(false);new Thread(()->{try{new VaultStore(this).change(verb,key,raw,title);PaperWidget.updateAll(this);runOnUiThread(this::finish);}catch(Exception e){runOnUiThread(()->{writing=false;save.setEnabled(true);save.setText("add".equals(action)?"추가하기":"저장하기");close.setEnabled(true);input.setEnabled(true);if(remove!=null)remove.setEnabled(true);error.setText(e.getMessage()==null?"저장하지 못했습니다.":e.getMessage());error.setVisibility(View.VISIBLE);});}},"floating-task-editor").start();}
}
