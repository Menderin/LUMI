package cl.lumi.panel;

import android.content.Context;
import android.os.SystemClock;
import org.json.JSONObject;
import org.webrtc.*;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Receptor WebRTC nativo, solo video, sin camara/microfono ni servidores ICE externos. */
final class NativeWebRtc {
    interface Signaling {
        JSONObject offer(JSONObject body)throws Exception;
        void close(String session)throws Exception;
    }
    private final EglBase egl=EglBase.create();
    private final PeerConnectionFactory factory;
    private final SurfaceViewRenderer renderer;
    private final ExecutorService network=Executors.newSingleThreadExecutor();
    private final VideoFrameStats frames=new VideoFrameStats();
    private volatile PeerConnection peer;
    private volatile long generation,lastFrame,lastAttempt;
    private volatile boolean starting,sent;
    private volatile String state="Desconectado",session="";
    private Signaling signaling;
    private volatile int videoWidth=640,videoHeight=480;

    NativeWebRtc(Context context){
        PeerConnectionFactory.initialize(PeerConnectionFactory.InitializationOptions.builder(context)
            .setEnableInternalTracer(false).createInitializationOptions());
        PeerConnectionFactory.Options options=new PeerConnectionFactory.Options();
        options.networkIgnoreMask=PeerConnectionFactory.Options.ADAPTER_TYPE_CELLULAR;
        factory=PeerConnectionFactory.builder().setOptions(options)
            .setVideoDecoderFactory(new DefaultVideoDecoderFactory(egl.getEglBaseContext()))
            .createPeerConnectionFactory();
        renderer=new SurfaceViewRenderer(context);
        renderer.init(egl.getEglBaseContext(),null);
        renderer.setScalingType(RendererCommon.ScalingType.SCALE_ASPECT_FIT);
        renderer.setEnableHardwareScaler(true);
    }
    SurfaceViewRenderer view(){return renderer;}
    void fit(){
        if(!(renderer.getParent() instanceof android.view.View))return;
        android.view.View parent=(android.view.View)renderer.getParent();
        int w=parent.getWidth(),h=parent.getHeight();if(w==0||h==0)return;
        double scale=Math.min(w/(double)videoWidth,h/(double)videoHeight);
        int width=Math.max(1,(int)(videoWidth*scale)),height=Math.max(1,(int)(videoHeight*scale));
        android.widget.FrameLayout.LayoutParams old=(android.widget.FrameLayout.LayoutParams)renderer.getLayoutParams();
        if(old.width!=width||old.height!=height)
            renderer.setLayoutParams(new android.widget.FrameLayout.LayoutParams(width,height,android.view.Gravity.CENTER));
    }
    void visible(boolean value){
        renderer.setVisibility(value?android.view.View.VISIBLE:android.view.View.GONE);
        if(value)renderer.disableFpsReduction();else renderer.pauseVideo();
    }
    String state(){
        if(lastFrame>0 && SystemClock.elapsedRealtime()-lastFrame>1800)return "Sin video reciente";
        return state;
    }
    double fps(){synchronized(frames){return frames.fps(SystemClock.elapsedRealtime());}}
    boolean needsRestart(){
        long now=SystemClock.elapsedRealtime();
        if(starting && now-lastAttempt>15000){state="Error: negociacion agotada; revisa UDP 50000-50009";starting=false;}
        return !starting && now-lastAttempt>5000 &&
            (peer==null || state.startsWith("Error") || (lastFrame==0 && now-lastAttempt>10000) || (lastFrame>0 && now-lastFrame>4000));
    }

