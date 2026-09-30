"""Write gallery.html next to previews/. Usage: python gallery.py <batch_dir> [outfit ...]
Card ids are the variant file stems, e.g. Felt_Sport__autumn."""
import html, json, sys
from pathlib import Path

VARIANTS = ["autumn", "winter", "pastel", "plaid", "floral"]
OUTFITS = ["General_1", "LaceDress", "Sport", "NightOuting"]

PAGE = """<!doctype html><meta charset=utf-8><title>Felt outfit variants</title>
<style>
body{font:14px system-ui;background:#16181d;color:#e6e6e6;margin:0;padding:16px}
h2{margin:24px 0 8px;border-bottom:1px solid #444}
.row{display:flex;flex-wrap:wrap;gap:12px}
.card{width:230px;background:#20232b;border:2px solid #333;border-radius:6px;padding:6px}
.card img{width:100%;display:block;background:#eee}
.card.keep{border-color:#3fb950}.card.reject{border-color:#f85149;opacity:.55}
.id{font-size:12px;word-break:break-all;margin:4px 0}
button{cursor:pointer;border:0;border-radius:4px;padding:5px 12px;margin-right:4px;background:#333;color:#eee}
button.on-k{background:#3fb950;color:#000}button.on-r{background:#f85149;color:#000}
#bar{position:sticky;top:0;background:#16181d;padding:8px 0;z-index:2}
</style>
<div id=bar><button onclick=copy()>Copy decisions</button> <span id=n></span></div>
%s
<script>
let d={};try{d=JSON.parse(localStorage.getItem('felt-b1')||'{}')}catch(e){}
function set(id,v){d[id]=d[id]===v?null:v;try{localStorage.setItem('felt-b1',JSON.stringify(d))}catch(e){}paint()}
function paint(){let k=0,r=0;document.querySelectorAll('.card[data-id]').forEach(c=>{const v=d[c.dataset.id];
c.classList.toggle('keep',v=='keep');c.classList.toggle('reject',v=='reject');
c.querySelector('.k').classList.toggle('on-k',v=='keep');c.querySelector('.r').classList.toggle('on-r',v=='reject');
k+=v=='keep';r+=v=='reject'});document.getElementById('n').textContent=k+' keep, '+r+' reject'}
function copy(){const o={keep:[],reject:[]};for(const[i,v]of Object.entries(d))if(v)o[v].push(i);
const t=JSON.stringify(o);(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).catch(()=>prompt('Copy:',t))}
paint()
</script>"""


def card(vid, label, decide=True):
    btn = (f'<button class=k onclick="set(\'{vid}\',\'keep\')">Keep</button>'
           f'<button class=r onclick="set(\'{vid}\',\'reject\')">Reject</button>') if decide else ""
    return (f'<div class=card {"data-id=" + vid if decide else ""}><img loading=lazy src="previews/{vid}.png">'
            f'<div class=id>{html.escape(label)}</div>{btn}</div>')


if __name__ == "__main__":
    b = Path(sys.argv[1])
    secs = []
    for o in sys.argv[2:] or OUTFITS:
        cards = [card(f"Felt_{o}", f"{o} (original)", False)]
        cards += [card(f"Felt_{o}__{v}", f"Felt_{o}__{v}") for v in VARIANTS
                  if (b / "previews" / f"Felt_{o}__{v}.png").exists()]
        secs.append(f"<h2>{o}</h2><div class=row>{''.join(cards)}</div>")
    (b / "gallery.html").write_text(PAGE.replace("%s", "\n".join(secs)), encoding="utf8")
