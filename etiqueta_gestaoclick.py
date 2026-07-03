import sys
import os
import json
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.error
import unicodedata

def remover_acentos(texto):
    nfkd = unicodedata.normalize('NFKD', str(texto))
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

BASE_DIR    = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__)
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CACHE_FILE  = os.path.join(BASE_DIR, "produtos_cache.json")
HIST_FILE     = os.path.join(BASE_DIR, "historico.json")
LAYOUTS_FILE  = os.path.join(BASE_DIR, "layouts_salvos.json")

# ── Conversão mm ↔ dots ──────────────────────────────────────────────────────
def mm_para_dots(mm, dpi=203):
    return round(float(mm) * dpi / 25.4)

def dots_para_mm(dots, dpi=203):
    return round(dots * 25.4 / dpi, 1)

# DPI padrão (pode ser sobrescrito pela config)
DPI_PADRAO = 203

# ── Presets em mm ────────────────────────────────────────────────────────────
# Cada preset define: largura_mm, altura_mm e os elementos com posições em mm
# 'tamanho' dos textos também em mm (altura do glifo ZPL)
LAYOUT_PRESETS = {
    "1 Coluna": {
        "largura_mm": 90.0,   # largura de 1 etiqueta (coluna)
        "papel_largura_mm": 90.0,
        "num_colunas": 1,
        "altura_mm":  30.0,
        "espaco_mm":  0.0,
        "cartela_esq_mm":  0.0,
        "cartela_dir_mm":  0.0,
        "cartela_topo_mm": 0.0,
        "cartela_base_mm": 0.0,
        "gap_col_mm":      0.0,
        "elementos": {
            "empresa": {"ativo": True,  "x_mm": 45.0, "y_mm": 1.7,  "alinha": "center", "tamanho_mm": 4.0},
            "linha":   {"ativo": True,  "x_mm": 0.0,  "y_mm": 6.5,  "visivel": True},
            "nome":    {"ativo": True,  "x_mm": 45.0, "y_mm": 8.2,  "alinha": "center", "tamanho_mm": 3.2},
            "preco":   {"ativo": True,  "x_mm": 45.0, "y_mm": 12.5, "alinha": "center", "tamanho_mm": 14.7},
                        "texto_fixo": {"ativo": False, "x_mm": 45.0, "y_mm": 1.0, "alinha": "center", "tamanho_mm": 2.5, "texto": ""},
            "barcode":    {"ativo": False, "y_mm": 22.0, "tamanho_mm": 5.0},
            "codigo":  {"ativo": False, "x_mm": 45.0, "y_mm": 26.5, "alinha": "center", "tamanho_mm": 2.5},
        }
    },
    "2 Colunas": {
        "largura_mm": 45.0,   # largura de 1 etiqueta (coluna)
        "papel_largura_mm": 90.0,
        "num_colunas": 2,
        "altura_mm":  30.0,
        "espaco_mm":  0.0,
        "cartela_esq_mm":  0.0,
        "cartela_dir_mm":  0.0,
        "cartela_topo_mm": 0.0,
        "cartela_base_mm": 0.0,
        "gap_col_mm":      0.0,
        "elementos": {
            "empresa": {"ativo": True,  "x_mm": 22.5, "y_mm": 1.7,  "alinha": "center", "tamanho_mm": 3.5},
            "linha":   {"ativo": True,  "x_mm": 0.0,  "y_mm": 6.5,  "visivel": True},
            "nome":    {"ativo": True,  "x_mm": 22.5, "y_mm": 8.2,  "alinha": "center", "tamanho_mm": 2.7},
            "preco":   {"ativo": True,  "x_mm": 22.5, "y_mm": 12.5, "alinha": "center", "tamanho_mm": 11.2},
                        "texto_fixo": {"ativo": False, "x_mm": 45.0, "y_mm": 1.0, "alinha": "center", "tamanho_mm": 2.5, "texto": ""},
            "barcode":    {"ativo": False, "y_mm": 22.0, "tamanho_mm": 5.0},
            "codigo":  {"ativo": False, "x_mm": 22.5, "y_mm": 26.5, "alinha": "center", "tamanho_mm": 2.5},
        }
    },
    "3 Colunas": {
        "largura_mm": 30.0,   # largura de 1 etiqueta (coluna)
        "papel_largura_mm": 90.0,
        "num_colunas": 3,
        "altura_mm":  30.0,
        "espaco_mm":  0.0,
        "cartela_esq_mm":  0.0,
        "cartela_dir_mm":  0.0,
        "cartela_topo_mm": 0.0,
        "cartela_base_mm": 0.0,
        "gap_col_mm":      0.0,
        "elementos": {
            "empresa": {"ativo": True,  "x_mm": 15.0, "y_mm": 1.5,  "alinha": "center", "tamanho_mm": 2.7},
            "linha":   {"ativo": True,  "x_mm": 0.0,  "y_mm": 6.0,  "visivel": True},
            "nome":    {"ativo": True,  "x_mm": 15.0, "y_mm": 7.2,  "alinha": "center", "tamanho_mm": 2.2},
            "preco":   {"ativo": True,  "x_mm": 15.0, "y_mm": 11.0, "alinha": "center", "tamanho_mm": 9.0},
                        "texto_fixo": {"ativo": False, "x_mm": 45.0, "y_mm": 1.0, "alinha": "center", "tamanho_mm": 2.5, "texto": ""},
            "barcode":    {"ativo": False, "y_mm": 22.0, "tamanho_mm": 5.0},
            "codigo":  {"ativo": False, "x_mm": 15.0, "y_mm": 26.0, "alinha": "center", "tamanho_mm": 2.0},
        }
    },
    "Só Preço": {
        "largura_mm": 90.0,
        "papel_largura_mm": 90.0,
        "num_colunas": 1,
        "altura_mm":  30.0,
        "espaco_mm":  0.0,
        "cartela_esq_mm":  0.0,
        "cartela_dir_mm":  0.0,
        "cartela_topo_mm": 0.0,
        "cartela_base_mm": 0.0,
        "gap_col_mm":      0.0,
        "elementos": {
            "empresa": {"ativo": True,  "x_mm": 45.0, "y_mm": 1.0,  "alinha": "center", "tamanho_mm": 2.7},
            "linha":   {"ativo": False, "x_mm": 0.0,  "y_mm": 4.5,  "visivel": False},
            "nome":    {"ativo": True,  "x_mm": 45.0, "y_mm": 5.0,  "alinha": "center", "tamanho_mm": 2.5},
            "preco":   {"ativo": True,  "x_mm": 45.0, "y_mm": 8.5,  "alinha": "center", "tamanho_mm": 18.5},
                        "texto_fixo": {"ativo": False, "x_mm": 45.0, "y_mm": 1.0, "alinha": "center", "tamanho_mm": 2.5, "texto": ""},
            "barcode":    {"ativo": False, "y_mm": 22.0, "tamanho_mm": 5.0},
            "codigo":  {"ativo": False, "x_mm": 45.0, "y_mm": 26.0, "alinha": "center", "tamanho_mm": 2.5},
        }
    },
}

DEFAULT_CFG = {
    "access_token": "",
    "secret_token": "",
    "empresa": "",
    "impressora": "",
    "api_base_url": "https://api.gestaoclick.com/api",
    "sync_auto": True,
    "dpi": DPI_PADRAO,
    # layout salvo no formato mm
    "layout_preset": "1 Coluna",
    "layout_elementos": None,
    "largura_mm": 90.0,
    "altura_mm":  30.0,
    "espaco_mm":  0.0,
    "papel_largura_mm": 90.0,
    "cartela_esq_mm":  0.0,
    "cartela_dir_mm":  0.0,
    "cartela_topo_mm": 0.0,
    "cartela_base_mm": 0.0,
    "gap_col_mm":      0.0,
}

# ───────────────────────── Config ─────────────────────────

def salvar_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

def carregar_config():
    cfg = dict(DEFAULT_CFG)
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


# ───────────────────────── Cache ─────────────────────────

def salvar_cache(produtos_por_codigo, meta):
    payload = {
        "atualizado_em": meta.get("atualizado_em", ""),
        "total_registros": meta.get("total_registros", 0),
        "produtos": produtos_por_codigo,
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)

def carregar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"atualizado_em": "", "total_registros": 0, "produtos": {}}

def indexar_produto(dic, item):
    reg = {
        "id": item.get("id", ""),
        "nome": item.get("nome") or item.get("descricao") or "—",
        "codigo_interno": item.get("codigo_interno", ""),
        "codigo_barra": item.get("codigo_barra", ""),
        "valor_venda": item.get("valor_venda", "0"),
    }
    cod   = (item.get("codigo_interno") or "").strip()
    barra = (item.get("codigo_barra")   or "").strip()
    if cod:
        dic[cod] = reg
    if barra and barra != cod:
        dic[barra] = reg

def sincronizar_produtos(api_base_url, access_token, secret_token, progress_q, cancel_event):
    produtos_por_codigo = {}
    pagina = 1
    total_paginas = None
    total_registros = 0

    while True:
        if cancel_event.is_set():
            progress_q.put(("cancelado", None))
            return

        url = f"{api_base_url.rstrip('/')}/produtos?pagina={pagina}"
        req = urllib.request.Request(url)
        req.add_header("access-token", access_token)
        req.add_header("secret-access-token", secret_token)
        req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            progress_q.put(("erro", f"Erro HTTP {e.code} na página {pagina}: {e.reason}"))
            return
        except urllib.error.URLError as e:
            progress_q.put(("erro", f"Erro de conexão na página {pagina}: {e.reason}"))
            return
        except Exception as e:
            progress_q.put(("erro", f"Erro inesperado na página {pagina}: {e}"))
            return

        itens = data.get("data", [])
        for item in itens:
            indexar_produto(produtos_por_codigo, item)

        meta = data.get("meta", {})
        total_paginas   = meta.get("total_paginas", pagina)
        total_registros = meta.get("total_registros", len(produtos_por_codigo))
        proxima         = meta.get("proxima_pagina")

        progress_q.put(("progresso", (pagina, total_paginas, len(produtos_por_codigo))))

        if not proxima or not itens:
            break
        pagina = proxima
        time.sleep(0.05)

    meta_final = {
        "atualizado_em": time.strftime("%d/%m/%Y %H:%M:%S"),
        "total_registros": total_registros,
    }
    salvar_cache(produtos_por_codigo, meta_final)
    progress_q.put(("concluido", (len(produtos_por_codigo), meta_final["atualizado_em"])))


# ───────────────────────── Histórico ─────────────────────────

def carregar_historico():
    if os.path.exists(HIST_FILE):
        with open(HIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def salvar_historico(historico):
    with open(HIST_FILE, "w", encoding="utf-8") as f:
        json.dump(historico[-500:], f, ensure_ascii=False, indent=2)

def registrar_historico(produtos, empresa):
    historico = carregar_historico()
    agora = time.strftime("%d/%m/%Y %H:%M:%S")
    total_etiquetas = sum(p["qtd"] for p in produtos)
    historico.append({
        "data_hora": agora,
        "empresa": empresa,
        "total_etiquetas": total_etiquetas,
        "produtos": [{"codigo": p["codigo"], "nome": p["nome"],
                      "preco": p["preco"], "qtd": p["qtd"]} for p in produtos],
    })
    salvar_historico(historico)


# ───────────────────────── ZPL / Impressora ─────────────────────────

def listar_impressoras():
    try:
        import win32print
        impressoras = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 4)
        return [p["pPrinterName"] for p in impressoras]
    except Exception:
        return []

def gerar_zpl(nome, preco, empresa, qtd=1, elementos=None, dims_mm=None, dpi=DPI_PADRAO, codigo=""):
    empresa_zpl = remover_acentos(empresa).upper()[:30]
    nome_zpl    = remover_acentos(nome).upper()[:120]
    codigo_zpl  = remover_acentos(codigo).upper()[:20]
    try:
        s = str(preco).replace("R$", "").strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        preco_fmt = f"R${float(s):.2f}".replace(".", ",")
    except Exception:
        preco_fmt = str(preco) if str(preco).startswith("R$") else f"R${preco}"

    if elementos is None:
        elementos = LAYOUT_PRESETS["1 Coluna"]["elementos"]
    if dims_mm is None:
        dims_mm = {"largura_mm": 90.0, "altura_mm": 30.0, "espaco_mm": 0.0}

    def mm(v):
        return mm_para_dots(v, dpi)

    pw      = mm(dims_mm.get("largura_mm",  90.0))
    ll      = mm(dims_mm.get("altura_mm",  30.0)) + mm(dims_mm.get("espaco_mm", 0.0))
    lh_topo = mm(dims_mm.get("cartela_topo_mm", 0.0))
    gap     = mm(dims_mm.get("espaco_mm",  0.0))

    el = elementos
    alinha_map = {"center": "C", "left": "L", "right": "R"}

    linhas_zpl = []

    # empresa
    emp = el.get("empresa", {})
    if emp.get("ativo", True):
        a = alinha_map.get(emp.get("alinha", "center"), "C")
        s = mm(emp.get("tamanho_mm", 4.0))
        y = mm(emp.get("y_mm", 1.7))
        linhas_zpl.append(f"^FO0,{y}^FB{pw},1,0,{a},0^A0N,{s},{s}^FD{empresa_zpl}^FS")

    # linha separadora
    lin = el.get("linha", {})
    if lin.get("ativo", True) and lin.get("visivel", True):
        y = mm(lin.get("y_mm", 6.5))
        linhas_zpl.append(f"^FO0,{y}^GB{pw},3,3^FS")

    # nome
    nom = el.get("nome", {})
    if nom.get("ativo", True):
        a = alinha_map.get(nom.get("alinha", "center"), "C")
        s = mm(nom.get("tamanho_mm", 3.2))
        y = mm(nom.get("y_mm", 8.2))
        linhas_zpl.append(f"^FO0,{y}^A0N,{s},{s}^FB{pw},3,0,{a},0^FD{nome_zpl}^FS")

    # preço
    pre = el.get("preco", {})
    if pre.get("ativo", True):
        a = alinha_map.get(pre.get("alinha", "center"), "C")
        s = mm(pre.get("tamanho_mm", 14.7))
        y = mm(pre.get("y_mm", 12.5))
        linhas_zpl.append(f"^FO0,{y}^FB{pw},1,0,{a},0^A0N,{s},{int(s*0.92)}^FD{preco_fmt}^FS")

    # código
    cod_el = el.get("codigo", {})
    if cod_el.get("ativo", False) and codigo_zpl:
        a = alinha_map.get(cod_el.get("alinha", "center"), "C")
        s = mm(cod_el.get("tamanho_mm", 2.5))
        y = mm(cod_el.get("y_mm", 26.5))
        linhas_zpl.append(f"^FO0,{y}^A0N,{s},{s}^FB{pw},1,0,{a},0^FD{codigo_zpl}^FS")

    # código de barras Code 128
    bar_el = el.get("barcode", {})
    if bar_el.get("ativo", False) and codigo_zpl:
        y_b = mm(bar_el.get("y_mm", 22.0))
        h_b = max(10, mm(bar_el.get("tamanho_mm", 5.0)))
        linhas_zpl.append(f"^FO4,{y_b}^BY2,2,{h_b}^BCN,{h_b},Y,N,N^FD{codigo_zpl}^FS")

    # texto fixo
    txf = el.get("texto_fixo", {})
    if txf.get("ativo", False):
        txt_val = remover_acentos(txf.get("texto", "")).upper()
        if txt_val:
            a = alinha_map.get(txf.get("alinha", "center"), "C")
            s = mm(txf.get("tamanho_mm", 2.5))
            y = mm(txf.get("y_mm", 1.0))
            linhas_zpl.append(f"^FO0,{y}^FB{pw},1,0,{a},0^A0N,{s},{s}^FD{txt_val}^FS")

    lh_cmd  = f"^LH0,{lh_topo}" if lh_topo > 0 else "^LH0,0"

    corpo = "\n".join(linhas_zpl)
    zpl = f"""^XA
^MMT
^PW{pw}
^LL{ll}
^LS0
{lh_cmd}
{corpo}
^PQ{qtd},0,1,Y
^XZ"""
    return zpl

