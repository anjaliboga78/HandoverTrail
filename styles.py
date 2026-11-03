"""The base stylesheet. Every colour, font and shape is a CSS variable, so core/themes.py can re-skin the whole app.

The variables below are the Notebook look (the default). A theme only changes variables; the rules stay the same.
"""
from core import themes

RULES = r"""
#MainMenu {visibility:hidden;} footer {visibility:hidden;}
html, body, .stApp {font-family:var(--serif); line-height:var(--lh); letter-spacing:var(--ls);}
body .stApp {color:var(--ink);}
body .stApp :is(p, li, label, h1, h2, h3, h4, h5, summary, td, th) {color:var(--ink);}
body .stApp [data-testid="stCaptionContainer"], body .stApp [data-testid="stCaptionContainer"] * {color:var(--muted);}
.stApp {background-color:var(--paper); background-image:var(--bgimg); background-size:var(--bgsize);}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stMain"], section.main {
  background-image:linear-gradient(90deg, transparent 34px, var(--marginc) 34px, var(--marginc) 36px, transparent 36px);}
.block-container {padding-top:2.2rem; padding-bottom:3rem; padding-left:var(--padl); max-width:1280px;}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {background:var(--paper2); border-right:var(--sidebd);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:.4rem;}
.side-logo {background:#fff; border:2px solid #101046; border-radius:14px; padding:8px 8px 4px;
            box-shadow:4px 4px 0 var(--teal); transform:rotate(calc(-1.2deg*var(--tiltk))); margin:6px 4px 10px 2px;}
.side-logo img {width:100%; display:block;}
.side-tag {font-family:var(--hand); font-size:calc(1.25rem*var(--hs)); color:var(--red); line-height:1.1; margin:0 0 14px 4px;}
.nametag {background:var(--card); border:2px solid var(--ink); border-radius:10px; overflow:hidden; margin:10px 4px 14px 2px;
          box-shadow:3px 3px 0 var(--line); transform:rotate(calc(1deg*var(--tiltk)));}
.nametag .top {background:var(--red); color:var(--onred); font-family:var(--hand); font-size:calc(1.05rem*var(--hs)); font-weight:700;
               text-align:center; letter-spacing:2px; padding:1px 0;}
.nametag .nm {font-family:var(--hand); font-size:calc(2.2rem*var(--hs)); font-weight:700; text-align:center; color:var(--ink);
              line-height:1.05; padding:4px 8px 0;}
.nametag .rl {text-align:center; padding:0 8px 8px;}
.nametag .rl span {display:inline-block; background:var(--yellow); color:var(--ink); border:1.5px dashed var(--ink); border-radius:999px;
                   padding:0 12px; font-size:.82rem; font-weight:600;}
.side-note {font-family:var(--hand); font-size:calc(1.15rem*var(--hs)); color:var(--muted); line-height:1.15;}

/* ---------- headings ---------- */
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {font-family:var(--hand); font-weight:700; letter-spacing:.2px;}
[data-testid="stHeadingWithActionElements"] h2 {font-size:calc(2.7rem*var(--hs)); line-height:1.1; padding:.2rem 0 .5rem;
    text-decoration:var(--hdeco); text-decoration-thickness:2px; text-underline-offset:9px;}
[data-testid="stHeadingWithActionElements"] h3 {font-size:calc(2rem*var(--hs)); padding-top:.6rem;}
.stApp p, .stApp li, .stApp label {font-family:var(--serif);}

/* ---------- hero ---------- */
.hero {position:relative; display:flex; flex-wrap:wrap; gap:18px 24px; align-items:center; background:var(--card);
       border:var(--panelbd); border-radius:var(--cardr); padding:22px 28px; margin:10px 0 28px; box-shadow:var(--panelsh);}
.hero:before {content:""; position:absolute; top:-14px; left:46px; width:112px; height:28px; opacity:var(--tape);
              background:rgba(240,206,110,.8); transform:rotate(-3deg); box-shadow:0 1px 2px rgba(0,0,0,.1);}
.hero .mark {width:86px; height:86px; border-radius:18px; border:2px solid #101046; background:#fff;
             box-shadow:4px 4px 0 var(--teal); flex:none; display:block; transform:rotate(calc(-3deg*var(--tiltk)));}
.hero .words {flex:1 1 320px; min-width:260px;}
.stApp .hero h1 {font-size:calc(3.6rem*var(--hs)); line-height:1; margin:0; padding:0;}
.hero h1 .t {color:var(--teal);}
.stApp .hero p {font-style:italic; color:var(--muted); margin:8px 0 0 0; font-size:1.02rem;}
.hero .who {flex:none; background:var(--yellow); color:var(--ink); border:1.5px dashed var(--ink); border-radius:4px; padding:6px 16px;
            font-family:var(--hand); font-size:calc(1.4rem*var(--hs)); font-weight:700; transform:rotate(calc(2deg*var(--tiltk)));
            box-shadow:3px 3px 0 rgba(16,16,70,.12);}

/* ---------- stepper: the trail ---------- */
.stepper {display:flex; flex-wrap:wrap; align-items:center; margin:0 0 28px 0; row-gap:10px;}
.step {display:flex; align-items:center; gap:9px; font-family:var(--hand); font-size:calc(1.5rem*var(--hs)); font-weight:700; color:var(--muted);}
.step + .step:before {content:""; display:inline-block; width:44px; border-top:3px dotted var(--line); margin:0 12px 0 6px;}
.step .num {width:38px; height:38px; border-radius:50%; border:2.5px solid var(--line); background:var(--numbg); color:var(--muted);
            display:flex; align-items:center; justify-content:center; font-size:calc(1.35rem*var(--hs)); line-height:1;}
.step.done {color:var(--tealD);}
.step.done .num {background:var(--teal); border-color:var(--ink); color:var(--onacc); font-size:0;}
.step.done .num:after {content:"\2713"; font-size:1.4rem; font-weight:700;}
.step.done + .step:before {border-top-color:var(--teal);}
.step.current {color:var(--ink); text-decoration:var(--hdeco); text-decoration-thickness:2px; text-underline-offset:7px;}
.step.current .num {background:var(--yellow); border-color:var(--red); color:var(--red); box-shadow:0 0 0 4px rgba(192,57,43,.14);}

/* ---------- item cards (sticky notes or flat cards) ---------- */
.card {position:relative; --bg:var(--yellow); background:var(--bg); border-radius:var(--cardr); border:var(--cardbd);
       padding:18px 20px 12px; margin:16px 0 12px; box-shadow:var(--cardsh); transform:rotate(calc(var(--r,0deg)*var(--tiltk)));}
.card:before {content:""; position:absolute; top:-11px; left:calc(50% - 40px); width:80px; height:20px; opacity:var(--tape);
              background:rgba(255,255,255,.62); border:1px solid rgba(0,0,0,.06); transform:rotate(var(--tr,-2deg));}
.card.t-decision {--bg:var(--yellow);} .card.t-owner {--bg:var(--blue);}
.card.t-open_question {--bg:var(--lav);} .card.t-blocker {--bg:var(--pink);}
.card.t-risk {--bg:var(--peach);} .card.t-dependency {--bg:var(--lime);}
.card.t-contact {--bg:var(--cyan);} .card.t-next_action {--bg:var(--green);}
.card.bad {outline:2px dashed var(--red); outline-offset:3px;}
.card.conf {outline:2px dashed #d9722b; outline-offset:3px;}
.card.warn {outline:2px dotted #c99a00; outline-offset:3px;}
.card .top {margin-bottom:8px;}
.card .text {font-size:1.02rem; color:var(--ink); line-height:1.5;}
.card .meta {font-family:var(--hand); color:var(--muted); font-size:calc(1.12rem*var(--hs)); margin-top:8px;}

.chip {display:inline-block; padding:1px 11px; margin:0 5px 5px 0; border-radius:999px; font-size:.76rem; font-weight:600;
       border:1.5px solid rgba(128,128,160,.55); background:var(--chipbg); color:var(--ink);}
.chip.type {background:var(--chipbg); color:var(--ink);}
.chip.ok {background:#c9f0d8; color:#0f5c33; border-color:#0f5c33;}
.chip.warn {background:#fff1bd; color:#6b4f00; border-color:#6b4f00;} .chip.bad {background:#ffd9d4; color:#9b1c14; border-color:#9b1c14;}
.chip.gap {background:#ffe1c8; color:#8a4208;} .chip.rec {background:#e3d8ff; color:#4b2a96;}
.chip.conf {background:#ffd8c4; color:#9c3708;} .chip.vis {background:var(--chipbg); color:var(--muted);}
.chip.due {background:#fff1bd; color:#6b4f00; border-color:#6b4f00;} .chip.over {background:#ffd9d4; color:#9b1c14; border-color:#9b1c14;}
.chip.later {background:var(--chipbg); color:var(--muted);} .chip.prom {background:#c9f0d8; color:#0f5c33; border-color:#0f5c33;}
.chip.sig {background:#ffe1c8; color:#8a4208; border-color:#8a4208;}

/* ---------- notices, start card ---------- */
.notice {position:relative; background:var(--card); border:1.5px var(--dst) var(--ink); color:var(--ink); border-radius:var(--cardr);
         padding:12px 16px 12px 40px; margin:8px 0 16px 0; font-size:.95rem; box-shadow:var(--panelsh);}
.notice:before {content:""; position:absolute; left:15px; top:16px; width:14px; height:14px; border-radius:50%;
                background:var(--red); box-shadow:inset -3px -3px 0 rgba(0,0,0,.18);}
.start {position:relative; background:var(--yellow); border-radius:var(--cardr); border:var(--cardbd); padding:22px 26px; margin:18px 0 20px;
        box-shadow:var(--cardsh); transform:rotate(calc(-.5deg*var(--tiltk))); font-size:1.02rem; line-height:1.55;}
.start:before {content:""; position:absolute; top:-12px; left:52px; width:96px; height:24px; background:rgba(255,255,255,.65); opacity:var(--tape);
               border:1px solid rgba(0,0,0,.06); transform:rotate(-3deg);}
.start h3 {font-size:calc(2.2rem*var(--hs)); margin:0 0 4px 0; color:var(--red);}

/* ---------- action plan ---------- */
.plancol {position:relative; --bg:var(--yellow); background:var(--bg); border-radius:var(--cardr); border:var(--cardbd);
          padding:20px 16px 12px; min-height:140px; box-shadow:var(--cardsh);}
.plancol:before {content:""; position:absolute; top:-11px; left:calc(50% - 38px); width:76px; height:20px; opacity:var(--tape);
                 background:rgba(255,255,255,.62); border:1px solid rgba(0,0,0,.06); transform:rotate(-2deg);}
.plancol.p0 {--bg:var(--yellow); transform:rotate(calc(-.6deg*var(--tiltk)));} .plancol.p1 {--bg:var(--blue); transform:rotate(calc(.5deg*var(--tiltk)));}
.plancol.p2 {--bg:var(--green); transform:rotate(calc(-.3deg*var(--tiltk)));}
.plancol h4 {margin:0 0 8px 0; color:var(--red) !important; font-size:calc(2rem*var(--hs)); line-height:1.05;}
.planline {position:relative; padding:9px 6px 9px 32px; border-bottom:1.5px dashed rgba(128,128,160,.4); font-size:.92rem;
           line-height:1.42; color:var(--ink);}
.planline:before {content:""; position:absolute; left:5px; top:12px; width:15px; height:15px; border:2px solid var(--ink);
                  border-radius:3px; transform:rotate(calc(-5deg*var(--tiltk))); background:rgba(255,255,255,.25);}
.planline .ref {color:var(--tealD); font-size:.78rem; font-weight:600; margin-left:5px;}

/* ---------- timeline ---------- */
.tl {border-left:3px dotted var(--teal); margin:8px 0 8px 12px; padding-left:22px;}
.tl-item {position:relative; margin:0 0 16px 0;}
.tl-item:before {content:""; position:absolute; left:-33px; top:7px; width:14px; height:14px; background:var(--teal);
                 border:3px solid var(--ink); border-radius:50%;}
.tl-date {font-family:var(--hand); font-weight:700; color:var(--red); font-size:calc(1.4rem*var(--hs)); line-height:1.1;}
.tl-body {font-size:.97rem; color:var(--ink);}

/* ---------- evidence ---------- */
.ev {font-family:'Courier New',Courier,monospace; font-size:.84rem; line-height:24px; color:var(--ink); padding:6px 14px;
     border:1.5px solid var(--line); border-radius:var(--cardr);
     background:repeating-linear-gradient(var(--card), var(--card) 23px, var(--line) 24px);}
.ev mark {background:linear-gradient(transparent 12%, var(--hl) 12%); padding:0 2px; color:inherit;}

/* ---------- native widgets ---------- */
[data-testid="stMetric"] {background:var(--card); border:var(--panelbd); border-radius:var(--cardr); padding:12px 14px;
                          box-shadow:var(--panelsh); transform:rotate(calc(-.6deg*var(--tiltk)));}
[data-testid="stColumn"]:nth-child(even) [data-testid="stMetric"], [data-testid="column"]:nth-child(even) [data-testid="stMetric"] {transform:rotate(calc(.7deg*var(--tiltk)));}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div {overflow:visible;}
[data-testid="stMetricLabel"] p {font-family:var(--hand); font-size:calc(1.3rem*var(--hs)); color:var(--red) !important; font-weight:700; padding-right:.5em;}
.bars {background:var(--card); border:var(--panelbd); border-radius:var(--cardr); padding:12px 18px; margin:14px 0 8px; box-shadow:var(--panelsh);}
.bar-row {display:flex; align-items:center; gap:14px; margin:4px 0;}
.bar-l {width:130px; font-family:var(--hand); font-size:calc(1.4rem*var(--hs)); font-weight:700; line-height:1.2; color:var(--ink);}
.bar-track {flex:1; height:18px; border:2px solid var(--ink); border-radius:10px; background:var(--card); overflow:hidden;}
.bar-fill {height:100%; min-width:0;} .bar-fill.ok {background:var(--teal);} .bar-fill.warn {background:#f2c94c;}
.bar-fill.bad {background:#e5533d;}
.bar-n {width:40px; text-align:right; font-family:var(--hand); font-size:calc(1.6rem*var(--hs)); font-weight:700; color:var(--ink);}
.rd-head {display:flex; align-items:center; gap:18px; margin:6px 0 10px;}
.rd-score {font-family:var(--hand); font-size:calc(3.4rem*var(--hs)); font-weight:700; line-height:1; color:var(--ink);}
.rd-score small {font-size:.4em; color:var(--muted);} .rd-band {font-weight:700; color:var(--ink);}
.rd-part {margin:10px 0 2px;} .rd-part .bar-l {width:240px; font-size:calc(1.15rem*var(--hs));}
.rd-part .bar-n {width:110px; font-size:calc(1.1rem*var(--hs));}
.rd-detail {margin:0 0 2px 0; font-size:.86rem; color:var(--muted);}
.rd-do {margin:2px 0 0 18px; font-size:.88rem; color:var(--ink);} .rd-do .ref {color:var(--muted); font-size:.78rem;}
[data-testid="stMetricValue"] {font-family:var(--hand); font-weight:700; font-size:calc(2.6rem*var(--hs)); color:var(--ink);}

.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stFormSubmitButton"] > button {
  background:var(--btnbg); color:var(--btnfg); border:var(--btnbd); border-radius:var(--btnr); padding:.2rem 1.1rem;
  box-shadow:var(--btnsh); transition:transform .08s, filter .08s;}
.stButton > button p, .stDownloadButton > button p, [data-testid="stFormSubmitButton"] > button p {
  font-family:var(--hand); font-size:calc(1.3rem*var(--hs)); font-weight:700; color:var(--btnfg) !important; line-height:1.3;}
.stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  background:var(--btnbg); color:var(--btnfg); border:var(--btnbd); transform:translate(-1px,-1px); filter:brightness(1.1);}
.stButton > button:active, .stDownloadButton > button:active {transform:translate(2px,2px); box-shadow:none;}
.stButton > button:disabled {opacity:.45;}

[data-testid="stAlert"] {border:1.5px var(--dst) var(--ink); border-radius:var(--cardr); background:var(--card); box-shadow:var(--panelsh);}
[data-testid="stAlert"] p {color:var(--ink);}
[data-testid="stExpander"] details {border:1.5px var(--dst) var(--line); border-radius:var(--cardr); background:var(--card);}
[data-testid="stExpander"] summary p {font-weight:600;}
[data-testid="stForm"] {border:1.5px var(--dst) var(--line); border-radius:var(--cardr); background:transparent;}
[data-testid="stTab"] p, button[role="tab"] p {font-family:var(--hand) !important; font-size:calc(1.6rem*var(--hs)); font-weight:700;}
[data-testid="stTab"][data-selected="true"] p, button[role="tab"][aria-selected="true"] p {color:var(--red) !important;}
[data-baseweb="tab-highlight"] {background:var(--red) !important; height:3px !important;}
[data-testid="stDataFrame"] {border:1.5px solid var(--line); border-radius:var(--cardr); box-shadow:var(--panelsh); overflow:hidden;}
[data-testid="stFileUploaderDropzone"] {background:var(--card); border:2px dashed var(--ink); border-radius:10px;}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {background:var(--card) !important;}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="select"] div {color:var(--ink) !important;}
[data-baseweb="input"] input::placeholder, [data-baseweb="textarea"] textarea::placeholder {color:var(--muted) !important; opacity:.8;}
.foot {font-family:var(--hand); color:var(--muted); font-size:calc(1.25rem*var(--hs)); text-align:center; margin-top:34px;}
.foot:before {content:""; display:block; width:160px; margin:0 auto 8px; border-top:3px dotted var(--teal);}

/* ---------- My notes ---------- */
.pn-title {font-family:var(--hand); font-size:calc(2.5rem*var(--hs)); font-weight:700; line-height:1; margin:0 0 4px; color:var(--ink);}
.pn-stats {font-size:.82rem; color:var(--muted); margin:0 0 8px;}
.pn-sub {color:var(--muted); font-style:italic; margin:0 0 10px;}
.pn-h {font-family:var(--hand); font-size:calc(1.9rem*var(--hs)); font-weight:700; line-height:1.1; margin:4px 0 6px; color:var(--ink);}
.sn-empty {border:2px var(--dst) var(--line); border-radius:var(--cardr); padding:28px 18px; text-align:center; color:var(--muted);
           font-family:var(--hand); font-size:calc(1.4rem*var(--hs)); background:var(--card); margin-top:8px;}
.sn {position:relative; --bg:var(--yellow); background:var(--bg); border-radius:var(--cardr); border:var(--cardbd);
     padding:10px 14px 8px; margin:12px 0 4px; box-shadow:var(--cardsh); transform:rotate(calc(var(--r,0deg)*var(--tiltk)));}
.sn.c-yellow {--bg:var(--yellow);} .sn.c-green {--bg:var(--green);} .sn.c-blue {--bg:var(--blue);} .sn.c-pink {--bg:var(--pink);}
.sn.pinned:after {content:""; position:absolute; top:-7px; right:16px; width:14px; height:14px; border-radius:50%; background:var(--red);
                  box-shadow:inset -3px -3px 0 rgba(0,0,0,.22), 0 2px 3px rgba(0,0,0,.25);}
.sn.done .sn-body {text-decoration:line-through; opacity:.55;}
.sn-top {display:flex; justify-content:space-between; align-items:flex-start; gap:8px; margin-bottom:4px;}
.sn-who {font-size:.74rem; color:var(--muted); white-space:nowrap; padding-top:2px;}
.sn-body {font-family:var(--hand); font-size:calc(1.4rem*var(--hs)); line-height:1.2; color:var(--ink); word-break:break-word;}
.sn-meta {font-size:.76rem; color:var(--muted); margin-top:5px;}
.stuck {display:block; width:fit-content; max-width:88%; margin:8px 0 0 auto; --bg:var(--green); background:var(--bg); color:var(--ink);
        padding:6px 11px; border-radius:var(--cardr); border:var(--cardbd); box-shadow:var(--cardsh);
        font-family:var(--hand); font-size:calc(1.15rem*var(--hs)); line-height:1.2; transform:rotate(calc(1.6deg*var(--tiltk)));}
.stuck b {font-weight:700;}
.noev {border:1.5px var(--dst) var(--ink); border-radius:var(--cardr); padding:10px 12px; font-size:.84rem; margin-top:14px;
       background:var(--card); color:var(--ink);}
.remind {background:var(--yellow); color:var(--ink); border:1.5px var(--dst) var(--ink); border-radius:var(--cardr);
         padding:9px 14px; margin:0 0 14px; font-size:.95rem; box-shadow:var(--panelsh);}
.remind b {font-family:var(--hand); font-size:calc(1.3rem*var(--hs));}

/* ---------- theme preview tiles ---------- */
.tp {background-color:var(--paper); background-image:var(--bgimg); background-size:var(--bgsize); color:var(--ink);
     font-family:var(--serif); border:2px solid var(--line); border-radius:14px; padding:12px 12px 14px; min-height:290px;
     overflow:hidden; line-height:1.35; letter-spacing:var(--ls);}
.tp.current {outline:3px solid #24baa2; outline-offset:2px;}
.tp-brand {font-family:var(--hand); font-size:calc(1.5rem*var(--hs)); font-weight:700; margin-bottom:6px; color:var(--ink);}
.tp-brand span {color:var(--teal);}
.tp-trail {display:flex; align-items:center; gap:0; margin:2px 0 8px;}
.tp-trail i {width:14px; height:14px; border-radius:50%; border:2.5px solid var(--ink); background:var(--numbg); display:block;}
.tp-trail i.d {background:var(--teal);} .tp-trail i.c {background:var(--yellow); border-color:var(--red);}
.tp-trail b {width:18px; border-top:3px dotted var(--teal); display:block;}
.tp .card {margin:10px 0 6px; padding:11px 12px 8px;}
.tp .card .text {font-size:.8rem; line-height:1.35;}
.tp .card .top {margin-bottom:4px;}
.tp .chip {font-size:.64rem; padding:0 8px;}
.tp-btn {display:inline-block; margin-top:8px; background:var(--btnbg); color:var(--btnfg); border:var(--btnbd); border-radius:var(--btnr);
         box-shadow:var(--btnsh); padding:2px 14px; font-family:var(--hand); font-size:calc(1.15rem*var(--hs)); font-weight:700;}
.tp-name {font-family:var(--hand); font-weight:700; font-size:1.05rem; margin:6px 0 0; color:var(--ink);}
.tp-desc {font-size:.78rem; color:var(--muted); margin:0 0 4px; min-height:2.4em;}
.swatches {display:flex; gap:8px; margin:2px 0 8px;} .swatches i {width:22px; height:22px; border-radius:50%; display:block; border:2px solid rgba(0,0,0,.25);}
"""


def base_css() -> str:
    v, _ = themes.theme_vars("notebook")
    return (f"<style>@import url('{themes.FONT_IMPORT}');\n:root{{{themes._decl(v)}}}\n{RULES}</style>")
