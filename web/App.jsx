import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Home, LayoutGrid, Brain, CheckSquare, Zap, Monitor, Code2, Globe,
  Settings, Mic, Search, Cloud, Timer, Play, Pause, Sliders,
  SkipBack, SkipForward, Bell, Plus, Music, X, Check, Folder,
  Gamepad2, FileText, ChevronRight, BookOpen, Radio, Star,
  Activity, Volume2, Cpu, HardDrive, Wifi,
} from "lucide-react";

// ✅ CORRECCIÓN: Carga QWebChannel desde PySide6
let pyBridge = null;

// Espera a que Python inicialice el WebChannel
if (window.qt && window.qt.webChannelTransport) {
  const script = document.createElement('script');
  script.src = 'qrc:///qtwebchannel/qwebchannel.js';
  script.onload = () => {
    new QWebChannel(window.qt.webChannelTransport, function(channel) {
      pyBridge = channel.objects.pythonBridge;
      console.log("✓ Conectado a Python");
    });
  };
  document.head.appendChild(script);
}

const sendCommand = (cmd) => {
  if (!pyBridge) {
    console.warn("Python bridge no disponible");
    return;
  }
  pyBridge.executeCommand(cmd, (result) => {
    console.log("Respuesta Python:", result);
  });
};

window.sendCommand = sendCommand;

console.log("✓ App.jsx cargado");
console.log("Window location:", window.location);

if (window.qt) {
  console.log("✓ PySide6 detectado");
} else {
  console.log("⚠ PySide6 NO detectado");
}

const C = {
  bgVoid:   "#050810",
  bgBase:   "#080d1a",
  bgPanel:  "#0c1422",
  bgSide:   "#070b17",
  bgHover:  "#111d2e",
  bgSel:    "#152640",
  border:   "#1a2540",
  borderHi: "#243556",
  text:     "#e2e8f0",
  textDim:  "#8099b4",
  muted:    "#3d5270",
  cyan:     "#38bdf8",
  cyanHi:   "#7dd3fc",
  cyanDeep: "#0ea5e9",
  cyanDim:  "#0c3a5e",
  ok:       "#34d399",
  warn:     "#fbbf24",
  err:      "#f87171",
  purple:   "#a78bfa",
  blue:     "#60a5fa",
  green:    "#4ade80",
};

const CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  @keyframes orbPulse {
    0%,100% { transform:scale(1); }
    50% { transform:scale(1.05); }
  }
  @keyframes ring1 {
    0%,100% { transform:scale(1); opacity:.6; }
    50% { transform:scale(1.05); opacity:.95; }
  }
  @keyframes ring2 {
    0%,100% { transform:scale(1); opacity:.3; }
    50% { transform:scale(1.1); opacity:.6; }
  }
  @keyframes ring3 {
    0%,100% { transform:scale(1); opacity:.12; }
    50% { transform:scale(1.15); opacity:.38; }
  }
  @keyframes waveBar {
    0%,100% { transform:scaleY(.22); }
    50% { transform:scaleY(1); }
  }
  @keyframes blink {
    0%,100% { opacity:1; }
    50% { opacity:.2; }
  }
  ::-webkit-scrollbar { width:3px; }
  ::-webkit-scrollbar-track { background:transparent; }
  ::-webkit-scrollbar-thumb { background:#1a2540; border-radius:2px; }
  .nav-item:hover { background:#111d2e !important; color:#8099b4 !important; }
  .nav-item.sel { background:#152640 !important; color:#7dd3fc !important; border-left:2px solid #38bdf8 !important; }
  .qbtn:hover { background:#0f1c2e !important; border-color:#243556 !important; }
  .mcard:hover { background:#0f1c2e !important; border-color:#243556 !important; }
  .sp-ctrl:hover { color:#e2e8f0 !important; }
`;

function VoiceOrb({ active = true }) {
  const rc = active ? C.cyan : C.muted;
  return (
    <div style={{ position:"relative", width:220, height:220, display:"flex", alignItems:"center", justifyContent:"center" }}>
      <div style={{ position:"absolute", width:210, height:210, borderRadius:"50%", border:`1px solid ${rc}18`, animation:"ring3 3.3s ease-in-out infinite .7s" }} />
      <div style={{ position:"absolute", width:162, height:162, borderRadius:"50%", border:`1px solid ${rc}40`, animation:"ring2 2.7s ease-in-out infinite .35s" }} />
      <div style={{ position:"absolute", width:118, height:118, borderRadius:"50%", border:`1.5px solid ${rc}75`, animation:"ring1 2.1s ease-in-out infinite" }} />
      <div style={{
        width:80, height:80, borderRadius:"50%",
        background: active
          ? `radial-gradient(circle at 38% 32%, ${C.cyanHi}cc, ${C.cyanDeep} 60%, #050810 100%)`
          : `radial-gradient(circle at 38% 32%, #1e3050, #0a1828)`,
        boxShadow: active ? `0 0 26px ${C.cyanDeep}88, 0 0 52px ${C.cyanDeep}28` : "none",
        animation:"orbPulse 2.3s ease-in-out infinite",
        display:"flex", alignItems:"center", justifyContent:"center",
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:3, height:28 }}>
          {[.32,.62,1,.62,.32].map((h,i) => (
            <div key={i} style={{
              width:4, height:28*h, background: active ? "#000c" : `${C.muted}55`,
              borderRadius:3,
              animation: active ? `waveBar ${.68+i*.14}s ease-in-out infinite` : "none",
              animationDelay:`${i*.09}s`,
              transformOrigin:"center",
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function Sparkline({ values, color }) {
  const w=58, h=22;
  const pts = values.map((v,i)=>`${(i/(values.length-1))*w},${h-(v/100)*h}`).join(" ");
  return (
    <svg width={w} height={h} style={{ overflow:"visible" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function SystemMetric({ label, initVal, color }) {
  const valRef = useRef(initVal);
  const [hist, setHist] = useState(() => Array(10).fill(initVal));
  useEffect(() => {
    const id = setInterval(() => {
      const n = Math.max(4, Math.min(96, valRef.current + (Math.random()-.45)*14));
      valRef.current = Math.round(n);
      setHist(h => [...h.slice(1), valRef.current]);
    }, 2000);
    return () => clearInterval(id);
  }, []);
  const cur = hist[hist.length-1];
  return (
    <div style={{ display:"flex", alignItems:"center", gap:12, padding:"7px 13px", background:C.bgPanel, borderRadius:10, border:`1px solid ${C.border}` }}>
      <div>
        <div style={{ fontSize:9, color:C.muted, letterSpacing:1.3, marginBottom:1 }}>{label}</div>
        <div style={{ fontSize:20, fontWeight:700, fontFamily:"monospace", color:C.text, lineHeight:1 }}>{cur}%</div>
      </div>
      <Sparkline values={hist} color={color} />
    </div>
  );
}

function MiniWave({ color="#38bdf8", count=12 }) {
  const heights = useMemo(() => Array(count).fill(0).map((_,i)=>5+((i*7+3)%11)), [count]);
  return (
    <div style={{ display:"flex", alignItems:"center", gap:2 }}>
      {heights.map((h,i) => (
        <div key={i} style={{
          width:2.5, height:h,
          background:`${color}55`, borderRadius:2,
          animation:`waveBar ${.5+i*.08}s ease-in-out infinite`,
          animationDelay:`${i*.055}s`,
        }} />
      ))}
    </div>
  );
}

function SpotifyWidget() {
  const [phase, setPhase] = useState("idle");
  const [tokenInput, setTokenInput] = useState("");
  const [token, setToken] = useState("");
  const [track, setTrack] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(1);
  const [error, setError] = useState("");

  const fetchNow = useCallback(async (t) => {
    try {
      const r = await fetch("https://api.spotify.com/v1/me/player/currently-playing", {
        headers:{ Authorization:`Bearer ${t}` },
      });
      if (r.status === 200) {
        const d = await r.json();
        if (d?.item) {
          setTrack(d.item); setPlaying(d.is_playing);
          setProgress(d.progress_ms); setDuration(d.item.duration_ms);
          setError("");
        }
      } else if (r.status === 401) { setError("Token expirado"); setPhase("idle"); }
    } catch { setError("Error de conexión"); }
  }, []);

  useEffect(() => {
    if (phase !== "connected") return;
    fetchNow(token);
    const id = setInterval(() => fetchNow(token), 4000);
    return () => clearInterval(id);
  }, [phase, token, fetchNow]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setProgress(p => Math.min(p+1000, duration)), 1000);
    return () => clearInterval(id);
  }, [playing, duration]);

  const connect = () => { if (tokenInput.trim()) { setToken(tokenInput.trim()); setPhase("connected"); } };
  const toggle = async () => {
    await fetch(`https://api.spotify.com/v1/me/player/${playing?"pause":"play"}`, {
      method:"PUT", headers:{ Authorization:`Bearer ${token}` },
    }).catch(()=>{});
    setPlaying(!playing);
  };
  const skip = async dir => {
    await fetch(`https://api.spotify.com/v1/me/player/${dir}`, {
      method:"POST", headers:{ Authorization:`Bearer ${token}` },
    }).catch(()=>{});
    setTimeout(() => fetchNow(token), 600);
  };
  const fmt = ms => { const s=Math.floor(ms/1000); return `${Math.floor(s/60)}:${String(s%60).padStart(2,"0")}`; };
  const pct = Math.min(100, (progress/duration)*100);

  const cardStyle = { background:C.bgBase, borderRadius:12, border:`1px solid ${C.border}`, padding:"14px 15px" };
  const hdrStyle = { display:"flex", alignItems:"center", gap:8, marginBottom:12 };
  const ctrlBtnStyle = { background:"transparent", border:"none", cursor:"pointer", color:C.textDim, display:"flex", padding:4 };

  if (phase === "idle") return (
    <div style={cardStyle}>
      <div style={hdrStyle}>
        <Music size={15} color="#1db954" />
        <span style={{ fontSize:10, fontWeight:600, color:C.textDim, letterSpacing:1.3 }}>SPOTIFY</span>
      </div>
      <button onClick={()=>setPhase("setup")} style={{
        width:"100%", padding:"9px", cursor:"pointer",
        background:"#1db95422", border:"1px solid #1db95448", borderRadius:8,
        color:"#1db954", fontSize:12, display:"flex", alignItems:"center", justifyContent:"center", gap:6,
      }}>
        <Music size={13} /> Conectar Spotify
      </button>
    </div>
  );

  if (phase === "setup") return (
    <div style={cardStyle}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:10 }}>
        <div style={{ display:"flex", alignItems:"center", gap:8 }}>
          <Music size={15} color="#1db954" />
          <span style={{ fontSize:10, fontWeight:600, color:C.textDim, letterSpacing:1.3 }}>SPOTIFY</span>
        </div>
        <button onClick={()=>setPhase("idle")} style={{ background:"transparent", border:"none", cursor:"pointer", color:C.muted }}>
          <X size={13} />
        </button>
      </div>
      <p style={{ fontSize:10, color:C.muted, lineHeight:1.55, marginBottom:9 }}>
        Obtén tu token en{" "}
        <a href="https://developer.spotify.com/console/get-the-users-currently-playing-track" target="_blank" style={{ color:C.cyan }}>
          Spotify Console
        </a>
        {" "}con los scopes:{" "}
        <span style={{ color:C.textDim }}>user-read-playback-state, user-modify-playback-state</span>
      </p>
      <input
        value={tokenInput} onChange={e=>setTokenInput(e.target.value)}
        onKeyDown={e=>e.key==="Enter"&&connect()}
        placeholder="Pega tu access token aquí..."
        style={{
          width:"100%", padding:"8px 10px", marginBottom:8,
          background:C.bgPanel, border:`1px solid ${C.borderHi}`,
          borderRadius:7, color:C.text, fontSize:11, outline:"none",
        }}
      />
      <div style={{ display:"flex", gap:6 }}>
        <button onClick={connect} style={{
          flex:1, padding:"8px", cursor:"pointer",
          background:"#1db954", border:"none", borderRadius:7,
          color:"#000", fontWeight:700, fontSize:12,
        }}>Conectar</button>
        <button onClick={()=>setPhase("idle")} style={{
          padding:"8px 10px", cursor:"pointer",
          background:"transparent", border:`1px solid ${C.border}`,
          borderRadius:7, color:C.textDim, fontSize:12,
        }}>✕</button>
      </div>
      {error && <p style={{ color:C.err, fontSize:10, marginTop:6 }}>{error}</p>}
    </div>
  );

  return (
    <div style={cardStyle}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
        <Music size={14} color="#1db954" />
        <span style={{ fontSize:10, color:C.textDim, letterSpacing:1, flex:1 }}>AHORA REPRODUCIENDO</span>
        <button onClick={()=>{ setPhase("idle"); setTrack(null); }} style={{ background:"transparent", border:"none", cursor:"pointer", color:C.muted }}>
          <X size={12} />
        </button>
      </div>
      {track ? (
        <>
          <div style={{ display:"flex", gap:10, marginBottom:11, alignItems:"center" }}>
            {track.album?.images?.[0] && (
              <img src={track.album.images[0].url} alt="" style={{ width:46, height:46, borderRadius:7, flexShrink:0 }} />
            )}
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ color:C.text, fontSize:13, fontWeight:600, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                {track.name}
              </div>
              <div style={{ color:C.textDim, fontSize:11 }}>
                {track.artists?.map(a=>a.name).join(", ")}
              </div>
            </div>
          </div>
          <div style={{ marginBottom:10 }}>
            <div style={{ height:3, background:C.bgPanel, borderRadius:2, marginBottom:5, cursor:"pointer" }}>
              <div style={{ height:"100%", width:`${pct}%`, background:"#1db954", borderRadius:2, transition:"width .8s linear" }} />
            </div>
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:10, color:C.muted }}>
              <span>{fmt(progress)}</span><span>{fmt(duration)}</span>
            </div>
          </div>
          <div style={{ display:"flex", alignItems:"center", justifyContent:"center", gap:20 }}>
            <button className="sp-ctrl" onClick={()=>skip("previous")} style={ctrlBtnStyle}><SkipBack size={18} /></button>
            <button onClick={toggle} style={{
              width:36, height:36, borderRadius:"50%", background:"#1db954",
              border:"none", cursor:"pointer", display:"flex", alignItems:"center", justifyContent:"center",
            }}>
              {playing ? <Pause size={16} color="#000" fill="#000" /> : <Play size={16} color="#000" fill="#000" />}
            </button>
            <button className="sp-ctrl" onClick={()=>skip("next")} style={ctrlBtnStyle}><SkipForward size={18} /></button>
          </div>
        </>
      ) : (
        <div style={{ textAlign:"center", color:C.muted, fontSize:12, padding:"10px 0" }}>Sin reproducción activa</div>
      )}
    </div>
  );
}

export default function App() {
  const [page, setPage] = useState("inicio");
  const [time, setTime] = useState(new Date());
  const [cmd, setCmd] = useState("");
  const [todos, setTodos] = useState([
    { id:1, text:"Terminar proyecto IA",          done:false },
    { id:2, text:"Estudiar Python avanzado",       done:false },
    { id:3, text:"Hacer ejercicio",                done:true  },
    { id:4, text:"Leer 20 páginas",                done:false },
    { id:5, text:"Revisar pendientes del trabajo", done:false },
  ]);

  useEffect(() => { const id=setInterval(()=>setTime(new Date()),1000); return()=>clearInterval(id); }, []);

  const MONTHS=["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
  const fmtT = d=>`${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`;
  const fmtD = d=>`${d.getDate()} ${MONTHS[d.getMonth()]}, ${d.getFullYear()}`;

  const navItems = [
    { id:"inicio",           Icon:Home,         label:"Inicio"           },
    { id:"modos",            Icon:LayoutGrid,    label:"Modos"            },
    { id:"memoria",          Icon:Brain,         label:"Memoria"          },
    { id:"pendientes",       Icon:CheckSquare,   label:"Pendientes"       },
    { id:"automatizaciones", Icon:Zap,           label:"Automatizaciones" },
    { id:"sistema",          Icon:Monitor,       label:"Sistema"          },
    { id:"desarrollo",       Icon:Code2,         label:"Desarrollo"       },
    { id:"internet",         Icon:Globe,         label:"Internet"         },
    { id:"notas",            Icon:FileText,      label:"Notas rápidas"    },
    { id:"config",           Icon:Settings,      label:"Configuración"    },
  ];

  const quickActions = [
    { Icon:Folder,   label:"Abrir app"     },
    { Icon:Timer,    label:"Pomodoro"      },
    { Icon:Bell,     label:"Recordatorio"  },
    { Icon:Search,   label:"Buscar"        },
    { Icon:Cloud,    label:"Clima"         },
    { Icon:FileText, label:"Notas"         },
  ];

  const activities = [
    { t:"18:35", Icon:Monitor,  color:C.cyan,   text:'Abrió Visual Studio Code',              cat:"Sistema"       },
    { t:"18:33", Icon:Code2,    color:C.purple, text:'Git push en proyecto "Lia-Assistant"',  cat:"Desarrollo"    },
    { t:"18:30", Icon:Timer,    color:C.err,    text:'Pomodoro iniciado (25 min)',             cat:"Productividad" },
    { t:"18:10", Icon:Bell,     color:C.warn,   text:'Recordatorio: Reunión de trabajo',       cat:"Recordatorio"  },
    { t:"17:45", Icon:Globe,    color:C.green,  text:'Buscó en Google: "Python threading"',    cat:"Internet"      },
  ];

  const modes = [
    { Icon:BookOpen, title:"Modo Estudio", claps:1, apps:["ChatGPT","WhatsApp","Calendario","Notas"],          color:C.blue,   bg:"#1e3357" },
    { Icon:Code2,    title:"Modo Código",  claps:2, apps:["VS Code","GitHub","Spotify","Terminal"],             color:C.purple, bg:"#2d1b4e" },
    { Icon:Gamepad2, title:"Modo Juego",   claps:3, apps:["Discord","Optimizaciones","Rendimiento","Juego"],    color:C.green,  bg:"#1a3a28" },
  ];

  const doneCnt = todos.filter(t=>t.done).length;
  const toggleTodo = id => setTodos(ts=>ts.map(t=>t.id===id?{...t,done:!t.done}:t));

  const row    = { display:"flex", alignItems:"center" };
  const col    = { display:"flex", flexDirection:"column" };
  const btwn   = { display:"flex", alignItems:"center", justifyContent:"space-between" };

  return (
    <>
      <style>{CSS}</style>
      <div style={{
        ...row, height:"100vh", background:C.bgVoid,
        color:C.text, fontFamily:"'Segoe UI Variable','Segoe UI',system-ui,sans-serif",
        fontSize:13, overflow:"hidden", minWidth:880,
      }}>

        {/* ── SIDEBAR ───────────────────────────────────────────────────── */}
        <div style={{
          width:212, flexShrink:0, background:C.bgSide,
          borderRight:`1px solid ${C.border}`,
          ...col, overflow:"hidden", height:"100%",
        }}>
          {/* Brand */}
          <div style={{ ...row, gap:10, padding:"13px 15px", background:C.bgBase, borderBottom:`1px solid ${C.border}` }}>
            <div style={{
              width:36, height:36, borderRadius:9, flexShrink:0,
              background:`linear-gradient(135deg, ${C.cyanDeep}, ${C.cyan}88)`,
              display:"flex", alignItems:"center", justifyContent:"center",
            }}>
              <Radio size={17} color="#fff" />
            </div>
            <div>
              <div style={{ fontSize:15, fontWeight:700, color:C.cyanHi, letterSpacing:2.5 }}>LIA</div>
              <div style={{ fontSize:9, color:C.muted, letterSpacing:1 }}>ASISTENTE PERSONAL</div>
            </div>
          </div>

          {/* Nav */}
          <nav style={{ flex:1, overflowY:"auto", padding:"6px 0" }}>
            {navItems.map(({ id, Icon, label }) => (
              <button
                key={id}
                className={`nav-item${page===id?" sel":""}`}
                onClick={()=>setPage(id)}
                style={{
                  width:"100%", padding:"9px 15px 9px 13px",
                  background:page===id?C.bgSel:"transparent",
                  border:"none", borderLeft:`2px solid ${page===id?C.cyan:"transparent"}`,
                  color:page===id?C.cyanHi:C.textDim,
                  cursor:"pointer", textAlign:"left",
                  display:"flex", alignItems:"center", gap:10,
                  fontSize:12, fontWeight:page===id?600:400,
                  transition:"all .12s",
                }}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </nav>

          {/* Status footer */}
          <div style={{ borderTop:`1px solid ${C.border}`, padding:"11px 13px 10px" }}>
            <div style={{ ...row, gap:10 }}>
              <div style={{
                width:32, height:32, borderRadius:"50%", flexShrink:0,
                background:`radial-gradient(circle at 38% 35%, ${C.cyanDeep}99, #0a1830)`,
                border:`1.5px solid ${C.cyanDim}`,
                display:"flex", alignItems:"center", justifyContent:"center",
              }}>
                <Radio size={14} color={C.cyan} />
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontSize:11, color:C.text, fontWeight:600 }}>Lia está activa</div>
                <div style={{ fontSize:10, color:C.ok, ...row, gap:5 }}>
                  <div style={{ width:5, height:5, borderRadius:"50%", background:C.ok, animation:"blink 1.6s ease-in-out infinite" }} />
                  Escuchando...
                </div>
              </div>
            </div>
            <div style={{ marginTop:8 }}><MiniWave color={C.cyan} count={14} /></div>
          </div>
        </div>

        {/* ── MAIN AREA ─────────────────────────────────────────────────── */}
        <div style={{ flex:1, ...col, overflow:"hidden", height:"100%" }}>

          {/* Top header */}
          <div style={{
            ...row, gap:12, padding:"10px 18px",
            background:C.bgBase, borderBottom:`1px solid ${C.border}`, flexShrink:0,
          }}>
            <div style={{ flex:1 }}>
              <div style={{ fontSize:18, fontWeight:600, color:C.text, ...row, gap:7 }}>
                Hola, soy Lia <Star size={16} color={C.warn} fill={C.warn} />
              </div>
              <div style={{ fontSize:11, color:C.textDim }}>¿En qué puedo ayudarte hoy?</div>
            </div>
            <div style={{
              padding:"7px 14px", background:C.bgPanel,
              borderRadius:9, border:`1px solid ${C.border}`, textAlign:"center", flexShrink:0,
            }}>
              <div style={{ fontSize:22, fontWeight:700, fontFamily:"monospace", color:C.text, lineHeight:1 }}>{fmtT(time)}</div>
              <div style={{ fontSize:9, color:C.muted, marginTop:2 }}>{fmtD(time)}</div>
            </div>
            <SystemMetric label="CPU"   initVal={23} color={C.cyan}   />
            <SystemMetric label="RAM"   initVal={41} color={C.purple} />
            <SystemMetric label="Disco" initVal={68} color={C.warn}   />
          </div>

          {/* Body */}
          <div style={{ flex:1, ...row, overflow:"hidden" }}>

            {/* Center panel */}
            <div style={{ flex:1, ...col, overflowY:"auto" }}>
              {/* Orb */}
              <div style={{
                ...col, alignItems:"center", justifyContent:"center",
                padding:"22px 0 14px",
                background:`linear-gradient(180deg, ${C.bgBase} 0%, ${C.bgVoid} 100%)`,
                flexShrink:0,
              }}>
                <VoiceOrb active />
                <div style={{ marginTop:10, color:C.cyan, fontSize:12, fontWeight:500, letterSpacing:2.5, animation:"blink 2.5s ease-in-out infinite" }}>
                  Escuchando...
                </div>
                <div style={{ marginTop:7 }}><MiniWave color={C.cyan} count={10} /></div>
              </div>

              <div style={{ padding:"0 18px 18px" }}>
                {/* Quick actions */}
                <div style={{ marginBottom:15 }}>
                  <div style={{ fontSize:9, color:C.muted, letterSpacing:2, fontWeight:600, marginBottom:9 }}>ACCIONES RÁPIDAS</div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:8 }}>
                    {quickActions.map(({ Icon, label }) => (
                      <button key={label} className="qbtn" style={{
                        padding:"11px 6px",
                        background:C.bgPanel, border:`1px solid ${C.border}`,
                        borderRadius:10, cursor:"pointer",
                        ...col, alignItems:"center", gap:6,
                        color:C.textDim, fontSize:11, transition:"all .12s",
                      }}>
                        <Icon size={17} color={C.cyan} />
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Activity */}
                <div>
                  <div style={{ ...btwn, marginBottom:9 }}>
                    <div style={{ fontSize:9, color:C.muted, letterSpacing:2, fontWeight:600 }}>ACTIVIDAD RECIENTE</div>
                    <button style={{ background:"transparent", border:"none", color:C.cyan, fontSize:11, cursor:"pointer" }}>Ver todo</button>
                  </div>
                  <div style={{ background:C.bgPanel, border:`1px solid ${C.border}`, borderRadius:10, overflow:"hidden" }}>
                    {activities.map(({ t, Icon, color, text, cat }, i) => (
                      <div key={i} style={{
                        ...row, gap:12, padding:"9px 14px",
                        borderBottom:i<activities.length-1?`1px solid ${C.border}`:"none",
                      }}>
                        <span style={{ fontSize:11, color:C.muted, fontFamily:"monospace", minWidth:36 }}>{t}</span>
                        <Icon size={13} color={color} />
                        <span style={{ flex:1, fontSize:12, color:C.textDim }}>{text}</span>
                        <span style={{ fontSize:10, color:C.muted }}>{cat}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* ── RIGHT PANEL ───────────────────────────────────────────── */}
            <div style={{
              width:278, flexShrink:0, overflowY:"auto",
              borderLeft:`1px solid ${C.border}`,
              padding:"14px 12px", ...col, gap:14,
            }}>
              {/* Modes */}
              <div>
                <div style={{ fontSize:9, color:C.muted, letterSpacing:2, fontWeight:600, marginBottom:10 }}>MODOS (APLAUSOS)</div>
                <div style={{ ...col, gap:8 }}>
                  {modes.map(({ Icon, title, claps, apps, color, bg }, i) => (
                    <div key={i} className="mcard" style={{
                      ...row, gap:11,
                      background:C.bgPanel, border:`1px solid ${C.border}`,
                      borderRadius:10, padding:"11px 11px",
                      cursor:"pointer", transition:"all .12s",
                    }}>
                      <div style={{
                        width:38, height:38, borderRadius:9, flexShrink:0,
                        background:bg, display:"flex", alignItems:"center",
                        justifyContent:"center", color,
                      }}>
                        <Icon size={18} />
                      </div>
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{ fontSize:12, fontWeight:600, color:C.text }}>{title}</div>
                        <div style={{ fontSize:10, color:C.muted }}>{claps} aplauso{claps>1?"s":""}</div>
                        <div style={{ fontSize:10, color:C.textDim, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                          {apps.join(" · ")}
                        </div>
                      </div>
                      <button style={{
                        width:26, height:26, borderRadius:"50%", flexShrink:0,
                        background:bg, border:`1px solid ${color}44`,
                        display:"flex", alignItems:"center", justifyContent:"center",
                        cursor:"pointer", color,
                      }}>
                        <Play size={11} fill={color} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Todos */}
              <div>
                <div style={{ ...btwn, marginBottom:10 }}>
                  <div style={{ fontSize:9, color:C.muted, letterSpacing:2, fontWeight:600 }}>PENDIENTES</div>
                  <button style={{ background:"transparent", border:"none", color:C.cyan, cursor:"pointer", padding:0 }}>
                    <Plus size={14} />
                  </button>
                </div>
                <div style={{ ...col, gap:8 }}>
                  {todos.map(({ id, text, done }) => (
                    <div key={id} style={{ ...row, gap:10, cursor:"pointer" }} onClick={()=>toggleTodo(id)}>
                      <div style={{
                        width:16, height:16, borderRadius:4, flexShrink:0,
                        background:done?C.cyanDeep:"transparent",
                        border:`1.5px solid ${done?C.cyanDeep:C.borderHi}`,
                        display:"flex", alignItems:"center", justifyContent:"center",
                      }}>
                        {done && <Check size={10} color="#fff" strokeWidth={3} />}
                      </div>
                      <span style={{
                        fontSize:12, color:done?C.muted:C.text,
                        textDecoration:done?"line-through":"none",
                      }}>{text}</span>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop:12 }}>
                  <div style={{ fontSize:10, color:C.muted, marginBottom:5 }}>{doneCnt} de {todos.length} completadas</div>
                  <div style={{ height:4, background:C.bgBase, borderRadius:3 }}>
                    <div style={{
                      height:"100%", borderRadius:3, background:C.ok,
                      width:`${(doneCnt/todos.length)*100}%`, transition:"width .3s ease",
                    }} />
                  </div>
                </div>
              </div>

              {/* Spotify */}
              <SpotifyWidget />
            </div>
          </div>

          {/* ── INPUT BAR ────────────────────────────────────────────────── */}
          <div style={{
            ...row, gap:10, padding:"9px 18px",
            background:C.bgBase, borderTop:`1px solid ${C.border}`, flexShrink:0,
          }}>
            <button style={{
              width:32, height:32, borderRadius:"50%", flexShrink:0,
              background:"transparent", border:`1px solid ${C.border}`,
              display:"flex", alignItems:"center", justifyContent:"center",
              cursor:"pointer", color:C.textDim,
            }}>
              <Sliders size={13} />
            </button>
            <input
              value={cmd}
              onChange={e => setCmd(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter" && cmd.trim()) {
                  sendCommand(`cmd:${cmd}`);
                  setCmd("");
                }
              }}
              placeholder='Di "Lia" seguido de tu comando...'
              style={{
                flex:1, padding:"10px 18px",
                background:C.bgPanel, border:`1px solid ${C.borderHi}`,
                borderRadius:22, color:C.text, fontSize:12, outline:"none",
              }}
            />
            <button style={{
              width:40, height:40, borderRadius:"50%", flexShrink:0,
              background:`linear-gradient(135deg, ${C.cyanDeep}, ${C.cyan})`,
              border:"none", display:"flex", alignItems:"center",
              justifyContent:"center", cursor:"pointer",
            }}>
              <Mic size={17} color="#000" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}