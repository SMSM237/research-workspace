package org.smsm.papercontrol;
public class RefreshJob extends android.app.job.JobService {
 @Override public boolean onStartJob(android.app.job.JobParameters p){new Thread(()->{PaperWidget.updateAll(this);jobFinished(p,false);},"widget-refresh").start();return true;}
 @Override public boolean onStopJob(android.app.job.JobParameters p){return false;}
}
