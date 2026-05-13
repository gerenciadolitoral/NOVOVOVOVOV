"""
Card de Monitoramento de Reservatórios — Bacia do Litoral
COGERH / GRLITORAL

Execução local:
    pip install streamlit pandas pillow requests numpy chardet
    streamlit run app.py
"""

import io
import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from engine import (
    df_to_json_safe,
    generate_pages,
    load_data_from_sheets,
    process_df,
    sheets_to_csv_url,
)

# ─────────────────────────────────────────────
# Configuração fixa — Bacia do Litoral
# ─────────────────────────────────────────────
BACIA_FILTRO       = "Litoral"
GERENCIA_FILTRO    = "GRLITORAL"

DEFAULT_SHEET_URL  = "https://docs.google.com/spreadsheets/d/15RrQ7ccfZITr2VslQGi1yglLLabKMVFTv5mUepjcW7g"
DEFAULT_GID        = "0"

BASE_DIR           = Path(__file__).parent
CAV_CSV_PATH       = BASE_DIR / "cav.csv"

# ─────────────────────────────────────────────
# Página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Cards Litoral — COGERH",
    page_icon="💧",
    layout="centered",
)

st.title("💧 Cards de Monitoramento · Bacia do Litoral")
st.caption("COGERH — GRLITORAL | Geração local, sem dependência de servidor externo")

# ─────────────────────────────────────────────
# Sidebar — configurações
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações")

    sheet_url = st.text_input(
        "Link da planilha Google Sheets",
        value=DEFAULT_SHEET_URL,
        help="Cole o link completo ou apenas o ID da planilha.",
    )
    gid = st.text_input(
        "GID da aba",
        value=DEFAULT_GID,
        help="Número da aba (gid=...). Use 0 para a primeira aba.",
    )

    st.divider()
    st.subheader("🖼️ Formato de saída")

    modo = st.selectbox(
        "Modo do card",
        ["Feed (1080x1350)", "Stories (1080x1920)"],
        index=0,
    )
    formato_saida = st.selectbox(
        "Formato da imagem",
        ["PNG", "JPG", "PDF"],
        index=0,
    )
    ordenar = st.selectbox(
        "Ordenação dos reservatórios",
        [
            "Manter ordem",
            "Maior variação positiva",
            "Maior variação negativa",
            "Maior variação absoluta",
        ],
        index=0,
    )
    converter_m3 = st.checkbox(
        "Converter m³ bruto para milhões",
        value=True,
        help="Divide valores de volume por 1.000.000 para exibição.",
    )

    st.divider()
    st.subheader("📐 Lookup CAV")
    show_cav = st.checkbox("Abrir consulta CAV", value=False)

# ─────────────────────────────────────────────
# Botão principal
# ─────────────────────────────────────────────
gerar = st.button("🔄 Carregar planilha e gerar cards", type="primary", use_container_width=True)

