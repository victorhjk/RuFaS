"""
Servidor Flask - Dashboard Interativo de Otimização e Análise de Sensibilidade
Fazenda Campo Dourado - Simplex em Duas Fases (NumPy Puro) & Padrão NASEM / RuFaS

Permite ao usuário:
1. Ajustar preços de insumos (R$/kg MS, R$/sc milho, R$/t silagem/DDGS) via sliders.
2. Alterar exigências nutricionais (Energia Líquida, Proteína, Cálcio, Fósforo, Produção de Leite).
3. Testar cenários de mercado em 1 clique (Safra recorde de milho, Choque de insumos, Seca, etc.).
4. Visualizar a dieta ótima, custo Z*, margem IOFC, gráficos e status das 12 restrições.
5. Inspecionar o Simplex passo a passo com o histórico interativo dos 20 tableaus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
from flask import Flask, jsonify, render_template, request

# Importar modelo canônico e solver Simplex nativo
import sys
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from campo_dourado.modelo_pl_campo_dourado import (
    CANDIDATE_FEEDS,
    FEED_NAMES_PT,
    carregar_custos_planilha,
    construir_modelo_pl_campo_dourado,
)
from RUFAS.biophysical.animal.ration.pure_simplex_solver import TwoPhaseSimplexSolver

app = Flask(__name__, template_folder="templates")

# Cotações padrão e dados bromatológicos
CUSTOS_BASE = carregar_custos_planilha()
MODELO_BASE = construir_modelo_pl_campo_dourado()


def resolver_dieta_customizada(
    custos_override: Dict[int, float],
    ne_req: float = 53.8518,
    mp_req: float = 2742.94,
    ca_req: float = 68.783,
    p_req: float = 65.517,
    dmi_min: float = 17.6309,
    dmi_max: float = 32.7431,
    leite_preco: float = 2.9692,
    leite_prod: float = 30.0,
    total_cows: int = 200,
    pct_milking: float = 79.0,
    raca: str = "HO",
    ordenhas: int = 3,
    metano_3nop: float = 90.0,
) -> Dict[str, Any]:
    """Resolve o modelo com custos, exigências e dimensionamento do rebanho customizados."""
    feeds = CANDIDATE_FEEDS
    n = len(feeds)

    # Ajustes de Raça e Peso Vivo (BW)
    pesos_vivos = {"HO": 640.5, "GIROLANDO": 580.0, "JERSEY": 480.0}
    raca_upper = raca.upper()
    bw_vaca = pesos_vivos.get(raca_upper, 640.5)

    # Ajuste de frequência de ordenhas (3x ao dia aumenta produtividade em ~10% vs 2x)
    prod_leite_vaca = leite_prod * (1.10 if ordenhas == 3 else 1.0)

    # Vetor de custos atualizado
    c = np.array([custos_override.get(fid, CUSTOS_BASE[fid]["custo_ms"]) for fid in feeds], dtype=np.float64)

    # Matriz e RHS do modelo
    A_ub = MODELO_BASE["A_ub"].copy()
    b_ub = MODELO_BASE["b_ub"].copy()

    # Atualizar termos independentes conforme sliders
    b_ub[0] = -float(dmi_min)
    b_ub[1] = float(dmi_max)
    b_ub[2] = -float(ne_req)
    b_ub[3] = -float(mp_req)
    b_ub[4] = -float(mp_req)
    b_ub[5] = float(mp_req * 1.5)
    b_ub[6] = -float(ca_req)
    b_ub[7] = -float(p_req)

    solver = TwoPhaseSimplexSolver(tol=1e-8, max_iter=2000)
    res = solver.solve(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        var_names=MODELO_BASE["var_names"],
        constraint_names=MODELO_BASE["constraint_names"],
    )

    x = res["x"]
    total_ms = float(np.sum(x))
    custo_total = float(res["fun"])
    custo_kg_ms = float(custo_total / total_ms) if total_ms > 0 else 0.0

    # Composição detalhada da dieta individual
    dieta_itens = []
    total_mn = 0.0
    ms_volumoso = 0.0
    ms_concentrado = 0.0
    cp_ponderado = 0.0
    ndf_ponderado = 0.0

    for i, fid in enumerate(feeds):
        kg_ms = float(x[i])
        pct_ms = float((kg_ms / total_ms * 100.0) if total_ms > 0 else 0.0)
        dm_pct = float(CUSTOS_BASE[fid]["DM"])
        kg_mn = float(kg_ms / (dm_pct / 100.0))
        total_mn += kg_mn

        categoria = CUSTOS_BASE[fid]["categoria"]
        if "Forragem" in categoria:
            ms_volumoso += kg_ms
        else:
            ms_concentrado += kg_ms

        cp_ponderado += kg_ms * float(CUSTOS_BASE[fid]["CP"])
        ndf_ponderado += kg_ms * float(CUSTOS_BASE[fid]["NDF"])

        em_base = bool(kg_ms > 1e-4)
        sens_entry = res["cost_sensitivity_ranges"][i] if i < len(res.get("cost_sensitivity_ranges", [])) else {}
        c_min = sens_entry.get("min_cost", -float("inf"))
        c_max = sens_entry.get("max_cost", float("inf"))

        dieta_itens.append({
            "fid": fid,
            "codigo": f"x{fid}",
            "nome": FEED_NAMES_PT[fid],
            "categoria": categoria,
            "kg_ms": round(kg_ms, 4),
            "pct_ms": round(pct_ms, 2),
            "kg_mn": round(kg_mn, 2),
            "custo_ms": round(float(c[i]), 4),
            "custo_dia": round(float(c[i] * kg_ms), 4),
            "em_base": em_base,
            "custo_reduzido": round(float(res["reduced_costs"][i]), 4),
            "custo_min": round(float(c_min), 4) if np.isfinite(c_min) else "-Inf",
            "custo_max": round(float(c_max), 4) if np.isfinite(c_max) else "+Inf",
        })

    rel_volumoso = round((ms_volumoso / total_ms * 100.0) if total_ms > 0 else 0.0, 1)
    rel_concentrado = round(100.0 - rel_volumoso, 1)
    cp_final = round((cp_ponderado / total_ms) if total_ms > 0 else 0.0, 2)
    ndf_final = round((ndf_ponderado / total_ms) if total_ms > 0 else 0.0, 2)
    fndf_final = round(((x[2] * CUSTOS_BASE[51]["NDF"]) / total_ms) if total_ms > 0 else 0.0, 2)

    # -------------------------------------------------------------------------
    # DIMENSIONAMENTO INTEGRAL DO REBANHO E FAZENDA
    # -------------------------------------------------------------------------
    n_vacas_lact = int(round(total_cows * (pct_milking / 100.0)))
    n_vacas_secas = max(0, total_cows - n_vacas_lact)

    # Produção de leite total
    leite_dia_rebanho = round(n_vacas_lact * prod_leite_vaca, 1)
    leite_mes_rebanho = round(leite_dia_rebanho * 30.0, 1)
    faturamento_dia_leite = round(leite_dia_rebanho * leite_preco, 2)
    faturamento_mes_leite = round(leite_mes_rebanho * leite_preco, 2)

    # Dieta e custo de vacas secas (mantença: ~13 kg MS, ~35 kg MN frescos, R$ 11.50/dia)
    ms_seca_dia = 13.0
    mn_seca_dia = 35.0
    custo_seca_dia = 11.50

    # Demanda de Comida no Cocho (Logística da Fazenda)
    demanda_ms_dia_t = round((n_vacas_lact * total_ms + n_vacas_secas * ms_seca_dia) / 1000.0, 2)
    demanda_mn_dia_t = round((n_vacas_lact * total_mn + n_vacas_secas * mn_seca_dia) / 1000.0, 2)
    demanda_mn_mes_t = round(demanda_mn_dia_t * 30.0, 1)

    # Silagem de milho anual e área de lavoura necessária (produtividade média Goiás: 45 t MN/ha)
    silagem_kg_mn_vaca = dieta_itens[2]["kg_mn"] if len(dieta_itens) > 2 else (total_mn * 0.74)
    silagem_t_ano_rebanho = round((n_vacas_lact * silagem_kg_mn_vaca * 365.0) / 1000.0, 1)
    area_lavoura_silagem_ha = round(silagem_t_ano_rebanho / 45.0, 1)

    # Balanço Financeiro Global da Fazenda (Custos de Ração e IOFC)
    custo_alim_dia_rebanho = round(n_vacas_lact * custo_total + n_vacas_secas * custo_seca_dia, 2)
    custo_alim_mes_rebanho = round(custo_alim_dia_rebanho * 30.0, 2)
    iofc_dia_rebanho = round(faturamento_dia_leite - custo_alim_dia_rebanho, 2)
    iofc_mes_rebanho = round(faturamento_mes_leite - custo_alim_mes_rebanho, 2)

    # Indicadores por vaca em lactação
    receita_leite_vaca = round(prod_leite_vaca * leite_preco, 2)
    iofc_vaca_dia = round(receita_leite_vaca - custo_total, 2)

    # Módulo Sustentabilidade & GEE (Mitigação com 3-NOP Bovaer)
    reducao_metano_pct = min(40.0, round(metano_3nop * 0.333, 1))
    ch4_base_dia_kg = 0.350
    ch4_evitado_dia_kg = ch4_base_dia_kg * (reducao_metano_pct / 100.0)
    co2e_evitado_ano_t = round((n_vacas_lact * ch4_evitado_dia_kg * 28.0 * 365.0) / 1000.0, 1)

    # Restrições avaliadas
    slack = b_ub - A_ub @ x
    restricoes_info = []
    for j, name in enumerate(MODELO_BASE["constraint_names"]):
        is_binding = bool(abs(slack[j]) < 1e-4)
        sp = float(res["shadow_prices"][j])
        rhs_val = float(abs(b_ub[j]))
        real_val = float(-(A_ub[j] @ x) if b_ub[j] < 0 else (A_ub[j] @ x))
        restricoes_info.append({
            "idx": j + 1,
            "nome": name,
            "limite": round(rhs_val, 2),
            "valor_real": round(real_val, 2),
            "status": "ATIVA" if is_binding else "FOLGA",
            "folga": round(float(abs(slack[j])), 4),
            "preco_sombra": round(sp, 4),
        })

    # Resumo dos tableaus para o visualizador passo a passo
    tableaus_resumo = []
    for t in res.get("tableaus", []):
        matrix_rows = []
        row_labels = []
        for r in t.get("matrix_rows", []):
            row_labels.append(r.get("basic_var", f"Linha {r.get('row_index', 0)}"))
            coeffs = [round(float(v), 3) for v in r.get("coefficients", [])]
            coeffs.append(round(float(r.get("rhs", 0.0)), 3))
            matrix_rows.append(coeffs)

        tableaus_resumo.append({
            "iteration": t["iteration"],
            "phase": t["phase"],
            "phase_name": t["phase_name"],
            "is_final": t["is_final"],
            "obj_val": round(float(t["objective_value"]), 4),
            "entering_var": t.get("entering_var"),
            "leaving_var": t.get("leaving_var"),
            "pivot_row": t.get("pivot_row"),
            "pivot_col": t.get("pivot_col"),
            "pivot_val": round(float(t["pivot_val"]), 4) if t.get("pivot_val") is not None else None,
            "col_names": t.get("col_names", []),
            "row_labels": row_labels,
            "matrix_rows": matrix_rows,
            "reduced_costs": [round(float(v), 3) for v in t.get("reduced_costs", [])],
            "description": t.get("description", ""),
        })

    return {
        "success": bool(res["success"]),
        "status": res["status"],
        "nit": int(res["nit"]),
        "custo_total": round(custo_total, 4),
        "custo_kg_ms": round(custo_kg_ms, 4),
        "total_ms": round(total_ms, 4),
        "total_mn": round(total_mn, 2),
        "rel_volumoso": rel_volumoso,
        "rel_concentrado": rel_concentrado,
        "cp_pct": cp_final,
        "ndf_pct": ndf_final,
        "fndf_pct": fndf_final,
        "receita_leite": receita_leite_vaca,
        "iofc_dia": iofc_vaca_dia,
        "total_cows": total_cows,
        "pct_milking": pct_milking,
        "n_vacas_lact": n_vacas_lact,
        "n_vacas_secas": n_vacas_secas,
        "raca": raca_upper,
        "ordenhas": ordenhas,
        "bw_vaca": bw_vaca,
        "leite_dia_rebanho": leite_dia_rebanho,
        "leite_mes_rebanho": leite_mes_rebanho,
        "faturamento_dia_leite": faturamento_dia_leite,
        "faturamento_mes_leite": faturamento_mes_leite,
        "demanda_ms_dia_t": demanda_ms_dia_t,
        "demanda_mn_dia_t": demanda_mn_dia_t,
        "demanda_mn_mes_t": demanda_mn_mes_t,
        "area_lavoura_silagem_ha": area_lavoura_silagem_ha,
        "silagem_t_ano_rebanho": silagem_t_ano_rebanho,
        "custo_alim_dia_rebanho": custo_alim_dia_rebanho,
        "custo_alim_mes_rebanho": custo_alim_mes_rebanho,
        "iofc_dia_rebanho": iofc_dia_rebanho,
        "iofc_mes_rebanho": iofc_mes_rebanho,
        "reducao_metano_pct": reducao_metano_pct,
        "co2e_evitado_ano_t": co2e_evitado_ano_t,
        "dieta": dieta_itens,
        "restricoes": restricoes_info,
        "tableaus": tableaus_resumo,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/otimizar", methods=["POST"])
def api_otimizar():
    data = request.get_json() or {}
    custos_override = {}
    for fid_str, valor in data.get("custos", {}).items():
        try:
            custos_override[int(fid_str)] = float(valor)
        except ValueError:
            pass

    ne_req = float(data.get("ne_req", 53.8518))
    mp_req = float(data.get("mp_req", 2742.94))
    ca_req = float(data.get("ca_req", 68.783))
    p_req = float(data.get("p_req", 65.517))
    leite_preco = float(data.get("leite_preco", 2.9692))
    leite_prod = float(data.get("leite_prod", 30.0))

    total_cows = int(data.get("total_cows", 200))
    pct_milking = float(data.get("pct_milking", 79.0))
    raca = str(data.get("raca", "HO"))
    ordenhas = int(data.get("ordenhas", 3))
    metano_3nop = float(data.get("metano_3nop", 90.0))

    resultado = resolver_dieta_customizada(
        custos_override=custos_override,
        ne_req=ne_req,
        mp_req=mp_req,
        ca_req=ca_req,
        p_req=p_req,
        leite_preco=leite_preco,
        leite_prod=leite_prod,
        total_cows=total_cows,
        pct_milking=pct_milking,
        raca=raca,
        ordenhas=ordenhas,
        metano_3nop=metano_3nop,
    )
    return jsonify(resultado)


@app.route("/api/padroes", methods=["GET"])
def api_padroes():
    """Retorna os valores padrão da Fazenda Campo Dourado e cotações CEPEA."""
    feeds_info = []
    for fid in CANDIDATE_FEEDS:
        info = CUSTOS_BASE[fid]
        feeds_info.append({
            "fid": fid,
            "codigo": f"x{fid}",
            "nome": FEED_NAMES_PT[fid],
            "categoria": info["categoria"],
            "dm": info["DM"],
            "custo_ms": info["custo_ms"],
            "preco_mn": info["preco_mn"],
            "fonte": info["fonte"],
        })
    return jsonify({
        "feeds": feeds_info,
        "ne_req": 53.8518,
        "mp_req": 2742.94,
        "ca_req": 68.783,
        "p_req": 65.517,
        "dmi_min": 17.6309,
        "dmi_max": 32.7431,
        "leite_preco": 2.9692,
        "leite_prod": 30.0,
        "total_cows": 200,
        "pct_milking": 79.0,
        "raca": "HO",
        "ordenhas": 3,
        "metano_3nop": 90.0,
    })


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    print("=" * 70)
    print(" 🚀 INICIANDO DASHBOARD INTERATIVO - FAZENDA CAMPO DOURADO (RuFaS / Simplex)")
    print(f" Acesse no navegador: http://127.0.0.1:{port} ou http://localhost:{port}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=port, debug=False)
