"""Generates the shared hotspot portal theme catalog (used by Mikro Wave and Ruijie).

Each theme picks a `layout` (a distinct HTML/CSS skeleton) plus its own
palette and typography, so themes differ in structure as well as color —
not just a recolored copy of the same card. This produces two sibling file
sets per theme+version, from the same THEMES entry: the Mikrotik-style
`$(variable)`-templated router pages under `themes/<id>/<version>/`, and a
Ruijie Cloud custom-portal bundle (`index.html` + `loadConfig.json`, meant
to be zipped with a background image by the app) under
`ruijie/<id>/<version>/`. Never hand-edit files under either directory —
both are generated output and get overwritten the next time this runs.

Run: python tools/generate_themes.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


THEMES = [
    {
        "id": "glass", "name": "Glass UI", "version": "1.0.0",
        "layout": "glass",
        "description": "Frosted glass over a deep blue and violet glow.",
        "background": "radial-gradient(circle at 18% 14%,#22d3ee70 0 140px,transparent 141px),"
                       "radial-gradient(circle at 88% 78%,#8b5cf670 0 190px,transparent 191px),"
                       "linear-gradient(145deg,#071322,#17112d)",
        "surface": "#ffffff18", "text": "#f8fbff", "mutedText": "#c6d2e8",
        "primary": "#67e8f9", "primaryText": "#07131c", "secondary": "#ffffff3d",
        "radius": "28px", "shadow": "0 28px 70px #02061799",
        "font": "'Segoe UI',Arial,sans-serif",
    },
    {
        "id": "classic", "name": "Classic", "version": "1.0.0",
        "layout": "classic",
        "description": "Warm paper tones with traditional serif type and fine rules.",
        "background": "linear-gradient(135deg,#f2eadb,#dfcfb4)",
        "surface": "#fffaf0", "text": "#30271d", "mutedText": "#796956",
        "primary": "#744a24", "primaryText": "#fffaf0", "secondary": "#c8b28f",
        "radius": "3px", "shadow": "0 22px 55px #51391f33",
        "font": "Georgia,'Times New Roman',serif",
    },
    {
        "id": "cyberpunk", "name": "Cyberpunk", "version": "1.0.0",
        "layout": "cyberpunk",
        "description": "Angular neon cyan and magenta interface on black.",
        "background": "linear-gradient(#07101acc 1px,transparent 1px),"
                       "linear-gradient(90deg,#07101acc 1px,transparent 1px),"
                       "radial-gradient(circle at 80% 12%,#ff2bd63d,transparent 36%),#02050a",
        "surface": "#080d17f2", "text": "#f6f8ff", "mutedText": "#81dce4",
        "primary": "#20f6ff", "primaryText": "#02070c", "secondary": "#ff2bd6",
        "radius": "2px", "shadow": "12px 12px 0 #ff2bd633,0 0 45px #20f6ff1f",
        "font": "'Courier New',monospace",
    },
    {
        "id": "dark", "name": "Dark UI", "version": "1.0.0",
        "layout": "dark",
        "description": "Clean charcoal interface with a restrained violet accent.",
        "background": "radial-gradient(circle at 50% -10%,#30364a 0,transparent 45%),"
                       "linear-gradient(160deg,#050609,#0c0f15)",
        "surface": "#151820", "text": "#f4f6fb", "mutedText": "#929aad",
        "primary": "#7c5cff", "primaryText": "#ffffff", "secondary": "#303541",
        "radius": "20px", "shadow": "0 28px 70px #000000a6",
        "font": "'Segoe UI',Arial,sans-serif",
    },
]


def compact(source: str) -> str:
    return "".join(line.strip() for line in source.splitlines())


def with_alpha(color: str, alpha_hex: str) -> str:
    """`color` (a #rrggbb or #rrggbbaa hex string) with its alpha replaced by `alpha_hex`."""
    return f"#{color.lstrip('#')[:6]}{alpha_hex}"


MW_LOGIN_JS = "function mwLogin(f){f.username.value=f.username.value.toUpperCase().trim();f.password.value=f.username.value;return true;}"


def base_reset(theme: dict) -> str:
    return f"*{{box-sizing:border-box}}body{{margin:0;font-family:{theme['font']};background:{theme['background']};color:{theme['text']};display:grid;place-items:center;min-height:100vh;padding:18px}}"


def shared_controls(theme: dict, extra: str = "") -> str:
    p, pt, sec, surf, txt = theme["primary"], theme["primaryText"], theme["secondary"], theme["surface"], theme["text"]
    return compact(f"""
    .field{{width:100%;padding:13px 14px;margin:7px 0;border:1px solid {sec};border-radius:10px;font-size:15px;background:{surf};color:{txt};text-transform:uppercase;font-family:inherit}}
    .btn{{display:block;width:100%;padding:13px;border:0;border-radius:10px;background:{p};color:{pt};font-size:15px;font-weight:700;margin-top:10px;text-align:center;text-decoration:none;font-family:inherit;cursor:pointer}}
    .error{{color:#e5484d;text-align:center;font-size:13px;margin:12px 0 0;min-height:14px}}
    .ok{{color:{p};text-align:center;font-size:44px}}
    .rows{{margin:6px 0 0}}.row{{display:flex;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid {sec}}}.row span{{color:{theme['mutedText']}}}
    {extra}
    """)


# ---------------------------------------------------------------- layouts --

def layout_card(theme: dict, title: str, sub: str, body: str) -> str:
    p = theme["primary"]
    card_css = f".wrap{{width:min(92vw,380px)}}.card{{background:{theme['surface']};padding:32px 28px;border-radius:{theme['radius']};box-shadow:{theme['shadow']};border:1px solid {theme['secondary']}}}"
    if theme.get("blur"):
        # No backdrop-filter: Android's captive-portal sign-in WebView (the OS's
        # "Sign in to Hotspot Router" screen, not a full Chrome tab) has been seen
        # rendering backdrop-filter elements solid black instead of blurring on
        # real devices — it reports the property as supported so @supports can't
        # detect the failure. A flatter, more opaque translucent panel is the
        # "glass" look that actually renders reliably there; see layout_glass().
        card_css += f".card{{background:{with_alpha(theme['surface'], '3d')};border:1px solid #ffffff33}}"
    if theme.get("hardBorder"):
        card_css += f".card{{border:3px solid {theme['secondary']}}}"
    if theme.get("accentBar"):
        card_css += f".card{{border:1px solid {theme['secondary']};border-left:5px solid {p}}}"
    if theme.get("neumorph"):
        card_css += f".card{{box-shadow:12px 12px 24px #b9bfd6,-12px -12px 24px #ffffff}}"
    css = base_reset(theme) + card_css + f".brand{{color:{theme['text'] if theme.get('neumorph') or theme.get('accentBar') else theme['primary']};text-align:center;margin:0 0 6px;font-size:26px}}.sub{{text-align:center;color:{theme['mutedText']};margin:0 0 22px;font-size:14px}}" + shared_controls(theme)
    return f"<style>{css}</style><main class='wrap'><div class='card'><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


def layout_split(theme: dict, title: str, sub: str, body: str) -> str:
    css = base_reset(theme) + compact(f"""
    body{{padding:0;align-items:stretch}}
    .wrap{{width:min(92vw,380px);border-radius:{theme['radius']};overflow:hidden;box-shadow:{theme['shadow']};margin:18px}}
    .band{{background:{theme['band']};color:#fff;padding:34px 26px 44px;text-align:center}}
    .band .brand{{margin:0 0 6px;font-size:26px}}.band .sub{{margin:0;opacity:.92;font-size:14px}}
    .panel{{background:{theme['surface']};padding:24px 26px 30px;margin-top:-22px;border-radius:18px 18px 0 0}}
    """) + shared_controls(theme)
    return f"<style>{css}</style><main class='wrap'><div class='band'><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p></div><div class='panel'>{body}</div></main>"


def layout_terminal(theme: dict, title: str, sub: str, body: str) -> str:
    p = theme["primary"]
    css = base_reset(theme) + compact(f"""
    .scan{{position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,#00000000 0 2px,#00000030 3px 4px)}}
    .wrap{{width:min(92vw,380px)}}
    .card{{background:{theme['surface']};padding:26px 24px;border-radius:{theme['radius']};box-shadow:{theme['shadow']};border:1px solid {p}66}}
    .titlebar{{color:{theme['mutedText']};font-size:12px;margin:0 0 14px;border-bottom:1px dashed {theme['secondary']};padding-bottom:8px}}
    .brand{{color:{p};text-align:left;margin:0 0 4px;font-size:22px;text-shadow:0 0 12px {p}55}}
    .brand::before{{content:'> '}}
    .sub{{text-align:left;color:{theme['mutedText']};margin:0 0 20px;font-size:13px}}
    """) + shared_controls(theme, f"input.field,.field{{background:{theme['surface']};color:{p};border:1px solid {theme['secondary']}}}")
    return f"<div class='scan'></div><style>{css}</style><main class='wrap'><div class='card'><p class='titlebar'>guest@hotspot:~$ connect</p><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


def layout_corporate(theme: dict, title: str, sub: str, body: str) -> str:
    css = base_reset(theme) + compact(f"""
    .wrap{{width:min(92vw,380px);border-radius:{theme['radius']};overflow:hidden;box-shadow:{theme['shadow']};background:{theme['surface']}}}
    .header{{background:{theme['header']};color:#fff;padding:20px 24px;display:flex;align-items:center;gap:12px}}
    .logo{{width:34px;height:34px;border-radius:8px;background:{theme['primary']};flex:none}}
    .header .org{{font-size:16px;font-weight:700}}
    .content{{padding:26px 24px 28px}}
    .brand{{display:none}}
    .sub{{color:{theme['mutedText']};margin:0 0 20px;font-size:14px}}
    """) + shared_controls(theme)
    return f"<style>{css}</style><main class='wrap'><div class='header'><div class='logo'></div><span class='org'>{title}</span></div><div class='content'><p class='sub'>{sub}</p>{body}</div></main>"


def layout_glow(theme: dict, title: str, sub: str, body: str) -> str:
    c1, c2, c3, c4 = theme["glowColors"]
    css = base_reset(theme) + compact(f"""
    .wrap{{width:min(92vw,380px)}}
    .glow{{padding:3px;border-radius:calc({theme['radius']} + 3px);background:conic-gradient(from 90deg,{c1},{c2},{c3},{c4})}}
    .card{{background:{theme['surface']};padding:30px 26px;border-radius:{theme['radius']};box-shadow:{theme['shadow']}}}
    .brand{{color:{theme['text']};text-align:center;margin:0 0 6px;font-size:24px;text-transform:uppercase;letter-spacing:2px}}
    .sub{{text-align:center;color:{theme['mutedText']};margin:0 0 22px;font-size:13px;text-transform:uppercase;letter-spacing:1px}}
    """) + shared_controls(theme, f".btn{{text-transform:uppercase;letter-spacing:1px}}")
    return f"<style>{css}</style><main class='wrap'><div class='glow'><div class='card'><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></div></main>"


def layout_glass(theme: dict, title: str, sub: str, body: str) -> str:
    # No card box and no icon badge here on purpose (design decision, not a
    # compatibility workaround — see layout_card()/layout_dark() for the
    # backdrop-filter history this theme used to carry). Content sits directly
    # on the ambient background; `.card` is kept only as a plain spacing
    # wrapper (padding, no visual box) so the internal layout doesn't need
    # reworking if a card look comes back later.
    css = base_reset(theme) + compact(f"""
    body::before{{content:'';position:fixed;width:210px;height:210px;border-radius:50%;top:7%;right:-70px;background:#ffffff16;box-shadow:inset 0 0 45px #ffffff18}}
    .wrap{{width:min(90vw,370px)}}
    .card{{padding:38px 28px 30px}}
    .brand{{color:{theme['text']};text-align:center;margin:0 0 7px;font-size:28px;letter-spacing:-.5px}}
    .sub{{text-align:center;color:{theme['mutedText']};margin:0 0 25px;font-size:14px}}
    """) + shared_controls(theme, compact(f"""
    .field{{background:#07132266;border:1px solid #ffffff3d;border-radius:14px;padding:15px;color:{theme['text']};outline:none}}
    .field:focus{{border-color:{theme['primary']};box-shadow:0 0 0 3px #67e8f921}}
    .field::placeholder{{color:#b9c7dd}}
    .btn{{border-radius:14px;padding:15px;box-shadow:0 12px 28px #67e8f92e}}
    """))
    return f"<style>{css}</style><main class='wrap'><div class='card'><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


def layout_classic(theme: dict, title: str, sub: str, body: str) -> str:
    css = base_reset(theme) + compact(f"""
    body::before{{content:'';position:fixed;inset:12px;border:1px solid #744a2433;pointer-events:none}}
    .wrap{{width:min(89vw,365px)}}
    .card{{padding:42px 30px 32px}}
    .ornament{{display:flex;align-items:center;gap:10px;margin:0 auto 25px;color:{theme['primary']}}}
    .ornament::before,.ornament::after{{content:'';height:1px;flex:1;background:{theme['secondary']}}}
    .diamond{{width:10px;height:10px;background:{theme['primary']};transform:rotate(45deg)}}
    .brand{{color:{theme['text']};text-align:center;margin:0 0 8px;font-size:30px;font-weight:600}}
    .sub{{text-align:center;color:{theme['mutedText']};margin:0 0 25px;font-size:14px;font-style:italic}}
    """) + shared_controls(theme, compact(f"""
    .field{{border-radius:0;background:#fffdf7;border:1px solid {theme['secondary']};padding:14px}}
    .field:focus{{outline:1px solid {theme['primary']};outline-offset:2px}}
    .btn{{border-radius:0;padding:14px;text-transform:uppercase;letter-spacing:2px;font-size:13px}}
    .error{{font-family:Arial,sans-serif}}
    """))
    return f"<style>{css}</style><main class='wrap'><div class='card'><div class='ornament'><i class='diamond'></i></div><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


def layout_cyberpunk(theme: dict, title: str, sub: str, body: str) -> str:
    css = base_reset(theme) + compact(f"""
    body{{background-size:32px 32px,32px 32px,auto,auto}}
    .wrap{{width:min(90vw,375px)}}
    .card{{padding:39px 25px 29px}}
    .signal{{display:flex;gap:5px;margin-bottom:25px}}
    .signal i{{display:block;height:5px;background:{theme['primary']}}}.signal i:nth-child(1){{width:48px}}.signal i:nth-child(2){{width:14px;background:{theme['secondary']}}}.signal i:nth-child(3){{width:7px}}
    .brand{{color:{theme['text']};text-align:left;margin:0 0 7px;font-size:27px;text-transform:uppercase;letter-spacing:1px;text-shadow:3px 0 0 #ff2bd66b,-2px 0 0 #20f6ff55}}
    .sub{{text-align:left;color:{theme['mutedText']};margin:0 0 24px;font-size:12px;text-transform:uppercase;letter-spacing:.8px}}
    """) + shared_controls(theme, compact(f"""
    .field{{background:#02050a;border:1px solid {theme['primary']}80;border-left:4px solid {theme['secondary']};border-radius:0;color:{theme['text']};padding:15px 13px;outline:none}}
    .field:focus{{border-color:{theme['primary']};box-shadow:0 0 15px #20f6ff33}}
    .field::placeholder{{color:#6d8390}}
    .btn{{border-radius:0;text-transform:uppercase;letter-spacing:2px;clip-path:polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,12px 100%,0 calc(100% - 12px));box-shadow:inset -5px -5px 0 #0bb7c3}}
    """))
    return f"<style>{css}</style><main class='wrap'><div class='card'><div class='signal'><i></i><i></i><i></i></div><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


def layout_dark(theme: dict, title: str, sub: str, body: str) -> str:
    css = base_reset(theme) + compact(f"""
    .wrap{{width:min(90vw,370px)}}
    .card{{padding:36px 28px 30px}}
    .brand{{color:{theme['text']};text-align:left;margin:0 0 7px;font-size:27px;letter-spacing:-.5px}}
    .sub{{text-align:left;color:{theme['mutedText']};margin:0 0 25px;font-size:14px}}
    """) + shared_controls(theme, compact(f"""
    .field{{background:#0c0f15;border:1px solid {theme['secondary']};border-radius:12px;color:{theme['text']};padding:15px;outline:none}}
    .field:focus{{border-color:{theme['primary']};box-shadow:0 0 0 3px #7c5cff1f}}
    .field::placeholder{{color:#6f7789}}
    .btn{{border-radius:12px;padding:15px}}
    """))
    return f"<style>{css}</style><main class='wrap'><div class='card'><h2 class='brand'>{title}</h2><p class='sub'>{sub}</p>{body}</div></main>"


LAYOUTS = {
    "card": layout_card, "split": layout_split, "terminal": layout_terminal,
    "corporate": layout_corporate, "glow": layout_glow,
    "glass": layout_glass, "classic": layout_classic,
    "cyberpunk": layout_cyberpunk, "dark": layout_dark,
}


# ------------------------------------------------------------ ruijie pages --
#
# Ruijie Cloud portals aren't $(variable)-templated router HTML like the
# Mikrotik/`themes/` files above -- they're a single-page app (index.html +
# loadConfig.json, zipped together with a bg.jpg by the app at apply-time)
# that calls Ruijie's own /api/auth/general endpoint. So instead of reusing
# `pages()`/LAYOUTS, each theme gets its own `ruijie_layout_*` that renders
# the same voucher/account/packages markup and JS inside a differently
# shaped, differently typeset card -- matching the personality its Mikrotik
# counterpart has, without pretending the two are the same HTML skeleton.
#
# `{{PACKAGES_SECTION}}` is left in the generated index.html for the app to
# substitute at apply-time with the merchant's actual package/price list (or
# blank it out if there are none) -- see buildVoucherMakerPortalBundle in
# voucher_maker's portal_bundle_builder.dart.

RUIJIE_PACKAGES_TOKEN = "{{PACKAGES_SECTION}}"

# "pass" (Ruijie's one-click / no-credential auth type) is intentionally
# excluded from login_options: with oneclick_validity/oneclick_times left at
# "0" (Ruijie's "no limit" default), including it would show a "Free Pass"
# tab that grants unlimited free Wi-Fi with a single tap, bypassing vouchers
# and accounts entirely -- not appropriate for a voucher-selling portal.
RUIJIE_LOAD_CONFIG = """loadConfig({
  "post_url":"https://www.ruijienetworks.com",
  "oneclick":{"oneclick_validity":"0","oneclick_qos":{"up_rate":"0","down_rate":"0"},"oneclick_times":"0"},
  "custom_html":{"login_options":["voucher","fixaccount"],"lang":["en_US"]}
});"""

RUIJIE_LOGIN_JS = compact("""
var currentAuth='voucher';
function sessionId(){try{return new URL(window.top.location.href).searchParams.get('sessionId')}catch(e){return new URL(location.href).searchParams.get('sessionId')}}
function chooseAuth(type){currentAuth=type;document.querySelectorAll('.field').forEach(function(e){e.classList.remove('active')});document.querySelectorAll('.tabs button').forEach(function(e){e.classList.toggle('active',e.dataset.auth===type)});var field=document.getElementById(type+'-field');if(field)field.classList.add('active')}
function selectVoucher(){chooseAuth('voucher');document.getElementById('voucher').focus()}
function loadConfig(data){var allowed=['voucher','fixaccount'];var options=((data.custom_html&&data.custom_html.login_options)||['voucher']).filter(function(value){return allowed.indexOf(value)>=0});if(!options.length)options=['voucher'];var labels={voucher:'Voucher',fixaccount:'Account'};var map={voucher:'voucher',fixaccount:'account'};var tabs=document.getElementById('tabs');tabs.innerHTML='';options.forEach(function(value){var auth=map[value]||value;var b=document.createElement('button');b.type='button';b.dataset.auth=auth;b.textContent=labels[value]||value;b.onclick=function(){chooseAuth(auth)};tabs.appendChild(b)});var preferred=options.indexOf('voucher')>=0?'voucher':(map[options[0]]||options[0]);chooseAuth(preferred)}
async function login(){var message=document.getElementById('message');message.textContent='';var payload={lang:'en_US',authType:currentAuth,sessionId:sessionId()};if(currentAuth==='voucher'){payload.account=document.getElementById('voucher').value.trim();if(!payload.account){message.textContent='Please enter voucher code';return}}else if(currentAuth==='account'){payload.authType='fixaccount';payload.account=document.getElementById('account').value.trim();payload.password=document.getElementById('password').value;if(!payload.account||!payload.password){message.textContent='Please enter username and password';return}}else{message.textContent='Please choose Voucher or Account login';return}var button=document.getElementById('login');button.disabled=true;button.textContent='Connecting...';try{var response=await fetch('/api/auth/general',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});var result=await response.json();if(result.success&&result.result&&result.result.logonUrl){location.href=result.result.logonUrl}else{message.textContent=result.message||'Login failed'}}catch(e){message.textContent='Unable to connect'}finally{button.disabled=false;button.textContent='Connect to Internet'}}
document.getElementById('login').addEventListener('click',login);
""")


def ruijie_common_css(theme: dict) -> str:
    p, pt, sec, surf, txt, muted = (
        theme["primary"], theme["primaryText"], theme["secondary"],
        theme["surface"], theme["text"], theme["mutedText"],
    )
    return compact(f"""
    *{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;font-family:{theme['font']};color:{txt}}}
    body{{min-height:100vh;background:url('./bg.jpg') center/cover fixed no-repeat;display:flex;justify-content:center;padding:28px 18px}}
    body:before{{content:"";position:fixed;inset:0;background:rgba(0,0,0,.38);z-index:-1}}
    main{{width:min(100%,430px);align-self:center;position:relative}}
    .brand{{margin-bottom:22px}}
    .tabs{{display:flex;gap:7px;padding:5px;background:#0003;border-radius:10px;margin-bottom:18px}}
    .tabs button{{flex:1;border:0;background:transparent;color:{muted};padding:11px 6px;border-radius:8px;font-weight:700;font-family:inherit;cursor:pointer}}
    .tabs button.active{{background:{p};color:{pt}}}
    .field{{display:none}}.field.active{{display:block}}
    .field label{{display:block;font-size:13px;color:{muted};margin:0 0 7px}}
    .field input{{width:100%;height:50px;border:1px solid {sec};border-radius:10px;background:#0003;color:{txt};padding:0 14px;font-size:16px;outline:none;font-family:inherit}}
    .field input:focus{{border-color:{p}}}
    #message{{min-height:24px;padding-top:7px;color:#ff8a80;font-size:12px;text-align:center}}
    #login{{width:100%;height:50px;border:0;border-radius:10px;background:{p};color:{pt};font-size:16px;font-weight:800;font-family:inherit;cursor:pointer}}
    .packages{{margin-top:24px}}.packages h2{{text-align:center;font-size:13px;letter-spacing:.6px;color:{muted};margin:0 0 11px}}
    .grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}}
    .package{{min-height:66px;border:1px solid {sec};border-radius:10px;background:#0003;color:{txt};padding:10px}}
    .package strong,.package span{{display:block;overflow-wrap:anywhere}}.package strong{{font-size:14px}}
    .package span{{margin-top:5px;color:{p};font-size:13px;font-weight:800}}
    @media(max-height:640px){{main{{align-self:flex-start}}.brand{{margin-bottom:15px}}.packages{{margin-top:17px}}}}
    """)


def ruijie_layout_glass(theme: dict) -> tuple[str, str]:
    # No card box here, same call as Mikrotik's layout_glass(): the whole
    # point of a Ruijie portal is the merchant's own background photo, so a
    # filled/blurred panel that hides it defeats the feature. Content sits
    # directly on the ambient background; only a soft corner glow remains.
    css = compact(f"""
    main{{padding:32px 24px 26px}}
    main::before{{content:'';position:absolute;width:190px;height:190px;border-radius:50%;top:-70px;right:-70px;background:#ffffff14;pointer-events:none}}
    .brand{{text-align:center;position:relative}}
    .logo{{font-size:40px;font-weight:800;color:{theme['primary']}}}
    .brand h1{{font-size:25px;margin:7px 0 4px;letter-spacing:-.5px}}
    .brand p{{margin:0;color:{theme['mutedText']};font-size:13px}}
    """)
    brand = (
        "<header class='brand'><div class='logo'>R</div>"
        "<h1>{{SHOP_NAME}}</h1><p>Connect with your voucher or account</p></header>"
    )
    return css, brand


def ruijie_layout_classic(theme: dict) -> tuple[str, str]:
    # No filled card -- see ruijie_layout_glass(). The thin inset rule is a
    # frame, not a panel: it has no background of its own, so it doesn't
    # hide the photo behind it.
    css = compact(f"""
    main{{padding:36px 26px 28px}}
    main::before{{content:'';position:absolute;inset:10px;border:1px solid {theme['primary']}26;pointer-events:none}}
    .brand{{text-align:center;position:relative}}
    .ornament{{display:flex;align-items:center;gap:9px;margin:0 auto 14px;color:{theme['primary']};width:80%}}
    .ornament::before,.ornament::after{{content:'';height:1px;flex:1;background:{theme['secondary']}}}
    .diamond{{width:8px;height:8px;background:{theme['primary']};transform:rotate(45deg);flex:none;display:inline-block}}
    .brand h1{{font-size:26px;margin:0 0 5px;font-weight:600}}
    .brand p{{margin:0;color:{theme['mutedText']};font-size:13px;font-style:italic}}
    .field input{{border-radius:0;background:#fffdf7}}
    .field input:focus{{outline:1px solid {theme['primary']};outline-offset:2px}}
    #login{{border-radius:0;text-transform:uppercase;letter-spacing:2px;font-size:13px}}
    .tabs,.tabs button{{border-radius:0}}
    """)
    brand = (
        "<header class='brand'><div class='ornament'><i class='diamond'></i></div>"
        "<h1>{{SHOP_NAME}}</h1><p>Connect with your voucher or account</p></header>"
    )
    return css, brand


def ruijie_layout_cyberpunk(theme: dict) -> tuple[str, str]:
    # No filled card -- see ruijie_layout_glass(). The neon outline is a
    # bare 1px border (no fill), so the background photo still reads through.
    css = compact(f"""
    body::after{{content:'';position:fixed;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,#00000000 0 2px,#00000024 3px 4px)}}
    main{{border:1px solid {theme['primary']}66;padding:30px 24px 26px}}
    .brand{{text-align:left}}
    .signal{{display:flex;gap:5px;margin-bottom:16px}}
    .signal i{{display:block;height:5px;background:{theme['primary']}}}
    .signal i:nth-child(1){{width:44px}}.signal i:nth-child(2){{width:13px;background:{theme['secondary']}}}.signal i:nth-child(3){{width:7px}}
    .brand h1{{font-size:24px;margin:0 0 6px;text-transform:uppercase;letter-spacing:1px;text-shadow:3px 0 0 {theme['secondary']}6b,-2px 0 0 {theme['primary']}55}}
    .brand p{{margin:0;color:{theme['mutedText']};font-size:12px;text-transform:uppercase;letter-spacing:.8px}}
    .field input{{border-radius:0;border-left:4px solid {theme['secondary']};background:#02050a}}
    #login{{border-radius:0;text-transform:uppercase;letter-spacing:2px;clip-path:polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,10px 100%,0 calc(100% - 10px))}}
    .tabs button{{text-transform:uppercase;font-size:12px}}
    """)
    brand = (
        "<header class='brand'><div class='signal'><i></i><i></i><i></i></div>"
        "<h1>{{SHOP_NAME}}</h1><p>Connect with your voucher or account</p></header>"
    )
    return css, brand


def ruijie_layout_dark(theme: dict) -> tuple[str, str]:
    # No filled card -- see ruijie_layout_glass().
    css = compact(f"""
    main{{padding:30px 24px 26px}}
    .brand{{text-align:left}}
    .logo{{font-size:34px;font-weight:800;color:{theme['primary']};margin-bottom:6px}}
    .brand h1{{font-size:24px;margin:0 0 5px;letter-spacing:-.5px}}
    .brand p{{margin:0;color:{theme['mutedText']};font-size:13px}}
    .field input{{background:#0c0f15}}
    """)
    brand = (
        "<header class='brand'><div class='logo'>R</div>"
        "<h1>{{SHOP_NAME}}</h1><p>Connect with your voucher or account</p></header>"
    )
    return css, brand


# New themes don't need a bespoke Ruijie skin right away -- add one to this
# map when you want the Ruijie portal to look different from `dark`, which
# is the fallback for any `layout` not listed here.
RUIJIE_LAYOUTS = {
    "glass": ruijie_layout_glass,
    "classic": ruijie_layout_classic,
    "cyberpunk": ruijie_layout_cyberpunk,
    "dark": ruijie_layout_dark,
}


def ruijie_index_html(theme: dict) -> str:
    render = RUIJIE_LAYOUTS.get(theme["layout"], ruijie_layout_dark)
    css, brand_html = render(theme)
    css = ruijie_common_css(theme) + css
    body = compact(f"""
    <main>
      {brand_html}
      <nav class="tabs" id="tabs"></nav>
      <section class="field" id="voucher-field">
        <label>Voucher Code</label>
        <input id="voucher" autocomplete="one-time-code" placeholder="Enter voucher code">
      </section>
      <section class="field" id="account-field">
        <label>Username</label>
        <input id="account" autocomplete="username" placeholder="Enter username">
        <label style="margin-top:10px">Password</label>
        <input id="password" type="password" autocomplete="current-password" placeholder="Enter password">
      </section>
      <div id="message"></div>
      <button id="login" type="button">Connect to Internet</button>
      {RUIJIE_PACKAGES_TOKEN}
    </main>
    """)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1'>"
        "<meta http-equiv='Cache-Control' content='no-cache'><title>{{SHOP_NAME}}</title>"
        f"<style>{css}</style></head><body>{body}"
        f"<script>{RUIJIE_LOGIN_JS}</script>"
        "<script src='./loadConfig.json'></script></body></html>"
    )


