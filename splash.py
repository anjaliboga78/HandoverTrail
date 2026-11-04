"""Start-up screen: source chips drop in, the logo card lands, a baton runs along the five-step trail, the tagline fades in.

Pure CSS (no JavaScript), phone friendly, uses the active theme colours. It covers the page, fades away by itself after
about 5 seconds and can be skipped with a tap. Skipped when "Reduce tilt and motion" is on. Only fixed text is shown.
"""
from __future__ import annotations

import ui

TAGLINE = "Knowledge stays when people go"
CHIPS = [("Meeting notes", "yellow"), ("Chat", "green"), ("Tasks", "blue"), ("GitHub", "pink")]
STEPS = 5

CSS = r"""
.sp{position:fixed;inset:0;z-index:1000000;background-color:var(--paper);background-image:var(--bgimg);background-size:var(--bgsize);
    display:grid;place-items:center;overflow:hidden;cursor:pointer;outline:none;animation:spOut .5s 4.6s both;}
.sp-d{margin:0;padding:0;}
.sp-d:not([open])>.sp{display:none;}
.sp::-webkit-details-marker{display:none;}
@keyframes spOut{to{opacity:0;visibility:hidden}}
@keyframes spIn{from{opacity:0}to{opacity:1}}

.sp-box{width:min(88vw,340px);display:flex;flex-direction:column;align-items:center;gap:1.5rem;text-align:center;}

/* sources drop in, then bob gently */
.sp-chips{display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem;}
.sp-chip{padding:.3rem .8rem;border:2px solid var(--ink);border-radius:999px;background:var(--bg);color:var(--ink);
         font-family:var(--serif);font-size:.82rem;font-weight:700;white-space:nowrap;opacity:0;
         animation:spChip .6s calc(.15s + var(--i)*.15s) cubic-bezier(.3,1.4,.5,1) both,
                   spBob 2.2s calc(1s + var(--i)*.2s) ease-in-out infinite;}
@keyframes spChip{0%{opacity:0;transform:translateY(-40px) scale(.7)}100%{opacity:1;transform:none}}
@keyframes spBob{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}

/* logo card lands */
.sp-logo{position:relative;width:min(66vw,230px);background:#fff;border:2px solid var(--ink);border-radius:14px;
         padding:8px 8px 4px;box-shadow:4px 4px 0 var(--teal);opacity:0;animation:spLand .7s .9s cubic-bezier(.3,1.1,.5,1) both;}
.sp-logo img{display:block;width:100%;}
.sp-logo:before{content:"";position:absolute;top:-11px;left:50%;width:76px;height:20px;margin-left:-38px;
                background:rgba(240,206,110,.9);transform:rotate(-3deg);}
@keyframes spLand{0%{opacity:0;transform:translateY(-70px) rotate(8deg) scale(1.3)}100%{opacity:1;transform:rotate(-2deg)}}

/* the trail: a baton runs along five stops */
.sp-trail{position:relative;width:100%;height:30px;opacity:0;animation:spIn .4s 1.6s both;}
.sp-trail:before{content:"";position:absolute;left:4%;right:4%;top:14px;border-top:3px dotted var(--teal);}
.sp-stops{position:absolute;left:4%;right:4%;top:4px;display:flex;justify-content:space-between;}
.sp-stop{width:20px;height:20px;border-radius:50%;border:3px solid var(--ink);background:var(--card);
         animation:spStop .35s calc(1.8s + var(--i)*.4s) both;}
@keyframes spStop{0%{transform:scale(1)}50%{transform:scale(1.5);background:var(--teal)}100%{transform:scale(1);background:var(--teal)}}
.sp-baton{position:absolute;left:4%;right:4%;top:0;height:30px;}
.sp-baton i{position:absolute;left:0;top:5px;width:20px;height:20px;margin-left:-10px;border-radius:50%;background:var(--red);
            border:3px solid var(--ink);animation:spRun 1.8s 1.8s ease-in-out both;}
@keyframes spRun{0%{left:0}100%{left:100%}}

.sp-tag{font-family:var(--hand);font-size:calc(1.6rem*var(--hs));color:var(--red);line-height:1.2;opacity:0;animation:spIn .7s 3.3s both;}
.sp-skip{position:absolute;left:0;right:0;bottom:1.2rem;text-align:center;font-size:.78rem;color:var(--muted);
         letter-spacing:.04em;opacity:0;animation:spIn .5s .8s both;}
@media (prefers-reduced-motion:reduce){.sp{display:none}}
"""


def markup(user_motion_off: bool = False) -> str:
    """The whole overlay (style + markup). Returns '' when motion is off."""
    if user_motion_off:
        return ""
    logo = ui.asset_uri("logo.png")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<b>HandoverTrail</b>"
    chips = "".join(f"<span class='sp-chip' style='--i:{i};--bg:var(--{c})'>{ui.esc(t)}</span>" for i, (t, c) in enumerate(CHIPS))
    stops = "".join(f"<i class='sp-stop' style='--i:{i}'></i>" for i in range(STEPS))
    return (f"<style>{CSS}</style>"
            "<details class='sp-d' open><summary class='sp' aria-label='HandoverTrail is starting. Tap to skip.'>"
            f"<div class='sp-box'><div class='sp-chips'>{chips}</div>"
            f"<div class='sp-logo'>{img}</div>"
            f"<div class='sp-trail'><div class='sp-stops'>{stops}</div><div class='sp-baton'><i></i></div></div>"
            f"<div class='sp-tag'>{ui.esc(TAGLINE)}</div></div>"
            "<div class='sp-skip'>Tap anywhere to skip</div></summary></details>")
