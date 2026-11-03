"""Start-up screen: the logo arrives in four short scenes, in pure CSS (no JavaScript).

1. Sources spiral in   Meeting notes, Chat, Tasks and GitHub swirl into the centre.
2. Five dots roll in   The five steps of the app roll in, hop into a line and gather.
3. Letters fly in      The icon flips and the name assembles letter by letter.
4. Logo lands         The taped logo card lands on its own, then the tagline fades in.

It is shown once per browser session, covers the page, fades away by itself after about 6.5 seconds, and can be
skipped with a click. It is skipped when "Reduce tilt and motion" is on, or when the person turns it off in
Appearance. Colours come from the active theme, so it matches all 20 themes. The only text is fixed (no user data).
"""
from __future__ import annotations
import math

import ui

TOTAL_SECONDS = 6.5
WORD = "HandoverTrail"
CHIPS = [("Meeting notes", "yellow", 0), ("Chat", "green", 90), ("Tasks", "blue", 180), ("GitHub", "pink", 270)]
TAGLINE = "Knowledge stays when people go"


def _rnd(i: int, k: int) -> float:
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)


CSS = r"""
.sp{position:fixed;inset:0;z-index:1000000;background-color:var(--paper);background-image:var(--bgimg);background-size:var(--bgsize);
    display:grid;place-items:center;overflow:hidden;cursor:pointer;outline:none;animation:spOut .5s 6s both;}
.sp-d{margin:0;padding:0;}
.sp-d:not([open])>.sp{display:none;}
.sp::-webkit-details-marker{display:none;}
@keyframes spOut{to{opacity:0;visibility:hidden}}
.sp-box{position:relative;width:320px;height:300px;perspective:700px;}
@media (max-width:380px){.sp-box{transform:scale(.8)}}
.sp .at{position:absolute;left:160px;top:150px;width:0;height:0;}
.sp .c{position:absolute;left:0;top:0;transform:translate(-50%,-50%);}
.sp-skip{position:absolute;left:0;right:0;bottom:0;text-align:center;font-size:.78rem;color:var(--muted);letter-spacing:.04em;animation:spIn .5s .6s both;}
@keyframes spIn{from{opacity:0}to{opacity:1}}
@keyframes spFade{to{opacity:0;transform:scale(.9)}}
@keyframes spRing{0%{opacity:1;transform:scale(1)}100%{opacity:0;transform:scale(9)}}

/* 1. sources spiral in */
.sp-orb{position:absolute;left:160px;top:150px;width:0;height:0;animation:spOrb 1.2s .1s cubic-bezier(.55,0,.8,.5) both;}
@keyframes spOrb{from{transform:rotate(var(--a0))}to{transform:rotate(calc(var(--a0) + 630deg))}}
.sp-chip{position:absolute;left:0;top:0;margin:-14px 0 0 -48px;width:96px;height:28px;display:grid;place-items:center;border:2px solid var(--ink);
         border-radius:999px;background:var(--bg);font-family:var(--serif);font-size:.74rem;font-weight:700;color:var(--ink);white-space:nowrap;
         animation:spChip 1.2s .1s cubic-bezier(.55,0,.8,.5) both;}
@keyframes spChip{from{opacity:1;transform:translateX(124px) rotate(calc(var(--a0) * -1)) scale(1)}85%{opacity:1}
                  to{opacity:0;transform:translateX(0) rotate(calc(var(--a0) * -1 - 630deg)) scale(.2)}}
.sp-ring{position:absolute;left:160px;top:150px;width:20px;height:20px;margin:-10px;border-radius:50%;border:3px solid var(--teal);opacity:0;}
.sp-ring.r1{animation:spRing .7s 1.25s forwards}

/* 2. five dots roll in */
.sp-ground{position:absolute;left:0;right:0;top:214px;border-top:3px dotted var(--teal);opacity:0;animation:spGround 1.7s 1.25s forwards;}
@keyframes spGround{0%{opacity:0}15%{opacity:.5}80%{opacity:.5}100%{opacity:0}}
.sp-dot{position:absolute;top:188px;width:26px;height:26px;border-radius:50%;border:3px solid var(--ink);
        background:conic-gradient(var(--k) 0 50%, var(--card) 50% 100%);opacity:0;animation:spDot 1.2s cubic-bezier(.25,.8,.35,1) forwards;
        animation-delay:calc(1.25s + var(--i) * .07s);}
@keyframes spDot{0%{opacity:1;transform:translate(var(--from),0) rotate(calc(var(--dir) * -900deg)) scale(1)}
  40%{opacity:1;transform:translate(0,0) rotate(0) scale(1)}47%{opacity:1;transform:translate(0,-20px) rotate(0) scale(1)}
  54%{opacity:1;transform:translate(0,0) rotate(0) scale(1.1)}62%{opacity:1;transform:translate(0,0) rotate(0) scale(1)}
  100%{opacity:0;transform:translate(var(--gx),-64px) rotate(0) scale(.2)}}
.sp-ring.r2{animation:spRing .6s 2.55s forwards}

/* 3. letters fly in */
.sp-word{position:absolute;inset:0;animation:spFade .3s 3.95s both;}
.sp-icon{position:absolute;left:160px;top:74px;width:72px;height:72px;margin:-36px 0 0 -36px;border-radius:16px;border:2px solid var(--ink);
         background:#fff;box-shadow:3px 3px 0 var(--teal);opacity:0;animation:spFlip .9s 2.45s cubic-bezier(.3,1.3,.5,1) both;}
@keyframes spFlip{0%{opacity:0;transform:rotateY(0) scale(.1)}100%{opacity:1;transform:rotateY(720deg) scale(1)}}
.sp-letters{position:absolute;left:0;right:0;top:150px;text-align:center;white-space:nowrap;font-family:var(--hand);font-weight:700;
            font-size:calc(3.1rem*var(--hs));line-height:1;color:var(--ink);}
.sp-letters span{display:inline-block;opacity:0;animation:spLt .65s cubic-bezier(.3,1.5,.5,1) both;animation-delay:calc(2.55s + var(--i) * .05s);}
.sp-letters .t{color:var(--teal);}
@keyframes spLt{0%{opacity:0;transform:translate(var(--x),var(--y)) rotate(var(--r)) scale(.3)}100%{opacity:1;transform:translate(0,0) rotate(0) scale(1)}}

/* 4. the taped logo lands */
.sp-logo{position:relative;width:190px;background:#fff;border:2px solid var(--ink);border-radius:14px;padding:8px 8px 4px;box-shadow:4px 4px 0 var(--teal);
         opacity:0;animation:spSlap2 .55s 4.3s cubic-bezier(.3,1.1,.5,1) both;}
.sp-logo img{display:block;width:100%;}
.sp-logo:before{content:"";position:absolute;top:-12px;left:50%;width:84px;height:22px;margin-left:-42px;background:rgba(240,206,110,.9);transform:rotate(-3deg);}
@keyframes spSlap2{0%{opacity:0;transform:translate(0,-260px) rotate(14deg) scale(1.8)}60%{opacity:1}100%{opacity:1;transform:translate(0,0) rotate(-2deg) scale(1)}}
.sp-tag{position:absolute;left:0;right:0;top:226px;text-align:center;font-family:var(--hand);font-size:calc(1.9rem*var(--hs));color:var(--red);
        white-space:nowrap;opacity:0;animation:spIn .6s 5s both;}
@media (prefers-reduced-motion:reduce){.sp{display:none}}
"""