def page(theme: dict, title: str, sub: str, body: str, page_title: str, extra_head: str = "") -> str:
    render = LAYOUTS[theme["layout"]]
    content = render(theme, title, sub, body)
    return f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{page_title}</title>{extra_head}</head><body>{content}</body></html>"


def pages(theme: dict) -> dict[str, str]:
    login_body = (
        "<form action='$(link-login-only)' method='post' onsubmit='return mwLogin(this)'>"
        "<input type='hidden' name='dst' value='$(link-status)'>"
        "<input class='field' name='username' value='$(username)' placeholder='Access Code' required>"
        "<input type='hidden' name='password' value=''>"
        "<button class='btn' type='submit'>Connect</button></form>"
        "<p class='error'>$(error)</p>"
    )
    alogin_body = "<div class='ok'>&#10003;</div><a class='btn' href='$(link-status)'>Continue</a>"
    redirect_body = "<a class='btn' href='$(link-login-only)'>Open Login</a>"
    status_body = (
        "<section class='rows'>"
        "<div class='row'><span>Plan Name</span><strong>$(profile)</strong></div>"
        "<div class='row'><span>Code</span><strong>$(username)</strong></div>"
        "</section>"
        "<form action='$(link-logout)' method='post'><button class='btn' type='submit'>Disconnect</button></form>"
    )
    login = page(theme, "{{SHOP_NAME}}", "Enter your access code", login_body, "{{SHOP_NAME}}",
                 f"<script>{MW_LOGIN_JS}</script>")
    alogin = page(theme, "Connected", "You are online now", alogin_body, "{{SHOP_NAME}} Connected",
                  "<script>window.onload=function(){setTimeout(function(){window.location='$(link-status)';},800);};</script>")
    redirect = page(theme, "{{SHOP_NAME}}", "Opening login page...", redirect_body, "{{SHOP_NAME}}")
    status = page(theme, "Connected", "", status_body, "{{SHOP_NAME}} Connected",
                  "<meta http-equiv='refresh' content='10'>")
    return {"login.html": login, "alogin.html": alogin, "redirect.html": redirect, "status.html": status}


