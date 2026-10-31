"""
Algoritmo Simplex Canônico de Duas Fases em NumPy Puro
Módulo de Pesquisa Operacional e Formulação Zootécnica de Rações (RuFaS)

Implementação independente desenvolvida para a disciplina Modelagem e Otimização Aplicada (IFG).
Autor Discente: Victor Hugo Jesus | Docente: Prof. Dr. Eduardo Noronha

Características do Algoritmo:
1. Padronização Canônica: conversão de restrições de desigualdade (<=, >=), igualdades e limites
   de variáveis na forma padrão com variáveis de folga (slack), excesso (surplus) e artificiais.
2. Fase 1: minimização da soma de variáveis artificiais W = sum(a_k) para obtenção de uma
   Solução Básica Viável (SBV) inicial sem necessidade de chute inicial arbitrário.
3. Fase 2: restauração da função objetivo econômica real min Z = c^T x, com pivotamento
   segundo a regra clássica de Dantzig (maior custo reduzido negativo) e critério da razão mínima.
4. Rastreamento Matricial: instrumentação de tableaus com armazenamento de estados, identificação
   explícita do elemento pivô, variável entrante e variável sainte em cada passo.
5. Teoria da Dualidade: cálculo exato de preços-sombra (vetor dual y = c_B^T B^{-1}) e folgas.
6. Análise Pós-Ótima: intervalos analíticos de estabilidade de base para custos (c_j) e lados direitos (b_i).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np


class TwoPhaseSimplexSolver:
    """
    Resolvedor Linear Simplex de Duas Fases matricial com instrumentação analítica completa.
    
    Resolve o modelo linear:
        min   c^T x
        sob   A_ub x <= b_ub
              A_eq x == b_eq  (opcional)
              l_j <= x_j <= u_j,  x_j >= 0
    """

    def __init__(self, tol: float = 1e-8, max_iter: int = 2000):
        self.tol = tol
        self.max_iter = max_iter
        self.history: List[Dict[str, Any]] = []

    def save_tableaus_json(self, filepath: str | Path) -> None:
        """Exporta o histórico completo de tableaus para arquivo JSON."""
        target_path = Path(filepath)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def solve(
        self,
        c: Sequence[float] | np.ndarray,
        A_ub: Optional[np.ndarray | Sequence[Sequence[float]]] = None,
        b_ub: Optional[Sequence[float] | np.ndarray] = None,
        A_eq: Optional[np.ndarray | Sequence[Sequence[float]]] = None,
        b_eq: Optional[Sequence[float] | np.ndarray] = None,
        bounds: Optional[List[Tuple[Optional[float], Optional[float]]]] = None,
        var_names: Optional[List[str]] = None,
        constraint_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executa a resolução em Duas Fases do problema de programação linear.
        """
        self.history = []
        c_obj = np.array(c, dtype=np.float64)
        n_vars = len(c_obj)

        if var_names is None or len(var_names) != n_vars:
            var_names = [f"x_{j+1}" for j in range(n_vars)]

        raw_constraints: List[np.ndarray] = []
        raw_rhs: List[float] = []
        type_constraints: List[str] = []  # 'LE' (<=), 'GE' (>=), 'EQ' (==)
        labels: List[str] = []

        # 1. Leitura de Restrições de Desigualdade A_ub x <= b_ub
        if A_ub is not None and b_ub is not None:
            A_mat = np.array(A_ub, dtype=np.float64)
            b_vec = np.array(b_ub, dtype=np.float64)
            for idx in range(len(b_vec)):
                raw_constraints.append(A_mat[idx].copy())
                raw_rhs.append(float(b_vec[idx]))
                type_constraints.append("LE")
                label_txt = (
                    constraint_names[idx]
                    if constraint_names and idx < len(constraint_names)
                    else f"Restricao_{idx+1}"
                )
                labels.append(label_txt)

        # 2. Leitura de Restrições de Igualdade A_eq x == b_eq
        if A_eq is not None and b_eq is not None:
            A_eq_mat = np.array(A_eq, dtype=np.float64)
            b_eq_vec = np.array(b_eq, dtype=np.float64)
            for idx in range(len(b_eq_vec)):
                raw_constraints.append(A_eq_mat[idx].copy())
                raw_rhs.append(float(b_eq_vec[idx]))
                type_constraints.append("EQ")
                labels.append(f"Igualdade_{idx+1}")

        # 3. Incorporação de Limites de Variáveis (Bounds)
        if bounds is not None:
            for j, (l_bound, u_bound) in enumerate(bounds):
                v_name = var_names[j]
                if l_bound is not None and l_bound > 0:
                    r_vec = np.zeros(n_vars, dtype=np.float64)
                    r_vec[j] = 1.0
                    raw_constraints.append(r_vec)
                    raw_rhs.append(float(l_bound))
                    type_constraints.append("GE")
                    labels.append(f"Limite_Min_{v_name}")
                if u_bound is not None and np.isfinite(u_bound):
                    r_vec = np.zeros(n_vars, dtype=np.float64)
                    r_vec[j] = 1.0
                    raw_constraints.append(r_vec)
                    raw_rhs.append(float(u_bound))
                    type_constraints.append("LE")
                    labels.append(f"Limite_Max_{v_name}")

        m_rows = len(raw_constraints)
        if m_rows == 0:
            return {
                "success": False,
                "status": 2,
                "message": "Modelo inconsistente: nenhuma restrição fornecida.",
                "x": None,
                "fun": 0.0,
                "nit": 0,
                "tableaus": [],
            }

        # 4. Normalização de b_i >= 0 (inversão de sinal quando o termo independente for negativo)
        std_matrix_rows: List[np.ndarray] = []
        std_rhs_vals: List[float] = []
        std_types: List[str] = []

        for i in range(m_rows):
            coefs = raw_constraints[i].copy()
            b_val = raw_rhs[i]
            c_type = type_constraints[i]

            if b_val < -self.tol:
                coefs = -coefs
                b_val = -b_val
                if c_type == "LE":
                    c_type = "GE"
                elif c_type == "GE":
                    c_type = "LE"
            elif abs(b_val) <= self.tol:
                b_val = 0.0

            std_matrix_rows.append(coefs)
            std_rhs_vals.append(b_val)
            std_types.append(c_type)

        # 5. Estruturação das Variáveis Auxiliares
        # Slacks para <=, Surplus + Artificial para >=, Artificial para ==
        n_slack = sum(1 for t in std_types if t == "LE")
        n_surplus = sum(1 for t in std_types if t == "GE")
        n_artificial = n_surplus + sum(1 for t in std_types if t == "EQ")
        n_total_p1 = n_vars + n_slack + n_surplus + n_artificial

        slack_col_names = [f"s_{i+1}" for i in range(n_slack)]
        surplus_col_names = [f"e_{i+1}" for i in range(n_surplus)]
        artificial_col_names = [f"a_{i+1}" for i in range(n_artificial)]
        all_cols_p1 = var_names + slack_col_names + surplus_col_names + artificial_col_names

        # Matriz ampliada
        A_augmented = np.zeros((m_rows, n_total_p1), dtype=np.float64)
        b_augmented = np.array(std_rhs_vals, dtype=np.float64)
        current_basis: List[int] = []
        artificial_indices: List[int] = []

        idx_s = n_vars
        idx_e = n_vars + n_slack
        idx_a = n_vars + n_slack + n_surplus

        mapping_structural: List[Tuple[str, int]] = []

        for i in range(m_rows):
            A_augmented[i, :n_vars] = std_matrix_rows[i]
            t = std_types[i]
            if t == "LE":
                A_augmented[i, idx_s] = 1.0
                current_basis.append(idx_s)
                mapping_structural.append(("LE", idx_s))
                idx_s += 1
            elif t == "GE":
                A_augmented[i, idx_e] = -1.0
                A_augmented[i, idx_a] = 1.0
                current_basis.append(idx_a)
                artificial_indices.append(idx_a)
                mapping_structural.append(("GE", idx_e))
                idx_e += 1
                idx_a += 1
            else:  # EQ
                A_augmented[i, idx_a] = 1.0
                current_basis.append(idx_a)
                artificial_indices.append(idx_a)
                mapping_structural.append(("EQ", idx_a))
                idx_a += 1

        cumulative_iterations = 0

        # =====================================================================
        # FASE 1: Viabilidade (Minimização de W = soma das variáveis artificiais)
        # =====================================================================
        if n_artificial > 0:
            tab_p1 = np.zeros((m_rows + 1, n_total_p1 + 1), dtype=np.float64)
            tab_p1[:m_rows, :n_total_p1] = A_augmented
            tab_p1[:m_rows, -1] = b_augmented

            # Linha objetivo da Fase 1: W = sum(a_k).
            # Para manter forma canônica, subtrai-se as linhas correspondentes às variáveis artificiais básicas
            for row_i, b_var in enumerate(current_basis):
                if b_var in artificial_indices:
                    tab_p1[-1, :n_total_p1] -= tab_p1[row_i, :n_total_p1]
                    tab_p1[-1, -1] -= tab_p1[row_i, -1]

            self._record_tableau_state(
                tableau=tab_p1,
                basis=current_basis,
                col_names=all_cols_p1,
                row_labels=labels,
                phase=1,
                iteration=0,
                description="Tableau Inicial da Fase 1: Busca de Solução Básica Viável inicial (min W = soma das variáveis artificiais).",
            )

            p1_converged, p1_iters = self._simplex_pivot_engine(
                tab_p1, current_basis, n_total_p1, all_cols_p1, labels, phase=1, iter_offset=0
            )
            cumulative_iterations += p1_iters

            violation_w = abs(tab_p1[-1, -1])
            if not p1_converged or violation_w > 1e-4:
                return {
                    "success": False,
                    "status": 2,
                    "message": f"Problema Inviável: Violação residual das artificiais W = {violation_w:.6f}",
                    "x": None,
                    "fun": 0.0,
                    "nit": cumulative_iterations,
                    "tableaus": self.history,
                }

            # Garantir que nenhuma variável artificial degenerada permaneça na base
            for row_i in range(m_rows):
                if current_basis[row_i] in artificial_indices:
                    for col_j in range(idx_a - n_artificial):
                        if abs(tab_p1[row_i, col_j]) > self.tol:
                            self._apply_gauss_jordan_pivot(tab_p1, current_basis, row_i, col_j)
                            break

            # Descartar colunas artificiais para a Fase 2
            n_cols_p2 = idx_a - n_artificial
            active_cols_p2 = list(range(n_cols_p2)) + [-1]
            sub_tab_p2 = tab_p1[:m_rows, active_cols_p2]
            cols_p2 = var_names + slack_col_names + surplus_col_names
        else:
            sub_tab_p2 = np.zeros((m_rows, n_total_p1 + 1), dtype=np.float64)
            sub_tab_p2[:m_rows, :n_total_p1] = A_augmented
            sub_tab_p2[:m_rows, -1] = b_augmented
            n_cols_p2 = n_total_p1
            cols_p2 = all_cols_p1

        # =====================================================================
        # FASE 2: Otimização Econômica da Ração (min Z = c^T x)
        # =====================================================================
        tab_p2 = np.zeros((m_rows + 1, n_cols_p2 + 1), dtype=np.float64)
        tab_p2[:m_rows, :] = sub_tab_p2

        # Vetor de custos para as variáveis ativas na Fase 2
        c_active = np.zeros(n_cols_p2, dtype=np.float64)
        c_active[:n_vars] = c_obj

        # Configurar linha de custo reduzido da função objetivo
        tab_p2[-1, :n_cols_p2] = c_active
        for row_i, b_var in enumerate(current_basis):
            c_b = c_active[b_var]
            if abs(c_b) > 1e-12:
                tab_p2[-1, :] -= c_b * tab_p2[row_i, :]

        self._record_tableau_state(
            tableau=tab_p2,
            basis=current_basis,
            col_names=cols_p2,
            row_labels=labels,
            phase=2,
            iteration=cumulative_iterations,
            description="Tableau Inicial da Fase 2: Ponto viável obtido. Início da minimização do custo econômico da ração.",
        )

        p2_converged, p2_iters = self._simplex_pivot_engine(
            tab_p2, current_basis, n_cols_p2, cols_p2, labels, phase=2, iter_offset=cumulative_iterations
        )
        cumulative_iterations += p2_iters

        if not p2_converged:
            return {
                "success": False,
                "status": 1,
                "message": "Iterações máximas do Simplex atingidas na Fase 2 sem convergência.",
                "x": None,
                "fun": 0.0,
                "nit": cumulative_iterations,
                "tableaus": self.history,
            }

        # Extração dos valores ótimos das variáveis de decisão
        sol_full = np.zeros(n_cols_p2, dtype=np.float64)
        for row_i, b_var in enumerate(current_basis):
            if b_var < n_cols_p2:
                sol_full[b_var] = max(0.0, tab_p2[row_i, -1])

        x_optimal = sol_full[:n_vars]
        z_optimal = float(np.dot(c_obj, x_optimal))

        # =====================================================================
        # ANÁLISE DE DUALIDADE & SENSIBILIDADE PARAMÉTRICA
        # =====================================================================
        shadow_prices, reduced_costs = self._compute_duals_and_reduced_costs(
            final_tableau=tab_p2,
            mapping_structural=mapping_structural,
            n_vars=n_vars,
            m_rows=m_rows,
        )

        cost_ranges, rhs_ranges = self._compute_post_optimal_sensitivity(
            final_tableau=tab_p2,
            basis=current_basis,
            c_obj=c_obj,
            n_vars=n_vars,
            m_rows=m_rows,
            n_cols=n_cols_p2,
            mapping_structural=mapping_structural,
        )

        self._record_tableau_state(
            tableau=tab_p2,
            basis=current_basis,
            col_names=cols_p2,
            row_labels=labels,
            phase=2,
            iteration=cumulative_iterations,
            description=f"Solução Ótima Convergida: Custo diário mínimo Z* = R$ {z_optimal:.4f}/vaca/dia. Todos os custos reduzidos são >= 0.",
            is_final=True,
        )

        return {
            "success": True,
            "status": 0,
            "x": x_optimal,
            "fun": z_optimal,
            "nit": cumulative_iterations,
            "basis": current_basis,
            "col_names": cols_p2,
            "row_labels": labels,
            "reduced_costs": reduced_costs,
            "shadow_prices": shadow_prices,
            "cost_sensitivity_ranges": cost_ranges,
            "rhs_sensitivity_ranges": rhs_ranges,
            "final_tableau": tab_p2.tolist(),
            "message": "Otimização linear convergida com sucesso via Simplex de Duas Fases.",
            "tableaus": self.history,
        }

    def _simplex_pivot_engine(
        self,
        tableau: np.ndarray,
        basis: List[int],
        n_active_vars: int,
        col_names: List[str],
        row_labels: List[str],
        phase: int,
        iter_offset: int,
    ) -> Tuple[bool, int]:
        """
        Executa as iterações de pivotamento do Simplex até a otimalidade ou limite de iterações.
        Regra de Dantzig para seleção da variável entrante e Teste da Razão Mínima para a sainte.
        """
        m_rows = len(basis)
        iteration_count = 0

        while iteration_count < self.max_iter:
            rc_vector = tableau[-1, :n_active_vars]
            min_rc = float(np.min(rc_vector))

            # Critério de Parada: se todos os custos reduzidos forem >= -tol, a base atual é ótima
            if min_rc >= -self.tol:
                return True, iteration_count

            # Variável Entrante: coluna com menor custo reduzido (regra de Dantzig)
            p_col = int(np.argmin(rc_vector))
            in_var_name = col_names[p_col]

            # Vetor de coeficientes da coluna pivô e valores do lado direito (RHS)
            col_entries = tableau[:m_rows, p_col]
            rhs_entries = tableau[:m_rows, -1]

            valid_pivots = col_entries > self.tol
            if not np.any(valid_pivots):
                # Solução ilimitada
                return False, iteration_count

            # Teste da Razão Mínima (Minimum Ratio Test - MRT)
            ratios = np.full(m_rows, np.inf, dtype=np.float64)
            ratios[valid_pivots] = rhs_entries[valid_pivots] / col_entries[valid_pivots]

            p_row = int(np.argmin(ratios))
            out_var_idx = basis[p_row]
            out_var_name = col_names[out_var_idx]
            min_ratio_val = float(ratios[p_row])
            p_val = float(tableau[p_row, p_col])

            iteration_count += 1
            current_iter_num = iter_offset + iteration_count

            step_desc = (
                f"Iteração {current_iter_num} (Fase {phase}): '{in_var_name}' entra na base "
                f"(custo reduzido = {min_rc:.4f}) substituindo '{out_var_name}' "
                f"(razão mínima = {min_ratio_val:.4f}). Pivô = {p_val:.4f}."
            )

            self._record_tableau_state(
                tableau=tableau,
                basis=basis,
                col_names=col_names,
                row_labels=row_labels,
                phase=phase,
                iteration=current_iter_num,
                pivot_row=p_row,
                pivot_col=p_col,
                pivot_val=p_val,
                entering_var=in_var_name,
                leaving_var=out_var_name,
                ratios=ratios.tolist(),
                description=step_desc,
            )

            # Executa o pivotamento elementar de Gauss-Jordan
            self._apply_gauss_jordan_pivot(tableau, basis, p_row, p_col)

        return False, iteration_count

    def _apply_gauss_jordan_pivot(
        self, tableau: np.ndarray, basis: List[int], pivot_row: int, pivot_col: int
    ) -> None:
        """Aplica as operações elementares de linha para normalizar a coluna do pivô."""
        p_val = tableau[pivot_row, pivot_col]
        tableau[pivot_row, :] /= p_val

        for i in range(tableau.shape[0]):
            if i != pivot_row:
                multiplier = tableau[i, pivot_col]
                if abs(multiplier) > 1e-15:
                    tableau[i, :] -= multiplier * tableau[pivot_row, :]

        basis[pivot_row] = pivot_col

    def _compute_duals_and_reduced_costs(
        self,
        final_tableau: np.ndarray,
        mapping_structural: List[Tuple[str, int]],
        n_vars: int,
        m_rows: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calcula os custos reduzidos analíticos (c_j - z_j) e os preços-sombra das restrições (variáveis duais y_i).
        """
        reduced_costs = np.maximum(0.0, final_tableau[-1, :n_vars])
        shadow_prices = np.zeros(m_rows, dtype=np.float64)

        for i, (con_type, col_pos) in enumerate(mapping_structural):
            if col_pos < final_tableau.shape[1] - 1:
                dual_val = final_tableau[-1, col_pos]
                shadow_prices[i] = max(0.0, float(dual_val))

        return shadow_prices, reduced_costs

    def _compute_post_optimal_sensitivity(
        self,
        final_tableau: np.ndarray,
        basis: List[int],
        c_obj: np.ndarray,
        n_vars: int,
        m_rows: int,
        n_cols: int,
        mapping_structural: List[Tuple[str, int]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Determina os intervalos analíticos de estabilidade de base para custos (c_j) e termos independentes (b_i).
        """
        cost_ranges: List[Dict[str, Any]] = []

        # Custos das variáveis na base atual
        c_full = np.zeros(n_cols, dtype=np.float64)
        c_full[:n_vars] = c_obj

        for j in range(n_vars):
            curr_c = float(c_obj[j])
            if j not in basis:
                # Variável não-básica: o custo pode aumentar indefinidamente; limite inferior é c_j - z_j
                rc = float(final_tableau[-1, j])
                c_min = curr_c - rc
                c_max = float("inf")
                allow_dec = rc
                allow_inc = float("inf")
                is_basic_flag = False
            else:
                # Variável básica: variação afeta toda a linha de custo reduzido
                row_idx = basis.index(j)
                dec_candidates = []
                inc_candidates = []

                for k in range(n_cols):
                    if k not in basis:
                        y_kj = final_tableau[row_idx, k]
                        rc_k = final_tableau[-1, k]
                        if y_kj > self.tol:
                            inc_candidates.append(rc_k / y_kj)
                        elif y_kj < -self.tol:
                            dec_candidates.append(-rc_k / y_kj)

                allow_inc = float(min(inc_candidates)) if inc_candidates else float("inf")
                allow_dec = float(min(dec_candidates)) if dec_candidates else float("inf")

                c_min = curr_c - allow_dec if np.isfinite(allow_dec) else -float("inf")
                c_max = curr_c + allow_inc if np.isfinite(allow_inc) else float("inf")
                is_basic_flag = True

            cost_ranges.append({
                "var_index": j,
                "is_basic": is_basic_flag,
                "current_cost": round(curr_c, 4),
                "min_cost": round(c_min, 4) if np.isfinite(c_min) else -float("inf"),
                "max_cost": round(c_max, 4) if np.isfinite(c_max) else float("inf"),
                "allowable_decrease": round(allow_dec, 4) if np.isfinite(allow_dec) else float("inf"),
                "allowable_increase": round(allow_inc, 4) if np.isfinite(allow_inc) else float("inf"),
            })

        # Intervalos de sensibilidade do Lado Direito (b_i)
        rhs_ranges: List[Dict[str, Any]] = []
        rhs_col = final_tableau[:m_rows, -1]

        for i, (con_type, col_pos) in enumerate(mapping_structural):
            if col_pos < n_cols:
                b_matrix_col = final_tableau[:m_rows, col_pos]
                inc_list = []
                dec_list = []

                for r in range(m_rows):
                    b_elem = b_matrix_col[r]
                    x_r = rhs_col[r]
                    if b_elem > self.tol:
                        inc_list.append(x_r / b_elem)
                    elif b_elem < -self.tol:
                        dec_list.append(-x_r / b_elem)

                rhs_inc = float(min(inc_list)) if inc_list else float("inf")
                rhs_dec = float(min(dec_list)) if dec_list else float("inf")

                rhs_ranges.append({
                    "constraint_index": i,
                    "allowable_increase": round(rhs_inc, 4) if np.isfinite(rhs_inc) else float("inf"),
                    "allowable_decrease": round(rhs_dec, 4) if np.isfinite(rhs_dec) else float("inf"),
                })
            else:
                rhs_ranges.append({
                    "constraint_index": i,
                    "allowable_increase": float("inf"),
                    "allowable_decrease": float("inf"),
                })

        return cost_ranges, rhs_ranges

    def _record_tableau_state(
        self,
        tableau: np.ndarray,
        basis: List[int],
        col_names: List[str],
        row_labels: List[str],
        phase: int,
        iteration: int,
        pivot_row: Optional[int] = None,
        pivot_col: Optional[int] = None,
        pivot_val: Optional[float] = None,
        entering_var: Optional[str] = None,
        leaving_var: Optional[str] = None,
        ratios: Optional[List[float]] = None,
        description: str = "",
        is_final: bool = False,
    ) -> None:
        """Registra o snapshot estruturado do tableau atual para análise visual e didática."""
        m_rows = len(basis)
        matrix_rows_data = []

        for r in range(m_rows):
            b_var_idx = basis[r]
            b_var_name = col_names[b_var_idx] if b_var_idx < len(col_names) else f"Base_{r+1}"
            label = row_labels[r] if r < len(row_labels) else f"Restricao_{r+1}"
            ratio_val = ratios[r] if ratios and r < len(ratios) and np.isfinite(ratios[r]) else None

            matrix_rows_data.append({
                "row_index": r,
                "label": label,
                "basic_var": b_var_name,
                "coefficients": [float(x) for x in tableau[r, :-1]],
                "rhs": float(tableau[r, -1]),
                "ratio": ratio_val,
            })

        reduced_costs_row = [float(x) for x in tableau[-1, :-1]]
        obj_val = float(tableau[-1, -1])

        self.history.append({
            "iteration": iteration,
            "phase": phase,
            "phase_name": "Fase 1 (Viabilidade)" if phase == 1 else "Fase 2 (Otimização)",
            "is_final": is_final,
            "col_names": list(col_names),
            "row_labels": list(row_labels),
            "matrix_rows": matrix_rows_data,
            "reduced_costs": reduced_costs_row,
            "objective_value": obj_val,
            "pivot_row": pivot_row,
            "pivot_col": pivot_col,
            "pivot_val": pivot_val,
            "entering_var": entering_var,
            "leaving_var": leaving_var,
            "description": description,
        })
