package cl.lumi.panel;
import android.content.Context;
import android.net.wifi.WifiManager;
import android.os.Build;

/** Foreground only. Does not select networks or change system Wi-Fi settings. */
final class ControlWifiPower {
    private WifiManager.WifiLock lock;
    private String status="Sin solicitud de baja latencia";
    synchronized void acquire(Context context) {
        if (lock != null && lock.isHeld()) return;
        try {
            WifiManager manager=(WifiManager)context.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if(manager == null) { status="Wi-Fi no disponible";return; }
            int mode=Build.VERSION.SDK_INT >= 29 ? WifiManager.WIFI_MODE_FULL_LOW_LATENCY : WifiManager.WIFI_MODE_FULL_HIGH_PERF;
            lock=manager.createWifiLock(mode,"LUMI:control");
            lock.setReferenceCounted(false);
            lock.acquire();
            status=Build.VERSION.SDK_INT >= 29 ? "Baja latencia solicitada" : "Alto rendimiento solicitado";
        } catch(RuntimeException error) { lock=null;status="Baja latencia no disponible"; }
    }
    synchronized String status() { return status; }
    synchronized void release() {
        if(lock != null && lock.isHeld()) lock.release();
        lock=null;
    }
}
