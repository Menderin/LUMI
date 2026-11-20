package cl.lumi.panel;
import org.json.JSONObject;
import android.os.SystemClock;
final class MotorBankSession {
    private final MotorSessionToken session=new MotorSessionToken();
    synchronized int update(JSONObject state,long started) throws Exception {
        if(state.optInt("protocolo_control")!=3) throw new Exception("Firmware incompatible: se requiere firmware de protocolo 3");
        int update=session.update(state.getLong("boot"),state.getLong("epoch"),state.getLong("seq"),
            state.getLong("uptime_ms"),state.getLong("ticket"),started,SystemClock.elapsedRealtime());
        if(update>=0 && !state.optBoolean("habilitado")) session.endMotion();
        return update;
    }
    synchronized int updateReply(JSONObject reply,long fallbackStarted) throws Exception {
        return update(reply.getJSONObject("banco"),reply.optLong("_request_started_ms",fallbackStarted));
    }
    synchronized JSONObject command(boolean motion) throws Exception {
        long[] v=session.command(SystemClock.elapsedRealtime(),motion);
        return new JSONObject().put("boot",v[0]).put("epoch",v[1]).put("seq",v[2]).put("ticket",v[3]);
    }
    synchronized void beginMotion() throws Exception { session.beginMotion(SystemClock.elapsedRealtime()); }
    synchronized void endMotion() { session.endMotion(); }
    synchronized JSONObject motionCommand() throws Exception {
        long[] v=session.motionCommand();return new JSONObject().put("boot",v[0]).put("epoch",v[1]).put("seq",v[2]).put("ticket",v[3]);
    }
    synchronized boolean needsRefresh() { return session.needsRefresh(SystemClock.elapsedRealtime()); }
    synchronized void clear() { session.clear(); }
}
