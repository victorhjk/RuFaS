"""
Análise de Sensibilidade Paramétrica - Fazenda Campo Dourado (GO_campo_dourado)
Baseado no Guia Oficial: 'Otimizacao Nutricao GO_campo_dourado_paisagem.pdf' (Seção 8)

Cenários simulados:
1. Variação do custo do milho moído (x44): identificar o ponto exato de virada (troca de base) previsto pelo Simplex.
2. Variação do custo das silagens (troca competitiva entre forragens: silagem de milho x51 vs capim-sudão x176): ±25%.
3. Variação do buffer de fósforo (0%, 25%, 50%, 75%): impacto na inclusão de mineral e custo diário.
4. Elasticidade de Consumo de MS e Exigências de Lactação (±10%).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

import sys
WORKSPACE_DIR = Path(__file__).resolve().parents[1]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from RUFAS.biophysical.animal.ration.pure_simplex_solver import TwoPhaseSimplexSolver
from campo_dourado.modelo_pl_campo_dourado import construir_modelo_pl_campo_dourado, FEED_NAMES_PT

RESULTS_DIR = WORKSPACE_DIR / "campo_dourado" / "resultados"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def resolver_variacao(c_mod: np.ndarray, b_ub_mod: np.ndarray, A_ub_mod: np.ndarray) -> Dict[str, Any]:
    """Resolve uma variação paramétrica com o Simplex nativo de duas fases."""
    modelo_base = construir_modelo_pl_campo_dourado()
    solver = TwoPhaseSimplexSolver(tol=1e-8, max_iter=2000)
    res = solver.solve(
        c=c_mod,
        A_ub=A_ub_mod,
        b_ub=b_ub_mod,
        bounds=modelo_base["bounds"],
        var_names=modelo_base["short_var_names"],
        constraint_names=modelo_base["constraint_names"],
    )
    return res


def cenario_1_preco_milho() -> List[Dict[str, Any]]:
    """Cenário 1: Variação do preço do milho grão moído (x44)."""
    modelo = construir_modelo_pl_campo_dourado()
    precos_milho = [0.30, 0.50, 0.65, 0.70, 0.7367, 0.75, 0.80, 1.00, 1.20, 1.2413, 1.50, 2.00]
    idx_milho = modelo["feeds"].index(44)
    idx_silagem = modelo["feeds"].index(51)
    idx_ddgs = modelo["feeds"].index(303)
    idx_mineral = modelo["feeds"].index(301)

    resultados = []
    for p in precos_milho:
        c_mod = modelo["c"].copy()
        c_mod[idx_milho] = p
        res = resolver_variacao(c_mod, modelo["b_ub"], modelo["A_ub"])

        x = res["x"]
        dmi = float(np.sum(x))
        resultados.append({
            "preco_milho_rs_kg": p,
            "sucesso": res["success"],
            "custo_diario_rs": round(res["fun"], 4),
            "custo_kg_ms": round(res["fun"] / dmi, 4) if dmi > 0 else 0.0,
            "milho_kg": round(float(x[idx_milho]), 4),
            "milho_pct": round(float(x[idx_milho]) / dmi * 100.0, 1) if dmi > 0 else 0.0,
            "silagem_kg": round(float(x[idx_silagem]), 4),
            "silagem_pct": round(float(x[idx_silagem]) / dmi * 100.0, 1) if dmi > 0 else 0.0,
            "ddgs_kg": round(float(x[idx_ddgs]), 4),
            "ddgs_pct": round(float(x[idx_ddgs]) / dmi * 100.0, 1) if dmi > 0 else 0.0,
            "mineral_kg": round(float(x[idx_mineral]), 4),
            "status_base": "MILHO_NA_BASE" if x[idx_milho] > 1e-3 else "MILHO_FORA_DA_BASE",
        })

    salvar_csv(resultados, RESULTS_DIR / "cenario_1_sensibilidade_milho.csv")
    return resultados


def cenario_2_competicao_silagens() -> List[Dict[str, Any]]:
    """Cenário 2: Variação nos custos das silagens (milho x51 vs capim-sudão x176)."""
    modelo = construir_modelo_pl_campo_dourado()
    idx_51 = modelo["feeds"].index(51)
    idx_176 = modelo["feeds"].index(176)
    idx_ddgs = modelo["feeds"].index(303)

    custo_base_51 = modelo["c"][idx_51]
    custo_base_176 = modelo["c"][idx_176]

    fatores = [0.75, 0.85, 1.00, 1.15, 1.25, 1.30, 1.40]
    resultados = []

    for f in fatores:
        # Variando custo da silagem de milho
        c_mod = modelo["c"].copy()
        c_mod[idx_51] = round(custo_base_51 * f, 4)
        res = resolver_variacao(c_mod, modelo["b_ub"], modelo["A_ub"])

        x = res["x"]
        dmi = float(np.sum(x))
        resultados.append({
            "fator_custo_silagem_milho": f,
            "custo_silagem_milho_rs": round(c_mod[idx_51], 4),
            "custo_diario_rs": round(res["fun"], 4),
            "silagem_milho_kg": round(float(x[idx_51]), 4),
            "silagem_sudao_kg": round(float(x[idx_176]), 4),
            "ddgs_kg": round(float(x[idx_ddgs]), 4),
            "forragem_predominante": "SILAGEM_MILHO" if x[idx_51] > x[idx_176] else "CAPIM_SUDAO",
        })

    salvar_csv(resultados, RESULTS_DIR / "cenario_2_sensibilidade_silagens.csv")
    return resultados


def cenario_3_buffer_fosforo() -> List[Dict[str, Any]]:
    """Cenário 3: Variação do buffer de exigência de fósforo (0%, 25%, 50%, 75%)."""
    modelo = construir_modelo_pl_campo_dourado()
    idx_mineral = modelo["feeds"].index(301)
    idx_ddgs = modelo["feeds"].index(303)
    idx_p = 7  # R7: Fósforo

    # P_req_base = 43.678 g (sem buffer).
    # Buffer 50% => 43.678 * 1.50 = 65.517 g (caso base).
    p_sem_buffer = 43.678
    buffers = [0, 25, 50, 75, 100]
    resultados = []

    for b in buffers:
        b_ub_mod = modelo["b_ub"].copy()
        req_p = p_sem_buffer * (1.0 + b / 100.0)
        b_ub_mod[idx_p] = -req_p

        res = resolver_variacao(modelo["c"], b_ub_mod, modelo["A_ub"])
        x = res["x"]
        resultados.append({
            "buffer_fosforo_pct": b,
            "exigencia_p_g_dia": round(req_p, 3),
            "custo_diario_rs": round(res["fun"], 4),
            "premix_mineral_kg": round(float(x[idx_mineral]), 4),
            "ddgs_kg": round(float(x[idx_ddgs]), 4),
            "preco_sombra_p": round(float(res["shadow_prices"][idx_p]), 4),
        })

    salvar_csv(resultados, RESULTS_DIR / "cenario_3_buffer_fosforo.csv")
    return resultados


def cenario_4_elasticidade_producao() -> List[Dict[str, Any]]:
    """Cenário 4: Elasticidade com relação à produção de leite / consumo de MS (±10%)."""
    modelo = construir_modelo_pl_campo_dourado()
    idx_dmi_min = 0
    idx_dmi_max = 1
    idx_ne = 2
    idx_pm_ndt = 3
    idx_pm_pdr = 4

    escalas = [0.90, 0.95, 1.00, 1.05, 1.10]
    resultados = []

    for s in escalas:
        b_ub_mod = modelo["b_ub"].copy()
        # Escalar as exigências de energia e proteína na proporção do leite
        b_ub_mod[idx_ne] = modelo["b_ub"][idx_ne] * s
        b_ub_mod[idx_pm_ndt] = modelo["b_ub"][idx_pm_ndt] * s
        b_ub_mod[idx_pm_pdr] = modelo["b_ub"][idx_pm_pdr] * s

        res = resolver_variacao(modelo["c"], b_ub_mod, modelo["A_ub"])
        x = res["x"]
        dmi = float(np.sum(x))
        resultados.append({
            "escala_producao": s,
            "variacao_pct": round((s - 1.0) * 100, 0),
            "custo_diario_rs": round(res["fun"], 4),
            "consumo_ms_total_kg": round(dmi, 4),
            "silagem_milho_kg": round(float(x[modelo["feeds"].index(51)]), 4),
            "ddgs_kg": round(float(x[modelo["feeds"].index(303)]), 4),
            "mineral_kg": round(float(x[modelo["feeds"].index(301)]), 4),
            "custo_kg_ms": round(res["fun"] / dmi, 4) if dmi > 0 else 0.0,
        })

    salvar_csv(resultados, RESULTS_DIR / "cenario_4_elasticidade_producao.csv")
    return resultados


def salvar_csv(dados: List[Dict[str, Any]], caminho: Path):
    if not dados:
        return
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=dados[0].keys())
        writer.writeheader()
        writer.writerows(dados)


def executar_todos_cenarios():
    print("=== EXECUTANDO CENÁRIOS DE SENSIBILIDADE (FAZENDA CAMPO DOURADO) ===")
    
    print("\n1. Cenário 1: Sensibilidade ao Preço do Milho...")
    c1 = cenario_1_preco_milho()
    for row in c1:
        if row["preco_milho_rs_kg"] in [0.50, 0.70, 0.7367, 0.80, 1.2413]:
            print(f"   Preço R$ {row['preco_milho_rs_kg']:>6.4f} -> Custo Diário: R$ {row['custo_diario_rs']:>7.4f} | Milho: {row['milho_kg']:>6.3f} kg ({row['status_base']})")

    print("\n2. Cenário 2: Competição entre Silagens (Milho vs Sudão)...")
    c2 = cenario_2_competicao_silagens()
    for row in c2:
        print(f"   Fator {row['fator_custo_silagem_milho']:>4.2f} (R$ {row['custo_silagem_milho_rs']:>6.4f}) -> Custo: R$ {row['custo_diario_rs']:>7.4f} | Forragem: {row['forragem_predominante']}")

    print("\n3. Cenário 3: Variação do Buffer de Fósforo...")
    c3 = cenario_3_buffer_fosforo()
    for row in c3:
        print(f"   Buffer {row['buffer_fosforo_pct']:>3d}% (Exigência {row['exigencia_p_g_dia']:>6.2f} g) -> Custo: R$ {row['custo_diario_rs']:>7.4f} | Mineral: {row['premix_mineral_kg']:>5.3f} kg | Sombra: R$ {row['preco_sombra_p']:>6.4f}")

    print("\n4. Cenário 4: Elasticidade de Produção / Consumo...")
    c4 = cenario_4_elasticidade_producao()
    for row in c4:
        print(f"   Escala {row['escala_producao']:>4.2f} ({row['variacao_pct']:>+3.0f}%) -> Consumo: {row['consumo_ms_total_kg']:>6.3f} kg MS | Custo Diário: R$ {row['custo_diario_rs']:>7.4f}")

    print(f"\nTodos os cenários gravados com sucesso em: {RESULTS_DIR}")


if __name__ == "__main__":
    executar_todos_cenarios()
