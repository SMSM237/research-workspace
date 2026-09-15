package org.smsm.papercontrol;
import java.time.*;
import java.util.regex.*;
/** Small supported frontmatter subset; the original body and unrelated properties survive edits. */
public final class MeetingDocument {
 public final String path,raw,title,date,time,minutes;public final boolean done;
 private final int end;private final String sep;
 public MeetingDocument(String path,String raw){
  if(!path.startsWith("Meetings/Schedule/")||path.contains("..")||path.contains("\\")||!path.endsWith(".md"))throw new IllegalArgumentException("회의 경로를 확인해 주세요.");
  this.path=path;this.raw=raw;sep=raw.contains("\r\n")?"\r\n":"\n";
  if(!raw.startsWith("---"+sep))throw new IllegalArgumentException("회의 속성을 읽지 못했습니다.");
  end=raw.indexOf(sep+"---",3);if(end<0)throw new IllegalArgumentException("회의 속성이 불완전합니다.");
  date=field("date");time=field("time");title=field("title");minutes=field("minutes");done=field("completed").equals("true");
  LocalDate.parse(date);if(!time.isEmpty())LocalTime.parse(time);if(title.isEmpty())throw new IllegalArgumentException("회의 제목이 없습니다.");
 }
 private String field(String key){Matcher m=Pattern.compile("(?m)^"+key+":[ \t]*([^\r\n]*)").matcher(raw.substring(0,end));String found="";int count=0;while(m.find()){found=m.group(1).trim();count++;}if(count>1)throw new IllegalArgumentException("회의 속성이 중복됩니다.");if(found.startsWith("\"")&&found.endsWith("\""))found=found.substring(1,found.length()-1).replace("\\\"","\"").replace("\\\\","\\");return found;}
 public boolean upcoming(String today){return date.compareTo(today)>=0;}
 public String toggle(String day){LocalDate.parse(day);String head=raw.substring(0,end);head=head.replaceAll("(?m)^completed(?:_date)?:[^\r\n]*(?:\r?\n|$)","");if(!head.endsWith(sep))head+=sep;return head+"completed: "+(!done)+(done?"":sep+"completed_date: "+day)+raw.substring(end);}
 public String when(){return date.substring(5).replace('-','.')+(time.isEmpty()?"":"  "+time);}
}
