"""
Visualizador de Tableaus do Simplex - Fazenda Campo Dourado
Formata e exibe os quadros intermediários do Simplex de Duas Fases de maneira didática.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_DIR = Path(__file__).resolve().parents[1]
TABLEAUS_JSON = WORKSPACE_DIR / "output" / "tableaus_simplex_campo_dourado.json"
MARKDOWN_OUTPUT = WORKSPACE_DIR / "campo_dourado" / "TABLEAUS_SIMPLEX_DETALHADOS.md"


def carregar_tableaus() -> List[Dict[str, Any]]:
    if not TABLEAUS_JSON.exists():
        from campo_dourado.otimizar_campo_dourado import executar_otimizacao_campo_dourado
        executar_otimizacao_campo_dourado(verbose=False)

    with open(TABLEAUS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def formatar_tableau_markdown(snap: Dict[str, Any]) -> str:
    """Gera tabela Markdown para um snapshot de tableau."""
    it = snap["iteration"]
    phase = snap["phase"]
    phase_name = snap["phase_name"]
    desc = snap.get("description", "")
    col_names = snap["col_names"]
    rows = snap["matrix_rows"]
    rcs = snap["reduced_costs"]
    obj_val = snap["objective_value"]
    is_final = snap.get("is_final", False)

    md = []
    md.append(f"### Iteração {it} — {phase_name}\n")
    md.append(f"*{desc}*\n")

    if snap.get("entering_var") and snap.get("leaving_var"):
        md.append(
            f"> **Pivoteamento:** Variável Entrante: `{snap['entering_var']}` | "
            f"Variável Sainte: `{snap['leaving_var']}` | Elemento Pivô: `{snap.get('pivot_val')}`\n"
        )

    # Cabeçalho da tabela
    headers = ["Base", "Restrição"] + col_names + ["Lado Direito (b)", "Razão Mín."]
    md.append("| " + " | ".join(headers) + " |")
    md.append("|" + "|".join(["---:"] + ["---"] + ["---:"] * (len(col_names) + 2)) + "|")

    for r in rows:
        row_cells = [
            f"`{r['basic_var']}`",
            r["label"][:30],
        ]
        for val in r["coefficients"]:
            row_cells.append(f"{val:.4f}")
        row_cells.append(f"**{r['rhs']:.4f}**")
        ratio_str = f"{r['ratio']:.4f}" if r["ratio"] is not None else "—"
        row_cells.append(ratio_str)
        md.append("| " + " | ".join(row_cells) + " |")

    # Linha de Custos Reduzidos
    bottom_label = "Custos Reduzidos (c_j - z_j)" if phase == 2 else "Custos Fase 1 (W)"
    rc_cells = ["**Z**" if phase == 2 else "**W**", f"**{bottom_label}**"]
    for rc in rcs:
        rc_cells.append(f"**{rc:.4f}**")
    rc_cells.append(f"**{obj_val:.4f}**")
    rc_cells.append("—")
    md.append("| " + " | ".join(rc_cells) + " |\n")

    return "\n".join(md)


def gerar_relatorio_tableaus_markdown():
    tableaus = carregar_tableaus()
    linhas_md = [
        "# Rastreamento Passo a Passo de Tableaus Simplex — Fazenda Campo Dourado (RuFaS)\n",
        "Documentação didática dos quadros do método Simplex de Duas Fases para o lote `lac_cow`.",
        f"Total de Tableaus Registrados: **{len(tableaus)}**\n",
        "---\n",
    ]

    for snap in tableaus:
        linhas_md.append(formatar_tableau_markdown(snap))
        linhas_md.append("\n---\n")

    with open(MARKDOWN_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_md))

    print(f"Relatório de Tableaus gerado com sucesso em: {MARKDOWN_OUTPUT}")


if __name__ == "__main__":
    gerar_relatorio_tableaus_markdown()
