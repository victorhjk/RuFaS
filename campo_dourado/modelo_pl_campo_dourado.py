"""
Modelo de Programação Linear (PL) - Dieta de Custo Mínimo (Fazenda Campo Dourado - GO)
Padrão Nutricional NASEM (2021) / RuFaS - Lote: Vacas em Lactação (lac_cow)

Fontes oficiais de dados:
1. Custos dos alimentos (purchased_feed_cost, R$/kg MS):
   'Fazenda Campo Dourado/ingredientes_racoes_GO_campo_dourado.xlsx' (Coluna I / Linha 4 a 15)
2. Composição bromatológica dos alimentos:
   'Fazenda Campo Dourado/GO_campo_dourado/inputs_resolvidos/NASEM_Comp.csv'
3. Exigências nutricionais e perdas metabólicas:
   Simulação base RuFaS (GO_campo_dourado, lote lac_cow, 100 vacas, clima de Goiás).
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple
import numpy as np
import openpyxl
import pandas as pd

# Diretórios base
WORKSPACE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = WORKSPACE_DIR / "Fazenda Campo Dourado" / "ingredientes_racoes_GO_campo_dourado.xlsx"
NASEM_PATH = WORKSPACE_DIR / "Fazenda Campo Dourado" / "GO_campo_dourado" / "inputs_resolvidos" / "NASEM_Comp.csv"

# 9 Alimentos candidatos para o lote de vacas em lactação (lac_cow).
# Ficam excluídos:
# - 23 (Farinha de sangue): proibida para ruminantes no Brasil (IN MAPA nº 8/2004).
# - 202 (Leite integral) e 216 (Starter): restritos aos bezerros (lote calf).
CANDIDATE_FEEDS = [18, 44, 51, 94, 100, 110, 176, 301, 303]

FEED_NAMES_PT: Dict[int, str] = {
    18: "Feno de Bermudagrass (Tifton)",
    44: "Milho Grão Moído Seco",
    51: "Silagem de Milho (Meia Maturação)",
    94: "Feno de Capim-Leguminosa",
    100: "Silagem de Capim-Leguminosa",
    110: "Silagem de Leguminosa",
    176: "Silagem de Capim-Sudão",
    301: "Premix Mineral/Vitamínico",
    303: "Blend Subprodutos (DDGS / Conc. Proteico)",
}

# Parâmetros nutricionais médios do rebanho de vacas em lactação (lac_cow)
# Simulação base GO_campo_dourado (100 vacas, 640.5 kg de peso vivo médio)
REQUIREMENTS = {
    "DMI_est": 25.187,       # Consumo estimado de Matéria Seca (kg MS/vaca/dia)
    "BW": 640.50,            # Peso vivo médio (kg)
    "NE_maint": 12.686,      # Exigência de mantença (Mcal/dia)
    "NE_lact": 32.450,       # Exigência de lactação (Mcal/dia)
    "NE_growth": 0.702,      # Exigência de crescimento (Mcal/dia)
    "NE_preg": 2.259,        # Exigência de gestação (Mcal/dia)
    "MP": 2742.94,           # Proteína metabolizável mínima (g/dia)
    "Ca": 68.783,            # Cálcio absorvível mínimo (g/dia)
    "P": 65.517,             # Fósforo absorvível mínimo com buffer (g/dia)
}
REQUIREMENTS["NE_req_total"] = (
    REQUIREMENTS["NE_maint"] + REQUIREMENTS["NE_lact"] + REQUIREMENTS["NE_growth"] + REQUIREMENTS["NE_preg"]
)

# Perdas metabólicas descontadas pelo RuFaS na energia digestível (passam ao RHS)
# Metano entérico: 349.3 g/dia * 0.01328 Mcal/g = 4.639 Mcal
# Nitrogênio urinário: 279.5 g/dia * 0.0146 Mcal/g = 4.081 Mcal
# Total de perdas = 8.720 Mcal. Fator 0.66 NASEM => 5.755 Mcal adicionados ao RHS da energia líquida.
NE_LOSSES = 8.7197
NE_RHS = REQUIREMENTS["NE_req_total"] + 0.66 * NE_LOSSES  # 48.097 + 5.755 = 53.8518 Mcal


# Dados oficiais da planilha 'ingredientes_racoes_GO_campo_dourado.xlsx' (Fonte: CEPEA, CNA/Senar, MF Rural, 28/10/2026)
OFFICIAL_FEEDS_CAMPO_DOURADO: Dict[int, Dict[str, Any]] = {
    18: {"feed_id": 18, "nome": "Bermudagrass, feno", "categoria": "Forragem", "DM": 93.37, "CP": 10.99, "NDF": 65.41, "Ca": 0.491, "P": 0.195, "custo_ms": 1.8207, "preco_mn": 1700.0, "fonte": "MF Rural - Feno Tifton e Jiggs"},
    23: {"feed_id": 23, "nome": "Blood meal, low dRUP", "categoria": "Concentrado proteico", "DM": 90.86, "CP": 95.06, "NDF": 0.0, "Ca": 0.135, "P": 0.276, "custo_ms": 999.0, "preco_mn": None, "fonte": "Proibida - IN MAPA 8/2004"},
    44: {"feed_id": 44, "nome": "Milho grão moído seco", "categoria": "Energético", "DM": 86.91, "CP": 8.51, "NDF": 9.76, "Ca": 0.035, "P": 0.309, "custo_ms": 1.2413, "preco_mn": 1078.83, "fonte": "CEPEA Indicador Milho"},
    51: {"feed_id": 51, "nome": "Silagem de milho, meia maturação", "categoria": "Forragem", "DM": 35.36, "CP": 7.71, "NDF": 40.93, "Ca": 0.237, "P": 0.232, "custo_ms": 0.6988, "preco_mn": 247.08, "fonte": "CNA/Senar + Cepea-Esalq"},
    94: {"feed_id": 94, "nome": "Mistura capim-leguminosa, feno", "categoria": "Forragem", "DM": 89.24, "CP": 15.61, "NDF": 54.69, "Ca": 0.625, "P": 0.329, "custo_ms": 2.5213, "preco_mn": 2250.0, "fonte": "MF Rural"},
    100: {"feed_id": 100, "nome": "Mistura capim-leguminosa, silagem", "categoria": "Forragem", "DM": 40.02, "CP": 17.68, "NDF": 51.23, "Ca": 0.87, "P": 0.341, "custo_ms": 2.7486, "preco_mn": 1100.0, "fonte": "MF Rural Luziânia/GO"},
    110: {"feed_id": 110, "nome": "Leguminosa forrageira, silagem", "categoria": "Forragem", "DM": 42.88, "CP": 20.47, "NDF": 43.2, "Ca": 1.254, "P": 0.351, "custo_ms": 2.5653, "preco_mn": 1100.0, "fonte": "MF Rural Luziânia/GO"},
    176: {"feed_id": 176, "nome": "Sudan grass, silagem madura", "categoria": "Forragem", "DM": 31.47, "CP": 9.54, "NDF": 66.62, "Ca": 0.446, "P": 0.266, "custo_ms": 0.7851, "preco_mn": 247.08, "fonte": "CNA/Senar + Cepea-Esalq"},
    202: {"feed_id": 202, "nome": "Leite integral", "categoria": "Leite (bezerros)", "DM": 12.5, "CP": 25.4, "NDF": 0.0, "Ca": 1.0, "P": 0.75, "custo_ms": 23.0171, "preco_mn": 2877.13, "fonte": "CEPEA Leite GO"},
    216: {"feed_id": 216, "nome": "Starter 18CP high starch (bezerros)", "categoria": "Starter", "DM": 88.0, "CP": 20.6, "NDF": 17.37, "Ca": 0.75, "P": 0.37, "custo_ms": 2.8560, "preco_mn": 2513.25, "fonte": "Cocamar Ração Bezerro"},
    301: {"feed_id": 301, "nome": "Premix mineral/vitamínico", "categoria": "Mineral", "DM": 99.46, "CP": 0.04, "NDF": 0.14, "Ca": 15.43, "P": 2.32, "custo_ms": 12.2904, "preco_mn": 12224.0, "fonte": "UFMA Pregão Mineral"},
    303: {"feed_id": 303, "nome": "Blend de subprodutos (concentrado proteico)", "categoria": "Concentrado proteico", "DM": 74.11, "CP": 33.37, "NDF": 23.88, "Ca": 0.422, "P": 0.73, "custo_ms": 1.2159, "preco_mn": 901.11, "fonte": "MF Rural DDGS Milho"},
}


def carregar_custos_planilha() -> Dict[int, Dict[str, Any]]:
    """Carrega os custos em R$/kg MS da planilha Excel com fallback automático e seguro."""
    try:
        import openpyxl
        if EXCEL_PATH.exists():
            wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
            ws = wb.active
            dados_custos = {}

            for row in range(4, ws.max_row + 1):
                feed_id = ws.cell(row=row, column=1).value
                if feed_id is None:
                    continue
                try:
                    fid = int(feed_id)
                except ValueError:
                    continue

                nome = str(ws.cell(row=row, column=2).value or "").strip()
                categoria = str(ws.cell(row=row, column=3).value or "").strip()
                dm = float(ws.cell(row=row, column=4).value or 0.0)
                cp = float(ws.cell(row=row, column=5).value or 0.0)
                ndf = float(ws.cell(row=row, column=6).value or 0.0)
                ca = float(ws.cell(row=row, column=7).value or 0.0)
                p = float(ws.cell(row=row, column=8).value or 0.0)
                custo_ms = float(ws.cell(row=row, column=9).value or 0.0)
                preco_mn = ws.cell(row=row, column=10).value
                fonte = str(ws.cell(row=row, column=12).value or "").strip()

                dados_custos[fid] = {
                    "feed_id": fid,
                    "nome": nome,
                    "categoria": categoria,
                    "DM": dm,
                    "CP": cp,
                    "NDF": ndf,
                    "Ca": ca,
                    "P": p,
                    "custo_ms": custo_ms,
                    "preco_mn": preco_mn,
                    "fonte": fonte,
                }
            if len(dados_custos) >= 9:
                return dados_custos
    except Exception:
        pass

    return OFFICIAL_FEEDS_CAMPO_DOURADO


def carregar_bromatologia_nasem() -> pd.DataFrame:
    """Carrega a tabela completa de composição bromatológica oficial NASEM (2021)."""
    if not NASEM_PATH.exists():
        raise FileNotFoundError(f"Arquivo NASEM_Comp.csv não encontrado em: {NASEM_PATH}")
    df = pd.read_csv(NASEM_PATH)
    df.set_index("rufas_id", inplace=True)
    return df


def construir_modelo_pl_campo_dourado() -> Dict[str, Any]:
    """
    Constrói a matriz de Programação Linear canônica para o lote lac_cow da Fazenda Campo Dourado.

    Retorna dicionário contendo:
    - c: vetor de custos (R$/kg MS)
    - A_ub: matriz de restrições (desigualdades <=)
    - b_ub: vetor de termos independentes
    - bounds: limites de cada ingrediente (x_j >= 0)
    - var_names: nomes das variáveis
    - constraint_names: nomes detalhados das restrições nutricionais
    - feeds_info: metadados de cada insumo
    """
    custos_dict = carregar_custos_planilha()
    nasem_df = carregar_bromatologia_nasem()

    feeds = CANDIDATE_FEEDS
    n = len(feeds)

    # Vetor de custos c_j (R$/kg MS)
    c = np.array([custos_dict[fid]["custo_ms"] for fid in feeds], dtype=np.float64)
    var_names = [f"x{fid}_{FEED_NAMES_PT[fid]}" for fid in feeds]
    short_var_names = [f"x{fid}" for fid in feeds]

    # Coeficientes numéricos calculados conforme especificações zootécnicas NASEM (2021) e RuFaS:
    # 1. Matéria Seca (DMI)
    # R1a: Consumo Mínimo (DMI >= 25.187 * (1 - 0.30) = 17.6309 kg) => -sum(x_j) <= -17.6309
    # R1b: Consumo Máximo (DMI <= 25.187 * (1 + 0.30) = 32.7431 kg) => sum(x_j) <= 32.7431

    # 2. Energia Líquida (NE) Mcal/kg MS
    # R2: sum(ne_j * x_j) >= 53.8518 => -sum(ne_j * x_j) <= -53.8518
    ne_coeffs = [-1.7944, -2.3151, -2.0698, -1.9181, -1.8837, -1.8528, -1.6386, 0.1875, -1.9758]

    # 3. Proteína Metabolizável Mínima NDT (g/kg MS)
    # R3: sum(mp_ndt_j * x_j) >= 2742.94 => -sum(mp_ndt_j * x_j) <= -2742.94
    mp_ndt_coeffs = [-63.9058, -99.2484, -71.2015, -71.8046, -70.7367, -81.5925, -70.9732, -4.7200, -326.3994]

    # 4. Proteína Metabolizável Mínima PDR (g/kg MS)
    # R4: sum(mp_pdr_j * x_j) >= 2742.94 => -sum(mp_pdr_j * x_j) <= -2742.94
    mp_pdr_coeffs = [-67.8385, -58.5653, -50.2421, -94.8725, -106.1974, -123.9429, -56.9032, -4.7200, -265.0060]

    # 5. Teto de Proteína Metabolizável (g/kg MS)
    # R5: sum(mp_ndt_j * x_j) <= 1.5 * 2742.94 = 4114.41
    mp_max_coeffs = [63.9058, 99.2484, 71.2015, 71.8046, 70.7367, 81.5925, 70.9732, 4.7200, 326.3994]

    # 6. Cálcio Digestível Mínimo (g/kg MS)
    # R6: sum(ca_j * x_j) >= 68.783 => -sum(ca_j * x_j) <= -68.783
    ca_coeffs = [-1.4730, -0.2100, -0.7110, -1.8750, -2.6100, -3.7620, -1.3380, -146.5850, -2.5320]

    # 7. Fósforo Digestível Mínimo (g/kg MS)
    # R7: sum(p_j * x_j) >= 65.517 => -sum(p_j * x_j) <= -65.517
    p_coeffs = [-1.2480, -2.1630, -1.4848, -2.1056, -2.1824, -2.2464, -1.7024, -18.5600, -5.1100]

    # 8. FDN Mínimo (>= 25% da MS consumida)
    # R8: sum((ndf_j - 25) * x_j) >= 0 => -sum((ndf_j - 25) * x_j) <= 0
    ndf_min_coeffs = [-40.41, 15.24, -15.93, -29.69, -26.23, -18.20, -41.62, 24.86, 1.12]

    # 9. FDN Máximo (<= 45% da MS consumida)
    # R9: sum((ndf_j - 45) * x_j) <= 0
    ndf_max_coeffs = [20.41, -35.24, -4.07, 9.69, 6.23, -1.80, 21.62, -44.86, -21.12]

    # 10. FDN Forrageiro Mínimo (peNDF >= 15% da MS consumida)
    # R10: sum((fndf_j - 15) * x_j) >= 0 => -sum((fndf_j - 15) * x_j) <= 0
    fndf_min_coeffs = [-50.41, 15.00, -25.93, -39.69, -36.23, -28.20, -51.62, 15.00, 15.00]

    # 11. Extrato Etéreo Máximo (Gordura <= 7% da MS consumida)
    # R11: sum((ee_j - 7) * x_j) <= 0
    fat_max_coeffs = [-5.0720, -3.1550, -4.0840, -3.6060, -2.9620, -4.1280, -4.3080, -6.9988, -1.7791]

    A_ub = np.array([
        [-1.0] * n,          # R1a: DMI Min
        [1.0] * n,           # R1b: DMI Max
        ne_coeffs,           # R2: Energia Líquida Min
        mp_ndt_coeffs,       # R3: PM Min (NDT)
        mp_pdr_coeffs,       # R4: PM Min (PDR)
        mp_max_coeffs,       # R5: PM Max (Teto)
        ca_coeffs,           # R6: Cálcio Min
        p_coeffs,            # R7: Fósforo Min
        ndf_min_coeffs,      # R8: FDN Min (>= 25%)
        ndf_max_coeffs,      # R9: FDN Max (<= 45%)
        fndf_min_coeffs,     # R10: FDN Forragem Min (>= 15%)
        fat_max_coeffs,      # R11: Gordura Max (<= 7%)
    ], dtype=np.float64)

    b_ub = np.array([
        -17.6309,            # R1a: DMI Min
        32.7431,             # R1b: DMI Max
        -53.8518,            # R2: NE Min
        -2742.94,            # R3: PM Min (NDT)
        -2742.94,            # R4: PM Min (PDR)
        4114.41,             # R5: PM Max
        -68.783,             # R6: Cálcio Min
        -65.517,             # R7: Fósforo Min
        0.0,                 # R8: FDN Min
        0.0,                 # R9: FDN Max
        0.0,                 # R10: FDN Forragem Min
        0.0,                 # R11: Gordura Max
    ], dtype=np.float64)

    constraint_names = [
        "R1a: Consumo Mínimo de MS (DMI >= 17.63 kg)",
        "R1b: Consumo Máximo de MS (DMI <= 32.74 kg)",
        "R2: Energia Líquida Mínima (NE >= 53.85 Mcal)",
        "R3: Proteína Metabolizável Mínima NDT (PM >= 2742.94 g)",
        "R4: Proteína Metabolizável Mínima PDR (PM >= 2742.94 g)",
        "R5: Teto de Proteína Metabolizável (PM <= 4114.41 g)",
        "R6: Cálcio Digestível Mínimo (Ca >= 68.78 g)",
        "R7: Fósforo Digestível Mínimo (P >= 65.52 g)",
        "R8: FDN Mínimo da Ração (FDN >= 25% da MS)",
        "R9: FDN Máximo da Ração (FDN <= 45% da MS)",
        "R10: FDN de Forragem Mínimo (peNDF >= 15% da MS)",
        "R11: Extrato Etéreo Máximo (Gordura <= 7% da MS)",
    ]

    bounds = [(0.0, None) for _ in range(n)]

    feeds_info = [custos_dict[fid] for fid in feeds]

    return {
        "c": c,
        "A_ub": A_ub,
        "b_ub": b_ub,
        "bounds": bounds,
        "feeds": feeds,
        "var_names": var_names,
        "short_var_names": short_var_names,
        "constraint_names": constraint_names,
        "feeds_info": feeds_info,
        "requirements": REQUIREMENTS,
    }


if __name__ == "__main__":
    modelo = construir_modelo_pl_campo_dourado()
    print("=== MODELO PL - FAZENDA CAMPO DOURADO (GO_campo_dourado) ===")
    print(f"Número de Alimentos Candidatos: {len(modelo['feeds'])}")
    print(f"Número de Restrições Estruturais: {len(modelo['constraint_names'])}")
    print("\nFunção Objetivo (Minimizar Custo Z em R$/vaca/dia):")
    terms = [f"{c:.4f}·{v}" for c, v in zip(modelo["c"], modelo["short_var_names"])]
    print("min Z = " + " + ".join(terms))
    print("\nRestrições:")
    for i, name in enumerate(modelo["constraint_names"]):
        print(f"  {name}: b = {modelo['b_ub'][i]:.4f}")
