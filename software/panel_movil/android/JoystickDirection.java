package cl.lumi.panel;

/** Geometry only: independent from connection, motors and Android events. */
final class JoystickDirection {
    static String bank(float x,float y,float radius,String active) {
        String direction=classify(x,y,radius);
        if(direction.equals("parar")) return direction;
        boolean sameHalf=("adelante".equals(active) && y<0) || ("atras".equals(active) && y>0);
        if(sameHalf && Math.abs(x)<=1.2f*Math.abs(y)) return active;
        if(active==null && Math.abs(y)<radius*.35f) return "parar";
        return direction;
    }
    static String classify(float x,float y,float radius) {
        if (Float.isNaN(x) || Float.isInfinite(x) || Float.isNaN(y) || Float.isInfinite(y) || Float.isNaN(radius) || Float.isInfinite(radius) || radius <= 0)
            return "parar";
        if (Math.hypot(x,y) < radius*.25f) return "parar";
        return Math.abs(x)>Math.abs(y) ? (x>0?"derecha":"izquierda") : (y<0?"adelante":"atras");
    }
}
