package org.smsm.papercontrol;
import java.time.LocalDate;
import java.util.*;
import java.util.regex.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Same Markdown/date rules as the deployed Obsidian dashboard. No Android APIs. */
public final class TaskDocument {
  private static final Pattern ROW=Pattern.compile("^(\\s*[-*+] \\[([ xX])\\]\\s+)(.+)$");
  private static final Pattern META=Pattern.compile("(?:📅|✅|➕|⏳)\\s*\\d{4}-\\d{2}-\\d{2}");
  private static final Pattern ID=Pattern.compile("\\s+(\\^[\\w-]+)\\s*$");
  public static final class Task {
    public final int line;public final String raw,key,title,editable,created,scheduled,completed;public final boolean done;
    Task(int i,String r,Matcher m){line=i;raw=r;done=m.group(2).equalsIgnoreCase("x");Matcher id=ID.matcher(r);key=id.find()?id.group(1):"raw:"+hash(r);editable=META.matcher(m.group(3)).replaceAll("").replaceAll("\\s*\\^[\\w-]+\\s*$","").trim();
      title=editable.replaceAll("\\[\\[([^\\]|]+)\\|([^\\]]+)\\]\\]","$2").replaceAll("\\[\\[([^\\]]+)\\]\\]","$1");created=date(r,"➕");scheduled=date(r,"⏳");completed=date(r,"✅");}
    public String start(){return scheduled.isEmpty()?created:scheduled;}
  }
  private final String text,sep;private final String[] lines;public final List<Task> tasks=new ArrayList<>();
  public TaskDocument(String text){
    if(text.length()>524288)throw new IllegalArgumentException("할 일 파일이 너무 큽니다.");
    if(Pattern.compile("^(<<<<<<<|=======|>>>>>>>)",Pattern.MULTILINE).matcher(text).find())throw new IllegalArgumentException("Git 충돌을 먼저 해결해 주세요.");
    this.text=text;sep=text.contains("\r\n")?"\r\n":"\n";lines=text.split("\\r?\\n",-1);String fence="";
    for(int i=0;i<lines.length;i++){String r=lines[i];Matcher f=Pattern.compile("^\\s*(`{3,}|~{3,})").matcher(r);if(f.find()){String c=f.group(1).substring(0,1);if(fence.isEmpty())fence=c;else if(fence.equals(c))fence="";continue;}if(!fence.isEmpty())continue;Matcher m=ROW.matcher(r);if(m.matches())tasks.add(new Task(i,r,m));}
  }
  public static String hash(String text){try{StringBuilder s=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)))s.append(String.format(Locale.ROOT,"%02x",b&255));return s.toString();}catch(Exception e){throw new IllegalStateException(e);}}
  private static String date(String r,String symbol){Matcher m=Pattern.compile(symbol+"\\s*(\\d{4}-\\d{2}-\\d{2})").matcher(r);if(!m.find())return "";try{return LocalDate.parse(m.group(1)).toString();}catch(Exception e){return "";}}
  public List<Task> today(String day){LocalDate.parse(day);List<Task> result=new ArrayList<>();for(Task t:tasks)if((t.done&&t.completed.equals(day))||(!t.done&&(t.start().isEmpty()||t.start().compareTo(day)<=0)))result.add(t);result.sort(Comparator.comparing(t->t.done));return result;}
  public Task exact(String key,String expectedRaw){List<Task> found=new ArrayList<>();for(Task t:tasks)if(t.key.equals(key))found.add(t);if(found.size()!=1||!found.get(0).raw.equals(expectedRaw))throw new IllegalArgumentException("다른 곳에서 할 일이 변경되었습니다. 새로고침 후 다시 선택해 주세요.");return found.get(0);}
  private String replace(Task t,String row,boolean delete){List<String> next=new ArrayList<>(Arrays.asList(lines));if(delete)next.remove(t.line);else next.set(t.line,row);return String.join(sep,next);}
  public String toggle(String key,String expectedRaw,String day){LocalDate.parse(day);Task t=exact(key,expectedRaw);String row=t.raw.replaceFirst("\\[[ xX]\\]",t.done?"[ ]":"[x]").replaceAll("\\s*✅\\s*\\d{4}-\\d{2}-\\d{2}","");if(!t.done){Matcher id=ID.matcher(row);row=id.find()?row.substring(0,id.start())+" ✅ "+day+" "+id.group(1):row+" ✅ "+day;}return replace(t,row,false);}
  public static String cleanTitle(String value){String t=value.trim();if(t.isEmpty()||t.length()>500||t.contains("\r")||t.contains("\n")||META.matcher(t).find()||Pattern.compile("\\^[\\w-]+\\s*$").matcher(t).find())throw new IllegalArgumentException("할 일 내용을 한 줄로 입력해 주세요. 날짜와 ID는 자동으로 유지됩니다.");return t;}
  public String edit(String key,String expectedRaw,String title){Task t=exact(key,expectedRaw);title=cleanTitle(title);if(title.equals(t.editable))return text;Matcher prefix=ROW.matcher(t.raw);prefix.matches();StringBuilder row=new StringBuilder(prefix.group(1)).append(title);Matcher metadata=META.matcher(t.raw);while(metadata.find())row.append(' ').append(metadata.group());Matcher id=ID.matcher(t.raw);if(id.find())row.append(' ').append(id.group(1));return replace(t,row.toString(),false);}
  public String delete(String key,String expectedRaw){return replace(exact(key,expectedRaw),"",true);}
  public String add(String title,String day){LocalDate.parse(day);String row="- [ ] "+cleanTitle(title)+" ➕ "+day+" ⏳ "+day+" ^task-"+UUID.randomUUID().toString().replace("-","");return text+(text.isEmpty()||text.endsWith("\n")?"":sep)+row+sep;}
}
