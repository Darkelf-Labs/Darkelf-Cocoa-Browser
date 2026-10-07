# Darkelf internal page and unified defense payloads.
# Extracted verbatim from the authoritative monolithic Cocoa browser.py.

import re

HOMEPAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Darkelf Browser</title>

<style>

:root{
  --bg:#0a0b10;
  --accent:#34C759;
  --text:#eef2f6;
}

*{box-sizing:border-box;}

html,body{
  height:100%;
  margin:0;
  overflow:hidden;
}

body{
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  background:
    radial-gradient(1200px 600px at 20% -10%, rgba(52,199,89,.35), transparent 60%),
    radial-gradient(1000px 600px at 120% 10%, rgba(52,199,89,.45), transparent 60%),
    var(--bg);

  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;

  color:var(--text);
}

/* animated particle grid */

.particles{
  position:fixed;
  inset:0;
  pointer-events:none;

  background-image:
    radial-gradient(rgba(52,199,89,.7) 1px, transparent 1px);

  background-size:90px 90px;

  opacity:.15;

  animation:particleMove 80s linear infinite;
}

@keyframes particleMove{
  from{transform:translateY(0);}
  to{transform:translateY(-200px);}
}

/* logo */

.brand{
  font-size:3.7rem;
  font-weight:800;
  letter-spacing:-.02em;
  color:#34C759;

  text-shadow:
    0 0 10px rgba(52,199,89,.8),
    0 0 30px rgba(52,199,89,.5),
    0 0 60px rgba(52,199,89,.25);

  animation:pulse 3s ease-in-out infinite;
}

@keyframes pulse{

  0%{
    text-shadow:
      0 0 10px rgba(52,199,89,.8),
      0 0 30px rgba(52,199,89,.5),
      0 0 60px rgba(52,199,89,.25);
  }

  50%{
    text-shadow:
      0 0 18px rgba(52,199,89,1),
      0 0 50px rgba(52,199,89,.7),
      0 0 90px rgba(52,199,89,.4);
  }

  100%{
    text-shadow:
      0 0 10px rgba(52,199,89,.8),
      0 0 30px rgba(52,199,89,.5),
      0 0 60px rgba(52,199,89,.25);
  }

}

.tagline{
  margin-top:20px;
  font-size:1rem;
  letter-spacing:.25em;
  text-transform:uppercase;
  color:#cfd8e3;
}

.ai{
  position:absolute;
  bottom:50px;
  font-size:.85rem;
  letter-spacing:.25em;
  color:#34C759;
  opacity:.8;
}

</style>
</head>

<body>

<div class="particles"></div>

<div class="brand">
Darkelf Browser
</div>

<div class="tagline">
Cocoa • Private • Hardened
</div>

<div class="ai">
Darkelf MiniAI Sentinel
</div>

