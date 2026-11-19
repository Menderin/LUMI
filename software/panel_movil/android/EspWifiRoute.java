package cl.lumi.panel;

import android.content.Context;
import android.net.ConnectivityManager;
import android.net.LinkAddress;
import android.net.LinkProperties;
import android.net.Network;
import android.net.NetworkCapabilities;
import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;

/** Route only ESP requests through its local-only Wi-Fi, never through cellular. */
final class EspWifiRoute {
    private static Network selectedNetwork;
    private static synchronized Network reuse(Network network) {
        if (selectedNetwork == null || !selectedNetwork.equals(network)) selectedNetwork = network;
        return selectedNetwork;
    }
    static HttpURLConnection open(Context context, URL url) throws IOException {
        if (!"192.168.4.1".equals(url.getHost())) return (HttpURLConnection)url.openConnection();
        return (HttpURLConnection) find(context).openConnection(url);
    }
    static void bind(Context context, java.net.DatagramSocket socket) throws IOException {
        find(context).bindSocket(socket);
    }
    private static Network find(Context context) throws IOException {
        ConnectivityManager manager = (ConnectivityManager)
                context.getSystemService(Context.CONNECTIVITY_SERVICE);
        if (manager != null) {
            for (Network network : manager.getAllNetworks()) {
                NetworkCapabilities capabilities = manager.getNetworkCapabilities(network);
                LinkProperties properties = manager.getLinkProperties(network);
                if (capabilities == null || properties == null ||
                        !capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) continue;
                for (LinkAddress address : properties.getLinkAddresses()) {
                    byte[] bytes = address.getAddress().getAddress();
                    if (bytes.length == 4 && (bytes[0] & 255) == 192 &&
                            (bytes[1] & 255) == 168 && (bytes[2] & 255) == 4) {
                        // Do not require INTERNET or VALIDATED for this private AP.
                        // Reuse the Network instance and its HTTP connection pool.
                        return reuse(network);
                    }
                }
            }
        }
        throw new IOException("Conecta a LUMI-BANCO y acepta permanecer sin Internet");
    }
}