# ----------------------------------------------------------------- build --

def clear_theme_version(theme_id: str, version: str) -> None:
    """Wipe only this one theme+version folder before regenerating it.

    Deliberately does NOT touch any other version folder, or any theme id
    no longer listed in THEMES. Apps in the field cache a manifest and may
    still be pointing at an older version's files (e.g. themes/glass/1.0.0/
    login.html) — deleting that out from under them would break their
    already-applied portal page. To publish a revised design, bump the
    theme's `version` in THEMES so it gets a fresh folder; don't rely on
    this function to clean up old ones.
    """
    directory = ROOT / "themes" / theme_id / version
    if not directory.exists():
        return
    for f in sorted(directory.rglob("*"), reverse=True):
        if f.is_file():
            f.unlink()
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir():
            d.rmdir()


def clear_ruijie_version(theme_id: str, version: str) -> None:
    """Same one-version-only wipe as clear_theme_version(), for ruijie/."""
    directory = ROOT / "ruijie" / theme_id / version
    if not directory.exists():
        return
    for f in sorted(directory.rglob("*"), reverse=True):
        if f.is_file():
            f.unlink()
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir():
            d.rmdir()


def main() -> None:
    manifest_path = ROOT / "manifest.json"
    backgrounds = []
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if isinstance(existing_manifest.get("backgrounds"), list):
            backgrounds = existing_manifest["backgrounds"]
    manifest = {"schemaVersion": 1, "backgrounds": backgrounds, "themes": []}
    for theme in THEMES:
        relative = Path("themes") / theme["id"] / theme["version"]
        directory = ROOT / relative
        clear_theme_version(theme["id"], theme["version"])
        directory.mkdir(parents=True, exist_ok=True)
        for name, source in pages(theme).items():
            (directory / name).write_text(source, encoding="utf-8")
        colors = {key: theme[key] for key in
                  ("background", "surface", "text", "mutedText", "primary", "primaryText", "secondary", "radius", "shadow")}
        entry = {
            "id": theme["id"], "name": theme["name"], "description": theme["description"],
            "version": theme["version"], "enabled": True,
            "preview": f"{(relative / 'preview.png').as_posix()}?render=actual",
            "previewOverlay": f"{(relative / 'preview-overlay.png').as_posix()}?render=actual",
            "colors": colors,
            "files": {key: (relative / f"{key}.html").as_posix() for key in ("login", "alogin", "redirect", "status")},
        }

        # Ruijie side: same theme, same versioning discipline (new folder per
        # version, old ones never touched -- see clear_ruijie_version()), but
        # a completely different file shape (see the "ruijie pages" section
        # above for why).
        ruijie_relative = Path("ruijie") / theme["id"] / theme["version"]
        ruijie_directory = ROOT / ruijie_relative
        clear_ruijie_version(theme["id"], theme["version"])
        ruijie_directory.mkdir(parents=True, exist_ok=True)
        (ruijie_directory / "index.html").write_text(ruijie_index_html(theme), encoding="utf-8")
        (ruijie_directory / "loadConfig.json").write_text(RUIJIE_LOAD_CONFIG, encoding="utf-8")
        entry["ruijieFiles"] = {
            "index": (ruijie_relative / "index.html").as_posix(),
            "loadConfig": (ruijie_relative / "loadConfig.json").as_posix(),
        }

        manifest["themes"].append(entry)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "render_previews.py")],
        check=True,
    )


if __name__ == "__main__":
    main()
