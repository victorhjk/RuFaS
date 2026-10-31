"""
Otimizador Simplex - Fazenda Campo Dourado (GO_campo_dourado)
Execução do Simplex de Duas Fases Nativo (NumPy), Validação com HiGHS e Análise Pós-Ótima.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import numpy as np
from scipy.optimize import linprog

import sys
WORKSPACE_DIR = Path(__file__).resolve().parents[1]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from RUFAS.biophysical.animal.ration.pure_simplex_solver import TwoPhaseSimplexSolver
from campo_dourado.modelo_pl_campo_dourado import (
    construir_modelo_pl_campo_dourado,
    FEED_NAMES_PT,
)


def executar_otimizacao_campo_dourado(verbose: bool = True) -> Dict[str, Any]:
    """
    Executa a resolução do modelo de PL da Fazenda Campo Dourado pelo Simplex Nativo de Duas Fases
    e compara com o solver de referência HiGHS.
    """
    modelo = construir_modelo_pl_campo_dourado()

    c = modelo["c"]
    A_ub = modelo["A_ub"]
    b_ub = modelo["b_ub"]
    var_names = modelo["short_var_names"]
    constraint_names = modelo["constraint_names"]
    feeds = modelo["feeds"]

    # 1. Resolver com o Solver Simplex de Duas Fases Nativo
    simplex_solver = TwoPhaseSimplexSolver(tol=1e-8, max_iter=2000)
    res_simplex = simplex_solver.solve(
        c=c,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=modelo["bounds"],
        var_names=var_names,
        constraint_names=constraint_names,
    )

    # Salvar histórico completo dos tableaus
    output_json = WORKSPACE_DIR / "output" / "tableaus_simplex_campo_dourado.json"
    simplex_solver.save_tableaus_json(output_json)

    # 2. Benchmark de Validação Cruzada com Scipy / HiGHS
    res_highs = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=(0, None), method="highs")

    # 3. Consolidação dos Resultados
    x_opt = res_simplex["x"]
    fun_opt = res_simplex["fun"]
    dmi_total = float(np.sum(x_opt))
    custo_kg_ms = fun_opt / dmi_total if dmi_total > 0 else 0.0

    diet_items = []
    for i, fid in enumerate(feeds):
        kg = float(x_opt[i])
        pct = (kg / dmi_total * 100.0) if dmi_total > 0 else 0.0
        unit_cost = float(c[i])
        diet_items.append({
            "feed_id": fid,
            "var_name": var_names[i],
            "feed_name": FEED_NAMES_PT[fid],
            "kg_ms_dia": round(kg, 4),
            "percentual_ms": round(pct, 2),
            "custo_unit_ms": unit_cost,
            "custo_diario": round(kg * unit_cost, 4),
            "is_included": kg > 1e-4,
        })

    # Avaliação das restrições nutricionais
    # Fornecimento efetivo = A_original * x_opt
    supply_values = np.dot(-A_ub, x_opt)  # para as restrições multiplicadas por -1
    constraint_eval = []
    for i, cname in enumerate(constraint_names):
        actual_lhs = float(np.dot(A_ub[i], x_opt))
        rhs_limit = float(b_ub[i])
        slack = rhs_limit - actual_lhs
        shadow = float(res_simplex["shadow_prices"][i])
        is_active = abs(slack) < 1e-4

        constraint_eval.append({
            "constraint_index": i + 1,
            "name": cname,
            "actual_lhs": round(actual_lhs, 4),
            "rhs_limit": round(rhs_limit, 4),
            "slack": round(abs(slack), 4),
            "shadow_price": round(shadow, 4),
            "is_active": is_active,
        })

    # Sensibilidade dos Custos c_j
    cost_sens = []
    for item in res_simplex["cost_sensitivity_ranges"]:
        idx = item["var_index"]
        fid = feeds[idx]
        rc = float(res_simplex["reduced_costs"][idx])
        cost_sens.append({
            "feed_id": fid,
            "var_name": var_names[idx],
            "feed_name": FEED_NAMES_PT[fid],
            "is_basic": item["is_basic"],
            "current_cost": item["current_cost"],
            "reduced_cost": round(rc, 4),
            "min_cost": item["min_cost"],
            "max_cost": item["max_cost"],
            "allowable_decrease": item["allowable_decrease"],
            "allowable_increase": item["allowable_increase"],
        })

    # Sensibilidade dos Lados Direitos b_i
    rhs_sens = []
    for i, item in enumerate(res_simplex["rhs_sensitivity_ranges"]):
        if i < len(constraint_names):
            rhs_sens.append({
                "constraint_index": i + 1,
                "name": constraint_names[i],
                "current_rhs": round(float(b_ub[i]), 4),
                "allowable_decrease": item["allowable_decrease"],
                "allowable_increase": item["allowable_increase"],
            })

    # Validação de discrepância entre os solvers
    diff_z = abs(fun_opt - res_highs.fun)
    diff_x = float(np.max(np.abs(x_opt - res_highs.x)))
    solvers_match = diff_z < 1e-5 and diff_x < 1e-5

    results_consolidated = {
        "success": bool(res_simplex["success"]),
        "nit_simplex": int(res_simplex["nit"]),
        "nit_highs": int(res_highs.nit),
        "fun_simplex": fun_opt,
        "fun_highs": float(res_highs.fun),
        "diff_z": diff_z,
        "diff_x": diff_x,
        "solvers_match": solvers_match,
        "dmi_total": round(dmi_total, 4),
        "custo_kg_ms": round(custo_kg_ms, 4),
        "diet": diet_items,
        "constraints": constraint_eval,
        "cost_sensitivity": cost_sens,
        "rhs_sensitivity": rhs_sens,
        "total_tableaus": len(res_simplex["tableaus"]),
        "output_json": str(output_json),
    }

    if verbose:
        imprimir_relatorio_terminal(results_consolidated)

    return results_consolidated


def imprimir_relatorio_terminal(res: Dict[str, Any]):
    """Imprime relatório formatado e didático dos resultados no terminal."""
    print("=" * 80)
    print("    OTIMIZAÇÃO DA DIETA - FAZENDA CAMPO DOURADO (GO_campo_dourado)")
    print("    Simulador: RuFaS (Ruminant Farm Systems) | Padrão Nutricional: NASEM (2021)")
    print("    Método: Simplex de Duas Fases Nativo (NumPy) com Rastreamento de Tableaus")
    print("=" * 80)

    print(f"\nStatus da Otimização: {'CONVERGIDA COM SUCESSO' if res['success'] else 'FALHA'}")
    print(f"Iterações do Simplex Nativo: {res['nit_simplex']} | Tableaus Gravados: {res['total_tableaus']}")
    print(f"Custo Mínimo Diário Z*: R$ {res['fun_simplex']:.4f} por vaca/dia")
    print(f"Consumo Total de MS: {res['dmi_total']:.4f} kg MS/dia | Custo por kg de MS: R$ {res['custo_kg_ms']:.4f}/kg MS")
    print(f"Benchmark HiGHS: Z* = R$ {res['fun_highs']:.4f} (Discrepância = {res['diff_z']:.2e}) -> {'PERFEITO' if res['solvers_match'] else 'DIVERGENTE'}")

    print("\n" + "-" * 80)
    print(" COMPOSIÇÃO DA DIETA ÓTIMA (Lote lac_cow - 100 Vacas em Lactação)")
    print("-" * 80)
    print(f"{'Código':<6} {'Ingrediente':<35} {'kg MS/dia':>10} {'% MS':>8} {'R$/kg MS':>10} {'R$/dia':>10}")
    print("-" * 80)
    for item in res["diet"]:
        flag = " *" if item["is_included"] else "  "
        print(
            f"{item['var_name']:<6} {item['feed_name']:<35} "
            f"{item['kg_ms_dia']:>10.4f} {item['percentual_ms']:>7.1f}% "
            f"{item['custo_unit_ms']:>10.4f} {item['custo_diario']:>10.4f}{flag}"
        )
    print("-" * 80)
    print(f"Total Diário:                                  {res['dmi_total']:>10.4f}  100.0%             R$ {res['fun_simplex']:>8.4f}")
    print("(* Ingredientes selecionados na solução básica ótima)")

    print("\n" + "-" * 80)
    print(" STATUS DAS RESTRIÇÕES NUTRICIONAIS (NASEM 2021) E PREÇOS-SOMBRA")
    print("-" * 80)
    print(f"{'Nº':<4} {'Restrição':<42} {'Status':<10} {'Folga/Exc':>10} {'Preço-Sombra':>12}")
    print("-" * 80)
    for c in res["constraints"]:
        status = "ATIVA" if c["is_active"] else "FOLGA"
        shadow_str = f"R$ {c['shadow_price']:.4f}" if c["is_active"] else "—"
        print(f"R{c['constraint_index']:<3} {c['name'][:40]:<42} {status:<10} {c['slack']:>10.4f} {shadow_str:>12}")
    print("-" * 80)

    print("\n" + "-" * 80)
    print(" ANÁLISE DE SENSIBILIDADE DOS CUSTOS (c_j) - FAIXA DE VALIDADE DA BASE")
    print("-" * 80)
    print(f"{'Var':<6} {'Ingrediente':<35} {'Base':<8} {'Custo Atual':>11} {'Custo Mín':>10} {'Custo Máx':>10}")
    print("-" * 80)
    for item in res["cost_sensitivity"]:
        base_str = "BÁSICA" if item["is_basic"] else "NÃO-BÁSICA"
        max_str = f"{item['max_cost']:.4f}" if item["max_cost"] != float("inf") else "+Inf"
        min_str = f"{item['min_cost']:.4f}"
        print(f"{item['var_name']:<6} {item['feed_name']:<35} {base_str:<8} R$ {item['current_cost']:>7.4f} R$ {min_str:>7} R$ {max_str:>7}")
    print("-" * 80)
    print(f"Log detalhado dos tableaus gravado em: {res['output_json']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    executar_otimizacao_campo_dourado(verbose=True)
