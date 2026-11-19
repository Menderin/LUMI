package cl.lumi.panel;
import java.net.DatagramSocket;
import java.net.DatagramPacket;
import java.net.SocketTimeoutException;
import java.util.Arrays;
import java.util.concurrent.TimeUnit;

/** Testable UDP exchange: connected peer only, matching reply, bounded wait, no retries. */
final class DatagramRoundTrip {
    interface Matcher { boolean matches(byte[] reply) throws Exception; }
    static byte[] exchange(DatagramSocket socket,byte[] payload,int timeoutMs,Matcher matcher) throws Exception {
        socket.send(new DatagramPacket(payload,payload.length));
        long until=System.nanoTime()+TimeUnit.MILLISECONDS.toNanos(timeoutMs);
        byte[] buffer=new byte[2048];
        while(true) {
            long remaining=until-System.nanoTime();
            if(remaining<=0) throw new SocketTimeoutException();
            socket.setSoTimeout((int)Math.max(1,TimeUnit.NANOSECONDS.toMillis(remaining)));
            DatagramPacket packet=new DatagramPacket(buffer,buffer.length);
            socket.receive(packet);
            byte[] reply=Arrays.copyOfRange(packet.getData(),packet.getOffset(),packet.getOffset()+packet.getLength());
            if(matcher.matches(reply)) return reply;
        }
    }
}
