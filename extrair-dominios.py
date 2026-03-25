"""
Extrai texto da ultima coluna via OCR (OpenCV + Tesseract).
Render de PDF com PyMuPDF (nao requer pdf2image nem Poppler).
"""
import argparse
import os
import re
import shutil
import sys

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image, ImageDraw, ImageFont


def encontrar_tesseract(caminho_explicito=None):
    """PATH, variavel TESSERACT_CMD, ou instalacao tipica no Windows."""
    if caminho_explicito and os.path.isfile(caminho_explicito):
        return os.path.abspath(caminho_explicito)
    env = os.environ.get("TESSERACT_CMD", "").strip()
    if env and os.path.isfile(env):
        return env
    w = shutil.which("tesseract")
    if w:
        return w
    for p in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.isfile(p):
            return p
    return None


def configurar_tesseract(caminho_explicito=None):
    exe = encontrar_tesseract(caminho_explicito)
    if not exe:
        return False
    pytesseract.pytesseract.tesseract_cmd = exe
    return True


def pdf_page_to_pil(doc, page_index_0: int, zoom: float = 2.0):
    """Converte uma pagina do PDF em PIL RGB (substitui pdf2image)."""
    page = doc[page_index_0]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def detect_table_structure(image):
    """
    Detecta as linhas horizontais e verticais da tabela para identificar as células.
    Retorna o limite X da última coluna.
    """
    img_np = np.array(image)
    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    detect_vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)

    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)
    table_mask = cv2.threshold(table_mask, 0, 255, cv2.THRESH_BINARY)[1]

    cnts = cv2.findContours(detect_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    if not cnts:
        return None, None, None

    v_lines_x = sorted([cv2.boundingRect(c)[0] for c in cnts])

    if len(v_lines_x) >= 2:
        last_col_start = v_lines_x[-2]
        last_col_end = v_lines_x[-1]

        h_cnts = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h_cnts = h_cnts[0] if len(h_cnts) == 2 else h_cnts[1]
        h_lines_y = sorted([cv2.boundingRect(c)[1] for c in h_cnts])

        if h_lines_y:
            table_top = h_lines_y[0]
            table_bottom = h_lines_y[-1]
            return last_col_start, last_col_end, (table_top, table_bottom)

    return None, None, None


def extract_and_save(pdf_path, output_image_path, output_txt_path, max_pages=0):
    # lista de (numero_pagina, texto) — o numero e a pagina do PDF onde foi lido
    all_last_column_data = []

    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError:
        print(
            "[ERRO] Tesseract nao executavel. Instale: "
            "https://github.com/UB-Mannheim/tesseract/wiki "
            "ou: winget install UB-Mannheim.TesseractOCR\n"
            "Depois: --tesseract \"C:\\Program Files\\Tesseract-OCR\\tesseract.exe\" "
            "ou defina TESSERACT_CMD.",
            file=sys.stderr,
        )
        return

    doc = fitz.open(pdf_path)
    try:
        total_pages = len(doc)
        if max_pages is None or max_pages <= 0:
            pages_to_process = total_pages
        else:
            pages_to_process = min(total_pages, max_pages)
        print(f"Inicio: {pages_to_process} pagina(s) a analisar (total no PDF: {total_pages}).", flush=True)

        for page_num in range(1, pages_to_process + 1):
            print(f"[INFO] Pagina {page_num}/{pages_to_process}", flush=True)
            page_img = pdf_page_to_pil(doc, page_num - 1, zoom=2.0)

            col_start, col_end, y_range = detect_table_structure(page_img)

            if col_start is None:
                print(f"       -> sem tabela detectada nesta pagina.", flush=True)
                continue

            print(f"       -> OCR da ultima coluna...", flush=True)
            try:
                ocr_data = pytesseract.image_to_data(
                    page_img, lang="por", output_type=pytesseract.Output.DICT
                )
            except Exception:
                ocr_data = pytesseract.image_to_data(
                    page_img, lang="eng", output_type=pytesseract.Output.DICT
                )

            lines = {}
            for i in range(len(ocr_data["text"])):
                text = ocr_data["text"][i].strip()
                if not text:
                    continue

                x = ocr_data["left"][i]
                y = ocr_data["top"][i]
                w = ocr_data["width"][i]

                is_inside_col = (x >= col_start - 5) and (x + w <= col_end + 5)
                is_inside_table_y = (y >= y_range[0]) and (y <= y_range[1])

                if is_inside_col and is_inside_table_y:
                    found_line = False
                    for line_y in lines:
                        if abs(y - line_y) < 15:
                            lines[line_y].append(i)
                            found_line = True
                            break
                    if not found_line:
                        lines[y] = [i]

            for y in sorted(lines.keys()):
                indices = lines[y]
                indices.sort(key=lambda idx: ocr_data["left"][idx])

                cell_text = "".join([ocr_data["text"][idx] for idx in indices]).strip()

                header_keywords = ["NOVOS", "DOMÍNIOS", "BLOQUEIO", "PARA"]
                if any(kw in cell_text.upper() for kw in header_keywords):
                    continue

                if cell_text and "." in cell_text:
                    clean_text = cell_text.replace(" ", "")
                    if not re.search(r"\d{2}\.\d{2}\.\d{4}", clean_text) and len(clean_text) > 3:
                        all_last_column_data.append((page_num, clean_text))
    finally:
        doc.close()

    seen = set()
    dedup = []
    for pg, txt in all_last_column_data:
        k = (pg, txt)
        if k in seen:
            continue
        seen.add(k)
        dedup.append((pg, txt))
    all_last_column_data = dedup

    if not all_last_column_data:
        print(f"Nenhum conteudo de celula encontrado na ultima coluna em {pdf_path}.")
        return

    os.makedirs(os.path.dirname(output_txt_path) or ".", exist_ok=True)

    with open(output_txt_path, "w", encoding="utf-8") as f:
        for _pg, item in all_last_column_data:
            f.write(f"{item}\n")

    font_size = 18
    line_height = 25
    padding = 30
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    linhas_img = [txt for _pg, txt in all_last_column_data]
    max_w = max([len(t) * 12 for t in linhas_img]) + (padding * 2) if linhas_img else padding * 2
    img_h = (len(linhas_img) * line_height) + (padding * 2)

    img = Image.new("RGB", (int(max_w), int(img_h)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y_text = padding
    for line in linhas_img:
        draw.text((padding, y_text), line, font=font, fill=(0, 0, 0))
        y_text += line_height
    os.makedirs(os.path.dirname(output_image_path) or ".", exist_ok=True)
    img.save(output_image_path)

    paginas_com_conteudo = sorted({pg for pg, _ in all_last_column_data})
    paginas_str = ", ".join(str(p) for p in paginas_com_conteudo)
    print(
        f"Sucesso: {len(all_last_column_data)} itens extraidos. "
        f"Paginas com conteudo: {paginas_str}",
        flush=True,
    )
    print(f"TXT: {output_txt_path} | PNG: {output_image_path}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR ultima coluna (OpenCV + Tesseract)")
    parser.add_argument("pdf", help="Caminho do PDF")
    parser.add_argument(
        "--saida",
        "-o",
        default="dominios_extraidos",
        help="Pasta de saida (padrao: dominios_extraidos)",
    )
    parser.add_argument(
        "--max-paginas",
        type=int,
        default=0,
        metavar="N",
        help="Maximo de paginas (0 ou omitir = todas; padrao: 0)",
    )
    parser.add_argument(
        "--tesseract",
        default=None,
        metavar="EXE",
        help=r'Caminho para tesseract.exe (ex.: "C:\Program Files\Tesseract-OCR\tesseract.exe")',
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pdf):
        print(f"[ERRO] Ficheiro nao encontrado: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    if not configurar_tesseract(args.tesseract):
        print(
            "[ERRO] Tesseract OCR nao encontrado.\n"
            "  Instale: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  Ou: winget install UB-Mannheim.TesseractOCR\n"
            "  Depois use: --tesseract \"C:\\Program Files\\Tesseract-OCR\\tesseract.exe\"\n"
            "  Ou defina a variavel de ambiente TESSERACT_CMD para o .exe.",
            file=sys.stderr,
        )
        sys.exit(1)

    os.makedirs(args.saida, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.pdf))[0]
    out_png = os.path.join(args.saida, f"{stem}_ocr.png")
    out_txt = os.path.join(args.saida, f"{stem}_ocr.txt")

    extract_and_save(args.pdf, out_png, out_txt, max_pages=args.max_paginas)
