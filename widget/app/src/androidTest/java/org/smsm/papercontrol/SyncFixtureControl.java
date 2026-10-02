package org.smsm.papercontrol;

import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.DocumentsContract;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** Bootstrap only the QA fixture URI, with no access to user storage. */
public class SyncFixtureControl extends ContentProvider {
 public static final Uri URI=Uri.parse("content://org.researchqa.widgetfixture.control");
 @Override public boolean onCreate(){return true;}
 @Override public Bundle call(String method,String arg,Bundle data){
  if(!"setTasks".equals(method)||!"org.smsm.papercontrol".equals(getCallingPackage()))throw new SecurityException("QA target only");
  try(FileOutputStream out=new FileOutputStream(new File(getContext().getFilesDir(),"sync-fixture-tasks.md"))){out.write(data.getString("text").getBytes(StandardCharsets.UTF_8));}catch(IOException e){throw new IllegalStateException(e);}
  getContext().grantUriPermission("org.smsm.papercontrol",SyncFixtureProvider.TREE,Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
  getContext().getContentResolver().notifyChange(DocumentsContract.buildDocumentUriUsingTree(SyncFixtureProvider.TREE,"tasks-note"),null);
  return new Bundle();
 }
 @Override public Cursor query(Uri uri,String[] projection,String selection,String[] args,String sort){throw new UnsupportedOperationException();}
 @Override public String getType(Uri uri){return "application/octet-stream";}
 @Override public Uri insert(Uri uri,ContentValues values){throw new UnsupportedOperationException();}
 @Override public int update(Uri uri,ContentValues values,String selection,String[] args){throw new UnsupportedOperationException();}
 @Override public int delete(Uri uri,String selection,String[] args){throw new UnsupportedOperationException();}
}
