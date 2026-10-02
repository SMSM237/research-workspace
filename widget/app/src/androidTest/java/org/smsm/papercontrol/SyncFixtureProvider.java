package org.smsm.papercontrol;

import android.content.Intent;
import android.database.*;
import android.net.Uri;
import android.os.*;
import android.provider.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

/** QA-only, disk-backed Vault; never packaged in the distributed app. */
public class SyncFixtureProvider extends DocumentsProvider {
 public static final String AUTHORITY="org.researchqa.widgetfixture.documents";
 public static final Uri TREE=Uri.parse("content://"+AUTHORITY+"/tree/vault");
 private static final String[] COLUMNS={DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE,DocumentsContract.Document.COLUMN_FLAGS,DocumentsContract.Document.COLUMN_LAST_MODIFIED};
 private File taskFile(){return new File(getContext().getFilesDir(),"sync-fixture-tasks.md");}
 @Override public boolean onCreate(){return true;}
 @Override public boolean isChildDocument(String parent,String child){return parent.equals("vault")&&(child.equals("tasks")||child.equals("tasks-note")||child.equals("meetings")||child.equals("schedule"))||parent.equals("tasks")&&child.equals("tasks-note")||parent.equals("meetings")&&child.equals("schedule");}
 private MatrixCursor rows(String[] projection){return new MatrixCursor(projection==null?COLUMNS:projection);}
 private void add(MatrixCursor c,String id,String name,boolean dir){MatrixCursor.RowBuilder r=c.newRow();for(String column:c.getColumnNames()){
  Object value=column.equals(DocumentsContract.Document.COLUMN_DOCUMENT_ID)?id:column.equals(DocumentsContract.Document.COLUMN_DISPLAY_NAME)?name:column.equals(DocumentsContract.Document.COLUMN_MIME_TYPE)?dir?DocumentsContract.Document.MIME_TYPE_DIR:"text/markdown":column.equals(DocumentsContract.Document.COLUMN_LAST_MODIFIED)?taskFile().lastModified():0;r.add(column,value);
 }}
 @Override public Cursor queryRoots(String[] projection){return new MatrixCursor(new String[]{DocumentsContract.Root.COLUMN_ROOT_ID,DocumentsContract.Root.COLUMN_DOCUMENT_ID,DocumentsContract.Root.COLUMN_TITLE});}
 @Override public Cursor queryDocument(String id,String[] projection){MatrixCursor c=rows(projection);add(c,id,id.equals("tasks-note")?"할 일.md":id,!id.equals("tasks-note"));return c;}
 @Override public Cursor queryChildDocuments(String parent,String[] projection,String sort){MatrixCursor c=rows(projection);switch(parent){case "vault":add(c,"tasks","Tasks",true);add(c,"meetings","Meetings",true);break;case "tasks":add(c,"tasks-note","할 일.md",false);break;case "meetings":add(c,"schedule","Schedule",true);break;}return c;}
 @Override public ParcelFileDescriptor openDocument(String id,String mode,CancellationSignal cancel)throws FileNotFoundException{if(!id.equals("tasks-note")||!mode.equals("r"))throw new FileNotFoundException(id);return ParcelFileDescriptor.open(taskFile(),ParcelFileDescriptor.MODE_READ_ONLY);}
}
