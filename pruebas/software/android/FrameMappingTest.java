package cl.lumi.panel;

public final class FrameMappingTest {
    public static void main(String[] args) {
        FrameMapping map=new FrameMapping(640,480,1000,500);
        float[] center=map.imagePoint(500,250);
        if(center==null||Math.abs(center[0]-320)>.01||Math.abs(center[1]-240)>.01)throw new AssertionError("Centro incorrecto");
        if(map.imagePoint(20,250)!=null)throw new AssertionError("Acepto banda lateral");
        map=new FrameMapping(640,480,400,500);
        if(map.imagePoint(200,20)!=null)throw new AssertionError("Acepto banda superior");
        float[] p=map.imagePoint(map.left+100*map.scale,map.top+200*map.scale);
        if(p==null||Math.abs(p[0]-100)>.01||Math.abs(p[1]-200)>.01)throw new AssertionError("Punto incorrecto");
        System.out.println("FrameMapping: OK");
    }
}
