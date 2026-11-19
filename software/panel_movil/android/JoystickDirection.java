package cl.lumi.panel;

/** Geometry only: independent from connection, motors and Android events. */
final class JoystickDirection {
    static String classify(float x,float y,float radius) {
        if (Float.isNaN(x) || Float.isInfinite(x) || Float.isNaN(y) || Float.isInfinite(y) || Float.isNaN(radius) || Float.isInfinite(radius) || radius <= 0)
            return "parar";
        if (Math.hypot(x,y) < radius*.25f) return "parar";
        return Math.abs(x)>Math.abs(y) ? (x>0?"derecha":"izquierda") : (y<0?"adelante":"atras");
    }
}