def markup(user_motion_off: bool = False) -> str:
    """The whole overlay (style + markup). Returns '' when motion is off."""
    if user_motion_off:
        return ""
    logo, icon = ui.asset_uri("logo.png"), ui.asset_uri("icon.png")
    chips = "".join(
        f"<div class='sp-orb' style='--a0:{a}deg'><div class='sp-chip' style='--bg:var(--{c});--a0:{a}deg'>{ui.esc(t)}</div></div>"
        for t, c, a in CHIPS)
    cols = ["var(--teal)", "var(--ink)", "var(--yellow)", "var(--pink)", "var(--blue)"]
    dots = ""
    for i in range(5):
        x = 60 + i * 50
        frm = 280 if i % 2 else -280
        dots += (f"<i class='sp-dot' style='left:{x - 13}px;--i:{i};--k:{cols[i]};--from:{frm}px;"
                 f"--dir:{-1 if frm > 0 else 1};--gx:{160 - x}px'></i>")
    letters = ""
    for i, ch in enumerate(WORD):
        a, dist = _rnd(i, 1) * 6.28, 150 + _rnd(i, 2) * 110
        letters += (f"<span class='{'t' if i >= 8 else ''}' style='--i:{i};--x:{round(math.cos(a) * dist)}px;"
                    f"--y:{round(math.sin(a) * dist - 30)}px;--r:{round((_rnd(i, 3) - .5) * 540)}deg'>{ui.esc(ch)}</span>")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<b>HandoverTrail</b>"
    icn = f"<img class='sp-icon' src='{icon}' alt=''>" if icon else ""
    return (f"<style>{CSS}</style>"
            "<details class='sp-d' open><summary class='sp' aria-label='HandoverTrail is starting. Click to skip.'><div class='sp-box'>"
            f"{chips}<i class='sp-ring r1'></i><div class='sp-ground'></div>{dots}<i class='sp-ring r2'></i>"
            f"<div class='sp-word'>{icn}<div class='sp-letters'>{letters}</div></div>"
            f"<div class='at'><div class='c'><div class='sp-logo'>{img}</div></div></div>"
            f"<div class='sp-tag'>{ui.esc(TAGLINE)}</div>"
            "<div class='sp-skip'>Click anywhere to skip</div></div></summary></details>")