def imprimir_zpl(zpl, nome_impressora):
    try:
        import win32print
    except ImportError:
        raise Exception("pywin32 nao instalado.\nFeche e abra o INSTALAR_E_RODAR.bat novamente.")
    hprinter = win32print.OpenPrinter(nome_impressora)
    try:
        win32print.StartDocPrinter(hprinter, 1, ("Etiqueta ZPL", None, "RAW"))
        win32print.StartPagePrinter(hprinter)
        win32print.WritePrinter(hprinter, zpl.encode("ascii", errors="replace"))
        win32print.EndPagePrinter(hprinter)
        win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)


# ───────────────────────── Paleta / estilo ─────────────────────────

COR = {
    "bg":        "#EEF1F8",
    "surface":   "#FFFFFF",
    "surface2":  "#F7F9FC",
    "border":    "#E2E6ED",
    "text":      "#1F2430",
    "muted":     "#7A8194",
    "primary":       "#3D5AFE",
    "primary_hover": "#2F46D6",
    "primary_press": "#26399F",
    "primary_soft":  "#EAEDFF",
    "success":   "#1AA260",
    "success_soft": "#E4F7EE",
    "danger":    "#E4483F",
    "danger_soft": "#FDEBEA",
    "warn":      "#B98900",
}

FONT_BASE   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_TINY   = ("Segoe UI", 8)
FONT_TITLE  = ("Segoe UI Semibold", 15)
FONT_LABEL  = ("Segoe UI Semibold", 9)



def _formatar_preco_str(preco):
    """Formata string de preço já existente para ZPL."""
    try:
        s = str(preco).replace("R$", "").strip()
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        return f"R${float(s):.2f}".replace(".", ",")
    except Exception:
        return str(preco) if str(preco).startswith("R$") else f"R${preco}"


def _campos_produto_zpl(prod, empresa, el, mm_fn, col_w, x_off):
    """Gera linhas ZPL para 1 produto em 1 coluna com offset X."""
    alinha_map = {"center": "C", "left": "L", "right": "R"}
    empresa_zpl = remover_acentos(empresa).upper()[:30]
    nome_zpl    = remover_acentos(prod.get("nome", "—")).upper()[:120]
    preco_fmt   = _formatar_preco_str(prod.get("preco", "0"))
    codigo_zpl  = remover_acentos(prod.get("codigo", "")).upper()[:20]

    linhas = []

    emp = el.get("empresa", {})
    if emp.get("ativo", True):
        a = alinha_map.get(emp.get("alinha", "center"), "C")
        s = mm_fn(emp.get("tamanho_mm", 4.0))
        y = mm_fn(emp.get("y_mm", 1.7))
        linhas.append(f"^FO{x_off},{y}^FB{col_w},1,0,{a},0^A0N,{s},{s}^FD{empresa_zpl}^FS")

    lin = el.get("linha", {})
    if lin.get("ativo", True) and lin.get("visivel", True):
        y = mm_fn(lin.get("y_mm", 6.5))
        linhas.append(f"^FO{x_off},{y}^GB{col_w},3,3^FS")

    nom = el.get("nome", {})
    if nom.get("ativo", True):
        a = alinha_map.get(nom.get("alinha", "center"), "C")
        s = mm_fn(nom.get("tamanho_mm", 3.2))
        y = mm_fn(nom.get("y_mm", 8.2))
        linhas.append(f"^FO{x_off},{y}^A0N,{s},{s}^FB{col_w},3,0,{a},0^FD{nome_zpl}^FS")

    pre = el.get("preco", {})
    if pre.get("ativo", True):
        a = alinha_map.get(pre.get("alinha", "center"), "C")
        s = mm_fn(pre.get("tamanho_mm", 14.7))
        y = mm_fn(pre.get("y_mm", 12.5))
        linhas.append(f"^FO{x_off},{y}^FB{col_w},1,0,{a},0^A0N,{s},{int(s*0.92)}^FD{preco_fmt}^FS")

    cod_el = el.get("codigo", {})
    if cod_el.get("ativo", False) and codigo_zpl:
        a = alinha_map.get(cod_el.get("alinha", "center"), "C")
        s = mm_fn(cod_el.get("tamanho_mm", 2.5))
        y = mm_fn(cod_el.get("y_mm", 26.5))
        linhas.append(f"^FO{x_off},{y}^A0N,{s},{s}^FB{col_w},1,0,{a},0^FD{codigo_zpl}^FS")

    # código de barras Code 128
    bar_el = el.get("barcode", {})
    if bar_el.get("ativo", False) and codigo_zpl:
        y_b = mm_fn(bar_el.get("y_mm", 22.0))
        h_b = max(10, mm_fn(bar_el.get("tamanho_mm", 5.0)))
        linhas.append(f"^FO{x_off + 4},{y_b}^BY2,2,{h_b}^BCN,{h_b},Y,N,N^FD{codigo_zpl}^FS")

    txf = el.get("texto_fixo", {})
    if txf.get("ativo", False):
        tv = remover_acentos(txf.get("texto", "")).upper()
        if tv:
            a = alinha_map.get(txf.get("alinha", "center"), "C")
            s = mm_fn(txf.get("tamanho_mm", 2.5))
            y = mm_fn(txf.get("y_mm", 1.0))
            linhas.append(f"^FO{x_off},{y}^FB{col_w},1,0,{a},0^A0N,{s},{s}^FD{tv}^FS")

    return linhas


def gerar_zpl_multicol(batch, empresa, dims_mm, elementos, dpi=DPI_PADRAO, num_col_cfg=None):
    """
    Gera 1 label ZPL com N colunas side-by-side.
    batch  = lista de dicts (ou None) com exatamente num_col_cfg itens.
    num_col_cfg = número TOTAL de colunas configuradas (mesmo que batch incompleto).
    O espaçamento é sempre baseado em num_col_cfg para manter posições corretas.
    """
    if elementos is None:
        elementos = LAYOUT_PRESETS["1 Coluna"]["elementos"]
    if dims_mm is None:
        dims_mm = {"largura_mm": 90.0, "altura_mm": 30.0, "espaco_mm": 0.0}

    def mm(v):
        return mm_para_dots(v, dpi)

    papel_mm = dims_mm.get("papel_largura_mm", dims_mm.get("largura_mm", 90.0))
    gap_col  = dims_mm.get("gap_col_mm", 0.0)
    lh_topo  = mm(dims_mm.get("cartela_topo_mm", 0.0))

    # Usa o número CONFIGURADO de colunas (não o do batch) para calcular col_w
    # Isso garante que uma linha incompleta (ex: 1 de 3) mantém o tamanho correto
    if num_col_cfg is None:
        num_col_cfg = max(1, dims_mm.get("num_colunas", len(batch)))
    num_col_cfg = max(1, num_col_cfg)

    tem_produto = any(p is not None for p in batch)
    if not tem_produto:
        return ""

    pw    = mm(papel_mm)
    gap_w = mm(gap_col)
    ll    = mm(dims_mm.get("altura_mm", 30.0)) + mm(dims_mm.get("espaco_mm", 0.0))
    lh_cmd = f"^LH0,{lh_topo}" if lh_topo > 0 else "^LH0,0"

    # Largura de cada coluna: divide o papel pelo total configurado (não pelo batch)
    col_w = (pw - (num_col_cfg - 1) * gap_w) // num_col_cfg

    linhas_zpl = []
    for col_idx, prod in enumerate(batch):
        if prod is None:
            continue   # coluna vazia: espaço reservado mas sem conteúdo
        x_off = col_idx * (col_w + gap_w)
        linhas_zpl.extend(
            _campos_produto_zpl(prod, empresa, elementos, mm, col_w, x_off)
        )

    corpo = "\n".join(linhas_zpl)
    return f"""^XA
^MMT
^PW{pw}
^LL{ll}
^LS0
{lh_cmd}
{corpo}
^PQ1,0,1,Y
^XZ"""


def setup_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=COR["bg"])

    style.configure("App.TFrame", background=COR["bg"])
    style.configure("Surface.TFrame", background=COR["surface"])
    style.configure("Panel.TFrame", background=COR["surface2"])

    style.configure("TLabel", background=COR["surface"], foreground=COR["text"], font=FONT_BASE)
    style.configure("App.TLabel", background=COR["bg"], foreground=COR["text"], font=FONT_BASE)
    style.configure("Muted.TLabel", background=COR["surface"], foreground=COR["muted"], font=FONT_SMALL)
    style.configure("AppMuted.TLabel", background=COR["bg"], foreground=COR["muted"], font=FONT_SMALL)
    style.configure("SectionTitle.TLabel", background=COR["surface"], foreground=COR["text"], font=FONT_LABEL)
    style.configure("Header.TLabel", background=COR["bg"], foreground=COR["text"], font=FONT_TITLE)
    style.configure("HeaderSub.TLabel", background=COR["bg"], foreground=COR["muted"], font=FONT_SMALL)
    style.configure("Total.TLabel", background=COR["surface"], foreground=COR["primary"], font=("Segoe UI Semibold", 11))

    style.configure("StatusOk.TLabel",  background=COR["success_soft"], foreground=COR["success"],
                     font=FONT_SMALL, padding=(10, 4))
    style.configure("StatusErr.TLabel", background=COR["danger_soft"],  foreground=COR["danger"],
                     font=FONT_SMALL, padding=(10, 4))
    style.configure("StatusMuted.TLabel", background=COR["surface2"], foreground=COR["muted"],
                     font=FONT_SMALL, padding=(10, 4))

    style.configure("TNotebook", background=COR["bg"], borderwidth=0, tabmargins=(0, 8, 0, 0))
    style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(22, 11),
                     background=COR["bg"], foreground=COR["muted"], borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", COR["surface"])],
              foreground=[("selected", COR["primary"])])
    style.layout("TNotebook.Tab", [
        ("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                ("Notebook.label", {"side": "top", "sticky": ""})
            ]})
        ]})
    ])

    style.configure("Primary.TButton", font=("Segoe UI Semibold", 12), foreground="#FFFFFF",
                     background=COR["primary"], borderwidth=0, padding=(20, 12), focusthickness=0)
    style.map("Primary.TButton",
              background=[("pressed", COR["primary_press"]), ("active", COR["primary_hover"])],
              foreground=[("disabled", "#C9CEDC")])

    style.configure("Secondary.TButton", font=("Segoe UI Semibold", 11), foreground=COR["text"],
                     background=COR["surface"], borderwidth=1, padding=(16, 10))
    style.map("Secondary.TButton",
              background=[("pressed", COR["surface2"]), ("active", COR["surface2"])],
              bordercolor=[("!disabled", COR["border"])])

    style.configure("Danger.TButton", font=("Segoe UI Semibold", 11), foreground=COR["danger"],
                     background=COR["surface"], borderwidth=1, padding=(16, 10))
    style.map("Danger.TButton",
              background=[("active", COR["danger_soft"])],
              bordercolor=[("!disabled", COR["border"])])

    style.configure("Ghost.TButton", font=FONT_SMALL, foreground=COR["primary"],
                     background=COR["surface"], borderwidth=0, padding=(10, 6))
    style.map("Ghost.TButton", background=[("active", COR["primary_soft"])])

    # Botão pequeno para + / −
    style.configure("Mini.TButton", font=("Segoe UI Semibold", 10), foreground=COR["primary"],
                     background=COR["surface"], borderwidth=1, padding=(4, 2), focusthickness=0)
    style.map("Mini.TButton",
              background=[("active", COR["primary_soft"])],
              bordercolor=[("!disabled", COR["border"])])

    style.configure("TEntry", fieldbackground=COR["surface"], background=COR["surface"],
                     bordercolor=COR["border"], lightcolor=COR["border"], darkcolor=COR["border"],
                     borderwidth=1, padding=7, foreground=COR["text"])
    style.map("TEntry", bordercolor=[("focus", COR["primary"])])

    style.configure("TSpinbox", fieldbackground=COR["surface"], bordercolor=COR["border"],
                     arrowsize=13, padding=6, foreground=COR["text"])
    style.map("TSpinbox", bordercolor=[("focus", COR["primary"])])

    style.configure("TCombobox", fieldbackground=COR["surface"], bordercolor=COR["border"],
                     padding=6, foreground=COR["text"])
    style.map("TCombobox", bordercolor=[("focus", COR["primary"])])

    style.configure("Treeview", background=COR["surface"], fieldbackground=COR["surface"],
                     foreground=COR["text"], font=FONT_BASE, rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", background=COR["surface2"], foreground=COR["muted"],
                     font=("Segoe UI Semibold", 9), borderwidth=0, relief="flat", padding=(8, 8))
    style.map("Treeview.Heading", background=[("active", COR["surface2"])])
    style.map("Treeview",
              background=[("selected", COR["primary_soft"])],
              foreground=[("selected", COR["primary"])])

    style.configure("TProgressbar", troughcolor=COR["surface2"], background=COR["primary"],
                     bordercolor=COR["surface2"], lightcolor=COR["primary"], darkcolor=COR["primary"])
    style.configure("Vertical.TScrollbar", background=COR["surface2"], troughcolor=COR["surface"],
                     bordercolor=COR["surface"], arrowsize=12)
    style.configure("TSeparator", background=COR["border"])


# ───────────────────────── Cantos arredondados ─────────────────────────

def _pontos_retangulo_arredondado(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1,  x2 - r, y1,  x2, y1,  x2, y1 + r,
        x2, y2 - r,  x2, y2,  x2 - r, y2,  x1 + r, y2,
        x1, y2,  x1, y2 - r,  x1, y1 + r,  x1, y1,
    ]


class RoundedCard(tk.Frame):
    def __init__(self, parent, bg_color, page_bg, radius=16, **kwargs):
        super().__init__(parent, bg=page_bg, highlightthickness=0)
        self.bg_color = bg_color
        self.radius = radius
        self.canvas = tk.Canvas(self, bg=page_bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg_color, **kwargs)
        self._bg_item = None
        self._win_item = self.canvas.create_window(0, 0, anchor="nw", window=self.body)
        self.canvas.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 4 or h < 4:
            return
        if self._bg_item is not None:
            self.canvas.delete(self._bg_item)
        pts = _pontos_retangulo_arredondado(1, 1, w - 1, h - 1, self.radius)
        self._bg_item = self.canvas.create_polygon(
            pts, smooth=True, fill=self.bg_color, outline=self.bg_color
        )
        self.canvas.tag_lower(self._bg_item)
        self.canvas.coords(self._win_item, 4, 4)
        self.canvas.itemconfig(self._win_item, width=w - 8, height=h - 8)

    def finalize_fixed_height(self, extra_pad=8):
        self.body.update_idletasks()
        h = self.body.winfo_reqheight() + extra_pad
        self.configure(height=h)
        self.canvas.configure(height=h)
        self.pack_propagate(False)
        self.update_idletasks()
        self._redraw()

    def finalize_fixed_size(self, extra_pad_x=8, extra_pad_y=8):
        self.body.update_idletasks()
        w = self.body.winfo_reqwidth() + extra_pad_x
        h = self.body.winfo_reqheight() + extra_pad_y
        self.configure(width=w, height=h)
        self.canvas.configure(width=w, height=h)
        self.pack_propagate(False)
        self.update_idletasks()
        self._redraw()


