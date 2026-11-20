package cl.lumi.panel;
import java.net.*;

/** Socket lifetime is independent of command acceptance or acknowledgement timeouts. */
final class PersistentDatagramEndpoint {
    interface Binder { void bind(DatagramSocket socket) throws Exception; }
    private DatagramSocket socket;
    private Object route;
    private long generation;
    synchronized DatagramSocket ensure(Object nextRoute,Binder binder,InetAddress peer,int port) throws Exception {
        if(socket!=null && !socket.isClosed() && nextRoute.equals(route)) return socket;
        close();
        DatagramSocket candidate=new DatagramSocket();
        try {
            binder.bind(candidate);candidate.connect(peer,port);
            socket=candidate;route=nextRoute;++generation;return socket;
        } catch(Exception error) { candidate.close();throw error; }
    }
    synchronized long generation() { return generation; }
    synchronized void failed(DatagramSocket failed,Exception error) { if(socket==failed) failed(error); }
    synchronized void failed(Exception error) {
        // Timeouts and protocol NACKs leave the channel intact.
        if(error instanceof SocketException) close();
    }
    synchronized void close() { if(socket!=null) socket.close();socket=null;route=null; }
}
