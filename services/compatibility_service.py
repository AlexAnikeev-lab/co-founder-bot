"""
Сервис для расчета совместимости и профиля пользователя
Реализует логику расчета согласно документации
"""

from typing import Optional, Dict, Tuple
import json
from texts.i18n import t


class CompatibilityService:
    """Сервис расчета совместимости"""
    
    # Таблицы конвертации ответов в числовые значения для основного теста
    MAIN_TEST_SCORING = {
        # Q3, Q4 - Ценности и этика
        "ethics": {
            "a": 0,
            "b": 50,
            "c": 100
        },
        # Q5 - Цели и мотивация
        "goals_q5": {
            "a": 100,
            "b": 30,
            "c": 60,
            "d": 40
        },
        # Q6 - Цели и мотивация
        "goals_q6": {
            "a": 100,
            "b": 70,
            "c": 35,
            "d": 50
        },
        # Q7 - Риск
        "risk": {
            "a": 100,
            "b": 60,
            "c": 20
        },
        # Q8 - Принятие решений
        "decision": {
            "a": 90,
            "b": 40,
            "c": 55,
            "d": 50
        },
        # Q9 - Коммуникация
        "comm_q9": {
            "a": 85,
            "b": 60,
            "c": 20
        },
        # Q10 - Коммуникация
        "comm_q10": {
            "a": 80,
            "b": 45,
            "c": 65
        }
    }
    
    # Таблицы для дополнительных тестов
    EXTRA_TEST_SCORING = {
        "ethics_extra": {
            "E1": "scale",  # Шкала 1-5
            "E2": {"a": 0, "b": 50, "c": 100},
            "E3": "scale",
            "E4": {"a": 0, "b": 50, "c": 100},
            "E5": {"a": 0, "b": 50, "c": 100},
            "E6": {"a": 0, "b": 50, "c": 100},
            "E7": {"a": 20, "b": 50, "c": 80},
            "E8": {"a": 0, "b": 60, "c": 100},
            "E9": {"a": 0, "b": 60, "c": 100},
            "E10": {"a": 0, "b": 50, "c": 100}
        },
        "goals_extra": {
            "G1": {"a": 100, "b": 30, "c": 60, "d": 40},
            "G2": {"a": 80, "b": 60, "c": 40, "d": 20},
            "G3": {"a": 40, "b": 100, "c": 30, "d": 90},
            "G4": {"a": 100, "b": 60, "c": 20, "d": 50},
            "G5": {"a": 100, "b": 30, "c": 40, "d": 80},
            "G6": "scale",
            "G7": {"a": 100, "b": 75, "c": 50, "d": 25},
            "G8": {"a": 100, "b": 40, "c": 60, "d": 50},
            "G9": {"a": 100, "b": 35, "c": 30, "d": 80},
            "G10": {"a": 100, "b": 60, "c": 80, "d": 70}
        },
        "risk_extra": {
            "K1": {"a": 100, "b": 70, "c": 35, "d": 10},
            "K2": {"a": 95, "b": 65, "c": 25, "d": 5},
            "K3": {"a": 90, "b": 60, "c": 30, "d": 10},
            "K4": "scale",
            "K5": {"a": 90, "b": 60, "c": 30, "d": 10},
            "K6": {"a": 90, "b": 60, "c": 30, "d": 10},
            "K7": {"a": 90, "b": 60, "c": 30, "d": 10},
            "K8": {"a": 90, "b": 60, "c": 35, "d": 15},
            "K9": {"a": 90, "b": 60, "c": 30, "d": 10},
            "K10": {"a": 90, "b": 60, "c": 30, "d": 10}
        },
        "decision_extra": {
            "D1": {"a": 90, "b": 20, "c": 55, "d": 10},
            "D2": {"a": 80, "b": 35, "c": 60, "d": 20},
            "D3": {"a": 85, "b": 60, "c": 30, "d": 55},
            "D4": {"a": 90, "b": 20, "c": 50, "d": 40},
            "D5": "scale",
            "D6": "scale",
            "D7": {"a": 85, "b": 30, "c": 55, "d": 50},
            "D8": {"a": 85, "b": 60, "c": 30, "d": 55},
            "D9": {"a": 90, "b": 60, "c": 25, "d": 10},
            "D10": {"a": 85, "b": 55, "c": 25, "d": 15}
        },
        "comm_extra": {
            "C1": {"a": 90, "b": 70, "c": 30, "d": 50},
            "C2": {"a": 85, "b": 65, "c": 25, "d": 55},
            "C3": {"a": 85, "b": 70, "c": 35, "d": 25},
            "C4": {"a": 90, "b": 70, "c": 40, "d": 20},
            "C5": {"a": 85, "b": 75, "c": 30, "d": 20},
            "C6": {"a": 85, "b": 75, "c": 35, "d": 25},
            "C7": "scale",
            "C8": "scale",
            "C9": {"a": 80, "b": 65, "c": 35, "d": 20},
            "C10": {"a": 85, "b": 55, "c": 35, "d": 75}
        }
    }
    
    @staticmethod
    def convert_scale_to_score(scale_value: str) -> int:
        """Конвертация шкалы 1-5 в 0-100"""
        scale_map = {
            "1": 0,
            "2": 25,
            "3": 50,
            "4": 75,
            "5": 100
        }
        return scale_map.get(scale_value, 50)
    
    @staticmethod
    def calculate_main_test_profile(answers: Dict[str, str]) -> Dict[str, any]:
        """
        Расчет профиля по основному тесту
        
        Args:
            answers: Словарь ответов {"Q1": "a", "Q2": "b", ...}
        
        Returns:
            Словарь с рассчитанными значениями
        """
        # B1) Роли HHH
        q1_role = "Hustler" if answers.get("Q1") == "a" else ("Hacker" if answers.get("Q1") == "b" else "Hipster")
        q2_role = "Hustler" if answers.get("Q2") == "a" else ("Hacker" if answers.get("Q2") == "b" else "Hipster")
        
        h_count = sum(1 for role in [q1_role, q2_role] if role == "Hustler")
        k_count = sum(1 for role in [q1_role, q2_role] if role == "Hacker")
        p_count = sum(1 for role in [q1_role, q2_role] if role == "Hipster")
        
        hustler_main = round((h_count / 2) * 100)
        hacker_main = round((k_count / 2) * 100)
        hipster_main = 100 - hustler_main - hacker_main
        
        # B2) Ценности и этика
        q3_score = CompatibilityService.MAIN_TEST_SCORING["ethics"].get(answers.get("Q3", ""), 50)
        q4_score = CompatibilityService.MAIN_TEST_SCORING["ethics"].get(answers.get("Q4", ""), 50)
        ethics_main = round((q3_score + q4_score) / 2)
        
        # B3) Цели и мотивация
        q5_score = CompatibilityService.MAIN_TEST_SCORING["goals_q5"].get(answers.get("Q5", ""), 50)
        q6_score = CompatibilityService.MAIN_TEST_SCORING["goals_q6"].get(answers.get("Q6", ""), 50)
        goals_main = round((q5_score + q6_score) / 2)
        
        # B4) Риск
        risk_main = CompatibilityService.MAIN_TEST_SCORING["risk"].get(answers.get("Q7", ""), 50)
        
        # B5) Принятие решений
        decision_main = CompatibilityService.MAIN_TEST_SCORING["decision"].get(answers.get("Q8", ""), 50)
        
        # B6) Коммуникация
        q9_score = CompatibilityService.MAIN_TEST_SCORING["comm_q9"].get(answers.get("Q9", ""), 50)
        q10_score = CompatibilityService.MAIN_TEST_SCORING["comm_q10"].get(answers.get("Q10", ""), 50)
        comm_main = round((q9_score + q10_score) / 2)
        
        return {
            "hustler_main": hustler_main,
            "hacker_main": hacker_main,
            "hipster_main": hipster_main,
            "ethics_main": ethics_main,
            "goals_main": goals_main,
            "risk_main": risk_main,
            "decision_main": decision_main,
            "comm_main": comm_main
        }
    
    @staticmethod
    def calculate_extra_test_score(test_type: str, answers: Dict[str, str]) -> Optional[int]:
        """
        Расчет балла по дополнительному тесту
        
        Args:
            test_type: Тип теста (ethics_extra, goals_extra, risk_extra, decision_extra, comm_extra)
            answers: Словарь ответов {"Q1": "a", "Q2": "b", ...}
        
        Returns:
            Балл 0-100 или None если тест не пройден
        """
        if test_type not in CompatibilityService.EXTRA_TEST_SCORING:
            return None
        
        scoring_table = CompatibilityService.EXTRA_TEST_SCORING[test_type]
        scores = []
        
        for i in range(1, 11):
            question_key = f"Q{i}"
            answer = answers.get(question_key)
            if not answer:
                continue
            
            # Определяем ключ для таблицы (E1, G1, K1, D1, C1)
            prefix = test_type[0].upper() if test_type.startswith("ethics") else test_type[0].upper()
            if test_type.startswith("ethics"):
                table_key = f"E{i}"
            elif test_type.startswith("goals"):
                table_key = f"G{i}"
            elif test_type.startswith("risk"):
                table_key = f"K{i}"
            elif test_type.startswith("decision"):
                table_key = f"D{i}"
            elif test_type.startswith("comm"):
                table_key = f"C{i}"
            else:
                continue
            
            if table_key not in scoring_table:
                continue
            
            scoring_rule = scoring_table[table_key]
            
            if scoring_rule == "scale":
                # Шкала 1-5
                score = CompatibilityService.convert_scale_to_score(answer)
            elif isinstance(scoring_rule, dict):
                # Таблица соответствия
                score = scoring_rule.get(answer, 50)
            else:
                score = 50
            
            scores.append(score)
        
        if not scores:
            return None
        
        return round(sum(scores) / len(scores))
    
    @staticmethod
    def calculate_roles_extra(answers: Dict[str, str]) -> Dict[str, int]:
        """
        Расчет ролей по дополнительному тесту
        
        Args:
            answers: Словарь ответов {"Q1": "a", "Q2": "b", ...}
        
        Returns:
            Словарь с процентами ролей
        """
        h_count = sum(1 for i in range(1, 11) if answers.get(f"Q{i}") == "a")
        k_count = sum(1 for i in range(1, 11) if answers.get(f"Q{i}") == "b")
        p_count = sum(1 for i in range(1, 11) if answers.get(f"Q{i}") == "c")
        
        total = h_count + k_count + p_count
        if total == 0:
            return {"hustler": 0, "hacker": 0, "hipster": 0}
        
        hustler_extra = round((h_count / total) * 100)
        hacker_extra = round((k_count / total) * 100)
        hipster_extra = 100 - hustler_extra - hacker_extra
        
        return {
            "hustler": hustler_extra,
            "hacker": hacker_extra,
            "hipster": hipster_extra
        }
    
    @staticmethod
    def calculate_final_profile(
        main_profile: Dict[str, any],
        roles_extra: Optional[Dict[str, int]] = None,
        ethics_extra: Optional[int] = None,
        goals_extra: Optional[int] = None,
        risk_extra: Optional[int] = None,
        decision_extra: Optional[int] = None,
        comm_extra: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Расчет финального профиля с учетом дополнительных тестов
        
        Args:
            main_profile: Профиль из основного теста
            roles_extra: Роли из дополнительного теста (если есть)
            ethics_extra: Балл этики из дополнительного теста (если есть)
            goals_extra: Балл целей из дополнительного теста (если есть)
            risk_extra: Балл риска из дополнительного теста (если есть)
            decision_extra: Балл решений из дополнительного теста (если есть)
            comm_extra: Балл коммуникации из дополнительного теста (если есть)
        
        Returns:
            Финальный профиль
        """
        # D1) Финальные роли
        if roles_extra:
            hustler_final = round(main_profile["hustler_main"] * 0.35 + roles_extra["hustler"] * 0.65)
            hacker_final = round(main_profile["hacker_main"] * 0.35 + roles_extra["hacker"] * 0.65)
            hipster_final = 100 - hustler_final - hacker_final
        else:
            hustler_final = main_profile["hustler_main"]
            hacker_final = main_profile["hacker_main"]
            hipster_final = main_profile["hipster_main"]
        
        # D2) Финальные числовые факторы
        ethics_final = round(main_profile["ethics_main"] * 0.35 + ethics_extra * 0.65) if ethics_extra is not None else main_profile["ethics_main"]
        goals_final = round(main_profile["goals_main"] * 0.35 + goals_extra * 0.65) if goals_extra is not None else main_profile["goals_main"]
        risk_final = round(main_profile["risk_main"] * 0.35 + risk_extra * 0.65) if risk_extra is not None else main_profile["risk_main"]
        decision_final = round(main_profile["decision_main"] * 0.35 + decision_extra * 0.65) if decision_extra is not None else main_profile["decision_main"]
        comm_final = round(main_profile["comm_main"] * 0.35 + comm_extra * 0.65) if comm_extra is not None else main_profile["comm_main"]
        
        # Определение лейбла профиля
        max_role = max(hustler_final, hacker_final, hipster_final)
        if max_role >= 45:
            if hustler_final == max_role:
                profile_label = "Hustler"
            elif hacker_final == max_role:
                profile_label = "Hacker"
            else:
                profile_label = "Hipster"
        else:
            profile_label = f"Hybrid (H/K/P: {hustler_final}/{hacker_final}/{hipster_final})"
        
        return {
            "hustler_percent": hustler_final,
            "hacker_percent": hacker_final,
            "hipster_percent": hipster_final,
            "ethics_score": ethics_final,
            "goals_score": goals_final,
            "risk_score": risk_final,
            "decision_score": decision_final,
            "comm_score": comm_final,
            "profile_label": profile_label
        }
    
    @staticmethod
    def calculate_compatibility(profile_a: Dict[str, any], profile_b: Dict[str, any]) -> int:
        """
        Расчет совместимости между двумя профилями
        
        Args:
            profile_a: Профиль пользователя A
            profile_b: Профиль пользователя B
        
        Returns:
            Процент совместимости 0-100
        """
        # E1) Частные совместимости по числовым факторам
        score_ethics = 100 - abs(profile_a["ethics_score"] - profile_b["ethics_score"])
        score_goals = 100 - abs(profile_a["goals_score"] - profile_b["goals_score"])
        score_risk = 100 - abs(profile_a["risk_score"] - profile_b["risk_score"])
        score_decision = 100 - abs(profile_a["decision_score"] - profile_b["decision_score"])
        score_comm = 100 - abs(profile_a["comm_score"] - profile_b["comm_score"])
        
        # E2) Совместимость ролей
        d_h = abs(profile_a["hustler_percent"] - profile_b["hustler_percent"])
        d_k = abs(profile_a["hacker_percent"] - profile_b["hacker_percent"])
        d_p = abs(profile_a["hipster_percent"] - profile_b["hipster_percent"])
        
        similarity = 100 - round((d_h + d_k + d_p) / 2)
        role_score = round(70 + (100 - similarity) * 0.3)
        role_score = max(0, min(100, role_score))  # Ограничение 0-100
        
        # E3) Базовая совместимость
        base = round(
            score_ethics * 0.22 +
            score_goals * 0.18 +
            role_score * 0.16 +
            score_risk * 0.14 +
            score_decision * 0.15 +
            score_comm * 0.15
        )
        
        # E4) Red flags (штрафы)
        diff_ethics = abs(profile_a["ethics_score"] - profile_b["ethics_score"])
        diff_goals = abs(profile_a["goals_score"] - profile_b["goals_score"])
        diff_risk = abs(profile_a["risk_score"] - profile_b["risk_score"])
        diff_comm = abs(profile_a["comm_score"] - profile_b["comm_score"])
        diff_decision = abs(profile_a["decision_score"] - profile_b["decision_score"])
        
        penalty = 0
        
        # RF1 Ethics
        if diff_ethics >= 60:
            penalty += 18
        elif diff_ethics >= 40:
            penalty += 8
        
        # RF2 Goals
        if diff_goals >= 60:
            penalty += 12
        elif diff_goals >= 40:
            penalty += 6
        
        # RF3 Risk
        if diff_risk >= 70:
            penalty += 10
        elif diff_risk >= 50:
            penalty += 5
        
        # RF4 Comm
        if diff_comm >= 70:
            penalty += 10
        elif diff_comm >= 50:
            penalty += 4
        
        # RF5 Decision
        if diff_decision >= 70:
            penalty += 8
        elif diff_decision >= 50:
            penalty += 3
        
        # E5) Итоговая совместимость
        final_compatibility = base - penalty
        final_compatibility = max(0, min(100, final_compatibility))
        
        return final_compatibility
    
    @staticmethod
    def calculate_compatibility_detailed(
        profile_a: Dict[str, any],
        profile_b: Dict[str, any]
    ) -> Tuple[int, Dict[str, any]]:
        """
        Расчёт совместимости с подробной разбивкой для проверки логики.
        
        Returns:
            (итоговый_процент, словарь с деталями)
        """
        # E1) Частные совместимости по числовым факторам
        diff_ethics = abs(profile_a["ethics_score"] - profile_b["ethics_score"])
        diff_goals = abs(profile_a["goals_score"] - profile_b["goals_score"])
        diff_risk = abs(profile_a["risk_score"] - profile_b["risk_score"])
        diff_decision = abs(profile_a["decision_score"] - profile_b["decision_score"])
        diff_comm = abs(profile_a["comm_score"] - profile_b["comm_score"])
        
        score_ethics = 100 - diff_ethics
        score_goals = 100 - diff_goals
        score_risk = 100 - diff_risk
        score_decision = 100 - diff_decision
        score_comm = 100 - diff_comm
        
        # E2) Совместимость ролей
        d_h = abs(profile_a["hustler_percent"] - profile_b["hustler_percent"])
        d_k = abs(profile_a["hacker_percent"] - profile_b["hacker_percent"])
        d_p = abs(profile_a["hipster_percent"] - profile_b["hipster_percent"])
        
        similarity = 100 - round((d_h + d_k + d_p) / 2)
        role_score = round(70 + (100 - similarity) * 0.3)
        role_score = max(0, min(100, role_score))
        
        # E3) Базовая совместимость (веса: ethics 0.22, goals 0.18, role 0.16, risk 0.14, decision 0.15, comm 0.15)
        base = round(
            score_ethics * 0.22 +
            score_goals * 0.18 +
            role_score * 0.16 +
            score_risk * 0.14 +
            score_decision * 0.15 +
            score_comm * 0.15
        )
        
        # E4) Red flags (штрафы)
        penalty = 0
        penalty_details = []
        
        if diff_ethics >= 60:
            penalty += 18
            penalty_details.append("RF1 Ethics: diff>=60 → -18")
        elif diff_ethics >= 40:
            penalty += 8
            penalty_details.append("RF1 Ethics: diff>=40 → -8")
        
        if diff_goals >= 60:
            penalty += 12
            penalty_details.append("RF2 Goals: diff>=60 → -12")
        elif diff_goals >= 40:
            penalty += 6
            penalty_details.append("RF2 Goals: diff>=40 → -6")
        
        if diff_risk >= 70:
            penalty += 10
            penalty_details.append("RF3 Risk: diff>=70 → -10")
        elif diff_risk >= 50:
            penalty += 5
            penalty_details.append("RF3 Risk: diff>=50 → -5")
        
        if diff_comm >= 70:
            penalty += 10
            penalty_details.append("RF4 Comm: diff>=70 → -10")
        elif diff_comm >= 50:
            penalty += 4
            penalty_details.append("RF4 Comm: diff>=50 → -4")
        
        if diff_decision >= 70:
            penalty += 8
            penalty_details.append("RF5 Decision: diff>=70 → -8")
        elif diff_decision >= 50:
            penalty += 3
            penalty_details.append("RF5 Decision: diff>=50 → -3")
        
        final_compatibility = base - penalty
        final_compatibility = max(0, min(100, final_compatibility))
        
        details = {
            "profile_a": dict(profile_a),
            "profile_b": dict(profile_b),
            "E1_scores": {
                "score_ethics": score_ethics,
                "score_goals": score_goals,
                "score_risk": score_risk,
                "score_decision": score_decision,
                "score_comm": score_comm,
                "diffs": {
                    "ethics": diff_ethics,
                    "goals": diff_goals,
                    "risk": diff_risk,
                    "decision": diff_decision,
                    "comm": diff_comm,
                },
            },
            "E2_roles": {
                "d_h": d_h,
                "d_k": d_k,
                "d_p": d_p,
                "similarity": similarity,
                "role_score": role_score,
            },
            "E3_base": base,
            "E4_penalty": penalty,
            "E4_penalty_details": penalty_details,
            "E5_final": final_compatibility,
        }
        return final_compatibility, details

    @staticmethod
    def get_compatibility_explanation(score: int, details: Dict[str, any], lang: str = "ru") -> str:
        """
        Формирует структурированный текст «почему такая совместимость»:
        секции «По тестам», «Роли в команде», «Учтено при расчёте» (штрафы), «Итог».
        """
        blocks = []

        # ——— Секция: по результатам тестов (списком) ———
        e1 = details.get("E1_scores") or {}
        scores = {
            "ethics": (e1.get("score_ethics"), t(lang, "compat_factor_ethics")),
            "goals": (e1.get("score_goals"), t(lang, "compat_factor_goals")),
            "risk": (e1.get("score_risk"), t(lang, "compat_factor_risk")),
            "decision": (e1.get("score_decision"), t(lang, "compat_factor_decision")),
            "comm": (e1.get("score_comm"), t(lang, "compat_factor_comm")),
        }
        lines = []
        for key, (val, label) in scores.items():
            if val is None:
                continue
            if val >= 80:
                suffix = f" ({t(lang, 'compat_suffix_very_close')})"
            elif val >= 60:
                suffix = ""
            elif val >= 40:
                suffix = f" ({t(lang, 'compat_suffix_some_diff')})"
            else:
                suffix = f" ({t(lang, 'compat_suffix_different')})"
            lines.append(f"• {label} — {val}%{suffix}")
        if lines:
            blocks.append(f"{t(lang, 'compat_section_tests')}\n" + "\n".join(lines))

        # ——— Секция: роли в команде ———
        profile_a = details.get("profile_a") or {}
        profile_b = details.get("profile_b") or {}
        label_a = profile_a.get("profile_label")
        label_b = profile_b.get("profile_label")
        if label_a and label_b:
            if label_a == label_b:
                role_text = t(lang, "compat_roles_same", role=label_a)
            else:
                role_text = t(lang, "compat_roles_diff", role_a=label_a, role_b=label_b)
            blocks.append(f"{t(lang, 'compat_section_roles')}\n{role_text}")

        # ——— Секция: штрафы (если есть) ———
        penalty = details.get("E4_penalty") or 0
        penalty_details = details.get("E4_penalty_details") or []
        if penalty > 0 and penalty_details:
            rf_names = []
            for p in penalty_details:
                if "Ethics" in p:
                    rf_names.append(t(lang, "compat_penalty_ethics"))
                elif "Goals" in p:
                    rf_names.append(t(lang, "compat_penalty_goals"))
                elif "Risk" in p:
                    rf_names.append(t(lang, "compat_penalty_risk"))
                elif "Comm" in p:
                    rf_names.append(t(lang, "compat_penalty_comm"))
                elif "Decision" in p:
                    rf_names.append(t(lang, "compat_penalty_decision"))
            if rf_names:
                blocks.append(
                    f"{t(lang, 'compat_section_penalty')}\n"
                    f"{t(lang, 'compat_penalty_intro', factors=', '.join(rf_names))}"
                )

        # ——— Секция: итог ———
        if score >= 75:
            summary = t(lang, "compat_summary_high")
        elif score >= 55:
            summary = t(lang, "compat_summary_mid")
        else:
            summary = t(lang, "compat_summary_low")
        blocks.append(f"{t(lang, 'compat_section_summary')}\n{summary}")

        return "\n\n".join(blocks)