class TabPill(tk.Canvas):
    def __init__(self, parent, text, command, page_bg, width=170, height=42, radius=21):
        super().__init__(parent, width=width, height=height, bg=page_bg,
                          highlightthickness=0, bd=0, cursor="hand2")
        self.text = text
        self.command = command
        self.radius = radius
        self.selected = False
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def set_selected(self, valor):
        self.selected = valor
        self._draw()

    def _draw(self):
        self.delete("all")
        w = self.winfo_width() or int(self["width"])
        h = self.winfo_height() or int(self["height"])
        fill = COR["primary"] if self.selected else COR["surface"]
        fg = "#FFFFFF" if self.selected else COR["muted"]
        pts = _pontos_retangulo_arredondado(2, 2, w - 2, h - 2, self.radius)
        self.create_polygon(pts, smooth=True, fill=fill, outline=fill)
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=("Segoe UI Semibold", 10))


def aplicar_cantos_arredondados_janela(root):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        valor = ctypes.c_int(DWMWCP_ROUND)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(valor), ctypes.sizeof(valor)
        )
    except Exception:
        pass


# ───────────────────────── App ─────────────────────────

def carregar_layouts_salvos():
    if os.path.exists(LAYOUTS_FILE):
        with open(LAYOUTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Inicializa com os presets padrão
    salvos = {}
    for nome_p, preset in LAYOUT_PRESETS.items():
        salvos[nome_p] = {
            "largura_mm": preset["largura_mm"], "altura_mm": preset["altura_mm"],
            "espaco_mm": preset.get("espaco_mm", 0.0),
            "papel_largura_mm": preset.get("papel_largura_mm", preset["largura_mm"]),
            "num_colunas": preset.get("num_colunas", 1),
            "cartela_esq_mm": preset.get("cartela_esq_mm", 0.0),
            "cartela_dir_mm": preset.get("cartela_dir_mm", 0.0),
            "cartela_topo_mm": preset.get("cartela_topo_mm", 0.0),
            "cartela_base_mm": preset.get("cartela_base_mm", 0.0),
            "gap_col_mm": preset.get("gap_col_mm", 0.0),
            "dpi": preset.get("dpi", 203),
            "elementos": json.loads(json.dumps(preset["elementos"])),
        }
    salvar_layouts_salvos(salvos)
    return salvos

def salvar_layouts_salvos(d):
    with open(LAYOUTS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


VERSION_ATUAL = "1.0.0"
VERSION_URL   = "https://raw.githubusercontent.com/GabrielKalok/etiquetap/main/version.json"
DOWNLOAD_URL  = "https://raw.githubusercontent.com/GabrielKalok/etiquetap/main/etiqueta_gestaoclick.py"

def verificar_atualizacao(callback):
    """Checa o version.json no GitHub em thread separada. Chama callback(info) se houver update."""
    def _check():
        try:
            req = urllib.request.Request(VERSION_URL)
            req.add_header("Cache-Control", "no-cache")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            versao_remota = data.get("versao", "0.0.0")
            if _versao_maior(versao_remota, VERSION_ATUAL):
                callback(data)
        except Exception:
            pass   # silencioso — sem internet ou GitHub fora do ar

    threading.Thread(target=_check, daemon=True).start()

def _versao_maior(remota, local):
    """Compara versões no formato X.Y.Z — retorna True se remota > local."""
    try:
        r = tuple(int(x) for x in remota.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False

def baixar_atualizacao(url_py, callback_progresso, callback_fim):
    """Baixa o novo .py em thread. callback_progresso(pct), callback_fim(ok, erro)."""
    def _download():
        try:
            destino = sys.executable if getattr(sys, "frozen", False) else                       os.path.join(os.path.dirname(os.path.abspath(__file__)), "etiqueta_gestaoclick.py")
            req = urllib.request.Request(url_py)
            with urllib.request.urlopen(req, timeout=30) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                baixado = 0
                chunks = []
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    baixado += len(chunk)
                    if total > 0:
                        callback_progresso(int(baixado / total * 100))
            conteudo = b"".join(chunks)
            # Salva arquivo (backup do original primeiro)
            bkp = destino + ".bkp"
            if os.path.exists(destino):
                import shutil
                shutil.copy2(destino, bkp)
            with open(destino, "wb") as f:
                f.write(conteudo)
            callback_fim(True, None)
        except Exception as e:
            callback_fim(False, str(e))

    threading.Thread(target=_download, daemon=True).start()


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("EtiqueTAP — Etiquetas GestãoClick · Elgin L42-PRO")
        self.root.resizable(True, True)
        self.cfg = carregar_config()
        self.cache = carregar_cache()
        self.produtos = []

        self.sync_queue = None
        self.sync_cancel = None
        self.sync_win = None

        # DPI configurado
        self._dpi = int(self.cfg.get("dpi", DPI_PADRAO))

        # Layout: carrega do cfg ou usa preset padrão
        saved = self.cfg.get("layout_elementos")
        preset_nome = self.cfg.get("layout_preset", "1 Coluna")
        if saved:
            self._layout_elementos = saved
            self._dims_mm = {
                "largura_mm":       float(self.cfg.get("largura_mm", 90.0)),
                "altura_mm":        float(self.cfg.get("altura_mm",  30.0)),
                "espaco_mm":        float(self.cfg.get("espaco_mm",  0.0)),
                "papel_largura_mm": float(self.cfg.get("papel_largura_mm", self.cfg.get("largura_mm", 90.0))),
                "cartela_esq_mm":   float(self.cfg.get("cartela_esq_mm",  0.0)),
                "cartela_dir_mm":   float(self.cfg.get("cartela_dir_mm",  0.0)),
                "cartela_topo_mm":  float(self.cfg.get("cartela_topo_mm", 0.0)),
                "cartela_base_mm":  float(self.cfg.get("cartela_base_mm", 0.0)),
                "gap_col_mm":       float(self.cfg.get("gap_col_mm",      0.0)),
            }
        else:
            import copy
            preset = LAYOUT_PRESETS.get(preset_nome, LAYOUT_PRESETS["1 Coluna"])
            self._layout_elementos = copy.deepcopy(preset["elementos"])
            self._dims_mm = {
                "largura_mm":       preset["largura_mm"],
                "altura_mm":        preset["altura_mm"],
                "espaco_mm":        preset.get("espaco_mm", 0.0),
                "papel_largura_mm": preset.get("papel_largura_mm", preset["largura_mm"]),
                "cartela_esq_mm":   preset.get("cartela_esq_mm",  0.0),
                "cartela_dir_mm":   preset.get("cartela_dir_mm",  0.0),
                "cartela_topo_mm":  preset.get("cartela_topo_mm", 0.0),
                "cartela_base_mm":  preset.get("cartela_base_mm", 0.0),
                "gap_col_mm":       preset.get("gap_col_mm",      0.0),
            }

        setup_style(self.root)
        self.build_ui()

        if self.cfg.get("sync_auto", True):
            at = self.cfg.get("access_token", "").strip()
            st = self.cfg.get("secret_token", "").strip()
            if at and st:
                self.root.after(800, self._sync_silencioso)
        self._agendar_sync_periodico()
        # Verificar atualização em background (5s de delay)
        self.root.after(5000, lambda: verificar_atualizacao(self._on_update_disponivel))

    # ══════════════════════════ UI ══════════════════════════

    def _on_update_disponivel(self, info):
        """Chamado pela thread de update quando há nova versão. Mostra notificação."""
        versao = info.get("versao", "?")
        notas  = info.get("notas", "")
        url_py = info.get("url_download", DOWNLOAD_URL)
        # Executa na thread principal
        self.root.after(0, lambda: self._mostrar_janela_update(versao, notas, url_py))

    def _mostrar_janela_update(self, versao, notas, url_py):
        win = tk.Toplevel(self.root)
        win.title("Atualização disponível")
        win.resizable(False, False)
        win.grab_set()

        # Cabeçalho
        hdr = tk.Frame(win, bg="#1AA260", pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🆕  Nova versão disponível!", bg="#1AA260", fg="white",
                 font=("Segoe UI Semibold", 13)).pack()
        tk.Label(hdr, text=f"Versão {versao}  (atual: {VERSION_ATUAL})", bg="#1AA260",
                 fg="#C8F5E3", font=("Segoe UI", 9)).pack()

        # Notas
        body = tk.Frame(win, bg="white", padx=20, pady=12)
        body.pack(fill="x")
        if notas:
            tk.Label(body, text="O que há de novo:", font=("Segoe UI Semibold", 9),
                     bg="white", anchor="w").pack(fill="x")
            tk.Label(body, text=notas, font=("Segoe UI", 9), bg="white",
                     fg="#555", wraplength=340, justify="left", anchor="w").pack(fill="x", pady=(4,0))

        # Barra de progresso (oculta até clicar)
        self._update_bar_var = tk.IntVar(value=0)
        self._update_bar = ttk.Progressbar(win, variable=self._update_bar_var,
                                            maximum=100, length=360)
        self._update_lbl = tk.Label(win, text="", font=("Segoe UI", 8), bg="white", fg="#888")

        # Botões
        btn_frm = tk.Frame(win, bg="white", pady=12, padx=20)
        btn_frm.pack(fill="x")

        btn_upd = ttk.Button(btn_frm, text="⬇️  Atualizar agora",
                              command=lambda: self._iniciar_download(win, url_py, btn_upd))
        btn_upd.pack(side="left", ipadx=6)
        ttk.Button(btn_frm, text="Depois", command=win.destroy).pack(side="right")

    def _iniciar_download(self, win, url_py, btn):
        btn.config(state="disabled", text="Baixando...")
        self._update_bar.pack(padx=20, pady=(0,4), fill="x")
        self._update_lbl.pack(padx=20, pady=(0,8))
        win.update()

        def progresso(pct):
            self.root.after(0, lambda p=pct: (
                self._update_bar_var.set(p),
                self._update_lbl.config(text=f"Baixando... {p}%"),
            ))

        def fim(ok, erro):
            def _ui():
                if ok:
                    self._update_bar_var.set(100)
                    self._update_lbl.config(text="✅ Download concluído!")
                    messagebox.showinfo("Atualização concluída",
                        "Arquivo atualizado com sucesso!\n\n"
                        "Feche e abra o programa novamente para usar a nova versão.",
                        parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("Erro no download",
                        f"Não foi possível baixar a atualização:\n{erro}\n\n"

                        "Baixe manualmente em:\ngithub.com/GabrielKalok/etiquetap",
                        parent=win)
                    btn.config(state="normal", text="⬇️  Tentar novamente")
            self.root.after(0, _ui)

        baixar_atualizacao(url_py, progresso, fim)

    def _on_global_return(self, event=None):
        """Se o scanner disparar Enter enquanto entry_cod tem conteúdo, processa o produto."""
        focused = self.root.focus_get()
        # Se o foco está no campo de código, aciona adicionar_produto
        if focused == self.entry_cod:
            self.adicionar_produto()
            return "break"

    def build_ui(self):
        root = self.root
        root.configure(bg=COR["bg"])

        wrapper = ttk.Frame(root, style="App.TFrame")
        wrapper.pack(fill="both", expand=True)

        header = ttk.Frame(wrapper, style="App.TFrame")
        header.pack(fill="x", padx=24, pady=(20, 10))
        ttk.Label(header, text="EtiqueTAP", style="Header.TLabel").pack(anchor="w")

        tabbar = tk.Frame(wrapper, bg=COR["bg"])
        tabbar.pack(fill="x", padx=22, pady=(4, 10))

        tab_imprimir  = TabPill(tabbar, "🖨   Imprimir",       lambda: self._selecionar_aba("imprimir"),
                                 page_bg=COR["bg"], width=160, height=42)
        tab_imprimir.pack(side="left", padx=(0, 8))
        tab_historico = TabPill(tabbar, "🕘   Histórico",      lambda: self._selecionar_aba("historico"),
                                 page_bg=COR["bg"], width=170, height=42)
        tab_historico.pack(side="left", padx=(0, 8))
        tab_pers      = TabPill(tabbar, "🖼   Personalização", lambda: self._selecionar_aba("personalizacao"),
                                 page_bg=COR["bg"], width=210, height=42)
        tab_pers.pack(side="left", padx=(0, 8))
        tab_config    = TabPill(tabbar, "⚙   Configurações",  lambda: self._selecionar_aba("config"),
                                 page_bg=COR["bg"], width=190, height=42)
        tab_config.pack(side="left")

        self._tabs = {"imprimir": tab_imprimir, "historico": tab_historico,
                       "personalizacao": tab_pers, "config": tab_config}

        content_card = RoundedCard(wrapper, bg_color=COR["surface"], page_bg=COR["bg"], radius=18)
        content_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        content_holder = tk.Frame(content_card.body, bg=COR["surface"])
        content_holder.pack(fill="both", expand=True)
        content_holder.grid_rowconfigure(0, weight=1)
        content_holder.grid_columnconfigure(0, weight=1)

        frm_main = ttk.Frame(content_holder, style="Surface.TFrame")
        frm_hist = ttk.Frame(content_holder, style="Surface.TFrame")
        frm_pers = ttk.Frame(content_holder, style="Surface.TFrame")
        frm_cfg  = ttk.Frame(content_holder, style="Surface.TFrame")
        frm_main.grid(row=0, column=0, sticky="nsew")
        frm_hist.grid(row=0, column=0, sticky="nsew")
        frm_pers.grid(row=0, column=0, sticky="nsew")
        frm_cfg .grid(row=0, column=0, sticky="nsew")

        self._paginas = {"imprimir": frm_main, "historico": frm_hist,
                          "personalizacao": frm_pers, "config": frm_cfg}

        self._build_aba_imprimir(frm_main)
        self._build_aba_historico(frm_hist)
        self._build_aba_personalizacao(frm_pers)
        self._build_aba_config(frm_cfg)

        self._selecionar_aba("imprimir")
        self._atualizar_impressoras()
        self.root.after(200, self.entry_cod.focus_set)
        # Captura global do scanner: qualquer digit+Enter volta para entry_cod
        self.root.bind("<Return>", self._on_global_return)

    def _selecionar_aba(self, chave):
        for k, tab in self._tabs.items():
            tab.set_selected(k == chave)
        self._paginas[chave].tkraise()

    # ── Aba Imprimir ──────────────────────────────────────────────────────────

    def _build_aba_imprimir(self, frm):
        frm_topo = ttk.Frame(frm, style="Surface.TFrame")
        frm_topo.pack(fill="x", padx=20, pady=(20, 12))

        card_busca = RoundedCard(frm_topo, bg_color=COR["surface2"], page_bg=COR["surface"], radius=14)
        card_busca.pack(side="left", anchor="n")
        inner_busca = ttk.Frame(card_busca.body, style="Panel.TFrame")
        inner_busca.pack(fill="x", padx=16, pady=14)

        ttk.Label(inner_busca, text="CÓDIGO DO PRODUTO", style="SectionTitle.TLabel",
                  background=COR["surface2"]).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(inner_busca, text="QTD", style="SectionTitle.TLabel",
                  background=COR["surface2"]).grid(row=0, column=1, sticky="w", padx=(0, 10))

        self.entry_cod = ttk.Entry(inner_busca, width=18, font=("Segoe UI", 11))
        self.entry_cod.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(4, 0))
        self.entry_cod.bind("<Return>", lambda e: self.adicionar_produto())

        self.spin_qtd = ttk.Spinbox(inner_busca, from_=1, to=999, width=6, font=("Segoe UI", 11))
        self.spin_qtd.set(1)
        self.spin_qtd.grid(row=1, column=1, sticky="w", padx=(0, 10), pady=(4, 0))

        ttk.Button(inner_busca, text="＋  Adicionar", style="Primary.TButton",
                   command=self.adicionar_produto).grid(row=1, column=2, sticky="w", pady=(4, 0))

        self.lbl_status = ttk.Label(inner_busca, text="", style="StatusMuted.TLabel",
                                     background=COR["surface2"])
        self.lbl_status.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        ttk.Separator(inner_busca, orient="horizontal").grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(14, 12))

        ttk.Label(inner_busca, text="BUSCAR POR NOME", style="SectionTitle.TLabel",
                  background=COR["surface2"]).grid(row=4, column=0, columnspan=2, sticky="w")

        self.entry_busca_nome = ttk.Entry(inner_busca, width=32, font=("Segoe UI", 10))
        self.entry_busca_nome.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.entry_busca_nome.bind("<Return>", lambda e: self._abrir_busca_nome())

        ttk.Button(inner_busca, text="🔍  Buscar", style="Secondary.TButton",
                   command=self._abrir_busca_nome).grid(row=5, column=2, sticky="w",
                                                         padx=(10, 0), pady=(4, 0))

        card_busca.finalize_fixed_size(extra_pad_x=16, extra_pad_y=16)

        preview_area = tk.Frame(frm_topo, bg=COR["surface"])
        preview_area.pack(side="left", fill="both", expand=True, padx=(16, 0))
        ttk.Label(preview_area, text="PRÉ-VISUALIZAÇÃO DA ETIQUETA", style="Muted.TLabel",
                  background=COR["surface"]).pack(anchor="center", pady=(0, 8))
        self.canvas_preview = tk.Canvas(preview_area, width=320, height=107,
                                         bg="white", highlightthickness=1,
                                         highlightbackground=COR["border"])
        self.canvas_preview.pack(anchor="center")

        frm_cache = ttk.Frame(frm, style="Surface.TFrame")
        frm_cache.pack(fill="x", padx=20, pady=(0, 10))
        self.lbl_cache = ttk.Label(frm_cache, text="", style="Muted.TLabel")
        self.lbl_cache.pack(side="left")
        ttk.Button(frm_cache, text="🔄  Sincronizar produtos", style="Ghost.TButton",
                   command=self.iniciar_sync).pack(side="right")
        self._atualizar_label_cache()

        card_tabela = RoundedCard(frm, bg_color=COR["surface"], page_bg=COR["surface"], radius=14)
        card_tabela.pack(fill="both", expand=True, padx=20, pady=(0, 4))
        card_tabela_inner = card_tabela.body

        cols = ("codigo", "nome", "preco", "qtd")
        self.tree = ttk.Treeview(card_tabela_inner, columns=cols, show="headings",
                                  height=8, selectmode="browse")
        self.tree.heading("codigo", text="CÓDIGO")
        self.tree.heading("nome",   text="NOME DO PRODUTO")
        self.tree.heading("preco",  text="PREÇO")
        self.tree.heading("qtd",    text="QTD")
        self.tree.column("codigo", width=90,  anchor="center")
        self.tree.column("nome",   width=300, anchor="w")
        self.tree.column("preco",  width=100, anchor="center")
        self.tree.column("qtd",    width=60,  anchor="center")
        self.tree.tag_configure("odd",  background=COR["surface"])
        self.tree.tag_configure("even", background=COR["surface2"])

        sb = ttk.Scrollbar(card_tabela_inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.editar_qtd)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._atualizar_preview_etiqueta())

        frm_acoes = ttk.Frame(frm, style="Surface.TFrame")
        frm_acoes.pack(fill="x", padx=20, pady=(10, 6))

        ttk.Button(frm_acoes, text="✏️  Editar qtd", style="Secondary.TButton",
                   command=self.editar_qtd).pack(side="left", padx=(0, 8))
        ttk.Button(frm_acoes, text="🗑  Remover", style="Danger.TButton",
                   command=self.remover_selecionado).pack(side="left", padx=(0, 8))
        ttk.Button(frm_acoes, text="🧹 Limpar tudo", style="Secondary.TButton",
                   command=self.limpar_tudo).pack(side="left")

        self.lbl_total = ttk.Label(frm_acoes, text="Total: 0 etiquetas", style="Total.TLabel")
        self.lbl_total.pack(side="right", padx=4)

        ttk.Separator(frm, orient="horizontal").pack(fill="x", padx=20, pady=(6, 14))

        frm_imp = ttk.Frame(frm, style="Surface.TFrame")
        frm_imp.pack(fill="x", padx=20, pady=(0, 20))

        self.btn_imp = ttk.Button(frm_imp, text="🖨   Imprimir tudo", style="Primary.TButton",
                                   command=self.imprimir_todos)
        self.btn_imp.pack(side="left", padx=(0, 10))
        ttk.Button(frm_imp, text="🧪  Imprimir teste", style="Secondary.TButton",
                   command=self.imprimir_teste).pack(side="left")

        self.lbl_imp_status = ttk.Label(frm_imp, text="", style="StatusMuted.TLabel")
        self.lbl_imp_status.pack(side="left", padx=14)

        self._atualizar_preview_etiqueta()

    # ── Aba Histórico ─────────────────────────────────────────────────────────

    def _build_aba_historico(self, frm):
        frm_top = ttk.Frame(frm, style="Surface.TFrame")
        frm_top.pack(fill="x", padx=20, pady=(20, 10))
        ttk.Label(frm_top, text="Histórico de impressões", style="SectionTitle.TLabel",
                  font=("Segoe UI Semibold", 12)).pack(side="left")
        ttk.Button(frm_top, text="🗑  Limpar histórico", style="Danger.TButton",
                   command=self._limpar_historico).pack(side="right")
        ttk.Button(frm_top, text="🔄  Atualizar", style="Secondary.TButton",
                   command=self._carregar_historico_ui).pack(side="right", padx=8)

        ttk.Label(frm, text="SESSÕES DE IMPRESSÃO", style="Muted.TLabel").pack(
            anchor="w", padx=22, pady=(4, 4))

        card_sess = RoundedCard(frm, bg_color=COR["surface"], page_bg=COR["surface"], radius=14)
        card_sess.pack(fill="x", padx=20, pady=(0, 14))
        card_sess.canvas.configure(height=170)
        card_sess.pack_propagate(False)
        card_sess.configure(height=170)

        cols_h = ("data_hora", "total", "produtos_qtd")
        self.tree_hist = ttk.Treeview(card_sess.body, columns=cols_h, show="headings",
                                       height=5, selectmode="browse")
        self.tree_hist.heading("data_hora",    text="DATA / HORA")
        self.tree_hist.heading("total",        text="ETIQUETAS")
        self.tree_hist.heading("produtos_qtd", text="PRODUTOS")
        self.tree_hist.column("data_hora",    width=180, anchor="center")
        self.tree_hist.column("total",        width=100, anchor="center")
        self.tree_hist.column("produtos_qtd", width=100, anchor="center")
        self.tree_hist.tag_configure("odd",  background=COR["surface"])
        self.tree_hist.tag_configure("even", background=COR["surface2"])
        sb_h = ttk.Scrollbar(card_sess.body, orient="vertical", command=self.tree_hist.yview)
        self.tree_hist.configure(yscrollcommand=sb_h.set)
        self.tree_hist.pack(side="left", fill="both", expand=True)
        sb_h.pack(side="right", fill="y")
        self.tree_hist.bind("<<TreeviewSelect>>", self._detalhar_sessao)

        ttk.Label(frm, text="PRODUTOS DA SESSÃO SELECIONADA", style="Muted.TLabel").pack(
            anchor="w", padx=22, pady=(0, 4))

        card_det = RoundedCard(frm, bg_color=COR["surface"], page_bg=COR["surface"], radius=14)
        card_det.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        cols_d = ("codigo", "nome", "preco", "qtd")
        self.tree_det = ttk.Treeview(card_det.body, columns=cols_d, show="headings", height=6)
        self.tree_det.heading("codigo", text="CÓDIGO")
        self.tree_det.heading("nome",   text="NOME")
        self.tree_det.heading("preco",  text="PREÇO")
        self.tree_det.heading("qtd",    text="QTD")
        self.tree_det.column("codigo", width=90,  anchor="center")
        self.tree_det.column("nome",   width=300, anchor="w")
        self.tree_det.column("preco",  width=100, anchor="center")
        self.tree_det.column("qtd",    width=60,  anchor="center")
        self.tree_det.tag_configure("odd",  background=COR["surface"])
        self.tree_det.tag_configure("even", background=COR["surface2"])
        sb_d = ttk.Scrollbar(card_det.body, orient="vertical", command=self.tree_det.yview)
        self.tree_det.configure(yscrollcommand=sb_d.set)
        self.tree_det.pack(side="left", fill="both", expand=True)
        sb_d.pack(side="right", fill="y")

        self._historico_dados = []
        self._carregar_historico_ui()

    def _carregar_historico_ui(self):
        self._historico_dados = list(reversed(carregar_historico()))
        for row in self.tree_hist.get_children():
            self.tree_hist.delete(row)
        for i, sess in enumerate(self._historico_dados):
            n_prod = len(sess.get("produtos", []))
            tag = "even" if i % 2 == 0 else "odd"
            self.tree_hist.insert("", "end", iid=str(i), tags=(tag,),
                                   values=(sess["data_hora"], sess["total_etiquetas"], n_prod))
        for row in self.tree_det.get_children():
            self.tree_det.delete(row)

    def _detalhar_sessao(self, event=None):
        sel = self.tree_hist.selection()
        if not sel:
            return
        idx = int(sel[0])
        sess = self._historico_dados[idx]
        for row in self.tree_det.get_children():
            self.tree_det.delete(row)
        for i, p in enumerate(sess.get("produtos", [])):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree_det.insert("", "end", tags=(tag,),
                                  values=(p["codigo"], p["nome"], p["preco"], p["qtd"]))

    def _limpar_historico(self):
        if messagebox.askyesno("Confirmar", "Apagar todo o histórico de impressões?"):
            salvar_historico([])
            self._carregar_historico_ui()

    # ── Aba Personalização ────────────────────────────────────────────────────

    # Configuração visual dos elementos (todos presentes)
    _EDITOR_ELEM_CFG = {
        "empresa":    {"label": "EMPRESA",      "cor": "#3D5AFE", "cor_txt": "white"},
        "linha":      {"label": "── LINHA ──",  "cor": "#555555", "cor_txt": "white"},
        "nome":       {"label": "Nome produto", "cor": "#1AA260", "cor_txt": "white"},
        "preco":      {"label": "R$ Preço",     "cor": "#E4483F", "cor_txt": "white"},
        "codigo":     {"label": "Código",       "cor": "#B98900", "cor_txt": "white"},
        "texto_fixo": {"label": "Texto fixo",   "cor": "#9C27B0", "cor_txt": "white"},
        "barcode":    {"label": "▐▌ Barcode",    "cor": "#212121", "cor_txt": "white"},
    }

    # Nome amigável e step de tamanho para cada elemento
    _ELEM_INFO = {
        "empresa":    {"nome": "Empresa",      "step_mm": 0.5},
        "linha":      {"nome": "Linha sep.",   "step_mm": None},
        "nome":       {"nome": "Nome produto", "step_mm": 0.5},
        "preco":      {"nome": "Preço",        "step_mm": 1.0},
        "codigo":     {"nome": "Código",       "step_mm": 0.5},
        "texto_fixo": {"nome": "Texto fixo",   "step_mm": 0.5},
        "barcode":    {"nome": "Cód. de barras","step_mm": 1.0, "tipo": "barcode"},
    }

    def _build_aba_personalizacao(self, frm):
        # ── Barra de Layouts Salvos (topo fixo, fora do scroll) ──
        self._layouts_salvos = carregar_layouts_salvos()
        barra_lay = tk.Frame(frm, bg=COR["surface2"], pady=6)
        barra_lay.pack(fill="x", padx=0, pady=(0,2))
        tk.Label(barra_lay, text="💾 Layout salvo:", bg=COR["surface2"],
                 fg=COR["text"], font=("Segoe UI Semibold", 9)).pack(side="left", padx=(12,6))
        self._var_layout_sel = tk.StringVar()
        self._combo_layouts = ttk.Combobox(barra_lay, textvariable=self._var_layout_sel,
                                            width=22, state="readonly")
        self._combo_layouts.pack(side="left", padx=(0,8))
        self._atualizar_combo_layouts()
        ttk.Button(barra_lay, text="Carregar",
                   command=self._carregar_layout_selecionado).pack(side="left", padx=2)
        ttk.Button(barra_lay, text="Salvar como...",
                   command=self._salvar_layout_como).pack(side="left", padx=2)
        ttk.Button(barra_lay, text="🗑 Excluir",
                   command=self._excluir_layout_salvo).pack(side="left", padx=2)

        outer = tk.Frame(frm, bg=COR["surface"])
        outer.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(outer, orient="vertical")
        vsb.pack(side="right", fill="y")
        canvas_scroll = tk.Canvas(outer, bg=COR["surface"], highlightthickness=0,
                                   yscrollcommand=vsb.set)
        canvas_scroll.pack(side="left", fill="both", expand=True)
        vsb.config(command=canvas_scroll.yview)
        wrap = tk.Frame(canvas_scroll, bg=COR["surface"])
        win_id = canvas_scroll.create_window((0, 0), window=wrap, anchor="nw")

        def _on_wrap_conf(e):
            canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
            canvas_scroll.itemconfig(win_id, width=canvas_scroll.winfo_width())
        wrap.bind("<Configure>", _on_wrap_conf)
        canvas_scroll.bind("<Configure>",
                           lambda e: canvas_scroll.itemconfig(win_id, width=e.width))

        # Scroll com roda do mouse
        def _scroll_mouse(e):
            canvas_scroll.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas_scroll.bind_all("<MouseWheel>", _scroll_mouse)

        pad = 24

        # ══ SEÇÃO 1 — DIMENSÕES (em mm) ══════════════════════════════════════
        frm_dim = tk.Frame(wrap, bg=COR["surface"])
        frm_dim.pack(fill="x", padx=pad, pady=(20, 0))

        ttk.Label(frm_dim, text="DIMENSÕES DA ETIQUETA  (em mm)",
                  style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=8, sticky="w",
                                                     pady=(0, 4))
        ttk.Label(frm_dim,
                  text=f"DPI configurado: {self._dpi} dpi  —  conversão automática para dots ZPL ao imprimir.",
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=8, sticky="w", pady=(0, 14))

        dim_campos = [
            ("Largura do papel (mm)",  "papel_largura_mm", 90.0, 10.0, 500.0),
            ("Largura da etiq. (mm)",  "largura_mm",       90.0, 10.0, 300.0),
            ("Altura (mm)",            "altura_mm",        30.0, 5.0,  200.0),
            ("Esp. vertical (mm)",     "espaco_mm",         0.0, 0.0,  50.0),
            ("Cartela esq. (mm)",      "cartela_esq_mm",    0.0, 0.0,  30.0),
            ("Cartela dir. (mm)",      "cartela_dir_mm",    0.0, 0.0,  30.0),
            ("Cartela topo (mm)",      "cartela_topo_mm",   0.0, 0.0,  30.0),
            ("Cartela base (mm)",      "cartela_base_mm",   0.0, 0.0,  30.0),
            ("Gap entre colunas (mm)", "gap_col_mm",        0.0, 0.0,  30.0),
        ]
        self._dim_vars = {}
        for col, (lbl, key, default, vmin, vmax) in enumerate(dim_campos):
            frm_c = tk.Frame(frm_dim, bg=COR["surface"])
            frm_c.grid(row=2, column=col * 2, sticky="nw", padx=(0, 14))
            ttk.Label(frm_c, text=lbl, style="Muted.TLabel", justify="left").pack(anchor="w")
            var = tk.DoubleVar(value=float(self._dims_mm.get(key, default)))
            self._dim_vars[key] = var
            spin = ttk.Spinbox(frm_c, from_=vmin, to=vmax, increment=0.5, width=8,
                                textvariable=var, font=("Segoe UI", 11), format="%.1f")
            spin.pack(anchor="w", pady=(4, 0))
            var.trace_add("write", lambda *a: self.root.after(100, self._on_dim_change))

        ttk.Button(frm_dim, text="Aplicar dimensões", style="Primary.TButton",
                   command=self._salvar_dims).grid(row=3, column=0, columnspan=3,
                                                    sticky="w", pady=(14, 0))

        ttk.Separator(wrap, orient="horizontal").pack(fill="x", padx=pad, pady=(20, 18))

        # ══ SEÇÃO 2 — PRESETS ════════════════════════════════════════════════
        frm_layout = tk.Frame(wrap, bg=COR["surface"])
        frm_layout.pack(fill="x", padx=pad)

        ttk.Label(frm_layout, text="LAYOUT DA ETIQUETA",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(frm_layout,
                  text="Cada preset carrega suas próprias dimensões e posições dos elementos.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        frm_presets = ttk.Frame(frm_layout, style="Surface.TFrame")
        frm_presets.pack(anchor="w", pady=(0, 14))
        for nome_preset in LAYOUT_PRESETS:
            ttk.Button(frm_presets, text=nome_preset, style="Secondary.TButton",
                       command=lambda n=nome_preset: self._aplicar_preset(n)
                       ).pack(side="left", padx=(0, 8))

        ttk.Separator(wrap, orient="horizontal").pack(fill="x", padx=pad, pady=(4, 18))

        # ══ SEÇÃO 3 — ELEMENTOS (visibilidade + tamanho) ═════════════════════
        frm_elem = tk.Frame(wrap, bg=COR["surface"])
        frm_elem.pack(fill="x", padx=pad)

        ttk.Label(frm_elem, text="ELEMENTOS DA ETIQUETA",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(frm_elem,
                  text="Marque quais elementos devem aparecer e ajuste o tamanho de cada um.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        # grade de controles por elemento
        tbl = tk.Frame(frm_elem, bg=COR["surface"])
        tbl.pack(anchor="w", pady=(0, 8))

        # cabeçalho da grade
        headers = ["Elemento", "Visível", "Tamanho (mm)", "", ""]
        for c, h in enumerate(headers):
            tk.Label(tbl, text=h, bg=COR["surface2"], fg=COR["muted"],
                     font=("Segoe UI Semibold", 8), padx=8, pady=4,
                     relief="flat").grid(row=0, column=c, sticky="ew", padx=2, pady=(0, 4))

        self._elem_ativo_vars = {}
        self._elem_tam_vars   = {}

        for row_i, (key, info) in enumerate(self._ELEM_INFO.items(), start=1):
            elem_cfg = self._layout_elementos.get(key, {})
            cfg_visual = self._EDITOR_ELEM_CFG[key]

            # nome com cor
            name_frm = tk.Frame(tbl, bg=COR["surface"])
            name_frm.grid(row=row_i, column=0, sticky="w", padx=(0, 10), pady=3)
            tk.Label(name_frm, bg=cfg_visual["cor"], width=2, height=1).pack(side="left", padx=(0, 6))
            tk.Label(name_frm, text=info["nome"], bg=COR["surface"],
                     fg=COR["text"], font=("Segoe UI", 9)).pack(side="left")

            # checkbox visível
            var_ativo = tk.BooleanVar(value=bool(elem_cfg.get("ativo", True)))
            self._elem_ativo_vars[key] = var_ativo
            chk = ttk.Checkbutton(tbl, variable=var_ativo,
                                   command=lambda k=key: self._on_elem_visibilidade(k))
            chk.grid(row=row_i, column=1, padx=10)

            # tamanho (só para elementos que têm tamanho)
            step = info["step_mm"]
            if step is not None:
                tam_atual = float(elem_cfg.get("tamanho_mm", 3.0))
                var_tam = tk.DoubleVar(value=tam_atual)
                self._elem_tam_vars[key] = var_tam

                tam_frm = tk.Frame(tbl, bg=COR["surface"])
                tam_frm.grid(row=row_i, column=2, padx=4)

                lbl_tam = tk.Label(tam_frm, text=f"{tam_atual:.1f}",
                                    bg=COR["surface"], fg=COR["text"],
                                    font=("Segoe UI Semibold", 10), width=5)
                lbl_tam.pack(side="left")

                ttk.Button(tam_frm, text="−", style="Mini.TButton", width=2,
                           command=lambda k=key, s=step, l=lbl_tam: self._diminuir_elem(k, s, l)
                           ).pack(side="left", padx=(6, 2))
                ttk.Button(tam_frm, text="＋", style="Mini.TButton", width=2,
                           command=lambda k=key, s=step, l=lbl_tam: self._aumentar_elem(k, s, l)
                           ).pack(side="left", padx=(2, 0))

                # campo extra de texto para texto_fixo
                if key == "texto_fixo":
                    if not hasattr(self, "_elem_texto_vars"):
                        self._elem_texto_vars = {}
                    var_txt = tk.StringVar(value=elem_cfg.get("texto", ""))
                    self._elem_texto_vars[key] = var_txt
                    entry_txt = ttk.Entry(tbl, textvariable=var_txt, width=18, font=("Segoe UI", 9))
                    entry_txt.grid(row=row_i, column=3, padx=(8, 0), pady=3, sticky="w")
                    entry_txt.bind("<KeyRelease>", lambda e, k=key: self._on_texto_fixo_change(k))
                    tk.Label(tbl, text="texto", bg=COR["surface"], fg=COR["muted"],
                             font=("Segoe UI", 7)).grid(row=0, column=3, sticky="w", padx=(8,0))
            else:
                # linha: apenas toggle de visível (sem tamanho)
                tk.Label(tbl, text="—", bg=COR["surface"], fg=COR["muted"],
                         font=("Segoe UI", 9)).grid(row=row_i, column=2)

        ttk.Separator(wrap, orient="horizontal").pack(fill="x", padx=pad, pady=(16, 18))

        # ══ SEÇÃO 4 — EDITOR DRAG-AND-DROP ═══════════════════════════════════
        ttk.Label(frm_layout, text="EDITOR DE POSIÇÃO  (arraste os elementos)",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 6))

        editor_outer = tk.Frame(frm_layout, bg=COR["surface"])
        editor_outer.pack(anchor="w")

        editor_border = tk.Frame(editor_outer, bg=COR["border"], bd=1, relief="solid")
        editor_border.pack(side="left")

        self.canvas_editor = tk.Canvas(editor_border, bg="white", highlightthickness=0,
                                        cursor="crosshair")
        self.canvas_editor.pack()

        legenda = tk.Frame(editor_outer, bg=COR["surface"])
        legenda.pack(side="left", padx=(14, 0), anchor="n")
        ttk.Label(legenda, text="Elementos:", style="Muted.TLabel").pack(anchor="w")
        for key, cfg_e in self._EDITOR_ELEM_CFG.items():
            row_l = tk.Frame(legenda, bg=COR["surface"])
            row_l.pack(anchor="w", pady=2)
            tk.Label(row_l, bg=cfg_e["cor"], width=3, height=1).pack(side="left", padx=(0, 6))
            tk.Label(row_l, text=cfg_e["label"], bg=COR["surface"],
                     fg=COR["text"], font=("Segoe UI", 9)).pack(side="left")

        ttk.Label(frm_layout,
                  text="Clique e arraste os rótulos para reposicionar. Salvo automaticamente ao soltar.",
                  style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

        self.root.after(120, self._redesenhar_editor_com_dims)

    # ── Controles de elementos ────────────────────────────────────────────────

    def _atualizar_combo_layouts(self):
        nomes = sorted(self._layouts_salvos.keys())
        self._combo_layouts["values"] = nomes
        if nomes:
            # Seleciona o que tiver nome mais próximo do atual, senão o primeiro
            self._var_layout_sel.set(nomes[0])

    def _carregar_layout_selecionado(self):
        nome = self._var_layout_sel.get()
        if not nome or nome not in self._layouts_salvos:
            messagebox.showwarning("Atenção", "Selecione um layout salvo primeiro.")
            return
        lay = self._layouts_salvos[nome]
        # Aplicar dimensões
        self._dims_mm = {k: lay.get(k, v) for k, v in {
            "largura_mm": 90.0, "altura_mm": 30.0, "espaco_mm": 0.0,
            "papel_largura_mm": 90.0, "num_colunas": 1,
            "cartela_esq_mm": 0.0, "cartela_dir_mm": 0.0,
            "cartela_topo_mm": 0.0, "cartela_base_mm": 0.0, "gap_col_mm": 0.0,
        }.items()}
        self._dpi = lay.get("dpi", 203)
        # Aplicar elementos
        self._layout_elementos = json.loads(json.dumps(lay.get("elementos", {})))
        # Atualizar spinboxes de dimensão
        if hasattr(self, "_dim_vars"):
            for key in self._dim_vars:
                if key in self._dims_mm:
                    self._dim_vars[key].set(self._dims_mm[key])
        # Atualizar checkboxes de elementos
        if hasattr(self, "_elem_ativo_vars"):
            for key, var in self._elem_ativo_vars.items():
                el = self._layout_elementos.get(key, {})
                var.set(el.get("ativo", False))
        # Atualizar tamanhos de elementos
        if hasattr(self, "_elem_tam_vars"):
            for key, var in self._elem_tam_vars.items():
                el = self._layout_elementos.get(key, {})
                var.set(el.get("tamanho_mm", 3.0))
        # Atualizar texto_fixo
        if hasattr(self, "_elem_texto_vars"):
            for key, var in self._elem_texto_vars.items():
                el = self._layout_elementos.get(key, {})
                var.set(el.get("texto", ""))
        self._salvar_layout()
        self._redesenhar_editor_com_dims()
        self._atualizar_preview_etiqueta()
        messagebox.showinfo("Layout carregado", f"Layout '{nome}' aplicado com sucesso!")

    def _salvar_layout_como(self):
        win = tk.Toplevel(self.root)
        win.title("Salvar layout como...")
        win.resizable(False, False)
        win.grab_set()
        tk.Label(win, text="Nome do layout:", font=("Segoe UI", 10)).pack(padx=20, pady=(16,4))
        var_nome = tk.StringVar(value=self._var_layout_sel.get() or "Meu Layout")
        entry = ttk.Entry(win, textvariable=var_nome, width=28, font=("Segoe UI", 10))
        entry.pack(padx=20, pady=4)
        entry.select_range(0, "end")
        entry.focus()
        def confirmar():
            nome = var_nome.get().strip()
            if not nome:
                messagebox.showwarning("Atenção", "Digite um nome.", parent=win)
                return
            # Captura estado atual
            lay = {k: self._dims_mm.get(k, 0) for k in [
                "largura_mm", "altura_mm", "espaco_mm", "papel_largura_mm",
                "num_colunas", "cartela_esq_mm", "cartela_dir_mm",
                "cartela_topo_mm", "cartela_base_mm", "gap_col_mm"]}
            lay["dpi"]      = self._dpi
            lay["elementos"] = json.loads(json.dumps(self._layout_elementos))
            self._layouts_salvos[nome] = lay
            salvar_layouts_salvos(self._layouts_salvos)
            self._atualizar_combo_layouts()
            self._var_layout_sel.set(nome)
            win.destroy()
            messagebox.showinfo("Salvo", f"Layout '{nome}' salvo com sucesso!")
        ttk.Button(win, text="Salvar", command=confirmar).pack(pady=(6,16))
        entry.bind("<Return>", lambda e: confirmar())

    def _excluir_layout_salvo(self):
        nome = self._var_layout_sel.get()
        if not nome or nome not in self._layouts_salvos:
            messagebox.showwarning("Atenção", "Selecione um layout para excluir.")
            return
        if not messagebox.askyesno("Confirmar", f"Excluir o layout '{nome}'?"):
            return
        del self._layouts_salvos[nome]
        salvar_layouts_salvos(self._layouts_salvos)
        self._atualizar_combo_layouts()
        messagebox.showinfo("Excluído", f"Layout '{nome}' removido.")

    def _on_elem_visibilidade(self, key):
        ativo = self._elem_ativo_vars[key].get()
        if key not in self._layout_elementos:
            self._layout_elementos[key] = {}
        self._layout_elementos[key]["ativo"] = ativo
        if key == "linha":
            self._layout_elementos[key]["visivel"] = ativo
        self._salvar_layout()
        self._desenhar_editor()
        self._atualizar_preview_etiqueta()

    def _aumentar_elem(self, key, step, lbl_tam):
        el = self._layout_elementos.get(key, {})
        atual = float(el.get("tamanho_mm", 3.0))
        novo = round(max(0.5, atual + step), 1)
        if key not in self._layout_elementos:
            self._layout_elementos[key] = {}
        self._layout_elementos[key]["tamanho_mm"] = novo
        lbl_tam.config(text=f"{novo:.1f}")
        self._salvar_layout()
        self._desenhar_editor()
        self._atualizar_preview_etiqueta()

    def _on_texto_fixo_change(self, key):
        if not hasattr(self, "_elem_texto_vars"):
            return
        var = self._elem_texto_vars.get(key)
        if var is None:
            return
        if key not in self._layout_elementos:
            self._layout_elementos[key] = {}
        self._layout_elementos[key]["texto"] = var.get()
        self._salvar_layout()
        self._desenhar_editor()
        self._atualizar_preview_etiqueta()

    def _diminuir_elem(self, key, step, lbl_tam):
        el = self._layout_elementos.get(key, {})
        atual = float(el.get("tamanho_mm", 3.0))
        novo = max(0.5, round(atual - step, 1))
        self._layout_elementos[key]["tamanho_mm"] = novo
        lbl_tam.config(text=f"{novo:.1f}")
        self._salvar_layout()
        self._desenhar_editor()
        self._atualizar_preview_etiqueta()

    def _salvar_layout(self):
        self.cfg["layout_elementos"]  = self._layout_elementos
        self.cfg["largura_mm"]        = self._dims_mm["largura_mm"]
        self.cfg["altura_mm"]         = self._dims_mm["altura_mm"]
        self.cfg["espaco_mm"]         = self._dims_mm["espaco_mm"]
        self.cfg["papel_largura_mm"]  = self._dims_mm.get("papel_largura_mm", self._dims_mm["largura_mm"])
        self.cfg["cartela_esq_mm"]    = self._dims_mm.get("cartela_esq_mm",  0.0)
        self.cfg["cartela_dir_mm"]    = self._dims_mm.get("cartela_dir_mm",  0.0)
        self.cfg["cartela_topo_mm"]   = self._dims_mm.get("cartela_topo_mm", 0.0)
        self.cfg["cartela_base_mm"]   = self._dims_mm.get("cartela_base_mm", 0.0)
        self.cfg["gap_col_mm"]        = self._dims_mm.get("gap_col_mm",      0.0)
        salvar_config(self.cfg)

    # ── Dimensões ─────────────────────────────────────────────────────────────

    def _salvar_dims(self):
        try:
            papel   = float(self._dim_vars["papel_largura_mm"].get())
            larg    = float(self._dim_vars["largura_mm"].get())
            alt     = float(self._dim_vars["altura_mm"].get())
            esp     = float(self._dim_vars["espaco_mm"].get())
            c_esq   = float(self._dim_vars["cartela_esq_mm"].get())
            c_dir   = float(self._dim_vars["cartela_dir_mm"].get())
            c_topo  = float(self._dim_vars["cartela_topo_mm"].get())
            c_base  = float(self._dim_vars["cartela_base_mm"].get())
            gap_col = float(self._dim_vars["gap_col_mm"].get())
        except Exception:
            messagebox.showerror("Erro", "Valores inválidos nas dimensões.")
            return
        num_col = max(1, round(papel / larg)) if larg > 0 else 1
        self._dims_mm = {"largura_mm": larg, "altura_mm": alt, "espaco_mm": esp,
                         "papel_largura_mm": papel, "num_colunas": num_col,
                         "cartela_esq_mm": c_esq, "cartela_dir_mm": c_dir,
                         "cartela_topo_mm": c_topo, "cartela_base_mm": c_base,
                         "gap_col_mm": gap_col}
        self._salvar_layout()
        self._redesenhar_editor_com_dims()
        self._atualizar_preview_etiqueta()
        messagebox.showinfo("Dimensões salvas",
                            f"Papel: {papel} mm  |  Etiqueta: {larg} × {alt} mm  |  {num_col} coluna(s)")

    def _on_dim_change(self):
        try:
            papel = float(self._dim_vars["papel_largura_mm"].get())
            larg  = float(self._dim_vars["largura_mm"].get())
            alt   = float(self._dim_vars["altura_mm"].get())
            self._dims_mm["papel_largura_mm"] = papel
            self._dims_mm["largura_mm"]       = larg
            self._dims_mm["altura_mm"]        = alt
            self._dims_mm["num_colunas"]      = max(1, round(papel/larg)) if larg>0 else 1
            for k in ("cartela_esq_mm","cartela_dir_mm","cartela_topo_mm","cartela_base_mm","gap_col_mm"):
                if k in self._dim_vars:
                    self._dims_mm[k] = float(self._dim_vars[k].get())
        except Exception:
            pass
        self._redesenhar_editor_com_dims()

    # ── Editor drag-and-drop ──────────────────────────────────────────────────

    def _aplicar_preset(self, nome_preset):
        preset = LAYOUT_PRESETS.get(nome_preset)
        if not preset:
            return
        import copy
        self._layout_elementos = copy.deepcopy(preset["elementos"])
        self._dims_mm = {
            "largura_mm":       preset["largura_mm"],
            "altura_mm":        preset["altura_mm"],
            "espaco_mm":        preset.get("espaco_mm", 0.0),
            "papel_largura_mm": preset.get("papel_largura_mm", preset["largura_mm"]),
            "num_colunas":      preset.get("num_colunas", 1),
            "cartela_esq_mm":   preset.get("cartela_esq_mm",  0.0),
            "cartela_dir_mm":   preset.get("cartela_dir_mm",  0.0),
            "cartela_topo_mm":  preset.get("cartela_topo_mm", 0.0),
            "cartela_base_mm":  preset.get("cartela_base_mm", 0.0),
            "gap_col_mm":       preset.get("gap_col_mm",      0.0),
        }
        # atualiza spinboxes de dimensão
        if hasattr(self, "_dim_vars"):
            for key in ("papel_largura_mm", "largura_mm", "altura_mm", "espaco_mm",
                        "cartela_esq_mm", "cartela_dir_mm", "cartela_topo_mm",
                        "cartela_base_mm", "gap_col_mm"):
                if key in self._dim_vars:
                    self._dim_vars[key].set(self._dims_mm[key])
        # atualiza checkboxes e labels de tamanho
        if hasattr(self, "_elem_ativo_vars"):
            for key, var in self._elem_ativo_vars.items():
                var.set(bool(self._layout_elementos.get(key, {}).get("ativo", True)))
        # sincroniza var de texto_fixo se existir
        if hasattr(self, "_elem_texto_vars") and "texto_fixo" in self._elem_texto_vars:
            self._elem_texto_vars["texto_fixo"].set(
                self._layout_elementos.get("texto_fixo", {}).get("texto", ""))
        # (labels de tamanho serão sincronizados na próxima abertura; ok para preset)
        self.cfg["layout_preset"] = nome_preset
        self._salvar_layout()
        self._redesenhar_editor_com_dims()
        self._atualizar_preview_etiqueta()

    def _redesenhar_editor_com_dims(self):
        if not hasattr(self, "canvas_editor"):
            return
        label_mm   = self._dims_mm.get("largura_mm", 90.0)
        papel_mm   = self._dims_mm.get("papel_largura_mm", label_mm)
        alt_mm     = self._dims_mm.get("altura_mm", 30.0)
        c_esq      = self._dims_mm.get("cartela_esq_mm",  0.0)
        c_dir      = self._dims_mm.get("cartela_dir_mm",  0.0)
        c_topo     = self._dims_mm.get("cartela_topo_mm", 0.0)
        c_base     = self._dims_mm.get("cartela_base_mm", 0.0)
        gap_col    = self._dims_mm.get("gap_col_mm",      0.0)
        num_col    = max(1, round(papel_mm / label_mm)) if label_mm > 0 else 1
        self._num_colunas = num_col

        # Canvas representa o papel inteiro (incluindo cartela)
        MAX_W, MAX_H = 560, 260
        total_h_mm = c_topo + alt_mm + c_base
        ratio = papel_mm / max(total_h_mm, 0.1)
        if ratio >= MAX_W / MAX_H:
            ew = MAX_W
            eh = max(40, int(MAX_W / ratio))
        else:
            eh = MAX_H
            ew = max(80, int(MAX_H * ratio))

        # Escala: pixels por mm no eixo do papel completo
        sx_papel = ew / papel_mm
        sy_papel = eh / max(total_h_mm, 0.1)

        # Área printável (etiqueta sem cartela)
        label_x0_px = c_esq * sx_papel   # onde começa a 1ª coluna no canvas
        label_y0_px = c_topo * sy_papel  # onde começa o topo da etiqueta
        label_w_px  = label_mm * sx_papel
        label_h_px  = alt_mm * sy_papel
        gap_col_px  = gap_col * sx_papel

        self._editor_col_width_px = label_w_px + gap_col_px
        self._editor_label_x0_px  = label_x0_px
        self._editor_label_y0_px  = label_y0_px
        self._editor_label_w_px   = label_w_px
        self._editor_label_h_px   = label_h_px
        self._editor_scale_x      = label_w_px / label_mm  # escala dentro de 1 etiqueta
        self._editor_scale_y      = label_h_px / alt_mm
        self._sx_papel            = sx_papel
        self._sy_papel            = sy_papel
        self.canvas_editor.config(width=ew, height=eh)
        self._desenhar_editor(ew, eh)

    def _desenhar_editor(self, W=None, H=None):
        if not hasattr(self, "canvas_editor"):
            return
        c = self.canvas_editor
        c.delete("all")
        sx      = getattr(self, "_editor_scale_x", 5.0)
        sy      = getattr(self, "_editor_scale_y", 5.0)
        num_col = getattr(self, "_num_colunas", 1)
        lw_px   = getattr(self, "_editor_label_w_px", None)
        lh_px   = getattr(self, "_editor_label_h_px", None)
        lx0     = getattr(self, "_editor_label_x0_px", 0.0)
        ly0     = getattr(self, "_editor_label_y0_px", 0.0)
        gap_px  = getattr(self, "_editor_col_width_px", None)
        if W is None: W = int(c["width"])
        if H is None: H = int(c["height"])
        if lw_px  is None: lw_px  = W / num_col
        if lh_px  is None: lh_px  = float(H)
        if gap_px is None: gap_px = lw_px
        col_step = gap_px  # passo entre colunas (label + gap)

        tem_cartela = (lx0 > 0 or ly0 > 0 or
                       (lx0 + lw_px * num_col + (num_col-1)*max(0, gap_px-lw_px)) < W - 1 or
                       (ly0 + lh_px) < H - 1)

        # Fundo = cartela (cinza claro)
        c.create_rectangle(0, 0, W, H, fill="#E8E8E8", outline="")

        # Linhas de guia sutis
        for y in range(0, H, 20):
            c.create_line(0, y, W, y, fill="#DCDCDC", dash=(2, 6))

        # Desenhar área de cada coluna (etiqueta = branco)
        for col in range(num_col):
            x0_col = lx0 + col * col_step
            x1_col = x0_col + lw_px
            y0_col = ly0
            y1_col = ly0 + lh_px
            fill_col = "#FFFFFF" if col % 2 == 0 else "#F8F8FF"
            c.create_rectangle(int(x0_col), int(y0_col), int(x1_col), int(y1_col),
                                fill=fill_col, outline="#BBBBBB", width=1)
            if num_col > 1:
                label_txt = f"Col {col+1}" if col > 0 else "Col 1 (arrastar)"
                c.create_text(x0_col + lw_px/2, y0_col + 6, text=label_txt,
                               font=("Segoe UI", 7), fill="#999999", anchor="n")

        # Borda do papel
        c.create_rectangle(1, 1, W-1, H-1, outline=COR["muted"], width=1)

        # Régua Y dentro da etiqueta
        alt_mm = self._dims_mm.get("altura_mm", 30.0)
        for mm_v in range(0, int(alt_mm)+1, 5):
            yp = ly0 + mm_v * sy
            c.create_line(0, yp, 5, yp, fill="#AAAAAA", width=1)
            if mm_v > 0:
                c.create_text(6, yp, text=str(mm_v), font=("Segoe UI", 6),
                               fill="#AAAAAA", anchor="w")

        el = self._layout_elementos
        self._editor_drag_items = {}
        label_mm = self._dims_mm.get("largura_mm", 90.0)

        for key, cfg_e in self._EDITOR_ELEM_CFG.items():
            elem  = el.get(key, {})
            ativo = elem.get("ativo", True)
            if not ativo:
                continue   # ← DESATIVADO: não aparece

            for col in range(num_col):
                x_off_col = lx0 + col * col_step  # offset X do início desta coluna
                is_first  = (col == 0)
                drag_tag  = (f"drag_{key}",) if is_first else ()

                if key == "linha":
                    y_mm = float(elem.get("y_mm", 6.5))
                    y_px = int(ly0 + y_mm * sy)
                    iid  = c.create_line(int(x_off_col)+2, y_px,
                                          int(x_off_col+lw_px)-2, y_px,
                                          fill=cfg_e["cor"], width=2, tags=drag_tag)
                    if is_first:
                        hit = c.create_rectangle(int(x_off_col)+2, y_px-6,
                                                  int(x_off_col+lw_px)-2, y_px+6,
                                                  fill="", outline="",
                                                  tags=(f"drag_{key}", f"hit_{key}"))
                        lbl = c.create_text(int(x_off_col + lw_px/2), y_px-8,
                                             text="── LINHA", fill="#888888",
                                             font=("Segoe UI", 7), tags=drag_tag)
                        self._editor_drag_items[key] = {"line": iid, "hit": hit,
                                                         "lbl": lbl, "type": "hline"}
                else:
                    x_mm   = float(elem.get("x_mm", label_mm/2))
                    y_mm   = float(elem.get("y_mm", 5.0))
                    tam_mm = float(elem.get("tamanho_mm", 3.0))
                    x_px   = int(x_off_col + x_mm * sx)
                    y_px   = int(ly0 + y_mm * sy)
                    # Bloco com altura PROPORCIONAL ao tamanho_mm
                    blk_h  = max(10, int(tam_mm * sy))
                    blk_w  = max(30, int(lw_px * 0.7))
                    x1b, y1b = x_px - blk_w//2, y_px
                    x2b, y2b = x_px + blk_w//2, y_px + blk_h
                    rect = c.create_rectangle(x1b, y1b, x2b, y2b,
                                               fill=cfg_e["cor"], outline="",
                                               tags=drag_tag)
                    item_txt = c.create_text(x_px, y_px + blk_h//2,
                                              text=cfg_e["label"],
                                              fill=cfg_e["cor_txt"],
                                              font=("Segoe UI Semibold", 8),
                                              anchor="center", tags=drag_tag)
                    if is_first:
                        self._editor_drag_items[key] = {"rect": rect, "txt": item_txt,
                                                         "type": "block",
                                                         "y1b_off": 0, "blk_h": blk_h,
                                                         "blk_w": blk_w}

        self._drag_data = {"key": None, "ox": 0, "oy": 0}
        c.bind("<ButtonPress-1>",   self._editor_drag_start)
        c.bind("<B1-Motion>",       self._editor_drag_move)
        c.bind("<ButtonRelease-1>", self._editor_drag_end)

    def _editor_hit_key(self, event):
        # só a 1ª coluna é interativa
        lx0      = getattr(self, "_editor_label_x0_px", 0.0)
        lw_px    = getattr(self, "_editor_label_w_px", float(self.canvas_editor["width"]))
        if event.x < lx0 or event.x > lx0 + lw_px:
            return None
        c = self.canvas_editor
        items = c.find_overlapping(event.x - 3, event.y - 3, event.x + 3, event.y + 3)
        for item in reversed(items):
            tags = c.gettags(item)
            for t in tags:
                if t.startswith("drag_"):
                    return t[5:]
        return None

    def _editor_drag_start(self, event):
        key = self._editor_hit_key(event)
        if not key:
            return
        self._drag_data = {"key": key, "ox": event.x, "oy": event.y}
        self.canvas_editor.config(cursor="fleur")

    def _editor_drag_move(self, event):
        key = self._drag_data.get("key")
        if not key:
            return
        c  = self.canvas_editor
        sx = self._editor_scale_x
        sy = self._editor_scale_y
        W  = int(c["width"])
        H  = int(c["height"])
        info = self._editor_drag_items.get(key, {})

        lx0   = getattr(self, "_editor_label_x0_px", 0.0)
        ly0   = getattr(self, "_editor_label_y0_px", 0.0)
        lw_px = getattr(self, "_editor_label_w_px", float(W))
        lh_px = getattr(self, "_editor_label_h_px", float(H))
        if info.get("type") == "hline":
            dy    = event.y - self._drag_data["oy"]
            orig_y_px = int(ly0 + float(self._layout_elementos[key]["y_mm"]) * sy)
            new_y = max(int(ly0)+2, min(int(ly0+lh_px)-2, orig_y_px + dy))
            c.coords(info["line"], int(lx0)+2, new_y, int(lx0+lw_px)-2, new_y)
            c.coords(info["hit"],  int(lx0)+2, new_y-6, int(lx0+lw_px)-2, new_y+6)
            c.coords(info["lbl"],  int(lx0+lw_px/2), new_y-8)
        else:
            dx = event.x - self._drag_data["ox"]
            dy = event.y - self._drag_data["oy"]
            x_orig_px = int(lx0 + float(self._layout_elementos[key]["x_mm"]) * sx)
            y_orig_px = int(ly0 + float(self._layout_elementos[key]["y_mm"]) * sy)
            blk_h = info.get("blk_h", 14)
            blk_w = info.get("blk_w", 40)
            nx = max(int(lx0)+4, min(int(lx0+lw_px)-4, x_orig_px + dx))
            ny = max(int(ly0)+2, min(int(ly0+lh_px)-blk_h-2, y_orig_px + dy))
            if info.get("rect"):
                c.coords(info["rect"], nx-blk_w//2, ny, nx+blk_w//2, ny+blk_h)
            if info.get("txt"):
                c.coords(info["txt"], nx, ny+blk_h//2)

    def _editor_drag_end(self, event):
        key = self._drag_data.get("key")
        if not key:
            return
        c  = self.canvas_editor
        sx = self._editor_scale_x
        sy = self._editor_scale_y
        larg_mm = self._dims_mm.get("largura_mm", 90.0)
        alt_mm  = self._dims_mm.get("altura_mm",  30.0)
        info = self._editor_drag_items.get(key, {})

        lx0   = getattr(self, "_editor_label_x0_px", 0.0)
        ly0   = getattr(self, "_editor_label_y0_px", 0.0)
        if info.get("type") == "hline":
            dy = event.y - self._drag_data["oy"]
            y_orig_mm = float(self._layout_elementos[key]["y_mm"])
            new_y_mm  = round(max(0.0, min(alt_mm, y_orig_mm + dy / sy)), 1)
            self._layout_elementos[key]["y_mm"] = new_y_mm
        else:
            dx = event.x - self._drag_data["ox"]
            dy = event.y - self._drag_data["oy"]
            x_orig_mm = float(self._layout_elementos[key]["x_mm"])
            y_orig_mm = float(self._layout_elementos[key]["y_mm"])
            self._layout_elementos[key]["x_mm"] = round(
                max(0.0, min(larg_mm, x_orig_mm + dx / sx)), 1)
            self._layout_elementos[key]["y_mm"] = round(
                max(0.0, min(alt_mm,  y_orig_mm + dy / sy)), 1)

        self._drag_data = {"key": None, "ox": 0, "oy": 0}
        c.config(cursor="crosshair")
        self._salvar_layout()
        self._desenhar_editor()
        self._atualizar_preview_etiqueta()

    # ── Pré-visualização ──────────────────────────────────────────────────────

    def _atualizar_preview_etiqueta(self, produto=None):
        if not hasattr(self, "canvas_preview"):
            return
        if produto is None:
            sel = self.tree.selection()
            if sel:
                idx = self.tree.index(sel[0])
                if 0 <= idx < len(self.produtos):
                    produto = self.produtos[idx]
            elif self.produtos:
                produto = self.produtos[-1]
        self._desenhar_preview_etiqueta(produto)

    def _desenhar_preview_etiqueta(self, produto):
        c = self.canvas_preview
        c.delete("all")

        larg_mm = self._dims_mm.get("largura_mm", 90.0)
        alt_mm  = self._dims_mm.get("altura_mm",  30.0)

        MAX_PW, MAX_PH = 320, 160
        ratio = larg_mm / max(alt_mm, 0.1)
        if ratio >= MAX_PW / MAX_PH:
            pw = MAX_PW
            ph = max(30, int(MAX_PW / ratio))
        else:
            ph = MAX_PH
            pw = max(60, int(MAX_PH * ratio))
        c.config(width=pw, height=ph)
        sx = pw / larg_mm
        sy = ph / alt_mm

        if not produto:
            c.create_text(pw / 2, ph / 2,
                           text="Adicione um produto\npara ver a etiqueta",
                           fill=COR["muted"], font=("Segoe UI", 9), justify="center")
            return

        empresa = remover_acentos(self.cfg.get("empresa", "") or "EMPRESA").upper()[:30]
        nome    = remover_acentos(produto["nome"]).upper()[:40]
        preco   = produto["preco"]
        codigo  = produto.get("codigo", "")

        el = self._layout_elementos
        anchor_map = {"center": "n", "left": "nw", "right": "ne"}

        # empresa
        emp = el.get("empresa", {})
        if emp.get("ativo", True):
            x_e = float(emp.get("x_mm", 45.0)) * sx
            y_e = float(emp.get("y_mm",  1.7)) * sy
            s_e = max(6, int(float(emp.get("tamanho_mm", 4.0)) * sy))
            a_e = anchor_map.get(emp.get("alinha", "center"), "n")
            c.create_text(x_e, y_e, text=empresa, anchor=a_e,
                           font=("Arial", s_e, "bold"), fill="black")

        # linha
        lin = el.get("linha", {})
        if lin.get("ativo", True) and lin.get("visivel", True):
            y_l = float(lin.get("y_mm", 6.5)) * sy
            c.create_line(2 * sx, y_l, pw - 2 * sx, y_l, fill="black", width=1)

        # nome
        nom = el.get("nome", {})
        if nom.get("ativo", True):
            x_n = float(nom.get("x_mm", 45.0)) * sx
            y_n = float(nom.get("y_mm",  8.2)) * sy
            s_n = max(6, int(float(nom.get("tamanho_mm", 3.2)) * sy))
            a_n = anchor_map.get(nom.get("alinha", "center"), "n")
            c.create_text(x_n, y_n, text=nome, anchor=a_n,
                           font=("Arial", s_n, "bold"), fill="black")

        # preço
        pre = el.get("preco", {})
        if pre.get("ativo", True):
            x_p = float(pre.get("x_mm", 45.0)) * sx
            y_p = float(pre.get("y_mm", 12.5)) * sy
            s_p = max(6, int(float(pre.get("tamanho_mm", 14.7)) * sy))
            a_p = anchor_map.get(pre.get("alinha", "center"), "n")
            c.create_text(x_p, y_p, text=preco, anchor=a_p,
                           font=("Arial", s_p, "bold"), fill="black")

        # código
        cod_el = el.get("codigo", {})
        if cod_el.get("ativo", False) and codigo:
            x_c = float(cod_el.get("x_mm", 45.0)) * sx
            y_c = float(cod_el.get("y_mm", 26.5)) * sy
            s_c = max(6, int(float(cod_el.get("tamanho_mm", 2.5)) * sy))
            a_c = anchor_map.get(cod_el.get("alinha", "center"), "n")
            c.create_text(x_c, y_c, text=codigo, anchor=a_c,
                           font=("Arial", s_c), fill="#555555")

        # texto fixo
        txf = el.get("texto_fixo", {})
        if txf.get("ativo", False):
            txt_val = remover_acentos(txf.get("texto", "")).upper()
            if txt_val:
                x_t = float(txf.get("x_mm", 45.0)) * sx
                y_t = float(txf.get("y_mm",  1.0)) * sy
                s_t = max(6, int(float(txf.get("tamanho_mm", 2.5)) * sy))
                a_t = anchor_map.get(txf.get("alinha", "center"), "n")
                c.create_text(x_t, y_t, text=txt_val, anchor=a_t,
                               font=("Arial", s_t), fill="#9C27B0")

        # barcode (representação visual)
        bar_el = el.get("barcode", {})
        if bar_el.get("ativo", False):
            y_b  = float(bar_el.get("y_mm",  22.0)) * sy
            h_b  = max(4, float(bar_el.get("tamanho_mm", 5.0)) * sy)
            x1_b = pw_px * 0.05
            x2_b = pw_px * 0.95
            c.create_rectangle(x1_b, y_b, x2_b, y_b + h_b, fill="#333333", outline="")
            # linhas de barcode simuladas
            import random; random.seed(42)
            step = (x2_b - x1_b) / 40
            for bi in range(40):
                if random.random() > 0.5:
                    bx = x1_b + bi * step
                    c.create_rectangle(bx, y_b, bx + step * 0.6, y_b + h_b,
                                        fill="#FFFFFF", outline="")
            # texto do código abaixo
            c.create_text((x1_b + x2_b) / 2, y_b + h_b + 2,
                           text="▐▌▐▌▐▌ CÓDIGO DE BARRAS", font=("Arial", 5),
                           fill="#333333", anchor="n")

    # ── Aba Configurações ─────────────────────────────────────────────────────

    def _build_aba_config(self, frm):
        cfg_wrap = ttk.Frame(frm, style="Surface.TFrame")
        cfg_wrap.pack(fill="both", expand=True, padx=24, pady=22)

        ttk.Label(cfg_wrap, text="CREDENCIAIS DA API",
                  style="SectionTitle.TLabel").grid(row=0, column=0, columnspan=2,
                                                     sticky="w", pady=(0, 10))

        campos = [
            ("Access Token",        "access_token", True),
            ("Secret Access Token", "secret_token", True),
            ("Nome da empresa",     "empresa",      False),
            ("URL base da API",     "api_base_url", False),
        ]
        self.cfg_vars = {}
        for i, (label, key, secret) in enumerate(campos, start=1):
            ttk.Label(cfg_wrap, text=label, style="Muted.TLabel").grid(
                row=i, column=0, sticky="w", pady=7, padx=(0, 14))
            var = tk.StringVar(value=self.cfg.get(key, ""))
            ttk.Entry(cfg_wrap, textvariable=var, width=44,
                      show="•" if secret else "").grid(row=i, column=1, sticky="w", pady=7)
            self.cfg_vars[key] = var

        dica_row = len(campos) + 1
        ttk.Label(cfg_wrap,
                  text="Dica: se a URL padrão não funcionar, tente o domínio que aparece\n"
                       "na barra de endereço do seu GestãoClick (ex: https://suaempresa.com.br/api)",
                  style="Muted.TLabel", justify="left", foreground=COR["muted"]
                  ).grid(row=dica_row, column=1, sticky="w", pady=(2, 18))

        ttk.Separator(cfg_wrap, orient="horizontal").grid(
            row=dica_row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        ttk.Label(cfg_wrap, text="IMPRESSORA",
                  style="SectionTitle.TLabel").grid(row=dica_row + 2, column=0,
                                                     columnspan=2, sticky="w", pady=(0, 10))

        row_imp = dica_row + 3
        ttk.Label(cfg_wrap, text="Impressora", style="Muted.TLabel").grid(
            row=row_imp, column=0, sticky="w", padx=(0, 14), pady=7)
        self.var_impressora = tk.StringVar(value=self.cfg.get("impressora", ""))
        self.combo_imp = ttk.Combobox(cfg_wrap, textvariable=self.var_impressora,
                                       width=41, state="readonly")
        self.combo_imp.grid(row=row_imp, column=1, sticky="w", pady=7)
        self.cfg_vars["impressora"] = self.var_impressora

        # DPI
        row_dpi = row_imp + 1
        ttk.Label(cfg_wrap, text="DPI da impressora", style="Muted.TLabel").grid(
            row=row_dpi, column=0, sticky="w", padx=(0, 14), pady=7)
        self.var_dpi = tk.IntVar(value=int(self.cfg.get("dpi", DPI_PADRAO)))
        combo_dpi = ttk.Combobox(cfg_wrap, textvariable=self.var_dpi,
                                  values=[203, 300], width=8, state="readonly")
        combo_dpi.grid(row=row_dpi, column=1, sticky="w", pady=7)
        ttk.Label(cfg_wrap, text="  (203 dpi = padrão Elgin / Zebra)",
                  style="Muted.TLabel").grid(row=row_dpi, column=1, sticky="e", pady=7)

        self.var_sync_auto = tk.BooleanVar(value=self.cfg.get("sync_auto", True))
        ttk.Checkbutton(cfg_wrap,
                         text="Sincronizar produtos automaticamente ao abrir o programa",
                         variable=self.var_sync_auto
                         ).grid(row=row_dpi + 1, column=1, sticky="w", pady=(6, 0))

        frm_cfg_btns = ttk.Frame(cfg_wrap, style="Surface.TFrame")
        frm_cfg_btns.grid(row=row_dpi + 2, column=1, sticky="w", pady=(10, 0))
        ttk.Button(frm_cfg_btns, text="🔄  Atualizar lista", style="Secondary.TButton",
                   command=self._atualizar_impressoras).pack(side="left")

        ttk.Button(cfg_wrap, text="Salvar configurações", style="Primary.TButton",
                   command=self.salvar_cfg).grid(row=row_dpi + 3, column=1,
                                                  sticky="w", pady=(22, 0))

    # ══════════════════════════ Helpers ══════════════════════════

    def _atualizar_impressoras(self):
        lista = listar_impressoras()
        self.combo_imp["values"] = lista
        atual = self.cfg.get("impressora", "")
        if atual in lista:
            self.var_impressora.set(atual)
        elif lista:
            self.var_impressora.set(lista[0])

    def _atualizar_total(self):
        total = sum(p["qtd"] for p in self.produtos)
        self.lbl_total.config(text=f"Total: {total} etiqueta(s)")

    def _atualizar_label_cache(self):
        n     = len(self.cache.get("produtos", {}))
        quando = self.cache.get("atualizado_em", "")
        if n:
            self.lbl_cache.config(text=f"📦  {n} produtos em cache  ·  sincronizado em {quando}")
        else:
            self.lbl_cache.config(
                text="⚠️  Nenhum produto em cache — clique em 'Sincronizar produtos'.")

    def salvar_cfg(self):
        for k, v in self.cfg_vars.items():
            self.cfg[k] = v.get().strip()
        self.cfg["sync_auto"] = self.var_sync_auto.get()
        novo_dpi = int(self.var_dpi.get())
        if novo_dpi != self._dpi:
            self._dpi = novo_dpi
            self.cfg["dpi"] = novo_dpi
        salvar_config(self.cfg)
        messagebox.showinfo("Salvo", "Configurações salvas!")

    # ══════════════════════════ Sincronização ══════════════════════════

    def iniciar_sync(self, silencioso=False):
        at       = self.cfg.get("access_token", "").strip()
        st       = self.cfg.get("secret_token", "").strip()
        base_url = self.cfg.get("api_base_url", "").strip() or DEFAULT_CFG["api_base_url"]
        if not at or not st:
            if not silencioso:
                messagebox.showwarning("Tokens ausentes",
                                       "Configure os tokens na aba Configurações antes de sincronizar.")
            return

        self.sync_queue  = queue.Queue()
        self.sync_cancel = threading.Event()

        if silencioso:
            self._iniciar_sync_silencioso(periodico=False)
            return

        win = tk.Toplevel(self.root)
        win.title("Sincronizando produtos")
        win.configure(bg=COR["surface"])
        win.resizable(False, False)
        win.grab_set()
        self.sync_win = win

        pad = ttk.Frame(win, style="Surface.TFrame")
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        ttk.Label(pad, text="🔄  Buscando produtos na API do GestãoClick...",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        lbl_prog = ttk.Label(pad, text="Página 0 / ?  —  0 produtos", style="Muted.TLabel")
        lbl_prog.pack(anchor="w", pady=(0, 8))
        bar = ttk.Progressbar(pad, mode="determinate", length=340)
        bar.pack(pady=(0, 16))

        def cancelar():
            self.sync_cancel.set()
            win.destroy()

        ttk.Button(pad, text="Cancelar", style="Secondary.TButton", command=cancelar).pack()
        win.protocol("WM_DELETE_WINDOW", cancelar)

        thread = threading.Thread(
            target=sincronizar_produtos,
            args=(base_url, at, st, self.sync_queue, self.sync_cancel),
            daemon=True,
        )
        thread.start()
        self._poll_sync(lbl_prog, bar, win)

    def _sync_silencioso(self):
        self._iniciar_sync_silencioso(periodico=False)

    def _iniciar_sync_silencioso(self, periodico=False):
        at       = self.cfg.get("access_token", "").strip()
        st       = self.cfg.get("secret_token", "").strip()
        base_url = self.cfg.get("api_base_url", "").strip() or DEFAULT_CFG["api_base_url"]
        if not at or not st:
            return
        self.sync_queue  = queue.Queue()
        self.sync_cancel = threading.Event()
        self.lbl_cache.config(text="🔄  Sincronizando...")
        thread = threading.Thread(
            target=sincronizar_produtos,
            args=(base_url, at, st, self.sync_queue, self.sync_cancel),
            daemon=True,
        )
        thread.start()
        self._poll_sync_silencioso(periodico=periodico)

    def _poll_sync_silencioso(self, periodico=False):
        try:
            while True:
                tipo, dado = self.sync_queue.get_nowait()
                if tipo == "concluido":
                    self.cache = carregar_cache()
                    self._atualizar_label_cache()
                    return
                elif tipo == "erro":
                    self._atualizar_label_cache()
                    origem = "Sync periódico" if periodico else "Sync automático"
                    messagebox.showwarning("Erro na sincronização",
                                           f"{origem} falhou:\n{dado}\n\n"
                                           "Verifique tokens e conexão.")
                    return
                elif tipo == "cancelado":
                    self._atualizar_label_cache()
                    return
        except queue.Empty:
            pass
        self.root.after(200, lambda: self._poll_sync_silencioso(periodico=periodico))

    def _agendar_sync_periodico(self):
        self._job_periodico = self.root.after(10 * 60 * 1000, self._executar_sync_periodico)

    def _executar_sync_periodico(self):
        at = self.cfg.get("access_token", "").strip()
        st = self.cfg.get("secret_token", "").strip()
        if at and st:
            self._iniciar_sync_silencioso(periodico=True)
        self._agendar_sync_periodico()

    def _poll_sync(self, lbl_prog, bar, win):
        try:
            while True:
                tipo, dado = self.sync_queue.get_nowait()
                if tipo == "progresso":
                    pagina, total_paginas, count = dado
                    bar["maximum"] = total_paginas or 1
                    bar["value"]   = pagina
                    lbl_prog.config(text=f"Página {pagina} / {total_paginas}  —  {count} produtos")
                elif tipo == "concluido":
                    count, quando = dado
                    self.cache = carregar_cache()
                    self._atualizar_label_cache()
                    win.destroy()
                    messagebox.showinfo("Sincronizado",
                                        f"{count} produtos sincronizados com sucesso!")
                    return
                elif tipo == "erro":
                    win.destroy()
                    messagebox.showerror("Erro na sincronização", dado)
                    return
                elif tipo == "cancelado":
                    return
        except queue.Empty:
            pass
        if win.winfo_exists():
            self.root.after(150, lambda: self._poll_sync(lbl_prog, bar, win))

    # ══════════════════════════ Busca por nome ══════════════════════════

    def _buscar_por_nome(self):
        termo = self.entry_busca_nome.get().strip()
        if len(termo) < 2:
            return
        self._abrir_busca_nome()

    def _abrir_busca_nome(self):
        termo = self.entry_busca_nome.get().strip().lower()
        if not termo:
            return

        produtos_cache = self.cache.get("produtos", {})
        if not produtos_cache:
            messagebox.showwarning("Sem cache", "Sincronize os produtos primeiro.")
            return

        vistos = set()
        resultados = []
        for cod, p in produtos_cache.items():
            chave = (p["nome"], p["valor_venda"])
            if chave in vistos:
                continue
            if termo in p["nome"].lower():
                vistos.add(chave)
                resultados.append((cod, p))

        if not resultados:
            messagebox.showinfo("Sem resultados",
                                f"Nenhum produto encontrado para '{termo}'.")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Resultados para '{termo}'")
        win.configure(bg=COR["surface"])
        win.geometry("640x420")
        win.grab_set()

        pad_f = ttk.Frame(win, style="Surface.TFrame")
        pad_f.pack(fill="both", expand=True, padx=18, pady=16)

        ttk.Label(pad_f, text=f"{len(resultados)} produto(s) encontrado(s)",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))

        card_r = RoundedCard(pad_f, bg_color=COR["surface"], page_bg=COR["surface"], radius=12)
        card_r.pack(fill="both", expand=True, pady=(0, 12))

        cols = ("codigo", "nome", "preco")
        tree_r = ttk.Treeview(card_r.body, columns=cols, show="headings", selectmode="browse")
        tree_r.heading("codigo", text="CÓDIGO")
        tree_r.heading("nome",   text="NOME")
        tree_r.heading("preco",  text="PREÇO")
        tree_r.column("codigo", width=90,  anchor="center")
        tree_r.column("nome",   width=360, anchor="w")
        tree_r.column("preco",  width=100, anchor="center")
        tree_r.tag_configure("odd",  background=COR["surface"])
        tree_r.tag_configure("even", background=COR["surface2"])
        sb_r = ttk.Scrollbar(card_r.body, orient="vertical", command=tree_r.yview)
        tree_r.configure(yscrollcommand=sb_r.set)
        tree_r.pack(side="left", fill="both", expand=True)
        sb_r.pack(side="right", fill="y")

        for i, (cod, p) in enumerate(resultados):
            try:
                preco_fmt = f"R${float(str(p['valor_venda']).replace(',', '.')):.2f}".replace(".", ",")
            except Exception:
                preco_fmt = p['valor_venda']
            tag = "even" if i % 2 == 0 else "odd"
            tree_r.insert("", "end", iid=cod, tags=(tag,),
                          values=(p["codigo_interno"] or cod, p["nome"], preco_fmt))

        frm_bot = ttk.Frame(pad_f, style="Surface.TFrame")
        frm_bot.pack(fill="x")

        ttk.Label(frm_bot, text="Qtd:", style="Muted.TLabel").pack(side="left")
        spin_r = ttk.Spinbox(frm_bot, from_=1, to=999, width=5, font=("Segoe UI", 10))
        spin_r.set(1)
        spin_r.pack(side="left", padx=8)

        def adicionar_selecionado():
            sel = tree_r.selection()
            if not sel:
                messagebox.showwarning("Atenção", "Selecione um produto.")
                return
            cod_key = sel[0]
            p = produtos_cache.get(cod_key)
            if not p:
                return
            try:
                qtd = int(spin_r.get())
                if qtd < 1:
                    qtd = 1
            except Exception:
                qtd = 1
            nome  = p.get("nome", "—")
            preco = p.get("valor_venda", "0")
            try:
                preco_fmt = f"R${float(str(preco).replace(',', '.')):.2f}".replace(".", ",")
            except Exception:
                preco_fmt = f"R${preco}"
            cod_display = p.get("codigo_interno") or cod_key
            for i, item in enumerate(self.produtos):
                if item["codigo"] == cod_display:
                    self.produtos[i]["qtd"] += qtd
                    self._refresh_tree()
                    self.lbl_status.config(
                        text=f"Qtd atualizada para {self.produtos[i]['qtd']} ✓",
                        style="StatusOk.TLabel")
                    win.destroy()
                    return
            self.produtos.append({"codigo": cod_display, "nome": nome,
                                   "preco": preco_fmt, "qtd": qtd})
            self._refresh_tree()
            self.lbl_status.config(text=f"'{nome[:30]}' adicionado ✓", style="StatusOk.TLabel")
            self.entry_busca_nome.delete(0, "end")
            win.destroy()

        ttk.Button(frm_bot, text="＋  Adicionar à lista", style="Primary.TButton",
                   command=adicionar_selecionado).pack(side="left", padx=(6, 8))
        ttk.Button(frm_bot, text="Fechar", style="Secondary.TButton",
                   command=win.destroy).pack(side="right")
        tree_r.bind("<Double-1>", lambda e: adicionar_selecionado())

    # ══════════════════════════ Produtos na lista ══════════════════════════

    def adicionar_produto(self):
        codigo = self.entry_cod.get().strip()
        if not codigo:
            messagebox.showwarning("Atenção", "Informe o código do produto.")
            return
        try:
            qtd = int(self.spin_qtd.get())
            if qtd < 1:
                qtd = 1
        except Exception:
            qtd = 1

        for i, p in enumerate(self.produtos):
            if p["codigo"] == codigo:
                self.produtos[i]["qtd"] += qtd
                self._refresh_tree()
                self.lbl_status.config(
                    text=f"Qtd atualizada para {self.produtos[i]['qtd']} ✓",
                    style="StatusOk.TLabel")
                self.entry_cod.delete(0, "end")
                self.spin_qtd.set(1)
                return

        produtos_cache = self.cache.get("produtos", {})
        prod = produtos_cache.get(codigo)

        if not prod:
            if not produtos_cache:
                messagebox.showwarning(
                    "Sem cache",
                    "Nenhum produto sincronizado ainda.\nClique em '🔄 Sincronizar produtos' primeiro.")
                self.lbl_status.config(text="Cache vazio — sincronize primeiro.",
                                        style="StatusErr.TLabel")
            else:
                messagebox.showerror(
                    "Não encontrado",
                    f"Produto com código '{codigo}' não encontrado no cache.\n"
                    "Se o produto é novo, sincronize novamente.")
                self.lbl_status.config(text="Não encontrado.", style="StatusErr.TLabel")
            return

        nome  = prod.get("nome", "—")
        preco = prod.get("valor_venda", "0")
        try:
            preco_fmt = f"R${float(str(preco).replace(',', '.')):.2f}".replace(".", ",")
        except Exception:
            preco_fmt = f"R${preco}"

        self.produtos.append({"codigo": codigo, "nome": nome, "preco": preco_fmt, "qtd": qtd})
        self._refresh_tree()
        self.lbl_status.config(text=f"'{nome[:30]}' adicionado ✓", style="StatusOk.TLabel")
        self.entry_cod.delete(0, "end")
        self.spin_qtd.set(1)
        # delay de 80ms para scanner USB: o leitor pode ainda estar processando Enter
        self.root.after(80, self.entry_cod.focus_set)

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for i, p in enumerate(self.produtos):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end",
                              values=(p["codigo"], p["nome"], p["preco"], p["qtd"]),
                              tags=(tag,))
        self._atualizar_total()
        self._atualizar_preview_etiqueta()

    def editar_qtd(self, event=None):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um produto na lista.")
            return
        idx  = self.tree.index(sel[0])
        prod = self.produtos[idx]

        win = tk.Toplevel(self.root)
        win.title("Editar quantidade")
        win.configure(bg=COR["surface"])
        win.resizable(False, False)
        win.grab_set()

        pad_f = ttk.Frame(win, style="Surface.TFrame")
        pad_f.pack(fill="both", expand=True, padx=22, pady=18)

        ttk.Label(pad_f, text=f"Produto: {prod['nome'][:40]}",
                  style="SectionTitle.TLabel").pack(anchor="w", pady=(0, 10))
        frm = ttk.Frame(pad_f, style="Surface.TFrame")
        frm.pack(anchor="w")
        ttk.Label(frm, text="Quantidade:", style="Muted.TLabel").pack(side="left")
        spin = ttk.Spinbox(frm, from_=1, to=999, width=6, font=("Segoe UI", 11))
        spin.set(prod["qtd"])
        spin.pack(side="left", padx=8)

        def confirmar():
            try:
                nova = int(spin.get())
                if nova < 1:
                    nova = 1
            except Exception:
                nova = 1
            self.produtos[idx]["qtd"] = nova
            self._refresh_tree()
            win.destroy()

        ttk.Button(pad_f, text="Confirmar", style="Primary.TButton",
                   command=confirmar).pack(pady=(16, 0))
        spin.focus()
        spin.bind("<Return>", lambda e: confirmar())

    def remover_selecionado(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Atenção", "Selecione um produto para remover.")
            return
        idx = self.tree.index(sel[0])
        self.produtos.pop(idx)
        self._refresh_tree()
        self.lbl_status.config(text="Produto removido.", style="StatusMuted.TLabel")

    def limpar_tudo(self):
        if not self.produtos:
            return
        if messagebox.askyesno("Confirmar", "Remover todos os produtos da lista?"):
            self.produtos.clear()
            self._refresh_tree()
            self.lbl_status.config(text="Lista limpa.", style="StatusMuted.TLabel")

    # ══════════════════════════ Impressão ══════════════════════════

    def imprimir_todos(self):
        if not self.produtos:
            messagebox.showwarning("Atenção", "Adicione pelo menos um produto à lista.")
            return
        impressora = self.var_impressora.get().strip()
        if not impressora:
            messagebox.showwarning("Atenção", "Selecione a impressora na aba Configurações.")
            return
        empresa     = self.cfg.get("empresa", "") or "EMPRESA"
        num_col     = max(1, self._dims_mm.get("num_colunas", 1))
        erros       = []
        total_enviado = 0

        if num_col > 1:
            # ── Multi-coluna: todos os produtos na mesma etiqueta ──
            # Expande lista respeitando qtd de cada produto
            expandido = []
            for p in self.produtos:
                for _ in range(max(1, p["qtd"])):
                    expandido.append(p)

            # Agrupa em batches de num_col (uma linha de etiquetas por batch)
            batches = [expandido[i:i+num_col] for i in range(0, len(expandido), num_col)]
            for batch in batches:
                # Completa colunas vazias com None se batch incompleto
                while len(batch) < num_col:
                    batch.append(None)
                try:
                    zpl = gerar_zpl_multicol(
                        batch, empresa, self._dims_mm,
                        self._layout_elementos, self._dpi,
                        num_col_cfg=num_col,
                    )
                    imprimir_zpl(zpl, impressora)
                    total_enviado += sum(1 for b in batch if b is not None)
                except Exception as ex:
                    erros.append(str(ex))
        else:
            # ── Coluna única: 1 produto por label ──
            for p in self.produtos:
                try:
                    zpl = gerar_zpl(
                        p["nome"], p["preco"], empresa, p["qtd"],
                        elementos=self._layout_elementos,
                        dims_mm=self._dims_mm,
                        dpi=self._dpi,
                        codigo=p.get("codigo", ""),
                    )
                    imprimir_zpl(zpl, impressora)
                    total_enviado += p["qtd"]
                except Exception as ex:
                    erros.append(f"{p['codigo']}: {ex}")

        if erros:
            messagebox.showerror("Erros ao imprimir", "\n".join(erros))
        else:
            registrar_historico(self.produtos, empresa)
            self._carregar_historico_ui()
            self.lbl_imp_status.config(
                text=f"{total_enviado} etiqueta(s) enviadas ✓",
                style="StatusOk.TLabel")

    def imprimir_teste(self):
        impressora = self.var_impressora.get().strip()
        if not impressora:
            messagebox.showwarning("Atenção", "Selecione a impressora na aba Configurações.")
            return
        empresa = self.cfg.get("empresa", "MINHA EMPRESA") or "MINHA EMPRESA"
        num_col = max(1, self._dims_mm.get("num_colunas", 1))
        try:
            if num_col > 1:
                # Preenche todas as colunas com produtos de teste numerados
                prod_teste = [
                    {"nome": f"TESTE {i+1}", "preco": f"R${(i+1)*9:.2f}".replace(".", ","),
                     "codigo": f"T00{i+1}"}
                    for i in range(num_col)
                ]
                zpl = gerar_zpl_multicol(
                    prod_teste, empresa, self._dims_mm,
                    self._layout_elementos, self._dpi,
                    num_col_cfg=num_col,
                )
            else:
                zpl = gerar_zpl(
                    "PRODUTO TESTE 123", "9.99", empresa, qtd=1,
                    elementos=self._layout_elementos,
                    dims_mm=self._dims_mm,
                    dpi=self._dpi,
                    codigo="COD-TESTE",
                )
            imprimir_zpl(zpl, impressora)
            self.lbl_imp_status.config(text="Etiqueta de teste enviada ✓", style="StatusOk.TLabel")
        except Exception as ex:
            messagebox.showerror("Erro de impressão", str(ex))


if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(780, 800)
    root.geometry("880x920")
    app = App(root)
    root.update_idletasks()
    aplicar_cantos_arredondados_janela(root)
    root.mainloop()
