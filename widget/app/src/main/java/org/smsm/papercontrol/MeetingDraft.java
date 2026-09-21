package org.smsm.papercontrol;
import java.time.*;
/** Dashboard-compatible meeting creation. No task source is involved. */
public final class MeetingDraft {
 public final String path,text;
 public static boolean isMeeting(String action,String kind,boolean widgetMeeting){return "add".equals(action)&&("meetings".equals(kind)||(kind==null&&widgetMeeting));}
 public static String title(String s){if(s==null||s.trim().isEmpty()||s.trim().length()>300||s.chars().anyMatch(c->c<32))throw new IllegalArgumentException("회의 제목을 한 줄로 입력해 주세요.");return s.trim();}
 public MeetingDraft(String title,String day,String time,String id){
  title=title(title);LocalDate.parse(day);if(!time.matches("(?:[01]\\d|2[0-3]):[0-5]\\d"))throw new IllegalArgumentException("회의 시간을 확인해 주세요.");
  if(!id.matches("[a-f0-9-]{36}"))throw new IllegalArgumentException("회의 저장 ID를 확인해 주세요.");
  path="Meetings/Schedule/"+day+" "+time.replace(":","")+" widget-"+id+".md";
  String quoted=title.replace("\\","\\\\").replace("\"","\\\"");
  text="---\ntype: meeting_schedule\ndate: "+day+"\ntime: \""+time+"\"\ntitle: \""+quoted+"\"\ncompleted: false\n---\n# "+title+"\n\n## 관련 프로젝트·논문\n\n## 준비할 내용\n\n## 회의록\n\n";
 }
}
