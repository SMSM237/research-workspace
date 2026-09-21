package org.smsm.papercontrol;
public class MeetingDraftTest {
 static void ok(boolean x){if(!x)throw new AssertionError();}
 static void fails(Runnable r){try{r.run();throw new AssertionError();}catch(IllegalArgumentException|java.time.DateTimeException expected){}}
 public static void main(String[] a){
 ok(MeetingDraft.isMeeting("add","meetings",false));ok(!MeetingDraft.isMeeting("add","tasks",true));ok(MeetingDraft.isMeeting("add",null,true));ok(!MeetingDraft.isMeeting("edit","meetings",true));
 String id="11111111-2222-3333-4444-555555555555",title="연구 \"진행\" \\ 검토";
 MeetingDraft d=new MeetingDraft(title,"2026-10-01","15:30",id);MeetingDocument read=new MeetingDocument(d.path,d.text);
 ok(read.title.equals(title));ok(read.date.equals("2026-10-01"));ok(read.time.equals("15:30"));ok(!read.done);ok(d.path.startsWith("Meetings/Schedule/"));ok(!d.text.contains("- [ ]"));
 ok(new MeetingDraft(title,"2026-10-01","15:30",id).text.equals(d.text));
 fails(()->new MeetingDraft("","2026-10-01","15:30",id));fails(()->new MeetingDraft("x\ntype: task","2026-10-01","15:30",id));fails(()->new MeetingDraft("x","2026-02-30","15:30",id));fails(()->new MeetingDraft("x","2026-10-01","25:30",id));fails(()->new MeetingDraft("x","2026-10-01","15:30","../bad"));
 System.out.println("PASS widget-scoped add route, edit isolation, meeting serialization/readback and invalid input rejection");
 }
}
