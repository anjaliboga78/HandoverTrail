"""Start-up screen: a quick 2.4 second intro. The logo card lands, a baton runs along the five-step trail, the tagline fades in.

Pure CSS, no JavaScript, uses the active theme colours. The overlay is fully opaque (so the app never shows through while it
loads), fades away by itself and can be skipped with a tap. Skipped when "Reduce tilt and motion" is on.
"""
from __future__ import annotations

import ui

TAGLINE = "Knowledge stays when people go"
STEPS = 5

CSS = r"""
.sp{position:fixed;inset:0;z-index:1000000;background-color:var(--paper,#faf6ea);background-image:var(--bgimg,none);
    background-size:var(--bgsize,auto);display:grid;place-items:center;overflow:hidden;cursor:pointer;outline:none;
    animation:spOut .45s 2.3s both;}
.sp-d{margin:0;padding:0;}
.sp-d:not([open])>.sp{display:none;}
.sp::-webkit-details-marker{display:none;}
@keyframes spOut{to{opacity:0;visibility:hidden}}
@keyframes spIn{from{opacity:0}to{opacity:1}}

.sp-box{width:min(80vw,320px);display:flex;flex-direction:column;align-items:center;gap:1.6rem;text-align:center;}

.sp-logo{position:relative;width:min(62vw,220px);background:#fff;border:2px solid var(--ink,#222);border-radius:14px;
         padding:8px 8px 4px;box-shadow:4px 4px 0 var(--teal,#1d8a8a);opacity:0;
         animation:spLand .6s .05s cubic-bezier(.3,1.1,.5,1) both;}
.sp-logo img{display:block;width:100%;}
.sp-logo:before{content:"";position:absolute;top:-11px;left:50%;width:76px;height:20px;margin-left:-38px;
                background:rgba(240,206,110,.9);transform:rotate(-3deg);}
@keyframes spLand{0%{opacity:0;transform:translateY(-50px) rotate(6deg) scale(1.2)}100%{opacity:1;transform:rotate(-2deg)}}

.sp-trail{position:relative;width:100%;height:30px;opacity:0;animation:spIn .3s .5s both;}
.sp-trail:before{content:"";position:absolute;left:4%;right:4%;top:14px;border-top:3px dotted var(--teal,#1d8a8a);}
.sp-stops{position:absolute;left:4%;right:4%;top:4px;display:flex;justify-content:space-between;}
.sp-stop{width:20px;height:20px;border-radius:50%;border:3px solid var(--ink,#222);background:var(--card,#fff);
         animation:spStop .3s calc(.6s + var(--i)*.22s) both;}
@keyframes spStop{0%{transform:scale(1)}50%{transform:scale(1.45);background:var(--teal,#1d8a8a)}100%{transform:scale(1);background:var(--teal,#1d8a8a)}}
.sp-baton{position:absolute;left:4%;right:4%;top:0;height:30px;}
.sp-baton i{position:absolute;left:0;top:5px;width:20px;height:20px;margin-left:-10px;border-radius:50%;background:var(--red,#d9534f);
            border:3px solid var(--ink,#222);animation:spRun 1s .6s ease-in-out both;}
@keyframes spRun{0%{left:0}100%{left:100%}}

.sp-tag{font-family:var(--hand,cursive);font-size:calc(1.5rem*var(--hs,1));color:var(--red,#d9534f);line-height:1.2;
        opacity:0;animation:spIn .5s 1.2s both;}
.sp-skip{position:absolute;left:0;right:0;bottom:1.2rem;text-align:center;font-size:.78rem;color:var(--muted,#777);
         letter-spacing:.04em;opacity:0;animation:spIn .4s .4s both;}
@media (prefers-reduced-motion:reduce){.sp{display:none}}
"""


def markup(user_motion_off: bool = False) -> str:
    """The whole overlay (style + markup). Returns '' when motion is off."""
    if user_motion_off:
        return ""
    logo = ui.asset_uri("logo.png")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<b>HandoverTrail</b>"
    stops = "".join(f"<i class='sp-stop' style='--i:{i}'></i>" for i in range(STEPS))
    return (f"<style>{CSS}</style>"
            "<details class='sp-d' open><summary class='sp' aria-label='HandoverTrail is starting. Tap to skip.'>"
            f"<div class='sp-box'><div class='sp-logo'>{img}</div>"
            f"<div class='sp-trail'><div class='sp-stops'>{stops}</div><div class='sp-baton'><i></i></div></div>"
            f"<div class='sp-tag'>{ui.esc(TAGLINE)}</div></div>"
            "<div class='sp-skip'>Tap anywhere to skip</div></summary></details>")
