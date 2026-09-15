package org.smsm.papercontrol;
/** Local successful-fetch evidence is neither permanent connectivity nor proof of push. */
public final class ConnectionEvidence {
 public static String state(String fetch,long modified,long now,long requested,long failed){
  boolean valid=fetch!=null&&fetch.matches("(?s)[a-fA-F0-9]{40,64}\\t[^\\n]*\\t[^\\n]+(?:\\n.*)?")&&modified>0&&modified<=now+60000&&now-modified<=900000;
  if(valid&&modified>=requested&&modified>=failed)return "verified";
  if(failed>0&&failed>=requested)return "error";
  if(requested>0&&now-requested<60000)return "pending";
  return valid&&requested==0?"verified":"unknown";
 }
}
