package org.smsm.papercontrol;
import android.content.Context;
import android.graphics.*;
/** Small, bounded Canvas frames: native widgets cannot execute a web animation library. */
public final class WidgetGraphics {
 private static Paint paint(int color){Paint p=new Paint(3);p.setColor(color);return p;}
 private static int color(String c){return Color.parseColor(c);}
 public static Bitmap dot(String state){Bitmap b=Bitmap.createBitmap(48,48,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);int col=color(state.equals("verified")?"#65EF56":state.equals("pending")?"#E9B842":state.equals("error")?"#E16758":"#98A49B");Paint p=paint(col);p.setAlpha(35);c.drawCircle(24,24,23,p);p.setAlpha(255);c.drawCircle(24,24,12,p);p.setColor(color("#55735D"));p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.5f);c.drawCircle(24,24,12,p);return b;}
 public static Bitmap wave(float ratio,float phase){Bitmap b=Bitmap.createBitmap(600,24,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);Paint p=paint(color("#DEE4DC"));RectF r=new RectF(0,0,600,24);c.drawRoundRect(r,12,12,p);Path clip=new Path();clip.addRoundRect(r,12,12,Path.Direction.CW);c.clipPath(clip);if(ratio<=0)return b;
  for(int layer=0;layer<2;layer++){Path path=new Path();path.moveTo(0,0);for(int y=0;y<=24;y++){float x=ratio>=1?602:phase<0?600*ratio:600*ratio+(float)Math.sin(y*.16+phase+layer*1.8)*5+layer*3;path.lineTo(x,y);}path.lineTo(0,24);path.close();p.setColor(color(layer==0?"#91CDB8":"#287B63"));c.drawPath(path,p);}return b;}
 public static Bitmap ripple(float progress){
  Bitmap b=Bitmap.createBitmap(240,40,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);Paint p=paint(color("#287B63"));
  float u=Math.max(0,Math.min(1,progress)),ease=u*u*(3-2*u);
  for(int layer=0;layer<2;layer++){Path front=new Path();front.moveTo(0,0);
   for(int y=0;y<=40;y++){float amplitude=8*(float)Math.sin(Math.PI*u);float x=240*ease+amplitude*(float)Math.sin(y*.15-u*12+layer*1.2);front.lineTo(Math.max(0,Math.min(240,x)),y);}
   front.lineTo(0,40);front.close();p.setColor(color(layer==0?"#91CDB8":"#287B63"));c.drawPath(front,p);
  }return b;
 }
 public static String label(String action){return action.equals("sync")?"동기화":action.equals("analyze")?"분석":action.equals("add")?"추가":"열기";}
 public static Bitmap button(Context context,String action,float t,String result,int widthDp,int heightDp){
  int w=Math.max(80,Math.min(240,widthDp*2)),h=heightDp*2;Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(b);c.scale(w/(float)widthDp,2);float width=widthDp,cx=width/2,cy=heightDp/2f;
  int ink=color(action.equals("analyze")?"#645080":"#225F4C");Paint p=paint(ink);p.setTypeface(Typeface.create("sans-serif",Typeface.BOLD));float fs=Math.min(13*context.getResources().getConfiguration().fontScale,(width-22)/(label(action).length()+.2f));p.setTextSize(Math.max(10,fs));p.setStrokeCap(Paint.Cap.ROUND);p.setStrokeJoin(Paint.Join.ROUND);
  String label=label(action);float tw=p.measureText(label),baseline=cy-(p.ascent()+p.descent())/2;
  if(t<0){float left=(width-tw-17)/2;icon(c,p,action,left+6,cy);p.setStyle(Paint.Style.FILL);c.drawText(label,left+17,baseline,p);return b;}
  if(result.equals("orbit")){
   float u=Math.min(1,Math.max(0,t)),ease=u*u*(3-2*u),left=(width-tw-17)/2;
   // Each glyph darts from its own position into the center; no elliptical orbit.
   for(int i=-1;i<label.length();i++){
    String glyph=i<0?"":label.substring(i,i+1);
    float start=i<0?left+6:left+17+p.measureText(label.substring(0,i))+p.measureText(glyph)/2;
    float q=Math.max(0,Math.min(1,(u-.065f*(i+1))/.68f));float pull=q*q*q;
    float x=start+(cx-start)*pull,y=cy;float scale=1-.85f*pull;
    if(q>.2f&&q<.97f){Paint trail=paint(ink);trail.setStrokeWidth(1.3f);trail.setStrokeCap(Paint.Cap.ROUND);trail.setAlpha((int)(80*Math.sin(Math.PI*q)));float length=(x-start)*.22f;c.drawLine(x-length,y,x,y,trail);}
    p.setAlpha((int)(255*(1-Math.max(0,(q-.75f)/.25f))));
    c.save();c.translate(x,y);c.scale(scale,scale);
    if(i<0)icon(c,p,action,0,0);else{p.setStyle(Paint.Style.FILL);c.drawText(glyph,-p.measureText(glyph)/2,-(p.ascent()+p.descent())/2,p);}c.restore();
   }return b;
  }
  if(result.equals("waiting")){for(int i=0;i<3;i++){double a=t*5+i*Math.PI*2/3;p.setAlpha(170+i*25);c.drawCircle(cx+(float)Math.cos(a)*7,cy+(float)Math.sin(a)*7,2,p);}return b;}
  boolean success=result.equals("sent");p.setColor(color(success?"#24745B":"#A64038"));p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(2.5f);float size=8*Math.min(1,t*5+.2f);
  if(success){Path check=new Path();check.moveTo(cx-size,cy);check.lineTo(cx-size*.2f,cy+size*.6f);check.lineTo(cx+size,cy-size*.7f);c.drawPath(check,p);}else{c.drawLine(cx-size,cy-size,cx+size,cy+size,p);c.drawLine(cx+size,cy-size,cx-size,cy+size,p);}
  if(t<.4f){float q=t/.4f;for(int i=0;i<8;i++){double a=i*Math.PI/4;p.setAlpha((int)(210*(1-q)));float inner=12+q*4,outer=inner+4*(1-q);c.drawLine(cx+(float)Math.cos(a)*inner,cy+(float)Math.sin(a)*inner,cx+(float)Math.cos(a)*outer,cy+(float)Math.sin(a)*outer,p);}}return b;
 }
 private static void icon(Canvas c,Paint p,String action,float x,float y){p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(1.6f);if(action.equals("add")){c.drawLine(x-4,y,x+4,y,p);c.drawLine(x,y-4,x,y+4,p);}else if(action.equals("sync")){c.save();c.translate(x-7,y-7);c.scale(14f/24,14f/24);p.setStrokeWidth(2.5f);
 Path arrows=new Path();arrows.moveTo(3,10);arrows.cubicTo(4,3,14,1,20,7);arrows.lineTo(22,10);arrows.moveTo(22,4);arrows.lineTo(22,10);arrows.lineTo(16,10);
 arrows.moveTo(21,14);arrows.cubicTo(20,21,10,23,4,17);arrows.lineTo(2,14);arrows.moveTo(2,20);arrows.lineTo(2,14);arrows.lineTo(8,14);c.drawPath(arrows,p);c.restore();p.setStrokeWidth(1.6f);}else if(action.equals("analyze")){Path t=new Path();t.moveTo(x-3,y-5);t.lineTo(x+5,y);t.lineTo(x-3,y+5);t.close();c.drawPath(t,p);}else{c.drawLine(x-4,y+4,x+4,y-4,p);c.drawLine(x,y-4,x+4,y-4,p);c.drawLine(x+4,y-4,x+4,y,p);}}
}
