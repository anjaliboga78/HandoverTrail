"""Start-up screen: minimal and pure CSS (no JavaScript).

1. Letters fly in   The letters of "HandoverTrail" start scattered and faint, then fly and spin into place.
2. Logo appears     The word fades out and the ORIGINAL logo (assets/logo.png, unchanged) fades in, then the tagline.

About 3.6 seconds in total. The overlay is fully opaque (the app never shows through while it loads), fades away by
itself and can be skipped with a tap. It uses the active theme colours. Skipped when "Reduce tilt and motion" is on.
"""
from __future__ import annotations
import math

import ui

TOTAL_SECONDS = 3.6
WORD = "HandoverTrail"
TAGLINE = "Knowledge stays when people go"


def _rnd(i: int, k: int) -> float:
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return x - math.floor(x)


CSS = r"""
.sp{position:fixed;inset:0;z-index:1000000;background-color:var(--paper,#ffffff);background-image:var(--bgimg,none);
    background-size:var(--bgsize,auto);display:grid;place-items:center;overflow:hidden;cursor:pointer;outline:none;
    animation:spOut .4s 3.2s both;}
.sp-d{margin:0;padding:0;}
.sp-d:not([open])>.sp{display:none;}
.sp::-webkit-details-marker{display:none;}
@keyframes spOut{to{opacity:0;visibility:hidden}}
@keyframes spIn{from{opacity:0}to{opacity:1}}

.sp-box{position:relative;width:min(88vw,340px);height:240px;}

/* 1. letters fly in, then the word fades away */
.sp-word{position:absolute;inset:0;display:grid;place-items:center;animation:spWordOut .3s 1.7s both;}
.sp-letters{white-space:nowrap;font-family:var(--hand,system-ui,sans-serif);font-weight:700;
            font-size:calc(2.5rem*var(--hs,1));line-height:1;color:var(--ink,#101046);}
.sp-letters span{display:inline-block;opacity:0;animation:spLt .8s cubic-bezier(.2,.9,.3,1) both;
                 animation-delay:calc(.1s + var(--i) * .05s);}
.sp-letters .t{color:var(--teal,#24baa2);}
@keyframes spLt{0%{opacity:0;transform:translate(var(--x),var(--y)) rotate(var(--r)) scale(.5)}100%{opacity:1;transform:translate(0,0) rotate(0) scale(1)}}
@keyframes spWordOut{to{opacity:0;transform:scale(.96)}}

/* 2. the original logo appears, then the tagline */
.sp-logo{position:absolute;left:50%;top:44%;width:min(62vw,210px);transform:translate(-50%,-50%);background:#fff;
         border-radius:14px;padding:8px;opacity:0;animation:spLogo .5s 2s ease-out both;}
.sp-logo img{display:block;width:100%;}
@keyframes spLogo{from{opacity:0;margin-top:8px}to{opacity:1;margin-top:0}}
.sp-tag{position:absolute;left:0;right:0;top:186px;text-align:center;font-family:var(--hand,system-ui,sans-serif);
        font-size:calc(1.15rem*var(--hs,1));color:var(--muted,#6b7090);opacity:0;animation:spIn .4s 2.5s both;}
.sp-skip{position:absolute;left:0;right:0;bottom:1.2rem;text-align:center;font-size:.78rem;color:var(--muted,#777);
         letter-spacing:.04em;opacity:0;animation:spIn .4s .4s both;}
@media (prefers-reduced-motion:reduce){.sp{display:none}}
"""


def markup(user_motion_off: bool = False) -> str:
    """The whole overlay (style + markup). Returns '' when motion is off."""
    if user_motion_off:
        return ""
    logo = ui.asset_uri("logo.png")
    letters = ""
    for i, ch in enumerate(WORD):
        a, dist = _rnd(i, 1) * 6.28, 120 + _rnd(i, 2) * 110
        letters += (f"<span class='{'t' if i >= 8 else ''}' style='--i:{i};--x:{round(math.cos(a) * dist)}px;"
                    f"--y:{round(math.sin(a) * dist - 20)}px;--r:{round((_rnd(i, 3) - .5) * 540)}deg'>{ui.esc(ch)}</span>")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<b>HandoverTrail</b>"
    return (f"<style>{CSS}</style>"
            "<details class='sp-d' open><summary class='sp' aria-label='HandoverTrail is starting. Tap to skip.'>"
            f"<div class='sp-box'><div class='sp-word'><div class='sp-letters'>{letters}</div></div>"
            f"<div class='sp-logo'>{img}</div><div class='sp-tag'>{ui.esc(TAGLINE)}</div></div>"
            "<div class='sp-skip'>Tap anywhere to skip</div></summary></details>")
