package org.smsm.papercontrol;
import android.content.Intent;
import android.appwidget.AppWidgetManager;
import android.widget.*;
import java.util.*;
public class TasksService extends RemoteViewsService {
 public RemoteViewsFactory onGetViewFactory(Intent i){int id=i.getIntExtra(AppWidgetManager.EXTRA_APPWIDGET_ID,0);return new RemoteViewsFactory(){List<RemoteViews> rows=new ArrayList<>();public void onCreate(){onDataSetChanged();}public void onDataSetChanged(){rows=new ArrayList<>();try{VaultStore s=new VaultStore(TasksService.this);boolean compact=PaperWidget.compact(TasksService.this,id);if(PaperWidget.meetings(TasksService.this,id)){for(MeetingDocument d:s.meetings())rows.add(PaperWidget.meetingRow(TasksService.this,d,compact));}else for(TaskDocument.Task t:new TaskDocument(s.read(s.source())).today(VaultStore.day()))rows.add(PaperWidget.row(TasksService.this,t,compact));}catch(Exception ignored){}}public void onDestroy(){}public int getCount(){return rows.size();}public RemoteViews getViewAt(int n){return n<rows.size()?rows.get(n):null;}public RemoteViews getLoadingView(){return null;}public int getViewTypeCount(){return 1;}public long getItemId(int n){return n;}public boolean hasStableIds(){return false;}};}
}