</body>
</html>
"""

UNIFIED_DEFENSE_JS = r"""
(function(){

    // Verification compatibility:
    // Do not perturb browser APIs inside third-party challenge frames.
    // The protected first-party page keeps Darkelf defenses enabled.
    try {
        const h = String(location.hostname || "").toLowerCase();
        const p = String(location.pathname || "");
        const challengeHost =
            h === "challenges.cloudflare.com" ||
            h === "hcaptcha.com" ||
            h.endsWith(".hcaptcha.com") ||
            h === "www.google.com" ||
            h === "www.gstatic.com";
        const challengePath =
            p.startsWith("/cdn-cgi/challenge-platform/") ||
            p.startsWith("/cdn-cgi/turnstile/") ||
            p.startsWith("/cdn-cgi/challenge/") ||
            p.startsWith("/recaptcha/");
        if (challengeHost || challengePath) {
            return;
        }
    } catch (e) {}

    // ============================================================
    // 🚫 WEBRTC HARD BLOCK (ALWAYS RUN FIRST)
    // ============================================================

    (function(){

        const block = () => { throw new Error("WebRTC blocked"); };

        try {
            Object.defineProperty(window, "RTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try {
            Object.defineProperty(window, "webkitRTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try {
            Object.defineProperty(window, "mozRTCPeerConnection", {
                get: () => undefined,
                configurable: true
            });
        } catch(e){}

        try { delete window.RTCIceCandidate; } catch(e){}
        try { delete window.RTCSessionDescription; } catch(e){}

        try {
            if (navigator.mediaDevices) {
                navigator.mediaDevices.getUserMedia = block;
                navigator.mediaDevices.enumerateDevices = async () => [];
            }
        } catch(e){}

        try { navigator.getUserMedia = block; } catch(e){}

    })();
    
    // ============================================================
    // 🌐 TIMEZONE / LOCALE DEFENSE
    // ============================================================

    try {

        const _resolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;

        Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
            value: function () {
                const opts = _resolvedOptions.call(this);

                opts.timeZone = "UTC";
                opts.locale = "en-US";

                return opts;
            },
            configurable: true
        });

        Object.defineProperty(Date.prototype, 'getTimezoneOffset', {
            value: function () {
                return 0;
            },
            configurable: true
        });

    } catch (e) {}


    // ============================================================
    // ⚡ PERFORMANCE DEFENSE
    // ============================================================

    (function() {
      if (window.performance && window.performance.now) {
        const realNow = window.performance.now.bind(window.performance);
        window.performance.now = function() {
          return realNow() + (Math.random() * 15 - 7);
        };
      }

      if (window.performance && window.performance.timing) {
        for (let k in window.performance.timing) {
          try {
            if (typeof window.performance.timing[k] === "number") {
              window.performance.timing[k] =
                window.performance.timing[k] + Math.floor(Math.random() * 15 - 7);
            }
          } catch(e){}
        }
      }
    })();


    // ============================================================
    // 🔋 BATTERY DEFENSE
    // ============================================================

    if ("getBattery" in navigator) {
      navigator.getBattery = function() {
        return Promise.resolve({
          charging: true,
          chargingTime: 0,
          dischargingTime: Infinity,
          level: 1,
          addEventListener: function(){},
          removeEventListener: function(){},
          onchargingchange: null,
          onlevelchange: null
        });
      };
    }

    // ============================================================
    // 🔐 PQ SEED REQUIRED BELOW
    // ============================================================

    let ROOT_HEX = window.__darkelf_pq_seed_hex || "deadbeefdeadbeefdeadbeefdeadbeef";

    // 🔥 DARKELF GROUP BUCKET (SYNC WITH UA)
    let __darkelf_bucket = 0;

    try {
        __darkelf_bucket = parseInt(ROOT_HEX.slice(0, 8), 16) % 32;
    } catch(e){}

    function hex32(s){ return parseInt(s,16)>>>0; }

    const ROOT0 = hex32(ROOT_HEX.slice(0,8));
    const ROOT1 = hex32(ROOT_HEX.slice(8,16));
    const ROOT2 = hex32(ROOT_HEX.slice(16,24));
    const ROOT3 = hex32(ROOT_HEX.slice(24,32));

    function mix4(x,a,b,c,d){
        x=(x^a)>>>0; x=Math.imul(x,0x9e3779b1)>>>0;
        x=(x^b)>>>0; x=Math.imul(x,0x85ebca6b)>>>0;
        x=(x^c)>>>0; x=Math.imul(x,0xc2b2ae35)>>>0;
        x=(x^d)>>>0; x=Math.imul(x,0x27d4eb2f)>>>0;
        x^=x>>>15; x^=x>>>13;
        return x>>>0;
    }

    function derive(a,b,c,d){
        return [(ROOT0^a)>>>0,(ROOT1^b)>>>0,(ROOT2^c)>>>0,(ROOT3^d)>>>0];
    }

    const CANVAS_SEED = derive(1,2,3,4);
    const FONT_SEED   = derive(5,6,7,8);
    const WEBGL_SEED  = derive(9,10,11,12);
    const AUDIO_SEED  = derive(13,14,15,16);

    function mixCanvas(x){return mix4(x,...CANVAS_SEED);}
    function mixFont(x){return mix4(x,...FONT_SEED);}
    function mixWebGL(x){return mix4(x,...WEBGL_SEED);}
    function mixAudio(x){return mix4(x,...AUDIO_SEED);}

    // ============================================================
    // 🌍 ORIGIN ENTROPY
    // ============================================================

    let origin = location.origin||"";
    try{origin=window.top.location.origin||origin;}catch(e){}

    let originHash=0;
    for(let i=0;i<origin.length;i++){
        originHash=(originHash*31+origin.charCodeAt(i))>>>0;
    }

    const FONT_SITE = mixFont(originHash);
    const WEBGL_SITE = mixWebGL(originHash);

    // ============================================================
    // 🎯 CANVAS
    // ============================================================

    (function(){

        function noise(i){
            return ((mixCanvas(i^(i*31))%8)-4);
        }

        function apply(img){
            const d=img.data;
            for(let i=0;i<d.length;i++){
                d[i]=Math.max(0,Math.min(255,d[i]+noise(i)));
            }
        }

        function clone(ctx,src){
            const c=ctx.createImageData(src.width,src.height);
            c.data.set(src.data);
            return c;
        }

        const origToDataURL=HTMLCanvasElement.prototype.toDataURL;

        HTMLCanvasElement.prototype.toDataURL=function(){
            try{
                const ctx=this.getContext("2d");
                if(ctx){
                    const w=this.width,h=this.height;
                    const orig=ctx.getImageData(0,0,w,h);
                    const mod=clone(ctx,orig);
                    apply(mod);
                    ctx.putImageData(mod,0,0);
                    const r=origToDataURL.apply(this,arguments);
                    ctx.putImageData(orig,0,0);
                    return r;
                }
            }catch(e){}
            return origToDataURL.apply(this,arguments);
        };

        const origGetImageData=CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData=function(x,y,w,h){
            const img=origGetImageData.call(this,x,y,w,h);
            apply(img);
            return img;
        };

    })();

    // ============================================================
    // 🔤 FONT
    // ============================================================

    function fontSeed(text){
        if(!text||!text.length) return FONT_SITE;
        return (
            text.length*131 ^
            text.charCodeAt(0)*17 ^
            text.charCodeAt(text.length-1)*31 ^
            FONT_SITE
        )>>>0;
    }

    const origMeasure=CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText=function(t){
        const r=origMeasure.apply(this,arguments);
        if(typeof t==="string"&&t.length){
            const m=mixFont(fontSeed(t));
            r.width+=((m%1000)/1000-0.5)*1.2;
        }
        return r;
    };

    // Layout geometry spoofing can break JS-driven sticky/responsive headers.
    // CNN receives native DOM geometry while the rest of the font defense
    // (including measureText noise) remains enabled.
    const __darkelf_native_layout_geometry =
        /(^|\\.)cnn\\.com$/i.test(String(location.hostname || ""));

    if (!__darkelf_native_layout_geometry) {
        const ow=Object.getOwnPropertyDescriptor(HTMLElement.prototype,"offsetWidth");
        const oh=Object.getOwnPropertyDescriptor(HTMLElement.prototype,"offsetHeight");

        if (ow && ow.get) {
            Object.defineProperty(HTMLElement.prototype,"offsetWidth",{get(){
                const w=ow.get.call(this);
                const t=this.textContent||"";
                return t? w+((mixFont(fontSeed(t))%5)-2):w;
            }});
        }

        if (oh && oh.get) {
            Object.defineProperty(HTMLElement.prototype,"offsetHeight",{get(){
                const h=oh.get.call(this);
                const t=this.textContent||"";
                return t? h+((mixFont(fontSeed(t)^0x9e3779b1)%5)-2):h;
            }});
        }

        const origRect=Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect=function(){
            const r=origRect.apply(this,arguments);
            const t=this.textContent||"";
            if(!t) return r;
            const m=mixFont(fontSeed(t)^0x85ebca6b);
            const dx=((m%5)-2)*0.25;
            const dy=(((m>>>3)%5)-2)*0.25;
            return {...r,x:r.x+dx,y:r.y+dy,left:r.left+dx,top:r.top+dy};
        };
    }

    // ============================================================
    // 🎯 WEBGL
    // ============================================================

    function patchGL(p){
        if(!p)return;

        const gp=p.getParameter;
        p.getParameter=function(x){
            const v=gp.apply(this,arguments);
            const m=mixWebGL(x^WEBGL_SITE);
            if(typeof v==="number") return v+((m%3)-1);
            if(typeof v==="string"&&m%2===0) return v+" ";
            return v;
        };

        const rp=p.readPixels;
        p.readPixels=function(x,y,w,h,f,t,pix){
            rp.apply(this,arguments);
            if(pix){
                for(let i=0;i<pix.length;i++){
                    pix[i]+=((mixWebGL(i^WEBGL_SITE)%3)-1);
                }
            }
        };
    }

    patchGL(WebGLRenderingContext&&WebGLRenderingContext.prototype);
    patchGL(WebGL2RenderingContext&&WebGL2RenderingContext.prototype);
    
    // ============================================================
    // 🚀 WEBGPU (SAFE HASH ROTATION — UNIFIED WITH PQ)
    // ============================================================

    (function(){

        if (!("gpu" in navigator)) return;

        // 🔒 derive WebGPU seed from existing root system
        const WEBGPU_SEED = derive(17,18,19,20);

        function mixWebGPU(x){
            return mix4(x, ...WEBGPU_SEED);
        }

        // 🌍 bind to origin (same pattern as WebGL)
        let origin = location.origin || "";
        try { origin = window.top.location.origin || origin; } catch(e){}

        let originHash = 0;
        for (let i = 0; i < origin.length; i++){
            originHash = (originHash * 31 + origin.charCodeAt(i)) >>> 0;
        }

        const WEBGPU_SITE = mixWebGPU(originHash);

        // --------------------------------------------------------
        // 🔧 PATCH navigator.gpu.requestAdapter
        // --------------------------------------------------------

        const origRequestAdapter = navigator.gpu.requestAdapter.bind(navigator.gpu);

        navigator.gpu.requestAdapter = async function(options){

            const adapter = await origRequestAdapter(options);
            if (!adapter) return adapter;

            return new Proxy(adapter, {

                get(target, prop){

                    // 🔒 Slight string perturbation (stable)
                    if (prop === "name"){
                        const base = target.name || "GPU";
                        const m = mixWebGPU(base.length ^ WEBGPU_SITE);
                        return (m % 2 === 0) ? base : base + " ";
                    }

                    // 🔒 Stable numeric perturbation
                    if (prop === "limits"){
                        const limits = target.limits;
                        return new Proxy(limits, {
                            get(lim, key){
                                const val = lim[key];
                                if (typeof val === "number"){
                                    return val + ((mixWebGPU(val ^ WEBGPU_SITE) % 3) - 1);
                                }
                                return val;
                            }
                        });
                    }

                    return target[prop];
                }
            });
        };

        // --------------------------------------------------------
        // 🔧 PATCH GPUDevice → buffer readback noise
        // --------------------------------------------------------

        const origRequestDevice = GPUAdapter.prototype.requestDevice;

        GPUAdapter.prototype.requestDevice = async function(){

            const device = await origRequestDevice.apply(this, arguments);
            if (!device) return device;

            const origCreateBuffer = device.createBuffer;

            device.createBuffer = function(desc){

                const buffer = origCreateBuffer.call(this, desc);

                const origMapAsync = buffer.mapAsync;

                buffer.mapAsync = async function(){

                    await origMapAsync.apply(this, arguments);

                    const origGetRange = this.getMappedRange;

                    this.getMappedRange = function(){

                        const raw = origGetRange.apply(this, arguments);
                        const view = new Uint8Array(raw);

                        // 🔒 deterministic low-noise injection
                        for (let i = 0; i < view.length; i++){
                            view[i] += ((mixWebGPU(i ^ WEBGPU_SITE) % 3) - 1);
                        }

                        return view;
                    };
                };

                return buffer;
            };

            return device;
        };

    })();
    
    // ============================================================
    // 🎯 AUDIO
    // ============================================================

    try{
        const orig=OfflineAudioContext.prototype.getChannelData;
        OfflineAudioContext.prototype.getChannelData=function(){
            const d=orig.apply(this,arguments);
            for(let i=0;i<d.length;i++){
                d[i]+=((mixAudio(i)%3)-1)*0.00001;
            }
            return d;
        };
    }catch(e){}

})();
"""


def homepage_html_for_accent(rgba, background_name="Darkelf Glow"):
    """Return the internal home page themed with the current accent/background."""
    try:
        r, g, b, _a = [max(0.0, min(1.0, float(v))) for v in rgba]
    except Exception:
        r, g, b = 0.20, 0.78, 0.35
    R, G, B = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    hex_color = f"#{R:02X}{G:02X}{B:02X}"
    html = HOMEPAGE_HTML.replace("#34C759", hex_color)
    html = html.replace("rgba(52,199,89,", f"rgba({R},{G},{B},")

    styles = {
        "Darkelf Glow": (
            f"radial-gradient(1200px 600px at 20% -10%, rgba({R},{G},{B},.35), transparent 60%),"
            f"radial-gradient(1000px 600px at 120% 10%, rgba({R},{G},{B},.45), transparent 60%),#0a0b10"
        ),
        "Midnight": (
            "radial-gradient(900px 520px at 50% -15%, rgba(35,64,110,.30), transparent 65%),"
            "linear-gradient(145deg,#05070c 0%,#0a1020 55%,#03050a 100%)"
        ),
        "Aurora": (
            f"radial-gradient(850px 500px at 12% 5%, rgba({R},{G},{B},.30), transparent 62%),"
            "radial-gradient(900px 550px at 92% 10%, rgba(40,120,170,.28), transparent 65%),"
            "linear-gradient(160deg,#050a0d,#071411 55%,#05070b)"
        ),
        "Nebula": (
            "radial-gradient(800px 520px at 20% 0%, rgba(108,55,190,.32), transparent 65%),"
            f"radial-gradient(900px 600px at 105% 20%, rgba({R},{G},{B},.22), transparent 65%),"
            "linear-gradient(150deg,#090711,#10091a 48%,#05070c)"
        ),
        "Carbon": (
            "linear-gradient(135deg,rgba(255,255,255,.025) 25%,transparent 25%) 0 0/24px 24px,"
            "linear-gradient(315deg,rgba(255,255,255,.018) 25%,transparent 25%) 0 0/24px 24px,"
            "linear-gradient(145deg,#090a0c,#111317 55%,#07080a)"
        ),
        "Pure Black": "#000000",
        "Deep Ocean": (
            "radial-gradient(900px 560px at 18% 0%, rgba(0,115,180,.34), transparent 62%),"
            "radial-gradient(900px 620px at 105% 18%, rgba(0,205,220,.16), transparent 66%),"
            "linear-gradient(155deg,#02070d 0%,#031421 52%,#010509 100%)"
        ),
        "Crimson Eclipse": (
            "radial-gradient(820px 520px at 50% -8%, rgba(190,28,48,.34), transparent 62%),"
            "radial-gradient(700px 520px at 100% 25%, rgba(105,8,24,.20), transparent 68%),"
            "linear-gradient(155deg,#080305 0%,#140508 52%,#030204 100%)"
        ),
        "Emerald Matrix": (
            "linear-gradient(rgba(20,210,100,.035) 1px,transparent 1px) 0 0/34px 34px,"
            "linear-gradient(90deg,rgba(20,210,100,.028) 1px,transparent 1px) 0 0/34px 34px,"
            "radial-gradient(900px 560px at 50% -10%,rgba(20,190,90,.22),transparent 64%),"
            "linear-gradient(160deg,#020805,#04110a 55%,#010403)"
        ),
    }
    bg = styles.get(str(background_name), styles["Darkelf Glow"])
    # Replace the complete original body background declaration.
    html = re.sub(
        r'background:\s*radial-gradient\(1200px 600px at 20% -10%, rgba\([^)]+\), transparent 60%\),\s*'
        r'radial-gradient\(1000px 600px at 120% 10%, rgba\([^)]+\), transparent 60%\),\s*var\(--bg\);',
        "background:" + bg + ";",
        html,
        count=1,
    )
    return html
