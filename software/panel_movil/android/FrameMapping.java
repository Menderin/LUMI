package cl.lumi.panel;

/** Geometria del video FIT_CENTER, compartida por dibujo y toque. */
final class FrameMapping {
    final float scale, left, top;
    final int width, height;
    FrameMapping(int imageWidth, int imageHeight, int viewWidth, int viewHeight) {
        width=imageWidth; height=imageHeight;
        scale=Math.min((float)viewWidth/imageWidth,(float)viewHeight/imageHeight);
        left=(viewWidth-imageWidth*scale)/2f;
        top=(viewHeight-imageHeight*scale)/2f;
    }
    float[] imagePoint(float x,float y) {
        if(scale<=0) return null;
        float ix=(x-left)/scale, iy=(y-top)/scale;
        return ix>=0 && iy>=0 && ix<width && iy<height ? new float[]{ix,iy}:null;
    }
}
