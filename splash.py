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
