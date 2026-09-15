package org.smsm.papercontrol.fixture;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.Bitmap;
import org.smsm.papercontrol.WidgetGraphics;
import java.io.*;
public class FrameExporter extends Activity {
 @Override public void onCreate(Bundle b){super.onCreate(b);new Thread(()->{try{
  File dir=new File(getExternalFilesDir(null),"motion032");dir.mkdirs();
  for(String action:new String[]{"sync","analyze"}){
   for(int n=0;n<61;n++)save(dir,String.format("%s_orbit_%03d",action,n),WidgetGraphics.button(this,action,n/60f,"orbit",84,40));
   for(int n=0;n<=20;n++)save(dir,String.format("%s_sent_%03d",action,n),WidgetGraphics.button(this,action,n*.02f,"sent",84,40));
   for(int n=0;n<60;n++)save(dir,String.format("%s_wait_%03d",action,n),WidgetGraphics.button(this,action,n*(float)(Math.PI*2/5/60),"waiting",84,40));
  }
  for(int n=0;n<101;n++)save(dir,String.format("wave_%03d",n),WidgetGraphics.ripple(n/100f));
  new File(dir,"complete").createNewFile();runOnUiThread(()->finish());
 }catch(Exception e){android.util.Log.e("FRAME_EXPORT", "Export failed",e);}},"native-frame-export").start();}
 private void save(File d,String name,Bitmap b)throws Exception{try(FileOutputStream out=new FileOutputStream(new File(d,name+".png"))){b.compress(Bitmap.CompressFormat.PNG,100,out);}b.recycle();}
}
