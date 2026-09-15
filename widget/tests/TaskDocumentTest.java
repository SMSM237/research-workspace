package org.smsm.papercontrol;
import java.nio.file.*;
public class TaskDocumentTest {
  static void check(boolean x){if(!x)throw new AssertionError();}
  static void fails(Runnable r){try{r.run();throw new AssertionError("Expected refusal");}catch(IllegalArgumentException ok){}}
  public static void main(String[] args)throws Exception {
    String raw="\ufeff# 할 일\r\n- [ ] [[Note|연구]] ➕ 2026-09-10 ⏳ 2026-09-10 ^task-a\r\n- [x] 어제 ✅ 2026-09-14 ^task-b\r\n- [ ] 내일 ⏳ 2026-09-16 ^task-c\r\n```\r\n- [ ] 코드 속 항목\r\n```\r\n";
    TaskDocument d=new TaskDocument(raw);check(d.tasks.size()==3);check(d.today("2026-09-15").size()==1);TaskDocument.Task a=d.tasks.get(0);
    String done=d.toggle(a.key,a.raw,"2026-09-15");check(done.contains("✅ 2026-09-15 ^task-a"));check(done.startsWith("\ufeff"));check(done.contains("\r\n"));
    TaskDocument nd=new TaskDocument(done);check(nd.today("2026-09-15").size()==1);check(nd.today("2026-09-16").size()==1);
    TaskDocument.Task b=nd.tasks.get(0);check(nd.toggle(b.key,b.raw,"2026-09-15").equals(raw));
    String edit=d.edit(a.key,a.raw,"[[Other|새 제목]]");check(edit.contains("[[Other|새 제목]] ➕ 2026-09-10 ⏳ 2026-09-10 ^task-a"));
    fails(()->new TaskDocument(edit).edit(a.key,a.raw,"stale"));fails(()->d.edit(a.key,a.raw,"bad\nline"));fails(()->d.add("injection ✅ 2026-09-15","2026-09-15"));
    fails(()->new TaskDocument(raw+a.raw+"\r\n").toggle(a.key,a.raw,"2026-09-15"));fails(()->new TaskDocument("<<<<<<< HEAD\nconflict"));
    check(new TaskDocument(d.delete(a.key,a.raw)).tasks.size()==2);check(new TaskDocument(d.add("새 일","2026-09-15")).today("2026-09-15").size()==2);
    String reordered="# header changed\r\n"+raw;check(new TaskDocument(reordered).toggle(a.key,a.raw,"2026-09-15").startsWith("# header changed\r\n"));
    if(args.length>0){String real=Files.readString(Path.of(args[0]));TaskDocument actual=new TaskDocument(real);System.out.println("REAL_COPY tasks="+actual.tasks.size()+" today="+actual.today("2026-09-15").size());if(!actual.today("2026-09-15").isEmpty()){TaskDocument.Task t=actual.today("2026-09-15").get(0);String changed=actual.edit(t.key,t.raw,"QA 제목");check(new TaskDocument(changed).tasks.size()==actual.tasks.size());check(changed.contains("^task-"));}}
    System.out.println("PASS: dates, rollover, metadata, CRLF/BOM, links, code blocks, stale edits, duplicate IDs, conflict, add/delete, reorder");
  }
}
