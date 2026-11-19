package cl.lumi.panel;
import org.json.JSONObject;
import android.os.SystemClock;
final class MotorBankSession {
    private final MotorSessionToken session = new MotorSessionToken();
    synchronized int update(JSONObject state, long started) throws Exception {
        if (state.optInt("protocolo_control") != 2)
            throw new Exception("Firmware antiguo: actualiza la ESP para LUMI 0.5.0");
        return session.update(state.getLong("boot"),state.getLong("epoch"),state.getLong("seq"),
            state.getLong("uptime_ms"),state.getLong("ticket"),SystemClock.elapsedRealtime());
    }
    synchronized JSONObject command() throws Exception {
        long[] v=session.command(SystemClock.elapsedRealtime());
        return new JSONObject().put("boot",v[0]).put("epoch",v[1]).put("seq",v[2]).put("ticket",v[3]);
    }
    synchronized boolean needsRefresh() { return session.needsRefresh(SystemClock.elapsedRealtime()); }
    synchronized void clear() { session.clear(); }
}
