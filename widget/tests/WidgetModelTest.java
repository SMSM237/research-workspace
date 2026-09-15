package org.smsm.papercontrol;
public class WidgetModelTest {
 static void ok(boolean v){if(!v)throw new AssertionError();}
 public static void main(String[] a){
  String raw="---\r\ntype: meeting_schedule\r\ndate: 2026-09-16\r\ntime: 09:30\r\ntitle: 연구 회의\r\nminutes: Meetings/Minutes/existing.md\r\ncompleted: false\r\n---\r\n# 준비\r\n본문 그대로\r\n";
  MeetingDocument d=new MeetingDocument("Meetings/Schedule/test.md",raw);ok(d.title.equals("연구 회의"));ok(d.upcoming("2026-09-15"));ok(!d.upcoming("2026-09-17"));
  String done=d.toggle("2026-09-16");ok(done.contains("completed: true\r\n"));ok(done.contains("completed_date: 2026-09-16\r\n"));ok(done.endsWith("본문 그대로\r\n"));ok(done.contains("minutes: Meetings/Minutes/existing.md"));ok(new MeetingDocument(d.path,done).done);
  ok(!new MeetingDocument(d.path,done).toggle("2026-09-16").contains("completed_date:"));
  try{new MeetingDocument("../bad.md",raw);throw new AssertionError();}catch(IllegalArgumentException expected){}
  String fetch="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\t\tbranch 'main' of https://github.com/example/repo\n";long now=10000000;
  ok(ConnectionEvidence.state(fetch,now-1000,now,0,0).equals("verified"));ok(ConnectionEvidence.state(fetch,now-1000000,now,0,0).equals("unknown"));ok(ConnectionEvidence.state("",now,now,0,0).equals("unknown"));
  ok(ConnectionEvidence.state(fetch,now-1000,now,now-500,0).equals("pending"));ok(ConnectionEvidence.state(fetch,now-1000,now,now-500,now-200).equals("error"));ok(ConnectionEvidence.state(fetch,now,now,now-500,now-200).equals("verified"));
  System.out.println("PASS meeting schema/metadata/dates and truthful fresh Git evidence");
 }
}
