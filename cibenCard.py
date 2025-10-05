# card_maker_pro_plus.py
from flask import Flask, request, render_template_string, send_file, Response
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import qrcode
import io, os, uuid, tempfile, time, base64

app = Flask(__name__)

# ====== Temp result dir ======
RESULT_DIR = os.path.join(tempfile.gettempdir(), "card_maker_results")
os.makedirs(RESULT_DIR, exist_ok=True)


def cleanup_old(max_age_hours=12):
    cutoff = time.time() - max_age_hours * 3600
    for name in os.listdir(RESULT_DIR):
        path = os.path.join(RESULT_DIR, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.remove(path)
        except Exception:
            pass


def save_result(data: bytes, ext: str):
    cleanup_old()
    token = uuid.uuid4().hex
    path = os.path.join(RESULT_DIR, f"{token}.{ext}")
    with open(path, "wb") as f:
        f.write(data)
    return f"/result/{token}.{ext}"


@app.route("/result/<fname>")
def serve_result(fname):
    path = os.path.join(RESULT_DIR, fname)
    if os.path.exists(path):
        mime = "image/png" if fname.lower().endswith(".png") else "application/pdf"
        return send_file(path, mimetype=mime, as_attachment=False, download_name=fname)
    return "Not Found", 404


# ====== Theme & Palette ======
THEMES = {
    # existing
    "pro-clean":   {"title": "Pro Clean", "bg": (255, 255, 255), "fg": (28, 28, 32), "sub": (110, 116, 125), "panel": (255, 255, 255)},
    "pro-modern":  {"title": "Pro Modern", "bg": (244, 247, 252), "fg": (21, 24, 31), "sub": (105, 113, 123), "panel": (255, 255, 255)},
    "pro-dark":    {"title": "Pro Dark", "bg": (18, 18, 22), "fg": (235, 238, 243), "sub": (160, 170, 182), "panel": (26, 27, 33)},
    "pro-glass":   {"title": "Glass Subtle", "bg": (15, 19, 23), "fg": (232, 238, 242), "sub": (180, 195, 205), "panel": "glass"},
    "pro-gradient": {"title": "Soft Gradient", "bg": "gradient", "fg": (255, 255, 255), "sub": (235, 235, 235), "panel": "glass"},
    "pro-kraft":   {"title": "Kraft Warm", "bg": (234, 219, 198), "fg": (48, 38, 30), "sub": (95, 78, 60), "panel": (236, 224, 206)},
    "pro-mono":    {"title": "Monochrome", "bg": (250, 250, 250), "fg": (20, 20, 20), "sub": (90, 90, 90), "panel": (255, 255, 255)},
    "pro-stripe":  {"title": "Tech Stripe", "bg": "stripe", "fg": (24, 28, 36), "sub": (98, 108, 124), "panel": (255, 255, 255)},
    # NEW premium themes
    "pro-aurora":  {"title": "Aurora Glow", "bg": "aurora", "fg": (240, 244, 255), "sub": (210, 220, 240), "panel": "glass"},
    "pro-carbon":  {"title": "Carbon Fiber", "bg": "carbon", "fg": (234, 237, 243), "sub": (160, 170, 182), "panel": (18, 19, 23)},
    "pro-lines":   {"title": "Geo Lines", "bg": "lines", "fg": (24, 28, 36), "sub": (98, 108, 124), "panel": (255, 255, 255)},
    "pro-satin":   {"title": "Satin Sheen", "bg": "satin", "fg": (22, 24, 28), "sub": (80, 88, 98), "panel": (255, 255, 255)},
}

PALETTES = [
    {"name": "Indigo", "hex": "#4f46e5"},
    {"name": "Blue", "hex": "#3b82f6"},
    {"name": "Sky", "hex": "#0ea5e9"},
    {"name": "Teal", "hex": "#14b8a6"},
    {"name": "Emerald", "hex": "#10b981"},
    {"name": "Amber", "hex": "#f59e0b"},
    {"name": "Orange", "hex": "#f97316"},
    {"name": "Rose", "hex": "#f43f5e"},
    {"name": "Fuchsia", "hex": "#a21caf"},
    {"name": "Slate", "hex": "#334155"},
]

# ====== UI (Tailwind + Alpine; PREVIEW server-side via /api/preview) ======
HTML = r"""
<!doctype html>
<html lang="id" x-data="ui()" :class="dark ? 'dark' : ''">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <title>Business Card Generator Ciben</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
  <meta name="theme-color" content="#ffffff">
  <style>
    html{-webkit-text-size-adjust:100%;}
    :root{
      --bg:#f5f6f7; --card:#fff; --border:#e7e7e7; --text:#111827; --dim:#6b7280; --ring:#6366f1;
    }
    .dark:root{
      --bg:#0b0e13; --card:#0f131a; --border:#1f2430; --text:#e5e7eb; --dim:#9aa1ad; --ring:#8b5cf6;
    }
    html,body{background:var(--bg);color:var(--text)}
    .wrap{max-width:1280px;margin-inline:auto}
    .appbar{position:sticky;top:0;z-index:40;background:color-mix(in oklab,var(--bg),transparent 6%);backdrop-filter:blur(10px);border-bottom:1px solid var(--border)}
    .brand{width:30px;height:30px;border-radius:8px;background:linear-gradient(135deg,#111827,#334155);color:#fff;display:grid;place-items:center;font-weight:700;letter-spacing:.5px}
    .dark .brand{background:linear-gradient(135deg,#e5e7eb,#9ca3af);color:#111827}
    .card{background:var(--card);border:1px solid var(--border);border-radius:14px}
    .label{font-size:13px;color:var(--dim);font-weight:600}
    .inpt{width:100%;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px;color:var(--text);outline:none;transition:border-color .15s, box-shadow .15s}
    .inpt:focus{border-color:var(--ring);box-shadow:0 0 0 4px color-mix(in oklab,var(--ring),transparent 78%)}
    .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 16px;border-radius:12px;font-weight:700;border:1px solid var(--border);background:linear-gradient(135deg,#111827,#334155);color:#fff;transition:transform .12s,box-shadow .15s,filter .15s}
    .btn:hover{transform:translateY(-1px);box-shadow:0 8px 18px rgba(0,0,0,.12);filter:saturate(1.05)}
    .btn-sec{background:transparent;color:var(--text)}
    .muted{font-size:12px;color:var(--dim)}
    .previewBox{border:1px dashed var(--border);border-radius:12px;overflow:hidden;background:var(--card);position:relative}
    .grid-cols-auto{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}
    .bottom-bar{position:sticky;bottom:0;left:0;right:0;z-index:50;background:var(--card);border-top:1px solid var(--border)}
    .badge{font-size:10px;padding:2px 6px;border:1px solid var(--border);border-radius:999px}
    .kbd{font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;padding:2px 6px;border-radius:6px;border:1px solid var(--border);font-size:12px}

    /* === Trakteer button === */
    .btn-trakteer{
      background: linear-gradient(135deg,#ef4444,#f97316);
      color:#fff;
      border-color: transparent;
      transition: transform .12s, box-shadow .15s, filter .15s;
    }
    .btn-trakteer:hover{
      transform: translateY(-1px);
      box-shadow: 0 8px 18px rgba(0,0,0,.18);
      filter: saturate(1.08);
    }

    /* === App Navigator styles (FAB fixed-size) === */
    .fab{
      --fab-size:52px;
      position: fixed; inset:auto 16px 20px auto;
      width:var(--fab-size); height:var(--fab-size);
      display:flex; align-items:center; justify-content:center; gap:6px;
      padding:0; border-radius:999px;
      background: linear-gradient(135deg,#111827,#334155);
      color:#fff; border:1px solid rgba(255,255,255,.08);
      box-shadow: 0 10px 24px rgba(0,0,0,.20);
      cursor: pointer; user-select:none; z-index:70;
      transition: transform .12s ease, box-shadow .15s ease, opacity .2s ease;
      font-size: 18px; line-height: 1;
    }
    .fab:hover{ transform: translateY(-2px); box-shadow: 0 14px 30px rgba(0,0,0,.24); }
    .fab .dot{ width:6px; height:6px; border-radius:999px; background:#22c55e; box-shadow:0 0 0 3px rgba(34,197,94,.18); position:absolute; right:8px; bottom:8px; }
    .dragging{ opacity:.85; cursor:grabbing; }

    .nav-overlay{
      position: fixed; inset:0; background: rgba(0,0,0,.4); backdrop-filter: blur(2px);
      z-index: 60; opacity:0; pointer-events:none; transition: opacity .18s ease;
    }
    .nav-overlay.show{ opacity:1; pointer-events:auto; }

    .drawer{
      position: fixed; top:0; bottom:0; width:min(360px, 90vw); z-index: 80;
      background: var(--card); border:1px solid var(--border); color: var(--text);
      box-shadow: 0 24px 60px rgba(0,0,0,.28);
      transform: translateX(-100%); transition: transform .22s cubic-bezier(.2,.7,.2,1);
    }
    .drawer.right{ right:0; left:auto; transform: translateX(100%); }
    .drawer.show.left, .drawer.show.right{ transform: translateX(0); }
    .drawer-header{ position: sticky; top:0; z-index:5; background: color-mix(in oklab, var(--card), transparent 4%); backdrop-filter: blur(6px) }
    .drawer .kbd{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size:12px; padding:2px 6px; border:1px solid var(--border); border-radius:6px }

    .dock{
      position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
      background: color-mix(in oklab, var(--card), transparent 4%);
      border: 1px solid var(--border); border-radius: 14px; padding: 8px;
      display: flex; gap: 6px; z-index: 65; backdrop-filter: blur(8px);
      box-shadow: 0 12px 30px rgba(0,0,0,.18);
    }
    .dock a{
      display:flex; align-items:center; gap:8px; padding:8px 10px; border-radius: 10px; border:1px solid transparent; color: var(--text);
    }
    .dock a:hover{ background: color-mix(in oklab, var(--card), transparent 8%); border-color: var(--border); transform: translateY(-1px); }
  </style>
</head>
<body x-init="init()">
  <header class="appbar">
    <div class="wrap px-5 py-3 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="brand">BC</div>
        <div>
          <div class="text-[13px]" style="color:var(--dim)">Toolkit</div>
          <div class="font-semibold leading-tight">Business Card Generator <span class="badge">by Cibens</span></div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button @click="toggle()" class="btn btn-sec px-3 py-2 text-sm" :aria-label="dark?'Switch to light':'Switch to dark'"><span x-show="!dark">🌙</span><span x-show="dark">☀️</span></button>
      </div>
    </div>
  </header>

  <main class="wrap px-5 py-6 grid xl:grid-cols-3 gap-6 pb-24">
    <!-- Left: Form -->
    <section class="xl:col-span-2 space-y-6">
      <div class="card p-5">
        <form id="cardForm" method="POST" enctype="multipart/form-data" @input="debouncedPreview" @change="debouncedPreview" @submit="beforeSubmit">
          <input type="hidden" name="action" value="generate">

          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <div class="label mb-1">Nama</div>
              <input class="inpt" name="name" placeholder="Nama Kamu" required>
            </div>
            <div>
              <div class="label mb-1">Jabatan</div>
              <input class="inpt" name="title" placeholder="Software Engineer">
            </div>
            <div>
              <div class="label mb-1">Perusahaan</div>
              <input class="inpt" name="company" placeholder="Nama Perusahaan">
            </div>
            <div>
              <div class="label mb-1">Website / Link (untuk QR)</div>
              <input class="inpt" name="url" placeholder="https://...">
              <div class="muted mt-1">QR akan muncul jika link diisi.</div>
            </div>
            <div>
              <div class="label mb-1">Email</div>
              <input class="inpt" name="email" placeholder="kamu@mail.com">
            </div>
            <div>
              <div class="label mb-1">Telepon</div>
              <input class="inpt" name="phone" placeholder="+62 ...">
            </div>
            <div class="md:col-span-2">
              <div class="label mb-1">Alamat (opsional)</div>
              <input class="inpt" name="address" placeholder="Jl. ...">
            </div>
            <div class="md:col-span-2">
              <div class="label mb-1">Logo (PNG/JPG, opsional)</div>
              <label class="inpt flex items-center justify-between gap-3 cursor-pointer" @dragover.prevent @drop.prevent="handleDrop($event)">
                <input id="logoInput" type="file" name="logo" accept="image/*" class="sr-only" @change="debouncedPreview">
                <span class="text-sm">Seret & lepas logo ke sini atau klik untuk memilih</span>
                <span class="badge">Opsional</span>
              </label>
              <template x-if="logoName"><div class="muted mt-1">Logo: <span x-text="logoName"></span></div></template>
            </div>
            <div>
              <div class="label mb-1">Ukuran</div>
              <div class="flex gap-2">
                <input class="inpt" name="size" value="1050x600" x-ref="sizeInput">
                <select class="inpt" @change="applyPreset($event)">
                  <option value="">Preset</option>
                  <option value="1050x600">US 3.5×2 in (300dpi)</option>
                  <option value="1004x614">EU 85×55 mm (300dpi)</option>
                  <option value="1260x756">US + bleed</option>
                </select>
              </div>
              <div class="muted mt-1">Gunakan format lebarxtinggi, contoh: 1050x600</div>
            </div>
            <div>
              <div class="label mb-1">DPI untuk PDF</div>
              <input class="inpt" name="dpi" value="300">
            </div>
          </div>

          <!-- Tema -->
          <div class="mt-6">
            <div class="label mb-2">Tema</div>
            <div class="grid grid-cols-auto gap-3">
              {% for key,desc in theme_previews.items() %}
              <label class="relative cursor-pointer group">
                <input class="sr-only" type="radio" name="theme" value="{{key}}" {% if loop.first %}checked{% endif %} @change="debouncedPreview">
                <div class="border border-[var(--border)] rounded-lg overflow-hidden hover:shadow transition group-hover:translate-y-[-1px]">
                  <img src="{{ desc['preview'] }}" class="w-full h-24 object-cover" alt="{{ key }}">
                  <div class="px-3 py-2 text-sm flex items-center justify-between">
                    <span>{{ desc['title'] }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded border border-[var(--border)]">Pilih</span>
                  </div>
                </div>
              </label>
              {% endfor %}
            </div>
          </div>

          <!-- Palette -->
          <div class="mt-6">
            <div class="label mb-2">Warna aksen / QR</div>
            <div class="flex flex-wrap gap-2">
              {% for p in palettes %}
              <label class="px-3 py-2 rounded-lg border flex items-center gap-2 hover:translate-y-[-1px] transition cursor-pointer">
                <input type="radio" class="sr-only" name="accent" value="{{p['hex']}}" {% if loop.index==2 %}checked{% endif %} @change="debouncedPreview">
                <span class="inline-block w-5 h-5 rounded-full" style="background: {{p['hex']}};"></span>
                <span class="text-sm">{{p['name']}}</span>
              </label>
              {% endfor %}
            </div>
          </div>

          <!-- Actions -->
          <div class="mt-5 hidden xl:flex gap-2">
            <button class="btn" title="Generate (Ctrl/Cmd+Enter)">Generate</button>
            <button type="reset" class="btn btn-sec" @click="resetPreview">Reset</button>
            <a href="https://teer.id/iben21" 
                target="_blank" 
                rel="noopener noreferrer"
                class="btn btn-trakteer flex items-center gap-2 px-4">
                ☕ <span>Support</span>
            </a>
          </div>

          <!-- Bottom bar (mobile/always visible actions) -->
          <div class="bottom-bar mt-5">
            <div class="wrap px-4 py-3 flex items-center justify-between gap-3">
              <div class="text-sm">
                <div class="font-semibold">Siap generate?</div>
                <div class="muted">Tekan <span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> untuk cepat.</div>
              </div>
              <div class="flex gap-2">
                <button type="reset" class="btn btn-sec px-3" @click="resetPreview">Reset</button>
                <button class="btn px-4">Generate</button>
              </div>
            </div>
          </div>
        </form>
      </div>

      {% if png_url or pdf_url %}
      <div class="card p-5">
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div class="font-semibold">Hasil kartu siap</div>
            <div class="muted">Klik untuk unduh, atau salin tautan.</div>
          </div>
        </div>
        <div class="mt-4 flex flex-wrap gap-2">
          {% if png_url %}<a class="btn" href="{{ png_url }}" download="business_card.png">⬇️ PNG</a><button class="btn btn-sec" x-data @click="navigator.clipboard.writeText('{{ png_url }}'); $dispatch('toast', 'Tautan PNG disalin')">🔗 Salin PNG</button>{% endif %}
          {% if pdf_url %}<a class="btn" href="{{ pdf_url }}" download="business_card.pdf">⬇️ PDF</a><button class="btn btn-sec" x-data @click="navigator.clipboard.writeText('{{ pdf_url }}'); $dispatch('toast', 'Tautan PDF disalin')">🔗 Salin PDF</button>{% endif %}
        </div>
      </div>
      {% endif %}
    </section>

    <!-- Right: Live Preview (Server-rendered) -->
    <aside class="space-y-4">
      <div class="card p-4">
        <div class="font-semibold mb-2">Preview Langsung</div>
        <div class="muted mb-3">Preview di-render server pakai engine yang sama dengan hasil akhir.</div>
        <div class="previewBox p-3" x-ref="previewWrap">
          <div x-show="loading" class="absolute inset-0 grid place-items-center"><div class="animate-pulse text-sm" style="color:var(--dim)">Merender preview…</div></div>
          <img x-ref="previewImg" src="" alt="preview" class="w-full h-auto block" style="min-height:140px;">
        </div>
        <div class="text-xs mt-2 muted">Jika preview tidak update, pastikan logo sudah dipilih (jika ingin dipakai) lalu ubah salah satu input kecil agar refresh.</div>
      </div>

      <div class="card p-4">
        <div class="font-semibold mb-1">Tips</div>
        <ul class="text-sm list-disc pl-5" style="color:var(--dim)">
          <li>Gunakan tema <b>Aurora Glow</b> untuk kesan futuristik premium.</li>
          <li>Pastikan kontras QR tinggi saat dipakai di bahan gelap.</li>
        </ul>
      </div>
    </aside>
  </main>

  <footer class="wrap px-5 py-8 muted">
    © 2025 andartelolat — MIT.
  </footer>

  <!-- Toasts -->
  <div x-data="{show:false, msg:''}" @toast.window="show=true; msg=$event.detail; setTimeout(()=>show=false,1800)" x-show="show" x-transition.opacity class="fixed bottom-24 right-6 bg-[var(--card)] border border-[var(--border)] rounded-xl px-4 py-2 shadow"> <span x-text="msg"></span> </div>

  <!-- === APP NAVIGATOR (Floating + Sidebar + Dock) === -->
  <div x-data="appNavigator()" x-init="init()">
    <!-- Floating Action Button: ikon-only, fixed-size -->
    <button
      class="fab select-none"
      :class="dragging ? 'dragging' : ''"
      @click="toggleDrawer()"
      @pointerdown="startDrag" @pointermove="onDrag" @pointerup="endDrag" @pointercancel="endDrag"
      :style="`left:${fabPos.x}px; top:${fabPos.y}px;`"
      title="Buka Navigator (Alt+K)"
      aria-label="Buka Navigator"
    >
      <span aria-hidden="true">📁</span>
      <span class="dot" aria-hidden="true"></span>
    </button>

    <!-- Compact Dock (opsional) -->
    <nav class="dock hidden md:flex" x-show="showDock" x-transition.opacity.duration.150ms>
      <template x-for="item in quickApps" :key="item.url">
        <a :href="item.url" target="_blank" rel="noopener noreferrer" :title="item.description">
          <span x-text="item.icon"></span>
          <span class="text-sm font-medium" x-text="item.name"></span>
        </a>
      </template>
      <button class="px-2 text-sm opacity-70 hover:opacity-100" @click="toggleDrawer()">Lainnya…</button>
    </nav>

    <!-- Overlay -->
    <div class="nav-overlay" :class="open ? 'show' : ''" @click="close()"></div>

    <!-- Drawer -->
    <aside class="drawer left" :class="`${open ? 'show' : ''} ${side}`" role="dialog" aria-modal="true" aria-label="Navigator">
      <header class="drawer-header px-4 py-3 border-b border-[var(--border)] flex items-center justify-between gap-3">
        <div class="flex items-center gap-2">
          <div class="brand w-8 h-8 rounded-lg grid place-items-center text-white" style="background:linear-gradient(135deg,#111827,#334155)">AP</div>
          <div>
            <div class="text-sm" style="color:var(--dim)">Launcher</div>
            <div class="font-semibold">App Navigator <span class="badge">Beta</span></div>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button class="text-sm px-2 py-1 border rounded-lg" @click="switchSide()" :title="side==='left' ? 'Pindah ke kanan' : 'Pindah ke kiri'">
            <span x-text="side==='left' ? '➡️ ke kanan' : '⬅️ ke kiri'"></span>
          </button>
          <button class="text-sm px-2 py-1 border rounded-lg" @click="close()" title="Tutup (Esc)">✖</button>
        </div>
      </header>

      <div class="p-4 flex items-center gap-2 border-b border-[var(--border)]">
        <div class="relative flex-1">
          <input type="search" x-model="q" @input="doFilter" placeholder="Cari aplikasi… (Alt+K)" class="inpt w-full pr-9" />
          <span class="absolute right-3 top-2.5 opacity-60">⌥K</span>
        </div>
        <label class="inline-flex items-center gap-2 text-sm px-3 py-2 border rounded-lg cursor-pointer">
          <input type="checkbox" class="sr-only" x-model="showIcons" @change="persist()">
          <span>Ikon</span>
          <span x-text="showIcons ? '🟢' : '⚪'"></span>
        </label>
      </div>

      <!-- Isi -->
      <div class="h-full overflow-y-auto p-3 pb-24">
        <!-- Pinned -->
        <section class="mb-4">
          <div class="flex items-center justify-between px-1 mb-2">
            <h3 class="text-sm font-semibold">Pinned</h3>
            <span class="text-xs" style="color:var(--dim)">sering dipakai</span>
          </div>
        <div class="grid grid-cols-1 gap-2">
          <template x-for="item in filteredPinned" :key="item.url">
            <a class="card p-3 hover:translate-y-[-1px] transition border hover:shadow" :href="item.url" target="_blank" rel="noopener noreferrer">
              <div class="flex items-center gap-3">
                <span x-show="showIcons" x-text="item.icon" class="text-xl"></span>
                <div class="min-w-0">
                  <div class="font-medium truncate" x-text="item.name"></div>
                  <div class="text-sm truncate" style="color:var(--dim)" x-text="item.description"></div>
                </div>
                <span class="ml-auto text-xs badge">Buka</span>
              </div>
            </a>
          </template>
        </div>
        </section>

        <!-- Groups -->
        <template x-for="group in groups" :key="group.name">
          <section class="mb-5">
            <div class="flex items-center justify-between px-1 mb-2">
              <h3 class="text-sm font-semibold" x-text="group.name"></h3>
              <button class="text-xs opacity-70 hover:opacity-100" @click="toggleGroup(group)">
                <span x-text="group.open ? 'Sembunyikan' : 'Tampilkan'"></span>
              </button>
            </div>
            <div class="grid grid-cols-1 gap-2" x-show="group.open" x-collapse>
              <template x-for="item in group.filtered" :key="item.url">
                <a class="card p-3 hover:translate-y-[-1px] transition border hover:shadow"
                   :href="item.url" target="_blank" rel="noopener noreferrer">
                  <div class="flex items-center gap-3">
                    <span x-show="showIcons" x-text="item.icon" class="text-xl"></span>
                    <div class="min-w-0">
                      <div class="font-medium truncate" x-text="item.name"></div>
                      <div class="text-sm truncate" style="color:var(--dim)" x-text="item.description"></div>
                    </div>
                    <span class="ml-auto text-xs badge" x-text="item.tag || 'App'"></span>
                  </div>
                </a>
              </template>
            </div>
          </section>
        </template>
      </div>

      <!-- Footer -->
      <footer class="drawer-header px-4 py-3 border-t border-[var(--border)] flex items-center justify-between text-sm">
        <div class="flex items-center gap-2">
          <span class="kbd">Alt</span>+<span class="kbd">K</span> buka •
          <span class="kbd">Esc</span> tutup •
          <span class="kbd">[</span>/<span class="kbd">]</span> posisi
        </div>
        <a href="https://trakteer.id/USERNAME/tip" target="_blank" rel="noopener" class="btn btn-trakteer px-3 py-1.5">☕ Dukung</a>
      </footer>
    </aside>
  </div>

  <script>
    function ui(){
      const debounce=(fn,ms=350)=>{let t;return(...a)=>{clearTimeout(t);t=setTimeout(()=>fn(...a),ms)}}
      return {
        dark:(() => { const s=localStorage.getItem('theme'); if(s==='dark') return true; if(s==='light') return false; return window.matchMedia('(prefers-color-scheme: dark)').matches; })(),
        loading:false,
        logoName:'',
        debouncedPreview:null,
        toggle(){
          this.dark=!this.dark;
          localStorage.setItem('theme', this.dark?'dark':'light');
          const m=document.querySelector('meta[name="theme-color"]');
          if(m) m.setAttribute('content', this.dark ? '#0b0e13' : '#ffffff');
        },
        init(){
          this.debouncedPreview = debounce(()=>this.updatePreview(), 250);
          setTimeout(()=>this.updatePreview(), 10);
          // hotkey submit
          window.addEventListener('keydown', (e)=>{
            if((e.ctrlKey||e.metaKey) && e.key==='Enter'){
              const form=document.getElementById('cardForm');
              if(form) form.requestSubmit();
            }
          })
        },
        resetPreview(){
          const form=document.getElementById('cardForm');
          form.reset();
          this.logoName='';
          this.updatePreview();
        },
        beforeSubmit(e){ /* keep defaults */ },
        applyPreset(e){
          const v=e.target.value; if(!v) return; this.$refs.sizeInput.value=v; this.updatePreview();
        },
        handleDrop(ev){
          const files=ev.dataTransfer.files; if(!files||!files.length) return;
          const input=document.getElementById('logoInput');
          input.files = files; this.logoName = files[0].name; this.updatePreview();
        },
        updatePreview(){
          const form=document.getElementById('cardForm'); if(!form) return;
          const fd=new FormData(form);
          this.loading=true;
          fetch('/api/preview', { method:'POST', body: fd })
            .then(r=>r.ok?r.blob():Promise.reject())
            .then(blob=>{
              const url=URL.createObjectURL(blob);
              this.$refs.previewImg.src=url;
              setTimeout(()=>URL.revokeObjectURL(url), 10000);
              this.loading=false;
            })
            .catch(()=>{ this.loading=false; });
        }
      }
    }
    (function(){
      const s=localStorage.getItem('theme');
      const d = s ? s==='dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      const m=document.querySelector('meta[name="theme-color"]');
      if(m) m.setAttribute('content', d ? '#0b0e13' : '#ffffff');
    })();

    // === APP NAV SCRIPT ===
    function appNavigator(){
      // === EDIT daftar aplikasi kamu di sini ===
      const APP_LINKS = {
        pinned: [
          //{ name:'QR Maker', icon:'🪪', url:'#', description:'Aplikasi kartu nama', tag:'Internal' },
          { name:'QR Maker', icon:'📊', url:'http://31.97.110.27:5010', description:'Statistik & kontrol', tag:'Dashboard' },
          { name:'YT Downloaer', icon:'📊', url:'http://31.97.110.27:5011', description:'Statistik & kontrol', tag:'Dashboard' },
        ],
        groups: [
          { name:'Produk', items:[
            { name:'QR Maker', icon:'📊', url:'http://31.97.110.27:5010', description:'Statistik & kontrol', tag:'Dashboard' },
            { name:'YT Downloaer', icon:'📊', url:'http://31.97.110.27:5011', description:'Statistik & kontrol', tag:'Dashboard' },
          ]},
          { name:'Tools', items:[
            { name:'PDF Tools', icon:'🎧', url:'http://31.97.110.27:5012', description:'Tiket & support', tag:'Ops' },
            { name:'on Progress', icon:'🚚', url:'https://example.com/log', description:'Pengiriman & stok', tag:'Ops' },
          ]},
          { name:'Eksperimen', items:[
            { name:'on Progress', icon:'🧪', url:'https://example.com/lab', description:'Coba model & tools', tag:'Lab' },
          ]},
        ]
      };

      return {
        open:false,
        side:(localStorage.getItem('nav_side')||'left'), // 'left' | 'right'
        q:'',
        showIcons: JSON.parse(localStorage.getItem('nav_icons')||'true'),
        showDock:true,
        dragging:false,
        fabPos:(()=>{
          const saved = localStorage.getItem('fab_pos');
          if(saved){ try{ return JSON.parse(saved) }catch(_){} }
          // default untuk FAB 52x52
          return { x: window.innerWidth - 72, y: window.innerHeight - 80 };
        })(),
        pinned: APP_LINKS.pinned,
        groups: APP_LINKS.groups.map(g=>({...g, open:true, filtered:g.items})),
        quickApps: [...APP_LINKS.pinned.slice(0,3)],
        filteredPinned: [],

        init(){
          // Hotkeys
          window.addEventListener('keydown',(e)=>{
            if(e.altKey && e.key.toLowerCase()==='k'){ e.preventDefault(); this.toggleDrawer(); }
            if(e.key==='Escape' && this.open){ this.close(); }
            if(e.key==='['){ this.side='left'; this.persist(); }
            if(e.key===']'){ this.side='right'; this.persist(); }
          });
          window.addEventListener('resize', ()=> this.boundFab());
          this.doFilter();
        },

        toggleDrawer(){ this.open=!this.open; this.persist(); },
        close(){ this.open=false; this.persist(); },
        switchSide(){ this.side = (this.side==='left') ? 'right' : 'left'; this.persist(); },

        doFilter(){
          const q=(this.q||'').trim().toLowerCase();
          this.filteredPinned = this.pinned.filter(it => !q || [it.name,it.description,it.tag].filter(Boolean).some(v => (v+'').toLowerCase().includes(q)));
          this.groups = this.groups.map(g => ({ ...g, filtered: g.items.filter(it => !q || [it.name,it.description,it.tag].filter(Boolean).some(v => (v+'').toLowerCase().includes(q))) }));
        },
        toggleGroup(group){ group.open=!group.open; },

        persist(){
          localStorage.setItem('nav_side', this.side);
          localStorage.setItem('nav_icons', JSON.stringify(this.showIcons));
        },

        // Drag FAB untuk ukuran tetap
        startDrag(e){ this.dragging=true; this._dragOffset={ x:e.clientX - this.fabPos.x, y:e.clientY - this.fabPos.y }; },
        onDrag(e){ if(!this.dragging) return; this.fabPos={ x:e.clientX - this._dragOffset.x, y:e.clientY - this._dragOffset.y }; this.boundFab(); },
        endDrag(){ if(!this.dragging) return; this.dragging=false; localStorage.setItem('fab_pos', JSON.stringify(this.fabPos)); },
        boundFab(){
          const pad=10, w=56, h=56; // FAB ~52px + margin aman
          const maxX=window.innerWidth - w - pad, maxY=window.innerHeight - h - pad;
          this.fabPos.x=Math.max(pad, Math.min(maxX, this.fabPos.x));
          this.fabPos.y=Math.max(pad, Math.min(maxY, this.fabPos.y));
        }
      }
    }
  </script>
</body>
</html>
"""

# ====== Font & Utils ======

def load_font(size, weight="regular"):
    candidates = {
        "regular": ["Inter-Regular.ttf", "Montserrat-Regular.ttf", "DejaVuSans.ttf", "arial.ttf"],
        "semibold": ["Inter-SemiBold.ttf", "Montserrat-SemiBold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
        "bold": ["Inter-Bold.ttf", "Montserrat-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
    }
    for name in candidates.get(weight, []) + candidates["regular"]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def parse_size(s: str, default=(1050, 600)):
    try:
        if "x" in s.lower():
            w, h = s.lower().split("x", 1)
            return (max(400, int(w)), max(250, int(h)))
    except Exception:
        pass
    return default


def parse_color(hexstr: str, default=(59, 130, 246)):
    try:
        s = hexstr.strip().lstrip("#")
        if len(s) == 3:
            r, g, b = [int(c * 2, 16) for c in s]
        elif len(s) == 6:
            r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        else:
            return default
        return (r, g, b)
    except Exception:
        return default


def fit_logo(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    iw, ih = img.size
    scale = min(max_w / iw, max_h / ih, 1.0)
    nw, nh = int(iw * scale), int(ih * scale)
    return img.resize((nw, nh), Image.LANCZOS)


def make_qr(data: str, fill=(17, 24, 39), back=(255, 255, 255), box_size=10):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill, back_color=back).convert("RGBA")
    return img


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_size: int, min_size: int, weight="regular"):
    size = max_size
    while size >= min_size:
        font = load_font(size, weight=weight)
        bbox = draw.textbbox((0, 0), text or "", font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            return font, size
        size -= 1
    return load_font(min_size, weight=weight), min_size


def wrap_text(draw, text, font, max_width):
    lines = []
    for paragraph in (text or "").split("\n"):
        if not paragraph.strip():
            continue
        words = paragraph.split()
        line = []
        for w in words:
            test = " ".join(line + [w])
            ww = draw.textbbox((0, 0), test, font=font)[2]
            if ww <= max_width or not line:
                line.append(w)
            else:
                lines.append(" ".join(line))
                line = [w]
        if line:
            lines.append(" ".join(line))
    return lines


def _draw_rounded_panel(canvas: Image.Image, fill=(255, 255, 255), alpha=55, outline_alpha=75, radius_factor=0.02, blur=0.5):
    W, H = canvas.size
    panel = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(panel)
    pad = int(W * 0.04)
    d.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(W * radius_factor), fill=(255, 255, 255, alpha), outline=(255, 255, 255, outline_alpha), width=2)
    return panel.filter(ImageFilter.GaussianBlur(blur))


def render_background(canvas: Image.Image, theme_key: str, accent=(59, 130, 246)):
    W, H = canvas.size
    t = THEMES.get(theme_key, THEMES["pro-modern"])
    bg = t["bg"]
    # Solid / known tokens first
    if isinstance(bg, tuple):
        canvas.paste(bg, [0, 0, W, H])
    elif bg == "gradient":
        grad = Image.new("RGB", (W, H), (0, 0, 0))
        p = grad.load()
        for y in range(H):
            for x in range(W):
                u = x / W; v = y / H
                r = int((1 - u) * 14 + u * 139)
                g = int((1 - u) * 165 + u * 92)
                b = int((1 - u) * 233 + u * 246)
                r = min(255, int(r * (0.85 + 0.3 * v)))
                g = min(255, int(g * (0.85 + 0.3 * v)))
                b = min(255, int(b * (0.85 + 0.3 * v)))
                p[x, y] = (r, g, b)
        canvas.paste(grad)
    elif bg == "stripe":
        base = Image.new("RGB", (W, H), (255, 255, 255))
        stripe = Image.new("RGB", (W * 2, H * 2), (229, 236, 255))
        for yy in range(0, H * 2, 20):
            ImageDraw.Draw(stripe).rectangle([0, yy, W * 2, yy + 10], fill=(229, 236, 255))
        stripe = stripe.rotate(45, expand=True).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
        base = Image.blend(base, stripe, 0.45)
        canvas.paste(base)
    elif bg == "aurora":
        # multi-stop soft blobs sweeping diagonally
        base = Image.new("RGB", (W, H), (7, 10, 16))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        def blob(cx, cy, rx, ry, color, alpha):
            for i in range(6, 0, -1):
                a = int(alpha * (i / 6) ** 2)
                d.ellipse([cx - rx * i, cy - ry * i, cx + rx * i, cy + ry * i], fill=color + (a,))
        blob(int(W*0.2), int(H*0.3), int(W*0.06), int(H*0.04), (14,165,233), 120)
        blob(int(W*0.7), int(H*0.2), int(W*0.08), int(H*0.06), (139,92,246), 110)
        blob(int(W*0.6), int(H*0.75), int(W*0.07), int(H*0.05), (20,184,166), 100)
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=max(8, int(min(W,H)*0.01))))
        base = base.convert("RGBA")
        base.alpha_composite(overlay)
        canvas.paste(base.convert("RGB"))
    elif bg == "carbon":
        base = Image.new("RGB", (W, H), (18, 19, 23))
        tex = Image.new("RGB", (W, H), (18, 19, 23))
        d = ImageDraw.Draw(tex)
        step = 8
        for y in range(0, H + step, step):
            for x in range(0, W + step, step):
                c = (24, 26, 32) if (x//step + y//step) % 2 == 0 else (20, 22, 27)
                d.rectangle([x, y, x + step, y + step], fill=c)
        tex = tex.filter(ImageFilter.GaussianBlur(0.6))
        canvas.paste(Image.blend(base, tex, 0.35))
    elif bg == "lines":
        base = Image.new("RGB", (W, H), (245, 246, 248))
        d = ImageDraw.Draw(base)
        gap = max(12, W // 60)
        for i in range(-H, W, gap):
            d.line([(i, 0), (i + H, H)], fill=(220, 226, 234), width=1)
        canvas.paste(base)
    elif bg == "satin":
        grad = Image.new("RGB", (W, H), (0, 0, 0))
        p = grad.load()
        for y in range(H):
          for x in range(W):
            u = x / W; v = y / H
            r = int(255 * (0.92 - 0.22 * v + 0.08 * u))
            g = int(255 * (0.95 - 0.18 * u))
            b = int(255 * (0.98 - 0.28 * u - 0.05 * v))
            p[x, y] = (max(210, min(255, r)), max(210, min(255, g)), max(210, min(255, b)))
        canvas.paste(grad)

    # Optional glass panel
    if t["panel"] == "glass":
        panel = _draw_rounded_panel(canvas)
        canvas.alpha_composite(panel)
    elif isinstance(t["panel"], tuple):
        W, H = canvas.size
        d = ImageDraw.Draw(canvas)
        pad = int(W * 0.04)
        d.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(W * 0.02), fill=t["panel"])


def render_card(payload: dict) -> Image.Image:
    """
    Render kartu menggunakan tema & layout profesional.
    """
    W, H = parse_size(payload.get("size", "1050x600"))
    theme_key = payload.get("theme", "pro-modern")
    accent = parse_color(payload.get("accent", "#3b82f6"))
    url = (payload.get("url") or "").strip()

    t = THEMES.get(theme_key, THEMES["pro-modern"])
    fg = t["fg"]; sub = t["sub"]
    panel_color = t["panel"] if isinstance(t["panel"], tuple) else None

    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    render_background(card, theme_key, accent=accent)
    draw = ImageDraw.Draw(card)

    if panel_color:
        pad = int(W * 0.04)
        draw.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(W * 0.02), fill=panel_color)

    pad = int(W * 0.06)
    inner_w = W - pad * 2
    inner_h = H - pad * 2
    left_x = pad + (int(W * 0.02) if t["panel"] in ["glass"] else 0)
    right_w = int(inner_w * 0.38)
    left_w = inner_w - right_w - int(W * 0.02)

    logo_img = None
    if payload.get("logo"):
        try:
            logo_img = Image.open(payload["logo"]).convert("RGBA")
        except Exception:
            logo_img = None

    name = payload.get("name", "").strip()
    title = payload.get("title", "").strip()
    company = payload.get("company", "").strip()
    email = payload.get("email", "").strip()
    phone = payload.get("phone", "").strip()
    address = payload.get("address", "").strip()

    y = pad + int(H * 0.02)

    if logo_img:
        max_lw = int(left_w * 0.35)
        max_lh = int(H * 0.22)
        logo_img = fit_logo(logo_img, max_lw, max_lh)
        card.alpha_composite(logo_img, dest=(left_x, y))
        y += logo_img.height + int(H * 0.03)

    # Name (auto-fit)
    name_max = int(left_w * 0.98)
    name_font, name_size = fit_text(draw, name or "Nama Kamu", name_max, max_size=int(H * 0.16), min_size=int(H * 0.09), weight="bold")
    draw.text((left_x, y), name or "Nama Kamu", font=name_font, fill=fg)
    y += int(name_size * 1.25)

    # Title + Company
    tc_line = ((title or "Jabatan") + (" — " if (title or company) else "") + (company or "")).strip()
    tfont, _ = fit_text(draw, tc_line or "Perusahaan", name_max, max_size=int(H * 0.08), min_size=int(H * 0.06), weight="semibold")
    w = draw.textbbox((0, 0), tc_line or "Perusahaan", font=tfont)[2]
    text_to_draw = tc_line or "Perusahaan"
    if w <= name_max:
        draw.text((left_x, y), text_to_draw, font=tfont, fill=sub)
        y += int(tfont.size * 1.5)
    else:
        base = load_font(int(H * 0.07), "semibold")
        lines = wrap_text(draw, text_to_draw, base, name_max)[:2]
        for ln in lines:
            draw.text((left_x, y), ln, font=base, fill=sub)
            y += int(base.size * 1.35)

    # Contacts
    info_font = load_font(int(H * 0.06), "regular")
    contacts = [x for x in [email, phone] if x]
    for line in contacts:
        draw.text((left_x, y), line, font=info_font, fill=fg)
        y += int(info_font.size * 1.35)

    if address:
        small = load_font(int(H * 0.055), "regular")
        for ln in wrap_text(draw, address, small, name_max)[:3]:
            draw.text((left_x, y), ln, font=small, fill=fg)
            y += int(small.size * 1.35)

    # QR with safe white frame on dark backgrounds
    if url:
        qr_size = min(int(H * 0.72), int(inner_w * 0.38))
        dark_bg = theme_key in ["pro-dark", "pro-glass", "pro-gradient", "pro-aurora", "pro-carbon"]
        back = (255, 255, 255)
        qr_img = make_qr(url, fill=accent, back=back, box_size=max(4, qr_size // 60))
        qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
        qr_x = W - pad - qr_size
        qr_y = pad + (inner_h - qr_size) // 2
        if dark_bg:
            frame_pad = int(qr_size * 0.08)
            frame = Image.new("RGBA", (qr_size + frame_pad * 2, qr_size + frame_pad * 2), (255, 255, 255, 28))
            r = int(min(frame.size) * 0.12)
            ImageDraw.Draw(frame).rounded_rectangle([0, 0, frame.size[0] - 1, frame.size[1] - 1], radius=r, fill=(255, 255, 255, 36), outline=(255, 255, 255, 60), width=2)
            card.alpha_composite(frame, dest=(qr_x - frame_pad, qr_y - frame_pad))
        card.alpha_composite(qr_img, dest=(qr_x, qr_y))

    return card


def pil_to_png_bytes(img: Image.Image) -> bytes:
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


def pil_to_pdf_bytes(img: Image.Image, dpi=300) -> bytes:
    bio = io.BytesIO()
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.save(bio, format="PDF", resolution=dpi)
    return bio.getvalue()


# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def index():
    png_url = None
    pdf_url = None

    if request.method == "POST" and request.form.get("action") == "generate":
        form = request.form
        payload = {
            "name": form.get("name", ""),
            "title": form.get("title", ""),
            "company": form.get("company", ""),
            "email": form.get("email", ""),
            "phone": form.get("phone", ""),
            "address": form.get("address", ""),
            "url": form.get("url", ""),
            "theme": form.get("theme", "pro-modern"),
            "accent": form.get("accent", "#3b82f6"),
            "size": form.get("size", "1050x600"),
            "dpi": int(form.get("dpi", "300") or 300),
        }
        logo_f = request.files.get("logo")
        payload["logo"] = (logo_f.stream if (logo_f and logo_f.filename) else None)

        try:
            img = render_card(payload)
            png_bytes = pil_to_png_bytes(img)
            pdf_bytes = pil_to_pdf_bytes(img, dpi=payload["dpi"])
            png_url = save_result(png_bytes, "png")
            pdf_url = save_result(pdf_bytes, "pdf")
        except Exception as e:
            return render_template_string(
                HTML,
                png_url=None,
                pdf_url=None,
                error=str(e),
                theme_previews=theme_previews(),
                palettes=PALETTES,
            )

    return render_template_string(
        HTML,
        png_url=png_url,
        pdf_url=pdf_url,
        error=None,
        theme_previews=theme_previews(),
        palettes=PALETTES,
    )


# Live preview: same engine, returns PNG bytes
@app.route("/api/preview", methods=["POST"])
def api_preview():
    form = request.form
    payload = {
        "name": form.get("name", ""),
        "title": form.get("title", ""),
        "company": form.get("company", ""),
        "email": form.get("email", ""),
        "phone": form.get("phone", ""),
        "address": form.get("address", ""),
        "url": form.get("url", ""),
        "theme": form.get("theme", "pro-modern"),
        "accent": form.get("accent", "#3b82f6"),
        "size": form.get("size", "1050x600"),
    }
    logo_f = request.files.get("logo")
    payload["logo"] = (logo_f.stream if (logo_f and logo_f.filename) else None)

    try:
        img = render_card(payload)
        png = pil_to_png_bytes(img)
        return Response(png, mimetype="image/png")
    except Exception as e:
        # return tiny error image so UI tetap jalan
        err = Image.new("RGB", (800, 200), (255, 240, 240))
        d = ImageDraw.Draw(err)
        d.text((12, 12), f"Preview error: {e}", fill=(160, 0, 0))
        bio = io.BytesIO(); err.save(bio, format="PNG")
        return Response(bio.getvalue(), mimetype="image/png")


# ====== Previews for theme cards (mini SVG to data URL) ======

def theme_previews():
    previews = {}
    for k, v in THEMES.items():
        bg_token = v["bg"]
        if isinstance(bg_token, tuple):
            r, g, b = bg_token
            bg = f"rgb({r},{g},{b})"
        elif bg_token in ("gradient", "aurora", "satin"):
            bg = "url(#g)"
        elif bg_token in ("stripe", "lines", "carbon"):
            bg = "url(#p)"
        else:
            bg = "#ffffff"
        title = v["title"]
        text_main = '#fff' if k in ['pro-dark','pro-glass','pro-gradient','pro-aurora','pro-carbon'] else '#1f2937'
        text_sub  = '#e5e7eb' if k in ['pro-dark','pro-glass','pro-gradient','pro-aurora','pro-carbon'] else '#6b7280'
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 100">
          <defs>
            <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#0ea5e9"/>
              <stop offset="100%" stop-color="#8b5cf6"/>
            </linearGradient>
            <pattern id="p" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="10" height="10" fill="#ffffff"/>
              <rect width="5" height="10" fill="#e5ecff"/>
            </pattern>
          </defs>
          <rect width="160" height="100" fill="{bg}"/>
          <rect x="10" y="10" width="140" height="80" rx="8" fill="rgba(255,255,255,0.18)" stroke="rgba(0,0,0,0.1)"/>
          <text x="18" y="42" font-size="14" font-weight="700" fill="{text_main}">{title}</text>
          <text x="18" y="62" font-size="10" fill="{text_sub}">preview</text>
        </svg>'''
        previews[k] = {"title": title, "preview": "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()}
    return previews


if __name__ == "__main__":
    # pip install flask pillow qrcode[pil]
    # python card_maker_pro_plus.py -> http://localhost:5013/
    app.run(debug=True, host="0.0.0.0", port=5013)