# ─────────────────────────────────────────────
# Processamento
# ─────────────────────────────────────────────
if gerar:
    if not sheet_url.strip():
        st.error("Informe o link da planilha.")
        st.stop()

    with st.spinner("Carregando planilha..."):
        csv_url = sheets_to_csv_url(sheet_url.strip(), gid=gid.strip() or "0")
        if not csv_url:
            st.error("Link ou ID inválido.")
            st.stop()
        try:
            df_raw = load_data_from_sheets(csv_url)
        except Exception as e:
            st.error(f"Erro ao acessar a planilha: {e}")
            st.stop()

    if df_raw is None or df_raw.empty:
        st.warning("Planilha vazia ou inacessível.")
        st.stop()

    with st.spinner("Processando dados..."):
        try:
            df_proc, info = process_df(df_raw)
        except Exception as e:
            st.error(f"Erro ao processar dados: {e}")
            st.stop()

    # ── Filtrar Litoral ──────────────────────────────────────────────
    mask = pd.Series([True] * len(df_proc), index=df_proc.index)

    if "bacia" in df_proc.columns:
        mask_bacia = df_proc["bacia"].str.strip().str.lower() == BACIA_FILTRO.lower()
        mask = mask & mask_bacia

    if "gerencia" in df_proc.columns:
        mask_ger = df_proc["gerencia"].str.strip().str.upper() == GERENCIA_FILTRO.upper()
        # Aceita filtrar por bacia OU gerência (usa bacia como primário)
        if mask_bacia.any():
            mask = mask & mask_bacia
        else:
            mask = mask & mask_ger

    df_litoral = df_proc[mask].reset_index(drop=True)

    if df_litoral.empty:
        st.warning(
            f"Nenhum registro encontrado para a bacia '{BACIA_FILTRO}' na planilha. "
            "Verifique se a coluna BACIA contém 'Litoral' ou se o GID está correto."
        )
        st.stop()

    periodo = info.get("periodo", {})
    date_anterior = periodo.get("anterior", "")
    date_atual    = periodo.get("atual", "")

    st.success(
        f"✅ {len(df_litoral)} reservatórios encontrados · "
        f"Período: **{date_anterior} → {date_atual}**"
    )

    # ── Tabela resumo ────────────────────────────────────────────────
    with st.expander("📋 Dados carregados", expanded=False):
        colunas_show = [c for c in [
            "nome", "municipio", "nivel_anterior", "nivel_atual",
            "variacao_m", "percentual", "volume_atual_m3", "falta_sangrar",
        ] if c in df_litoral.columns]
        st.dataframe(df_litoral[colunas_show], use_container_width=True)

    # ── Gerar imagens ────────────────────────────────────────────────
    with st.spinner("Gerando cards..."):
        try:
            pages = generate_pages(
                df_all=df_litoral,
                mode=modo,
                date_anterior=date_anterior,
                date_atual=date_atual,
                ordenar=ordenar,
                formato="PNG",           # sempre PNG internamente; converte depois se JPG
                convert_raw_m3_to_millions=converter_m3,
            )
        except Exception as e:
            st.error(f"Erro ao gerar cards: {e}")
            st.stop()

    st.subheader(f"🖼️ Preview — {len(pages)} página(s)")
    for i, img in enumerate(pages, start=1):
        st.image(img, caption=f"Página {i}/{len(pages)}", use_container_width=True)

    # ── Download ─────────────────────────────────────────────────────
    fmt_req = formato_saida.upper()

    if fmt_req == "PDF":
        # Montar PDF A4 (2480×3508 px @ ~300 dpi) com até 2 cards por folha
        A4_W, A4_H, margin = 2480, 3508, 80
        pdf_pages: list[Image.Image] = []
        i = 0
        while i < len(pages):
            group = pages[i: i + 2]
            sheet = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))
            if len(group) == 1:
                img = group[0].convert("RGB")
                w, h = img.size
                scale = min((A4_W - 2 * margin) / w, (A4_H - 2 * margin) / h)
                ns = (int(w * scale), int(h * scale))
                sheet.paste(img.resize(ns, Image.LANCZOS),
                            ((A4_W - ns[0]) // 2, (A4_H - ns[1]) // 2))
            else:
                avail_h = (A4_H - 3 * margin) // 2
                for k, src in enumerate(group):
                    src = src.convert("RGB")
                    w, h = src.size
                    scale = min((A4_W - 2 * margin) / w, avail_h / h)
                    ns = (int(w * scale), int(h * scale))
                    y_top = margin + k * (avail_h + margin)
                    sheet.paste(src.resize(ns, Image.LANCZOS),
                                ((A4_W - ns[0]) // 2, y_top + (avail_h - ns[1]) // 2))
            pdf_pages.append(sheet)
            i += 2

        buf = io.BytesIO()
        pdf_pages[0].save(buf, format="PDF", save_all=True, append_images=pdf_pages[1:])
        buf.seek(0)
        st.download_button(
            "⬇️ Baixar PDF",
            data=buf,
            file_name="litoral_cards.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    elif len(pages) == 1:
        # Arquivo único
        buf = io.BytesIO()
        fmt_pil = "JPEG" if fmt_req == "JPG" else "PNG"
        mime    = "image/jpeg" if fmt_req == "JPG" else "image/png"
        ext     = "jpg" if fmt_req == "JPG" else "png"
        if fmt_pil == "JPEG":
            pages[0].convert("RGB").save(buf, format=fmt_pil, quality=95, optimize=True)
        else:
            pages[0].save(buf, format=fmt_pil, optimize=True)
        buf.seek(0)
        st.download_button(
            f"⬇️ Baixar card ({ext.upper()})",
            data=buf,
            file_name=f"litoral_card.{ext}",
            mime=mime,
            use_container_width=True,
        )

    else:
        # ZIP com múltiplas páginas
        fmt_pil = "JPEG" if fmt_req == "JPG" else "PNG"
        ext     = "jpg" if fmt_req == "JPG" else "png"
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for i, img in enumerate(pages, start=1):
                img_buf = io.BytesIO()
                if fmt_pil == "JPEG":
                    img.convert("RGB").save(img_buf, format=fmt_pil, quality=95, optimize=True)
                else:
                    img.save(img_buf, format=fmt_pil, optimize=True)
                img_buf.seek(0)
                zf.writestr(f"litoral_card_p{i}.{ext}", img_buf.getvalue())
        zip_buf.seek(0)
        st.download_button(
            f"⬇️ Baixar todas as páginas (ZIP)",
            data=zip_buf,
            file_name="litoral_cards.zip",
            mime="application/zip",
            use_container_width=True,
        )

# ─────────────────────────────────────────────
# Lookup CAV (opcional)
# ─────────────────────────────────────────────
if show_cav:
    st.divider()
    st.subheader("📐 Consulta CAV — Cota / Área / Volume")

    if not CAV_CSV_PATH.is_file():
        st.warning("Arquivo `cav.csv` não encontrado na pasta do app.")
    else:
        @st.cache_data(show_spinner=False)
        def load_cav():
            return pd.read_csv(CAV_CSV_PATH, sep=",", dtype=str, encoding="utf-8")

        df_cav = load_cav()
        df_cav.columns = [c.strip() for c in df_cav.columns]

        # Normalizar nome da coluna reservatório
        col_res = next(
            (c for c in df_cav.columns if c.strip().lower() in ("reservatório", "reservatorio")),
            None,
        )
        col_bacia_cav = "bacia" if "bacia" in df_cav.columns else None

        if not col_res or not col_bacia_cav:
            st.error("Colunas 'Reservatório' e 'bacia' não encontradas em cav.csv.")
        else:
            # Filtrar só Litoral
            df_cav_lit = df_cav[
                df_cav[col_bacia_cav].str.strip().str.lower() == BACIA_FILTRO.lower()
            ].copy()

            reservatorios_lit = sorted(
                df_cav_lit[col_res].dropna().astype(str).str.strip().unique().tolist()
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                res_sel = st.selectbox("Reservatório", reservatorios_lit)
            with col2:
                barrote_sel = st.number_input("Barrote", min_value=0, step=1, value=0)
            with col3:
                leitura_sel = st.number_input("Leitura", min_value=0, step=1, value=0)
            with col4:
                st.write("")
                buscar_cav = st.button("🔍 Buscar", use_container_width=True)

            if buscar_cav:
                mask_cav = (
                    (df_cav_lit[col_res].astype(str).str.strip().str.lower() == res_sel.lower())
                    & (df_cav_lit["barrote"].astype(str).str.strip() == str(int(barrote_sel)))
                    & (df_cav_lit["leitura"].astype(str).str.strip() == str(int(leitura_sel)))
                )
                resultado = df_cav_lit[mask_cav]
                if resultado.empty:
                    st.warning("Combinação não encontrada no cav.csv.")
                else:
                    row = resultado.iloc[0]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Cota (m)", row.get("cota", "N/A"))
                    c2.metric("Área (km²)", row.get("area_km2", "N/A"))
                    c3.metric("Volume (m³)", row.get("volume_m3", "N/A"))

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.divider()
st.caption(
    "COGERH · GRLITORAL — Bacia do Litoral | "
    "Execute com: `streamlit run app.py`"
)
