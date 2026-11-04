"""Simple start-up screen: logo drops in, tagline fades in. Pure CSS. Click to skip."""
from __future__ import annotations

import ui

TAGLINE = "Knowledge stays when people go"

CSS = r"""
.sp{position:fixed;inset:0;z-index:1000000;background-color:var(--paper);background-image:var(--bgimg);background-size:var(--bgsize);
    display:grid;place-items:center;overflow:hidden;cursor:pointer;outline:none;animation:spOut .5s 3s both;}
.sp-d{margin:0;padding:0;}
.sp-d:not([open])>.sp{display:none;}
.sp::-webkit-details-marker{display:none;}
@keyframes spOut{to{opacity:0;visibility:hidden}}
.sp-box{display:flex;flex-direction:column;align-items:center;gap:1.2rem;padding:0 1rem;text-align:center;}
.sp-logo{position:relative;width:min(70vw,230px);background:#fff;border:2px solid var(--ink);border-radius:14px;padding:8px 8px 4px;
         box-shadow:4px 4px 0 var(--teal);opacity:0;animation:spDrop .7s .2s cubic-bezier(.3,1.1,.5,1) both;}
.sp-logo img{display:block;width:100%;}
@keyframes spDrop{0%{opacity:0;transform:translateY(-80px) rotate(8deg) scale(1.3)}100%{opacity:1;transform:none rotate(-2deg)}}
.sp-tag{font-family:var(--hand);font-size:calc(1.6rem*var(--hs));color:var(--red);opacity:0;animation:spIn .6s 1s both;}
.sp-skip{font-size:.78rem;color:var(--muted);letter-spacing:.04em;opacity:0;animation:spIn .5s .8s both;}
@keyframes spIn{from{opacity:0}to{opacity:1}}
@media (prefers-reduced-motion:reduce){.sp{display:none}}
"""


def markup(user_motion_off: bool = False) -> str:
    if user_motion_off:
        return ""
    logo = ui.asset_uri("logo.png")
    img = f"<img src='{logo}' alt='HandoverTrail logo'>" if logo else "<b>HandoverTrail</b>"
    return (f"<style>{CSS}</style>"
            "<details class='sp-d' open><summary class='sp' aria-label='HandoverTrail is starting. Click to skip.'>"
            f"<div class='sp-box'><div class='sp-logo'>{img}</div>"
            f"<div class='sp-tag'>{ui.esc(TAGLINE)}</div>"
            "<div class='sp-skip'>Tap to skip</div></div></summary></details>")
