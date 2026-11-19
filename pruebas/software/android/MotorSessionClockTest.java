package cl.lumi.panel;

public final class MotorSessionClockTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        MotorSessionClock session = new MotorSessionClock();
        check(session.update(1,1,0,1000,0,100) == 0, "primera sesión");
        long[] first = session.command(100);
        check(first[2] == 1 && first[3] == 1230, "compensar tránsito de respuesta");
        session.update(1,2,1,1100,140,160); // New ACK with new arm generation.
        check(session.update(1,1,0,1050,130,180) == -1, "detectar GET viejo");
        long[] next = session.command(181);
        check(next[1] == 2 && next[2] == 2, "GET viejo no debe revertir epoch/seq");
        check(session.update(2,1,0,20,200,220) == 1, "detectar reinicio");
        check(session.command(221)[2] == 1, "secuencia nueva tras reinicio");
        session.update(2,1,1,30,230,500);
        try { session.command(501); throw new AssertionError("aceptó RTT excesivo"); }
        catch (Exception expected) { check(expected.getMessage().contains("Wi-Fi lento"), "diagnóstico RTT"); }
        session.update(2,1,1,100,501,510);
        try { session.command(1010); throw new AssertionError("aceptó estado vencido"); }
        catch (Exception expected) { check(expected.getMessage().contains("vigente"), "diagnóstico estado"); }
        session.clear();
        try { session.command(1011); throw new AssertionError("aceptó sesión borrada"); }
        catch (Exception expected) { }
        System.out.println("PASS: tránsito, ACK/GET fuera de orden, reinicio, RTT, caducidad y desconexión");
    }
}
