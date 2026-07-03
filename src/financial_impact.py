"""
Estimativa de impacto financeiro da ferramenta, a partir dos números dados no
desafio: hoje, 5 analistas levam 3 dias por ciclo de análise, salário de R$5.000.

O PDF não diz se R$5.000 é mensal ou por ciclo — assumo mensal (leitura mais
natural de "custo salarial") e derivo o custo por dia útil. Todas as premissas
ficam explícitas e parametrizadas, para ajustar ao vivo na entrevista se
necessário.
"""

from dataclasses import dataclass, asdict

import pandas as pd

from src.config import CONFIG

_CFG = CONFIG["financial_impact"]


@dataclass
class Assumptions:
    n_analysts_current: int = _CFG["n_analysts_current"]
    salary_month: float = _CFG["salary_month"]
    work_days_month: int = _CFG["work_days_month"]
    days_per_cycle_current: float = _CFG["days_per_cycle_current"]
    n_analysts_with_tool: float = _CFG["n_analysts_with_tool"]
    days_per_cycle_with_tool: float = _CFG["days_per_cycle_with_tool"]  # revisão/validação humana
    analyses_per_month: int = _CFG["analyses_per_month"]  # premissa — ajustável


def daily_rate(a: Assumptions) -> float:
    return a.salary_month / a.work_days_month


def cost_per_cycle(n_analysts: float, days: float, a: Assumptions) -> float:
    return n_analysts * days * daily_rate(a)


def compute_impact(a: Assumptions = Assumptions()) -> dict:
    rate = daily_rate(a)
    cost_current = cost_per_cycle(a.n_analysts_current, a.days_per_cycle_current, a)
    cost_with_tool = cost_per_cycle(a.n_analysts_with_tool, a.days_per_cycle_with_tool, a)
    savings_per_cycle = cost_current - cost_with_tool
    pct_reduction = savings_per_cycle / cost_current

    monthly_savings = savings_per_cycle * a.analyses_per_month
    annual_savings = monthly_savings * 12

    analyst_days_freed_per_cycle = (
        a.n_analysts_current * a.days_per_cycle_current
        - a.n_analysts_with_tool * a.days_per_cycle_with_tool
    )

    return {
        "assumptions": asdict(a),
        "daily_rate": rate,
        "cost_per_cycle_current": cost_current,
        "cost_per_cycle_with_tool": cost_with_tool,
        "savings_per_cycle": savings_per_cycle,
        "pct_reduction": pct_reduction,
        "analyst_days_freed_per_cycle": analyst_days_freed_per_cycle,
        "monthly_savings": monthly_savings,
        "annual_savings": annual_savings,
    }


def sensitivity_table(a: Assumptions = Assumptions(), scenarios=(1, 2, 4, 8, 12)) -> pd.DataFrame:
    rows = []
    for n in scenarios:
        scenario = Assumptions(**{**asdict(a), "analyses_per_month": n})
        result = compute_impact(scenario)
        rows.append(
            {
                "analises_por_mes": n,
                "economia_mensal": result["monthly_savings"],
                "economia_anual": result["annual_savings"],
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    result = compute_impact()
    print("Premissas:", result["assumptions"])
    print(f"\nTaxa diária por analista: R$ {result['daily_rate']:.2f}")
    print(f"Custo por ciclo HOJE (manual): R$ {result['cost_per_cycle_current']:,.2f}")
    print(f"Custo por ciclo COM a ferramenta: R$ {result['cost_per_cycle_with_tool']:,.2f}")
    print(f"Economia por ciclo: R$ {result['savings_per_cycle']:,.2f} ({result['pct_reduction']:.1%})")
    print(f"Dias-analista liberados por ciclo: {result['analyst_days_freed_per_cycle']:.1f}")
    print(f"\nCom {result['assumptions']['analyses_per_month']} ciclos/mês (premissa):")
    print(f"  Economia mensal: R$ {result['monthly_savings']:,.2f}")
    print(f"  Economia anual: R$ {result['annual_savings']:,.2f}")

    print("\nSensibilidade (nº de ciclos de análise por mês):")
    print(sensitivity_table().to_string(index=False))
