# Extrair domínios (OCR na última coluna)

Script em Python que converte cada página de um PDF em imagem, tenta detetar a **tabela** (OpenCV) e corre **OCR (Tesseract)** **apenas na região da última coluna** dessa tabela — **não** extrai texto das outras colunas nem fora da grelha.

O resultado são os textos lidos nessa coluna (ex.: domínios ou IPs), guardados num `.txt` e num `.png` de resumo.

### Âmbito

| Faz | Não faz |
|-----|---------|
| OCR na **última coluna** da tabela detetada | Extração das colunas do meio ou da primeira coluna |
| Uma tabela por página (quando a deteção encontra grelha) | Corpo do documento fora da tabela |

## Requisitos

- **Python 3.10+** (testado com 3.13)
- **Tesseract OCR** instalado no sistema (o `pytesseract` só chama o executável `tesseract`)

## 1. Instalar o Tesseract (Windows)

Escolha uma opção:

1. **Instalador oficial (recomendado)**  
   - [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)  
   - Instale e marque **português** (`por`) se quiser OCR em PT.

2. **winget** (linha de comandos):
   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```

Caminho típico do executável:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Se o script não encontrar o Tesseract:

- Defina a variável de ambiente **`TESSERACT_CMD`** com o caminho completo para `tesseract.exe`, **ou**
- Passe **`--tesseract`** ao correr o script (ver abaixo).

## 2. Instalar dependências Python

Na pasta do projeto:

```powershell
cd caminho\para\extrair-dominios
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Uso

```powershell
python extrair-dominios.py ".\documento.pdf"
```

*(O PDF deve conter tabelas com **várias colunas**; só a **última coluna** é processada.)*

### Saída (por defeito na pasta `dominios_extraidos/`)

| Ficheiro | Conteúdo |
|----------|----------|
| `{nome_do_pdf}_ocr.txt` | Uma linha por texto extraído **da última coluna** (só o conteúdo, sem número de página). |
| `{nome_do_pdf}_ocr.png` | Imagem com as mesmas linhas de texto. |

No **final da execução** no terminal aparece o resumo das **páginas onde houve conteúdo** na última coluna.

### Opções

| Opção | Descrição |
|-------|-----------|
| `-o`, `--saida` | Pasta de saída (predefinição: `dominios_extraidos`). |
| `--max-paginas N` | Processa no máximo **N** páginas. Com **0** (predefinição) ou omitindo, processa **todo** o PDF. |
| `--tesseract` | Caminho completo para `tesseract.exe` se não estiver no PATH. |

### Exemplos

```powershell
# PDF completo
python extrair-dominios.py ".\meu-documento.pdf"

# Só as primeiras 20 páginas
python extrair-dominios.py ".\documento.pdf" --max-paginas 20

# Pasta de saída à escolha
python extrair-dominios.py ".\documento.pdf" -o .\resultados

# Tesseract num caminho fixo
python extrair-dominios.py ".\documento.pdf" --tesseract "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Notas

- O processamento de **muitas páginas** com OCR pode ser **lento**.
- Se aparecer `Nenhuma tabela detectada` numa página, a deteção automática da grelha (OpenCV) não encontrou linhas; nessa página **não** há OCR da última coluna.
- O script **não** foi pensado para PDFs sem tabela clara nem para extrair a folha inteira — só a **última coluna** após detetar a tabela.
- Se o pacote de idioma **português** não estiver instalado no Tesseract, o script tenta **inglês** (`eng`) como alternativa.

## Estrutura relevante

```text
extrair-dominios/
  extrair-dominios.py   # script principal
  requirements.txt
  README.md
  LICENSE
```

## Licença

Ver ficheiro [LICENSE](LICENSE) (Apache 2.0).
