package org.smsm.papercontrol.fixture;
import android.app.Activity;
import android.os.Bundle;
public class Receiver extends Activity { @Override public void onCreate(Bundle b){super.onCreate(b);android.util.Log.i("QA_URI_RECEIVER",String.valueOf(getIntent().getData()));finish();} }