    void start(Signaling transport){
        stop();
        signaling=transport;long ticket=++generation;
        starting=true;sent=false;state="Negociando";lastAttempt=SystemClock.elapsedRealtime();lastFrame=0;
        synchronized(frames){frames.reset();}
        PeerConnection.RTCConfiguration config=new PeerConnection.RTCConfiguration(Collections.emptyList());
        config.sdpSemantics=PeerConnection.SdpSemantics.UNIFIED_PLAN;
        config.bundlePolicy=PeerConnection.BundlePolicy.MAXBUNDLE;
        config.tcpCandidatePolicy=PeerConnection.TcpCandidatePolicy.DISABLED;
        config.networkPreference=PeerConnection.AdapterType.WIFI;
        config.continualGatheringPolicy=PeerConnection.ContinualGatheringPolicy.GATHER_ONCE;
        peer=factory.createPeerConnection(config,new PeerConnection.Observer(){
            public void onSignalingChange(PeerConnection.SignalingState s){}
            public void onIceConnectionChange(PeerConnection.IceConnectionState s){
                if(ticket!=generation)return;
                if(s==PeerConnection.IceConnectionState.FAILED){state="Error ICE: revisa UDP 50000-50009";starting=false;}
            }
            public void onConnectionChange(PeerConnection.PeerConnectionState s){
                if(ticket!=generation)return;
                if(s==PeerConnection.PeerConnectionState.CONNECTED){state="Conectado";starting=false;}
                else if(s==PeerConnection.PeerConnectionState.FAILED){state="Error de conexion WebRTC";starting=false;}
            }
            public void onIceConnectionReceivingChange(boolean value){}
            public void onIceGatheringChange(PeerConnection.IceGatheringState s){
                if(s==PeerConnection.IceGatheringState.COMPLETE)sendOffer(ticket);
            }
            public void onIceCandidate(IceCandidate candidate){}
            public void onIceCandidatesRemoved(IceCandidate[] candidates){}
            public void onAddStream(MediaStream stream){}
            public void onRemoveStream(MediaStream stream){}
            public void onDataChannel(DataChannel channel){channel.close();}
            public void onRenegotiationNeeded(){}
            public void onTrack(RtpTransceiver transceiver){
                if(ticket!=generation)return;
                MediaStreamTrack track=transceiver.getReceiver().track();
                if(track instanceof VideoTrack)((VideoTrack)track).addSink(frame->{
                    if(ticket!=generation)return;
                    long now=SystemClock.elapsedRealtime();lastFrame=now;state="Conectado";starting=false;
                    synchronized(frames){frames.record(Long.toString(frame.getTimestampNs()),now);}
                    int width=frame.getRotatedWidth(),height=frame.getRotatedHeight();
                    if(width!=videoWidth||height!=videoHeight){videoWidth=width;videoHeight=height;renderer.post(()->fit());}
                    renderer.onFrame(frame);
                });
            }
        });
        if(peer==null){state="Error creando receptor WebRTC";starting=false;return;}
        PeerConnection current=peer;
        current.addTransceiver(MediaStreamTrack.MediaType.MEDIA_TYPE_VIDEO,
            new RtpTransceiver.RtpTransceiverInit(RtpTransceiver.RtpTransceiverDirection.RECV_ONLY));
        current.createOffer(new Observer(){
            public void onCreateSuccess(SessionDescription sdp){
                if(ticket!=generation)return;
                current.setLocalDescription(new Observer(){
                    public void onSetSuccess(){sendOffer(ticket);}
                    public void onSetFailure(String error){fail(ticket,error);}
                },sdp);
            }
            public void onCreateFailure(String error){fail(ticket,error);}
        },new MediaConstraints());
    }

    private synchronized void sendOffer(long ticket){
        PeerConnection current=peer;
        if(ticket!=generation||sent||current==null||current.getLocalDescription()==null ||
            current.iceGatheringState()!=PeerConnection.IceGatheringState.COMPLETE)return;
        sent=true;
        SessionDescription local=current.getLocalDescription();
        Signaling transport=signaling;
        network.execute(()->{
            try{
                JSONObject request=new JSONObject();request.put("sdp",local.description);request.put("type","offer");
                JSONObject answer=transport.offer(request);
                String id=answer.getString("sesion");
                if(ticket!=generation){transport.close(id);return;}
                session=id;
                current.setRemoteDescription(new Observer(){
                    public void onSetSuccess(){if(ticket==generation)state="Conectando UDP";}
                    public void onSetFailure(String error){fail(ticket,error);}
                },new SessionDescription(SessionDescription.Type.ANSWER,answer.getString("sdp")));
            }catch(Exception error){fail(ticket,error.getMessage());}
        });
    }
    private void fail(long ticket,String message){
        if(ticket==generation){state="Error: "+message;starting=false;}
    }
    void stop(){
        generation++;starting=false;sent=false;lastFrame=0;
        PeerConnection old=peer;peer=null;
        if(old!=null){old.close();old.dispose();}
        renderer.clearImage();
        String oldSession=session;session="";Signaling transport=signaling;
        if(!oldSession.isEmpty() && transport!=null)network.execute(()->{try{transport.close(oldSession);}catch(Exception ignored){}});
        state="Desconectado";
        synchronized(frames){frames.reset();}
    }
    void release(){stop();network.shutdown();renderer.release();factory.dispose();egl.release();}
    private static class Observer implements SdpObserver {
        public void onCreateSuccess(SessionDescription sdp){}
        public void onSetSuccess(){}
        public void onCreateFailure(String error){}
        public void onSetFailure(String error){}
    }
}
