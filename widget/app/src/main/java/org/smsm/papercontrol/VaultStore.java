package org.smsm.papercontrol;
import android.content.*;
import android.database.Cursor;
import android.net.Uri;
import android.provider.DocumentsContract;
import java.io.*;
import java.nio.charset.*;
import java.time.*;
import java.util.*;
import org.json.*;

/** Access only the user-selected SAF tree. No broad storage or network access. */
public final class VaultStore {
  public static final Object WRITE_LOCK=new Object();
  private final Context context;private final ContentResolver resolver;
  public VaultStore(Context c){context=c.getApplicationContext();resolver=context.getContentResolver();}
  public static SharedPreferences prefs(Context c){return c.getSharedPreferences("papercontrol",Context.MODE_PRIVATE);}
  public String source(){return prefs(context).getString("source","Tasks/할 일.md");}
  public static String day(){return java.time.LocalDate.now().toString();}
  public Uri root(){String s=prefs(context).getString("tree","");if(s.isEmpty())throw new IllegalStateException("앱에서 Vault 폴더를 먼저 선택해 주세요.");Uri t=Uri.parse(s);return DocumentsContract.buildDocumentUriUsingTree(t,DocumentsContract.getTreeDocumentId(t));}
  public List<String> names(String path)throws Exception{Uri parent=resolve(path,false,true);List<String> names=new ArrayList<>();if(parent==null)return names;Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(parent,DocumentsContract.getDocumentId(parent));try(Cursor c=resolver.query(children,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null)){if(c==null)throw new IOException("폴더를 읽지 못했습니다.");while(c.moveToNext()){if(names.size()>=1000)throw new IOException("폴더에 파일이 너무 많습니다.");names.add(c.getString(0));}}return names;}
  public Uri resolve(String path,boolean create,boolean folder)throws Exception{
    if(path.startsWith("/")||path.contains("\\")||path.contains(":"))throw new IOException("Vault 안의 상대 경로를 사용해 주세요.");
    Uri parent=root();if(path.isEmpty())return parent;String[] parts=path.split("/",-1);
    for(int i=0;i<parts.length;i++){
      String part=parts[i];if(part.isEmpty()||part.equals(".")||part.equals(".."))throw new IOException("잘못된 파일 경로입니다.");
      Uri child=null;String mime=null;Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(parent,DocumentsContract.getDocumentId(parent));
      try(Cursor c=resolver.query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME,DocumentsContract.Document.COLUMN_MIME_TYPE},null,null,null)){
        if(c==null)throw new IOException("Vault 읽기 권한을 확인해 주세요.");int count=0;
        while(c.moveToNext()){if(++count>5000)throw new IOException("폴더에 항목이 너무 많습니다.");if(part.equals(c.getString(1))){if(child!=null)throw new IOException("같은 이름의 파일이 여러 개입니다.");child=DocumentsContract.buildDocumentUriUsingTree(parent,c.getString(0));mime=c.getString(2);}}
      }
      boolean dir=i<parts.length-1||folder;
      if(child==null){if(!create)return null;mime=dir?DocumentsContract.Document.MIME_TYPE_DIR:part.endsWith(".json")?"application/json":part.endsWith(".md")?"text/markdown":"application/octet-stream";child=DocumentsContract.createDocument(resolver,parent,mime,part);if(child==null)throw new IOException("파일을 만들지 못했습니다.");try(Cursor created=resolver.query(child,new String[]{DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null)){if(created==null||!created.moveToFirst()||!part.equals(created.getString(0)))throw new IOException("파일 제공자가 이름을 변경했습니다. 로컬 Vault 폴더를 선택해 주세요.");}}
      if(dir!=DocumentsContract.Document.MIME_TYPE_DIR.equals(mime))throw new IOException("파일과 폴더 경로를 확인해 주세요.");parent=child;
    }return parent;
  }
  public String read(String path)throws Exception{Uri uri=resolve(path,false,false);if(uri==null)throw new FileNotFoundException("파일이 없습니다: "+path);return readUri(uri);}
  private String readUri(Uri uri)throws Exception{try(InputStream in=resolver.openInputStream(uri)){if(in==null)throw new IOException("파일을 열지 못했습니다.");ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[8192];int n;while((n=in.read(b))!=-1){if(out.size()+n>1048576)throw new IOException("파일이 1MB를 넘습니다.");out.write(b,0,n);}return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(java.nio.ByteBuffer.wrap(out.toByteArray())).toString();}}
  private void writeUri(Uri uri,String text)throws Exception{try(OutputStream out=resolver.openOutputStream(uri,"wt")){if(out==null)throw new IOException("쓰기 권한이 없습니다.");out.write(text.getBytes(StandardCharsets.UTF_8));}if(!readUri(uri).equals(text))throw new IOException("저장 확인에 실패했습니다. 앱 안에 복구 사본을 보관했습니다.");}
  public void writeNew(String path,String text)throws Exception{if(resolve(path,false,false)!=null)throw new IOException("이미 있는 파일입니다.");writeUri(resolve(path,true,false),text);}
  private void backup(String before)throws Exception{File dir=new File(context.getFilesDir(),"task-backups");if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("백업 폴더를 만들지 못했습니다.");File f=new File(dir,System.currentTimeMillis()+"-"+TaskDocument.hash(before).substring(0,12)+".md");try(OutputStream out=new FileOutputStream(f)){out.write(before.getBytes(StandardCharsets.UTF_8));}File[] files=dir.listFiles();if(files!=null&&files.length>20){Arrays.sort(files,Comparator.comparing(File::getName));for(int i=0;i<files.length-20;i++)files[i].delete();}}
  public void change(String action,String key,String expected,String title)throws Exception{synchronized(WRITE_LOCK){String path=source(),before=read(path);TaskDocument d=new TaskDocument(before);String after;
    switch(action){case "toggle":after=d.toggle(key,expected,day());break;case "edit":after=d.edit(key,expected,title);break;case "delete":after=d.delete(key,expected);break;case "add":after=d.add(title,day());break;default:throw new IOException("알 수 없는 동작입니다.");}
    if(after.equals(before))return;backup(before);Uri uri=resolve(path,false,false);if(uri==null||!readUri(uri).equals(before))throw new IOException("다른 앱에서 파일이 변경되었습니다. 다시 선택해 주세요.");writeUri(uri,after);
    // Same daily activity identity used by the Obsidian dashboard.
    String activity=".research-activity/"+day()+"/"+TaskDocument.hash(path)+".json";
    try{if(resolve(activity,false,false)==null)writeNew(activity,new JSONObject().put("day",day()).put("path",path).toString());}catch(Exception ignored){/* Task success remains durable; dashboard can discover the edit after sync. */}
    prefs(context).edit().putString("notice","저장됨 · 동기화 전").apply();
  }}
  public String requestAnalysis()throws Exception{synchronized(WRITE_LOCK){
    Set<String> terminal=new HashSet<>(Arrays.asList("complete","verified","empty","cancelled"));
    for(String name:names(".paper-control/requests"))if(name.matches("[a-f0-9-]{36}\\.json")){
      String id=name.substring(0,36);JSONObject r=new JSONObject(read(".paper-control/requests/"+name));if(!id.equals(r.optString("id")))throw new IOException("실행 요청 ID를 확인해 주세요.");
      String phase="pending";Uri status=resolve(".paper-control/status/"+name,false,false);
      if(status!=null){JSONObject s=new JSONObject(readUri(status));if(!id.equals(s.optString("id")))throw new IOException("실행 상태 ID를 확인해 주세요.");phase=s.optString("state","pending");}
      if(!terminal.contains(phase))return id;
    }
    String id=UUID.randomUUID().toString();JSONObject r=new JSONObject().put("version",1).put("id",id).put("action","analyze-inbox").put("createdAt",Instant.now().toString()).put("maxPapers",10);
    writeNew(".paper-control/requests/"+id+".json",r.toString(2));prefs(context).edit().putString("notice","분석 요청 저장 · 동기화 전").apply();return id;
  }}
  public String analysisState(){try{JSONObject latest=null;for(String n:names(".paper-control/requests")){if(!n.matches("[a-f0-9-]{36}\\.json"))continue;JSONObject r=new JSONObject(read(".paper-control/requests/"+n));if(latest==null||r.optString("createdAt").compareTo(latest.optString("createdAt"))>0)latest=r;}if(latest==null)return "분석 요청 없음";String id=latest.optString("id");if(!id.matches("[a-f0-9-]{36}"))return "상태 확인 필요";Uri uri=resolve(".paper-control/status/"+id+".json",false,false);if(uri==null)return "PC 접수 대기";JSONObject s=new JSONObject(readUri(uri));if(!id.equals(s.optString("id")))return "상태 확인 필요";switch(s.optString("state")){case "queued":return "Codex 실행 대기";case "running":return "분석 중";case "complete":return "Git 게시 완료";case "verified":return "연결 확인 완료";case "empty":return "새 논문 없음";case "blocked":return "분석 조치 필요";case "waiting":return "분석 확인 대기";default:return "분석 요청 대기";}}catch(Exception e){return "분석 상태 확인 필요";}}
  public List<MeetingDocument> meetings()throws Exception{List<MeetingDocument> rows=new ArrayList<>();for(String name:names("Meetings/Schedule")){if(!name.endsWith(".md"))continue;MeetingDocument d=new MeetingDocument("Meetings/Schedule/"+name,read("Meetings/Schedule/"+name));if(d.upcoming(day()))rows.add(d);}rows.sort(Comparator.comparing((MeetingDocument d)->d.date+" "+d.time).thenComparing(d->d.title));return rows;}
  public void toggleMeeting(String path,String expected)throws Exception{synchronized(WRITE_LOCK){String before=read(path);if(!TaskDocument.hash(before).equals(expected))throw new IOException("다른 곳에서 회의가 변경되었습니다. 다시 선택해 주세요.");MeetingDocument d=new MeetingDocument(path,before);String after=d.toggle(day());backup(before);Uri uri=resolve(path,false,false);if(uri==null||!readUri(uri).equals(before))throw new IOException("회의가 변경되었습니다. 다시 선택해 주세요.");writeUri(uri,after);}}
  public String gitState(){String fetch="";long modified=0;try{Uri uri=resolve(".git/FETCH_HEAD",false,false);if(uri!=null){fetch=readUri(uri);try(Cursor cur=resolver.query(uri,new String[]{DocumentsContract.Document.COLUMN_LAST_MODIFIED},null,null,null)){if(cur!=null&&cur.moveToFirst())modified=cur.getLong(0);}}}catch(Exception ignored){}return ConnectionEvidence.state(fetch,modified,System.currentTimeMillis(),prefs(context).getLong("git_requested",0),prefs(context).getLong("git_failed",0));}
  public String gitDetail(){String state=gitState();return state.equals("verified")?"최근 15분 안에 이 Vault의 Git 원격 읽기가 성공한 기록을 확인했습니다. 지금의 상시 연결이나 업로드 완료를 뜻하지 않습니다.":state.equals("pending")?"Git 동기화를 요청했습니다. 성공 기록을 기다리고 있습니다.":state.equals("error")?"Git 동기화 앱으로 요청을 전달하지 못했습니다. 연결 설정을 확인해 주세요.":"이 기기에서 최근 Git 성공 기록을 확인하지 못했습니다. 저장이나 분석기 진단 결과를 Git 연결 성공으로 표시하지 않습니다.";}
}
