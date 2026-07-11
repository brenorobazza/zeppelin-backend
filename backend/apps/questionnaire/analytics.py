import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

from apps.organization.models import Organization
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import AdoptedLevel, Answer, Questionnaire, Statement


@lru_cache(maxsize=1)
def load_recommendations_catalog():
    catalog_path = (
        Path(__file__).resolve().parent / "data" / "recommendations_catalog.csv"
    )
    if not catalog_path.exists():
        return {}

    with catalog_path.open(encoding="utf-8-sig", newline="") as catalog_file:
        reader = csv.DictReader(catalog_file)
        return {
            (row.get("Question number") or "").strip(): {
                "question_description": (row.get("Question Description") or "").strip(),
                "catalog_recommendation": (row.get("Recommendation") or "").strip(),
            }
            for row in reader
            if (row.get("Question number") or "").strip()
        }


class QuestionnaireAnalyticsService:
    DEFAULT_ORGANIZATION_TYPE_KEY = "software-house"
    ORGANIZATION_TYPE_WEIGHT_MAP = {
        "startup": {
            0: 0,
            10: 17,
            30: 33,
            60: 61,
            100: 100,
        },
        "software-house": {
            0: 0,
            10: 10,
            30: 30,
            60: 60,
            100: 100,
        },
        "organization-with-it-department": {
            0: 0,
            10: 22,
            30: 38,
            60: 68,
            100: 100,
        },
    }
    ORGANIZATION_TYPE_ALIASES = {
        "startup": "startup",
        "software": "software-house",
        "software-house": "software-house",
        "organization-with-it-department": "organization-with-it-department",
        "organization-with-ti-department": "organization-with-it-department",
        "organizacao-com-departamento-de-ti": "organization-with-it-department",
    }
    # Estágios usados como recorte principal da análise do frontend atual.
    CI_CD_STAGE_NAMES = (
        "Continuous Integration",
        "Continuous Deployment",
        "Integracao Continua",
        "Entrega Continua",
    )

    # Converte nomes completos do banco em siglas amigaveis para a interface.
    STAGE_SHORT_NAMES = {
        "Traditional Development": "Traditional",
        "Agile R&D Organization": "Agile",
        "Continuous Integration": "CI",
        "Continuous Deployment": "CD",
        "R&D as an Experiment System": "Experimentation",
        "Desenvolvimento Agil": "Agile",
        "Integracao Continua": "CI",
        "Entrega Continua": "CD",
        "Experimentacao Continua": "Experimentation",
    }

    # Mantem uma ordem previsivel de exibicao dos estagios.
    STAGE_ORDER = {
        "Traditional Development": 0,
        "Agile R&D Organization": 1,
        "Continuous Integration": 2,
        "Continuous Deployment": 3,
        "R&D as an Experiment System": 4,
        "Desenvolvimento Agil": 1,
        "Integracao Continua": 2,
        "Entrega Continua": 3,
        "Experimentacao Continua": 4,
    }

    DIMENSION_LABELS = {
        "Traditional Development": "Traditional Development",
        "Agile R&D Organization": "Agile Development",
        "Continuous Integration": "Continuous Integration",
        "Continuous Deployment": "Continuous Deployment",
        "R&D as an Experiment System": "Continuous Experimentation",
        "Desenvolvimento Agil": "Agile Development",
        "Integracao Continua": "Continuous Integration",
        "Entrega Continua": "Continuous Deployment",
        "Experimentacao Continua": "Continuous Experimentation",
    }
    DIMENSION_ORDER = {
        "Development": 0,
        "Quality": 1,
        "Software Management": 2,
        "Team": 3,
        "Technical Solution": 4,
        "Knowledge": 5,
        "Operation": 6,
        "Business": 7,
        "User/Customer": 8,
        "Agile Development": 9,
        "Continuous Integration": 10,
        "Continuous Deployment": 11,
        "Continuous Experimentation": 12,
        "Traditional Development": 13,
        "Unclassified": 999,
    }
    ADOPTION_OVERVIEW_STAGES = (
        {
            "key": "agile",
            "labels": (
                "Agile R&D Organization",
                "Desenvolvimento Agil",
            ),
            "title": "Agile R&D Organization",
        },
        {
            "key": "ci",
            "labels": (
                "Continuous Integration",
                "Integracao Continua",
            ),
            "title": "Continuous Integration",
        },
        {
            "key": "cd",
            "labels": (
                "Continuous Deployment",
                "Entrega Continua",
            ),
            "title": "Continuous Deployment",
        },
        {
            "key": "experimentation",
            "labels": (
                "R&D as an Experiment System",
                "Experimentacao Continua",
            ),
            "title": "R&D as an Experiment System",
        },
    )
    DIMENSION_STAGE_MATRIX_DIMENSIONS = (
        "Development",
        "Quality",
        "Software Management",
        "Team",
        "Technical Solution",
        "Knowledge",
        "Operation",
        "Business",
        "User/Customer",
    )
    PROCESS_OVERVIEW_PROCESSES = (
        "Business Alignment",
        "Continuous Planning, Monitoring and Control",
        "Continuous Quality Assurance",
        "Continuous Improvement & Innovation",
        "Continuous Knowledge Management",
        "Continuous Software Measurement",
    )
    DIMENSION_STAGE_BASELINE_COUNTS = {
        "Development": {"agile": 8, "experimentation": 0},
        "Quality": {"agile": 2, "experimentation": 0},
        "Software Management": {"agile": 10, "experimentation": 0},
        "Team": {"agile": 2, "experimentation": 2},
        "Technical Solution": {"agile": 1, "experimentation": 0},
        "Knowledge": {"agile": 2, "experimentation": 3},
        "Operation": {"agile": 0, "experimentation": 2},
        "Business": {"agile": 1, "experimentation": 3},
        "User/Customer": {"agile": 0, "experimentation": 3},
    }
    ELEMENT_STAGE_BASELINE_COUNTS = (
        {
            "dimension": "Development",
            "element": "Continuous planning activities",
            "agile": 6,
            "experimentation": 0,
        },
        {
            "dimension": "Development",
            "element": "Continuous requirements engineering",
            "agile": 1,
            "experimentation": 0,
        },
        {
            "dimension": "Development",
            "element": "Focus on Feature",
            "agile": 1,
            "experimentation": 0,
        },
        {
            "dimension": "Development",
            "element": "Modularized architecture and design",
            "agile": 0,
            "experimentation": 0,
        },
        {"dimension": "Quality", "element": "Audits", "agile": 2, "experimentation": 0},
        {
            "dimension": "Quality",
            "element": "Automated Tests",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Quality",
            "element": "Code coverage",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Quality",
            "element": "Pull-Request",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Quality",
            "element": "Regular Builds",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Software Management",
            "element": "Agile Practice",
            "agile": 10,
            "experimentation": 0,
        },
        {
            "dimension": "Software Management",
            "element": "Continuous delivery",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Software Management",
            "element": "Continuous deployment of releases",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Software Management",
            "element": "Continuous integration of work",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Team",
            "element": "Contemporary and continuously evolving skills",
            "agile": 1,
            "experimentation": 2,
        },
        {
            "dimension": "Team",
            "element": "Self-reflection and discipline",
            "agile": 1,
            "experimentation": 0,
        },
        {
            "dimension": "Technical Solution",
            "element": "Branching strategies",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Technical Solution",
            "element": "Code review",
            "agile": 1,
            "experimentation": 0,
        },
        {
            "dimension": "Technical Solution",
            "element": "Version control",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Knowledge",
            "element": "Capturing decisions and rationale",
            "agile": 1,
            "experimentation": 3,
        },
        {
            "dimension": "Knowledge",
            "element": "Continuous learning",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "Knowledge",
            "element": "Sharing Knowledge",
            "agile": 1,
            "experimentation": 0,
        },
        {
            "dimension": "Operation",
            "element": "Logging and monitoring",
            "agile": 0,
            "experimentation": 1,
        },
        {
            "dimension": "Operation",
            "element": "Reusable infrastructure",
            "agile": 0,
            "experimentation": 1,
        },
        {
            "dimension": "Business",
            "element": "Appropriate product idea",
            "agile": 0,
            "experimentation": 2,
        },
        {
            "dimension": "Business",
            "element": "Management commitment",
            "agile": 1,
            "experimentation": 1,
        },
        {
            "dimension": "User/Customer",
            "element": "Involved users other stakeholders",
            "agile": 0,
            "experimentation": 0,
        },
        {
            "dimension": "User/Customer",
            "element": "Learning from usage data and feedback",
            "agile": 0,
            "experimentation": 3,
        },
        {
            "dimension": "User/Customer",
            "element": "Proactive customers",
            "agile": 0,
            "experimentation": 0,
        },
    )
    ELEMENT_NAME_ALIASES = {
        "Appropriate product ideia": "Appropriate product idea",
        "Continuos delivery": "Continuous delivery",
        "Continuos deployment of releases": "Continuous deployment of releases",
        "Continuos integration of work": "Continuous integration of work",
        "Continuos learning": "Continuous learning",
        "Management commitement": "Management commitment",
    }
    STATEMENT_PROCESS_CATALOG = {
        "AO.01": ("Business Alignment",),
        "AO.02": ("Continuous Planning, Monitoring and Control",),
        "AO.03": ("Continuous Planning, Monitoring and Control",),
        "AO.04": ("Continuous Planning, Monitoring and Control",),
        "AO.05": ("Continuous Planning, Monitoring and Control",),
        "AO.06": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
        ),
        "AO.07": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
        ),
        "AO.08": ("Continuous Planning, Monitoring and Control",),
        "AO.09": (
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "AO.10": ("Continuous Quality Assurance",),
        "AO.11": ("Continuous Improvement & Innovation",),
        "AO.12": ("Continuous Improvement & Innovation",),
        "AO.13": ("Continuous Knowledge Management",),
        "AO.14": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Software Measurement",
        ),
        "AO.15": ("Continuous Improvement & Innovation",),
        "AO.16": ("Continuous Knowledge Management",),
        "AO.17": ("Continuous Quality Assurance",),
        "AO.18": ("Continuous Quality Assurance",),
        "AO.19": (
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "AO.20": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "AO.21": ("Continuous Knowledge Management",),
        "AO.22": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "AO.23": ("Continuous Quality Assurance",),
        "AO.24": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
            "Continuous Software Measurement",
        ),
        "AO.25": ("Continuous Knowledge Management",),
        "AO.26": ("Business Alignment",),
        "CI.01": ("Continuous Quality Assurance",),
        "CI.02": ("Continuous Planning, Monitoring and Control",),
        "CI.03": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "CI.04": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "CI.05": ("Continuous Quality Assurance",),
        "CI.06": ("Continuous Planning, Monitoring and Control",),
        "CI.07": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
        ),
        "CI.08": ("Continuous Quality Assurance",),
        "CI.09": ("Continuous Quality Assurance",),
        "CI.10": ("Continuous Planning, Monitoring and Control",),
        "CI.11": ("Continuous Planning, Monitoring and Control",),
        "CI.12": ("Continuous Planning, Monitoring and Control",),
        "CI.13": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "CI.14": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "CI.15": (
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "CI.16": (
            "Continuous Quality Assurance",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
            "Continuous Software Measurement",
        ),
        "CI.17": (
            "Continuous Quality Assurance",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
            "Continuous Software Measurement",
        ),
        "CI.18": (
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
        ),
        "CD.01": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "CD.02": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "CD.03": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "CD.04": (
            "Business Alignment",
            "Continuous Quality Assurance",
            "Continuous Software Measurement",
        ),
        "CD.05": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Improvement & Innovation",
            "Continuous Software Measurement",
        ),
        "CD.06": ("Continuous Improvement & Innovation",),
        "CD.07": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
        ),
        "CD.08": ("Business Alignment",),
        "CD.09": ("Continuous Knowledge Management",),
        "CD.10": ("Business Alignment",),
        "CD.11": ("Business Alignment",),
        "CD.12": ("Business Alignment",),
        "CD.13": ("Business Alignment",),
        "CD.14": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
            "Continuous Software Measurement",
        ),
        "CD.15": ("Continuous Quality Assurance",),
        "CD.16": ("Continuous Knowledge Management",),
        "CD.17": ("Continuous Improvement & Innovation",),
        "CD.18": ("Continuous Knowledge Management",),
        "CD.19": ("Continuous Knowledge Management",),
        "IS.01": ("Continuous Knowledge Management",),
        "IS.02": ("Business Alignment", "Continuous Knowledge Management"),
        "IS.03": (
            "Business Alignment",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
        ),
        "IS.04": ("Business Alignment",),
        "IS.05": (
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
        ),
        "IS.06": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
            "Continuous Software Measurement",
        ),
        "IS.07": ("Continuous Improvement & Innovation",),
        "IS.08": ("Continuous Improvement & Innovation",),
        "IS.09": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
        ),
        "IS.10": (
            "Continuous Planning, Monitoring and Control",
            "Continuous Quality Assurance",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
            "Continuous Software Measurement",
        ),
        "IS.11": (
            "Business Alignment",
            "Continuous Improvement & Innovation",
            "Continuous Knowledge Management",
        ),
        "IS.12": (
            "Business Alignment",
            "Continuous Planning, Monitoring and Control",
        ),
        "IS.13": ("Continuous Knowledge Management",),
    }
    INSTRUMENT_PRACTICE_CATALOG = {
        "AO.01": {"dimension": "Business", "element": "Management commitement"},
        "AO.02": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.03": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "AO.04": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "AO.05": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "AO.06": {"dimension": "Development", "element": "Focus on Feature"},
        "AO.07": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.08": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.09": {
            "dimension": "Development",
            "element": "Continuous requirements engineering",
        },
        "AO.10": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.11": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.12": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.13": {
            "dimension": "Team",
            "element": "Contemporary and continuously evolving skills",
        },
        "AO.14": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.15": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.16": {"dimension": "Team", "element": "Self-reflection and discipline"},
        "AO.17": {"dimension": "Technical Solution", "element": "Code review"},
        "AO.18": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.19": {"dimension": "Quality", "element": "Audits"},
        "AO.20": {"dimension": "Quality", "element": "Audits"},
        "AO.21": {
            "dimension": "Knowledge",
            "element": "Capturing decisions and rationale",
        },
        "AO.22": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "AO.23": {"dimension": "Software Management", "element": "Agile Practice"},
        "AO.24": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "AO.25": {"dimension": "Knowledge", "element": "Sharing Knowledge"},
        "AO.26": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "CI.01": {
            "dimension": "Development",
            "element": "Modularized architecture and design",
        },
        "CI.02": {
            "dimension": "Development",
            "element": "Modularized architecture and design",
        },
        "CI.03": {
            "dimension": "Software Management",
            "element": "Continuos integration of work",
        },
        "CI.04": {"dimension": "Quality", "element": "Automated Tests"},
        "CI.05": {"dimension": "Quality", "element": "Automated Tests"},
        "CI.06": {"dimension": "Quality", "element": "Regular Builds"},
        "CI.07": {"dimension": "Quality", "element": "Regular Builds"},
        "CI.08": {"dimension": "Technical Solution", "element": "Version control"},
        "CI.09": {"dimension": "Technical Solution", "element": "Branching strategies"},
        "CI.10": {"dimension": "Quality", "element": "Pull-Request"},
        "CI.11": {"dimension": "Quality", "element": "Code coverage"},
        "CI.12": {"dimension": "Quality", "element": "Audits"},
        "CI.13": {"dimension": "Software Management", "element": "Agile Practice"},
        "CI.14": {
            "dimension": "Development",
            "element": "Continuous planning activities",
        },
        "CI.15": {"dimension": "Knowledge", "element": "Sharing Knowledge"},
        "CD.01": {
            "dimension": "User/Customer",
            "element": "Involved users other stakeholders",
        },
        "CD.02": {"dimension": "Quality", "element": "Audits"},
        "CD.03": {
            "dimension": "Software Management",
            "element": "Continuos deployment of releases",
        },
        "CD.04": {"dimension": "Business", "element": "Management commitement"},
        "CD.05": {
            "dimension": "Development",
            "element": "Modularized architecture and design",
        },
        "CD.06": {"dimension": "User/Customer", "element": "Proactive customers"},
        "CD.07": {
            "dimension": "User/Customer",
            "element": "Learning from usage data and feedback",
        },
        "CD.08": {"dimension": "Business", "element": "Appropriate product ideia"},
        "CD.09": {"dimension": "Business", "element": "Management commitement"},
        "CD.10": {"dimension": "Business", "element": "Management commitement"},
        "CD.11": {
            "dimension": "User/Customer",
            "element": "Involved users other stakeholders",
        },
        "CD.12": {"dimension": "Software Management", "element": "Continuos delivery"},
        "CD.13": {
            "dimension": "Software Management",
            "element": "Continuos deployment of releases",
        },
        "CD.14": {
            "dimension": "Knowledge",
            "element": "Capturing decisions and rationale",
        },
        "CD.15": {"dimension": "Software Management", "element": "Agile Practice"},
        "CD.16": {"dimension": "Knowledge", "element": "Continuos learning"},
        "CD.17": {"dimension": "Knowledge", "element": "Sharing Knowledge"},
        "IS.01": {"dimension": "Knowledge", "element": "Continuos learning"},
        "IS.02": {"dimension": "Operation", "element": "Logging and monitoring"},
        "IS.03": {"dimension": "Business", "element": "Appropriate product ideia"},
        "IS.04": {"dimension": "Business", "element": "Appropriate product ideia"},
        "IS.05": {
            "dimension": "User/Customer",
            "element": "Learning from usage data and feedback",
        },
        "IS.06": {
            "dimension": "User/Customer",
            "element": "Learning from usage data and feedback",
        },
        "IS.07": {"dimension": "Operation", "element": "Reusable infrastructure"},
        "IS.08": {"dimension": "Knowledge", "element": "Continuos learning"},
        "IS.09": {"dimension": "Business", "element": "Management commitement"},
        "IS.10": {
            "dimension": "Team",
            "element": "Contemporary and continuously evolving skills",
        },
        "IS.11": {
            "dimension": "User/Customer",
            "element": "Learning from usage data and feedback",
        },
        "IS.12": {
            "dimension": "Team",
            "element": "Contemporary and continuously evolving skills",
        },
        "IS.13": {"dimension": "Knowledge", "element": "Continuos learning"},
    }
    # Agrupa as recomendações em trilhas simples de roadmap.
    RECOMMENDATION_TRACKS = (
        {
            "key": "Adopt now",
            "title": "Adopt first",
            "description": (
                "Practices still absent or abandoned in the selected cycle."
            ),
        },
        {
            "key": "Consolidate",
            "title": "Consolidate to process level",
            "description": (
                "Practices that exist locally and should be expanded "
                "to process level."
            ),
        },
    )
    COMPARISON_LENS_CONFIG = {
        "eye": {
            "title": "Eye of CSE benchmark",
            "subtitle": "Seven-dimensional view of maturity balance across the organization.",
            "axes": [
                {"key": "Development", "label": "Development"},
                {"key": "Quality", "label": "Quality"},
                {"key": "Software Management", "label": "Software Mgt"},
                {"key": "Technical Solution", "label": "Technical Solution"},
                {"key": "Knowledge", "label": "Knowledge"},
                {"key": "Business", "label": "Business"},
                {"key": "User/Customer", "label": "User/Customer"},
            ],
            "item_key": "name",
            "item_value": "score",
        },
        "sth": {
            "title": "StH benchmark",
            "subtitle": "Stairway to Heaven stages compared against the selected peer average.",
            "axes": [
                {"key": "Agile", "label": "ARO"},
                {"key": "CI", "label": "CI"},
                {"key": "CD", "label": "CD"},
                {"key": "Experimentation", "label": "EXP"},
            ],
            "item_key": "short_name",
            "item_value": "score",
        },
    }

    # Numero minimo de empresas para formar um benchmark significativo.
    BENCHMARK_MIN_COMPANY_THRESHOLD = 5

    # Carrega os níveis de adoção uma única vez para reutilização ao longo dos cálculos.
    def __init__(self):
        self.adopted_levels = list(AdoptedLevel.objects.order_by("percentage"))
        self.recommendations_catalog = load_recommendations_catalog()

    def _get_recommendations_catalog(self):
        catalog = getattr(self, "recommendations_catalog", None)
        if catalog is None:
            catalog = load_recommendations_catalog()
            self.recommendations_catalog = catalog
        return catalog

    # Monta a resposta resumida do dashboard, focada em resultado geral do ciclo atual.
    def get_dashboard_payload(self, request):
        context = self._resolve_context(request)
        organization = context["organization"]
        answers = context["current_answers"]
        selected_answers = context.get("selected_answers", answers)
        selected_cycle_empty = context.get("selected_cycle_empty", False)
        expected_statement_count = context.get("expected_statement_count", len(answers))
        expected_stage_counts = context.get("expected_stage_counts")
        stage_scores = self._build_stage_scores(
            answers,
            expected_stage_counts=expected_stage_counts,
            organization=organization,
        )
        recommendations = self._build_recommendations(
            answers, organization=organization
        )
        history_cycles = self._build_history_cycles(
            context["all_answers"], context["organization"], expected_statement_count
        )
        overall_score = self._score_for_answers(
            answers,
            expected_total=expected_statement_count,
            organization=organization,
        )
        questionnaire_status = self._questionnaire_status(
            len(answers), expected_statement_count
        )

        return {
            "organization": self._serialize_organization(organization),
            "cycle": self._serialize_cycle(
                context["questionnaire"],
                selected_answers if context["questionnaire"] is not None else answers,
            ),
            "scope": context["stage_scope"],
            "selected_cycle_empty": selected_cycle_empty,
            "snapshot": {
                "overall_score": overall_score,
                "overall_level": self._resolve_average_level(
                    overall_score,
                    organization=organization,
                ),
                "answered_practices": len(answers),
                "questionnaire_status": questionnaire_status,
                "recommendation_count": len(recommendations),
                "executive_summary": self._build_executive_summary(stage_scores),
                "overall_delta": self._history_delta(
                    history_cycles,
                    "overall_score",
                ),
            },
            "stage_scores": stage_scores,
            "adoption_levels": self._build_adoption_distribution(answers),
            "strengths": self._build_strengths(answers, organization=organization),
            "bottlenecks": self._build_bottlenecks(answers, organization=organization),
            "recommendations_preview": recommendations[:3],
        }

    # Monta a resposta detalhada da tela de resultados, com foco em forças e gargalos.
    def get_results_payload(self, request):
        context = self._resolve_context(request)
        organization = context["organization"]
        answers = context["current_answers"]
        selected_answers = context.get("selected_answers", answers)
        selected_cycle_empty = context.get("selected_cycle_empty", False)
        expected_statement_count = context.get("expected_statement_count", len(answers))
        expected_stage_counts = context.get("expected_stage_counts")
        stage_scores = self._build_stage_scores(
            answers,
            expected_stage_counts=expected_stage_counts,
            organization=organization,
        )
        recommendations = self._build_recommendations(
            answers, organization=organization
        )
        overall_score = self._score_for_answers(answers, organization=organization)
        questionnaire_status = self._questionnaire_status(
            len(answers), expected_statement_count
        )
        stage_coverage = self._build_stage_coverage(
            answers,
            expected_stage_counts=expected_stage_counts,
        )

        stage_values = [item["score"] for item in stage_scores]
        stage_gap = (
            max(stage_values) - min(stage_values) if len(stage_values) > 1 else 0
        )

        return {
            "organization": self._serialize_organization(organization),
            "cycle": self._serialize_cycle(
                context["questionnaire"],
                selected_answers if context["questionnaire"] is not None else answers,
            ),
            "scope": context["stage_scope"],
            "selected_cycle_empty": selected_cycle_empty,
            "summary": {
                "overall_score": overall_score,
                "overall_level": self._resolve_average_level(
                    overall_score,
                    organization=organization,
                ),
                "answered_practices": len(answers),
                "questionnaire_status": questionnaire_status,
                "represented_stages": stage_coverage["represented_stages"],
                "total_stages": stage_coverage["total_stages"],
                "missing_stages": stage_coverage["missing_stages"],
                "stage_gap": stage_gap,
            },
            "stage_scores": stage_scores,
            "adoption_level_stage_overview": self._build_adoption_level_stage_overview(
                answers,
                organization=organization,
            ),
            "dimensions": self._build_dimension_results(
                answers, organization=organization
            ),
            "dimension_score_overview": self._build_dimension_stage_overview(
                answers,
                organization=organization,
            ),
            "dimension_overview": self._build_dimension_stage_matrix(
                stage_scope=context["stage_scope"],
            ),
            "element_overview": self._build_dimension_element_overview(
                answers,
                organization=organization,
                stage_scope=context["stage_scope"],
            ),
            "process_overview": self._build_process_overview(
                answers,
                organization=organization,
                stage_scope=context["stage_scope"],
            ),
            "strengths": self._build_strengths(answers, organization=organization),
            "bottlenecks": self._build_bottlenecks(answers, organization=organization),
            "opportunities": recommendations[:5],
        }

    # Gera o roadmap acionável a partir das práticas com menor maturidade.
    def get_recommendations_payload(self, request):
        context = self._resolve_context(request)
        organization = context["organization"]
        answers = context["current_answers"]
        selected_answers = context.get("selected_answers", answers)
        selected_cycle_empty = context.get("selected_cycle_empty", False)
        expected_statement_count = context.get("expected_statement_count", len(answers))
        expected_stage_counts = context.get("expected_stage_counts")
        recommendations = self._build_recommendations(
            answers, organization=organization
        )
        questionnaire_status = self._questionnaire_status(
            len(answers), expected_statement_count
        )
        stage_coverage = self._build_stage_coverage(
            answers,
            expected_stage_counts=expected_stage_counts,
        )

        grouped_tracks = []
        for lane in self.RECOMMENDATION_TRACKS:
            items = [item for item in recommendations if item["track"] == lane["key"]]
            grouped_tracks.append({**lane, "count": len(items), "items": items})

        return {
            "organization": self._serialize_organization(organization),
            "cycle": self._serialize_cycle(
                context["questionnaire"],
                selected_answers if context["questionnaire"] is not None else answers,
            ),
            "scope": context["stage_scope"],
            "selected_cycle_empty": selected_cycle_empty,
            "summary": {
                "triggered_recommendations": len(recommendations),
                "adopt_now_count": len(
                    [item for item in recommendations if item["track"] == "Adopt now"]
                ),
                "consolidate_count": len(
                    [item for item in recommendations if item["track"] == "Consolidate"]
                ),
                "questionnaire_status": questionnaire_status,
                "answered_practices": len(answers),
                "expected_practices": expected_statement_count,
                "represented_stages": stage_coverage["represented_stages"],
                "total_stages": stage_coverage["total_stages"],
                "missing_stages": stage_coverage["missing_stages"],
            },
            "filters": {
                "available_stages": sorted(
                    {
                        item["stage_short_name"]
                        for item in recommendations
                        if item["stage_short_name"]
                    }
                ),
                "available_tracks": [
                    item["key"] for item in self.RECOMMENDATION_TRACKS
                ],
                "available_practice_groups": sorted(
                    {
                        item["dimension_name"]
                        for item in recommendations
                        if item["dimension_name"]
                    }
                ),
                "available_priorities": ["High", "Medium", "Low"],
            },
            "tracks": grouped_tracks,
            "items": recommendations,
        }

    # Resume a evolução entre ciclos para responder o que mudou ao longo do tempo.
    def get_history_payload(self, request):
        context = self._resolve_context(request)
        selected_answers = context.get("selected_answers", context["current_answers"])
        selected_cycle_empty = context.get("selected_cycle_empty", False)
        cycles = self._build_history_cycles(
            context["all_answers"],
            context["organization"],
            context.get("expected_statement_count"),
        )

        if len(cycles) >= 2:
            baseline = cycles[0]
            current = cycles[-1]
            overall_delta = current["overall_score"] - baseline["overall_score"]
            recommendation_reduction = (
                baseline["recommendation_count"] - current["recommendation_count"]
            )
        else:
            overall_delta = 0
            recommendation_reduction = 0

        return {
            "organization": self._serialize_organization(context["organization"]),
            "cycle": self._serialize_cycle(
                context["questionnaire"],
                selected_answers,
            ),
            "scope": context["stage_scope"],
            "selected_cycle_empty": selected_cycle_empty,
            "summary": {
                "cycle_count": len(cycles),
                "overall_delta": overall_delta,
                "recommendation_reduction": recommendation_reduction,
            },
            "cycles": cycles,
        }

    # Monta a resposta agregada de comparacao para o card de benchmark.
    def get_comparison_payload(self, request):
        context = self._resolve_context(request)
        organization = context["organization"]
        current_answers = context["current_answers"]
        all_answers = context["all_answers"]

        reference_mode = request.query_params.get("reference_mode", "first-submission")
        reference_questionnaire_id = request.query_params.get(
            "reference_questionnaire_id"
        )

        reference_answers, reference_questionnaire = self._resolve_reference_answers(
            all_answers,
            reference_mode,
            reference_questionnaire_id,
        )

        reference_cycle = self._serialize_cycle(
            reference_questionnaire,
            reference_answers,
        )
        current_cycle = reference_cycle  # verificar se isso da certo

        current_overall_score = self._score_for_answers(
            current_answers,
            organization=organization,
        )
        reference_overall_score = self._score_for_answers(
            reference_answers,
            organization=organization,
        )

        return {
            "organization": self._serialize_organization(organization),
            "scope": context["stage_scope"],
            "selection": {
                "reference_mode": reference_mode,
                "current_cycle": current_cycle,
                "reference_cycle": reference_cycle,
                "available_cycles": self._build_history_cycles(
                    all_answers,
                    None,
                    context.get("expected_statement_count"),
                    filter_incomplete=True,
                ),
            },
            "summary": {
                "current_score": current_overall_score,
                "reference_score": reference_overall_score,
                "delta": current_overall_score - reference_overall_score,
                "current_answered_practices": len(current_answers),
                "reference_answered_practices": len(reference_answers),
            },
            "lenses": {
                "eye": self._build_comparison_lens_payload(
                    lens_key="eye",
                    current_items=self._build_dimension_results(current_answers),
                    reference_items=self._build_dimension_results(reference_answers),
                    current_overall_score=current_overall_score,
                    reference_overall_score=reference_overall_score,
                ),
                "sth": self._build_comparison_lens_payload(
                    lens_key="sth",
                    current_items=[
                        item
                        for item in self._build_stage_scores(current_answers)
                        if item["short_name"] != "Traditional"
                    ],
                    reference_items=[
                        item
                        for item in self._build_stage_scores(reference_answers)
                        if item["short_name"] != "Traditional"
                    ],
                    current_overall_score=current_overall_score,
                    reference_overall_score=reference_overall_score,
                ),
            },
        }

    # Monta a resposta de benchmark baseada em um grupo de peer organizations.
    def get_benchmark_payload(self, request):
        # Resolve current org context (keeps organization info consistent)
        context = self._resolve_context(request)
        organization = context["organization"]
        stage_scope = context["stage_scope"]
        expected_statement_count = context["expected_statement_count"]

        def pick_latest_complete_cycle(answer_rows):
            grouped = self._group_answers_by_questionnaire(answer_rows)
            complete_groups = []

            for questionnaire_id, cycle_answers in grouped.items():
                questionnaire = (
                    cycle_answers[0].questionnaire_answer
                    if cycle_answers and questionnaire_id is not None
                    else None
                )
                if questionnaire is None:
                    continue
                if len(cycle_answers) >= expected_statement_count:
                    complete_groups.append((questionnaire, cycle_answers))

            if not complete_groups:
                return None, []

            complete_groups.sort(key=lambda item: self._questionnaire_sort_key(item[0]))
            return complete_groups[-1]

        def summarize_snapshot(answer_rows, snapshot_organization):
            return {
                "overall_score": self._score_for_answers(
                    answer_rows,
                    organization=snapshot_organization,
                ),
                "dimension_items": self._build_dimension_results(
                    answer_rows,
                    organization=snapshot_organization,
                ),
                "stage_items": [
                    item
                    for item in self._build_stage_scores(
                        answer_rows,
                        organization=snapshot_organization,
                    )
                    if item["short_name"] != "Traditional"
                ],
                "answered_practices": len(answer_rows),
            }

        def aggregate_snapshot_items(snapshot_items, item_key, item_value):
            grouped_values = defaultdict(list)
            templates = {}

            for items in snapshot_items:
                for item in items:
                    key = item.get(item_key)
                    if key is None:
                        continue

                    templates.setdefault(key, item)
                    value = item.get(item_value)
                    if value is not None:
                        grouped_values[key].append(value)

            aggregated_items = []
            for key, values in grouped_values.items():
                aggregated_items.append(
                    {
                        item_key: key,
                        item_value: round(median(values)) if values else 0,
                    }
                )

            return aggregated_items

        # Current organization must have at least one complete snapshot.
        current_questionnaire, current_answers = pick_latest_complete_cycle(
            context["all_answers"]
        )

        current_snapshot = summarize_snapshot(current_answers, organization)

        available_cycles = self._build_history_cycles(
            context["all_answers"],
            context["organization"],
            expected_statement_count,
            filter_incomplete=True,
        )

        base_payload = {
            "organization": self._serialize_organization(context["organization"]),
            "scope": stage_scope,
            "selection": {
                "reference_mode": "peer-aggregate",
                "current_cycle": self._serialize_cycle(
                    current_questionnaire,
                    current_answers,
                ),
                "reference_cycle": None,
                "available_cycles": available_cycles,
            },
            "summary": {
                "current_score": 0,
                "reference_score": 0,
                "delta": 0,
                "current_answered_practices": 0,
                "reference_answered_practices": 0,
            },
            "lenses": {},
        }

        peer_organizations = list(self._resolve_benchmark_peer_organizations(request))
        company_count = 0
        reference_overall_scores = []
        reference_dimension_snapshots = []
        reference_stage_snapshots = []
        snapshot_ids = set()
        reference_answered_practices = 0

        for org in peer_organizations:
            org_answers = list(self._base_answers_queryset(org.id, stage_scope))
            org_questionnaire, org_complete_answers = pick_latest_complete_cycle(
                org_answers
            )
            if org_questionnaire is None:
                continue

            snapshot_summary = summarize_snapshot(org_complete_answers, org)
            company_count += 1
            snapshot_ids.add(org_questionnaire.id)
            reference_answered_practices += snapshot_summary["answered_practices"]
            reference_overall_scores.append(snapshot_summary["overall_score"])
            reference_dimension_snapshots.append(snapshot_summary["dimension_items"])
            reference_stage_snapshots.append(snapshot_summary["stage_items"])

        snapshot_count = len(snapshot_ids)
        reference_overall_score = (
            round(median(reference_overall_scores)) if reference_overall_scores else 0
        )
        reference_dimension_items = aggregate_snapshot_items(
            reference_dimension_snapshots,
            "name",
            "score",
        )
        reference_stage_items = aggregate_snapshot_items(
            reference_stage_snapshots,
            "short_name",
            "score",
        )

        base_payload["selection"]["reference_context"] = {
            "company_count": company_count,
            "snapshot_count": snapshot_count,
            "label": "Peer group",
            "filters": {
                "organization_category": request.query_params.get(
                    "organization_category"
                ),
                "organization_size": request.query_params.get("organization_size"),
                "organization_type": request.query_params.get("organization_type"),
                "target_audience": request.query_params.get("target_audience"),
            },
        }

        if current_questionnaire is None:
            base_payload["benchmark_state"] = {
                "code": "empty_results",
                "title": "No benchmark data yet",
                "message": (
                    "The selected organization has no fully submitted questionnaires yet. "
                    "Benchmark comparison becomes available after the first complete snapshot."
                ),
                "error_code": "empty_results",
                "min_company_threshold": self.BENCHMARK_MIN_COMPANY_THRESHOLD,
                "company_count": company_count,
                "snapshot_count": snapshot_count,
            }
            return base_payload

        if company_count < self.BENCHMARK_MIN_COMPANY_THRESHOLD:
            base_payload["benchmark_state"] = {
                "code": "insufficient_data",
                "title": "Not enough peer companies",
                "message": (
                    f"At least {self.BENCHMARK_MIN_COMPANY_THRESHOLD} companies are required to run the benchmark."
                ),
                "error_code": "insufficient_data",
                "min_company_threshold": self.BENCHMARK_MIN_COMPANY_THRESHOLD,
                "company_count": company_count,
                "snapshot_count": snapshot_count,
            }
            return base_payload

        current_overall_score = current_snapshot["overall_score"]

        base_payload["summary"] = {
            "current_score": current_overall_score,
            "reference_score": reference_overall_score,
            "delta": current_overall_score - reference_overall_score,
            "current_answered_practices": len(current_answers),
            "reference_answered_practices": reference_answered_practices,
        }

        eye_current = current_snapshot["dimension_items"]
        sth_current = current_snapshot["stage_items"]

        base_payload["lenses"]["eye"] = self._build_comparison_lens_payload(
            lens_key="eye",
            current_items=eye_current,
            reference_items=reference_dimension_items,
            current_overall_score=current_overall_score,
            reference_overall_score=reference_overall_score,
        )

        base_payload["lenses"]["sth"] = self._build_comparison_lens_payload(
            lens_key="sth",
            current_items=sth_current,
            reference_items=reference_stage_items,
            current_overall_score=current_overall_score,
            reference_overall_score=reference_overall_score,
        )

        base_payload["benchmark_state"] = {
            "code": "ready",
            "title": "Benchmark ready",
            "message": "Benchmark is ready with enough peer companies.",
            "min_company_threshold": self.BENCHMARK_MIN_COMPANY_THRESHOLD,
            "company_count": company_count,
            "snapshot_count": snapshot_count,
        }

        return base_payload

    # Resolve todo o contexto necessário: organização, escopo, ciclo escolhido e respostas filtradas.
    def _resolve_context(self, request):
        organization = self._resolve_organization(request)
        stage_scope = request.query_params.get("stage_scope", "all")
        all_answers = self._deduplicate_answers(
            list(self._base_answers_queryset(organization.id, stage_scope)),
            per_questionnaire=True,
        )
        questionnaire = self._resolve_questionnaire(
            request,
            organization.id,
            all_answers,
        )
        selected_answers = self._answers_for_questionnaire(
            all_answers,
            questionnaire,
        )
        selected_cycle_empty = questionnaire is not None and not selected_answers
        current_answers = selected_answers

        if not current_answers:
            current_answers = all_answers

        expected_statement_count, expected_stage_counts = self._build_statement_targets(
            stage_scope
        )

        return {
            "organization": organization,
            "questionnaire": questionnaire,
            "stage_scope": stage_scope,
            "all_answers": all_answers,
            "selected_answers": selected_answers,
            "selected_cycle_empty": selected_cycle_empty,
            "current_answers": current_answers,
            "expected_statement_count": expected_statement_count,
            "expected_stage_counts": expected_stage_counts,
        }

    def _resolve_reference_answers(
        self,
        answers,
        reference_mode,
        reference_questionnaire_id,
    ):
        grouped = self._group_answers_by_questionnaire(answers)

        if reference_mode == "first-submission":
            ordered_groups = sorted(
                grouped.items(),
                key=lambda item: self._questionnaire_sort_key(
                    item[1][0].questionnaire_answer if item[1] else None
                ),
            )
            if not ordered_groups:
                return list(answers), None

            for questionnaire_id, cycle_answers in ordered_groups:
                if questionnaire_id is not None:
                    return cycle_answers, cycle_answers[0].questionnaire_answer

            fallback_answers = ordered_groups[0][1]
            return (
                fallback_answers,
                fallback_answers[0].questionnaire_answer if fallback_answers else None,
            )

        if reference_mode == "specific-cycles":
            if reference_questionnaire_id in (None, ""):
                raise ValidationError(
                    "reference_questionnaire_id is required for specific-cycles comparison"
                )

            try:
                questionnaire_id = int(reference_questionnaire_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    "reference_questionnaire_id must be an integer"
                ) from exc

            cycle_answers = grouped.get(questionnaire_id)
            if cycle_answers is None:
                raise ValidationError("reference_questionnaire_id not found")
            if not cycle_answers:
                raise ValidationError(
                    "reference_questionnaire_id has no answers in the selected scope"
                )

            return cycle_answers, cycle_answers[0].questionnaire_answer

        raise ValidationError(
            "reference_mode must be first-submission or specific-cycles"
        )

    def _resolve_benchmark_peer_organizations(self, request):
        qs = Organization.objects.all()
        category = request.query_params.get("organization_category")
        size = request.query_params.get("organization_size")
        org_type = request.query_params.get("organization_type")
        target = request.query_params.get("target_audience")

        if category:
            qs = qs.filter(
                organization_type__category_organization_type__name__iexact=category
            )
        if size:
            qs = qs.filter(organization_size__name__iexact=size)
        if org_type:
            qs = qs.filter(organization_type__name__iexact=org_type)
        if target:
            qs = qs.filter(target_audience__icontains=target)

        return qs

    def _statement_identity(self, answer):
        statement_id = getattr(answer, "statement_answer_id", None)
        if statement_id is not None:
            return statement_id

        statement = getattr(answer, "statement_answer", None)
        if statement is not None:
            statement_id = getattr(statement, "id", None)
            if statement_id is not None:
                return statement_id

            statement_code = getattr(statement, "code", None)
            if statement_code:
                return statement_code

        answer_id = getattr(answer, "id", None)
        if answer_id is not None:
            return f"answer:{answer_id}"

        return id(answer)

    def _deduplicate_answers(self, answers, per_questionnaire=False):
        latest_by_key = {}
        ordered_keys = []

        for answer in answers:
            statement_key = self._statement_identity(answer)
            key = (
                (getattr(answer, "questionnaire_answer_id", None), statement_key)
                if per_questionnaire
                else statement_key
            )

            if key not in latest_by_key:
                ordered_keys.append(key)
            latest_by_key[key] = answer

        return [latest_by_key[key] for key in ordered_keys]

    def _group_answers_by_questionnaire(self, answers):
        answers = self._deduplicate_answers(answers, per_questionnaire=True)
        grouped = defaultdict(list)
        for answer in answers:
            grouped[answer.questionnaire_answer_id].append(answer)
        return grouped

    def _questionnaire_sort_key(self, questionnaire):
        if questionnaire is None:
            return ("9999-12-31", 999999)

        applied_date = questionnaire.applied_date or questionnaire.uploaded_at
        return (
            applied_date.isoformat() if applied_date is not None else "9999-12-30",
            questionnaire.id,
        )

    def _build_comparison_lens_payload(
        self,
        lens_key,
        current_items,
        reference_items,
        current_overall_score,
        reference_overall_score,
    ):
        config = self.COMPARISON_LENS_CONFIG[lens_key]
        current_lookup = {
            item[config["item_key"]]: item[config["item_value"]]
            for item in current_items
        }
        reference_lookup = {
            item[config["item_key"]]: item[config["item_value"]]
            for item in reference_items
        }

        axes = []
        for axis in config["axes"]:
            current_value = current_lookup.get(axis["key"], 0)
            reference_value = reference_lookup.get(axis["key"], 0)
            axes.append(
                {
                    "key": axis["key"],
                    "label": axis["label"],
                    "current": current_value,
                    "reference": reference_value,
                    "delta": current_value - reference_value,
                }
            )

        return {
            "title": config["title"],
            "subtitle": config["subtitle"],
            "current_score": current_overall_score,
            "reference_score": reference_overall_score,
            "delta": current_overall_score - reference_overall_score,
            "axes": axes,
        }

    # Descobre a organização a partir da URL ou do usuário autenticado.
    def _resolve_organization(self, request):
        organization_id = request.query_params.get("organization_id")

        # O usuário deve estar obrigatoriamente autenticado.
        if not request.user or not request.user.is_authenticated:
            raise ValidationError(
                "organization_id is required when the user is not authenticated"
            )

        # Identifica todas as organizações às quais o usuário tem acesso (via Employee).
        user_organizations = Organization.objects.filter(
            employee_organization_employee__e_mail__iexact=request.user.email
        ).distinct()

        if organization_id:
            # Trava de Segurança: Verifica se o usuário tem permissão para a empresa solicitada.
            org = user_organizations.filter(id=organization_id).first()
            if not org:
                raise ValidationError(
                    f"Access denied or organization {organization_id} not found."
                )
            return org

        # Fallback: Se nenhuma empresa foi pedida na URL, assume a primeira vinculada ao usuário.
        org = user_organizations.first()
        if not org:
            raise ValidationError(
                "could not resolve any organization for the authenticated user"
            )

        return org

    # Consulta base com relacionamentos carregados para evitar excesso de queries.
    def _base_answers_queryset(self, organization_id, stage_scope):
        queryset = (
            Answer.objects.filter(organization_answer_id=organization_id)
            .select_related(
                "organization_answer",
                "questionnaire_answer",
                "adopted_level_answer",
                "statement_answer__sth_stage",
                "statement_answer__pe_element__dimension",
            )
            .order_by(
                "questionnaire_answer_id",
                "statement_answer__code",
                "id",
            )
        )

        if stage_scope == "ci_cd":
            queryset = queryset.filter(
                statement_answer__sth_stage__name__in=self.CI_CD_STAGE_NAMES
            )

        return queryset

    # Resolve qual ciclo/questionário deve ser usado na análise atual.
    def _resolve_questionnaire(self, request, organization_id, answers):
        questionnaire_id = request.query_params.get("questionnaire_id")
        if questionnaire_id:
            questionnaire = Questionnaire.objects.filter(id=questionnaire_id).first()
            if questionnaire is None:
                raise ValidationError("questionnaire_id not found")
            return questionnaire

        questionnaire_ids = {
            answer.questionnaire_answer_id
            for answer in answers
            if answer.questionnaire_answer_id is not None
        }
        if not questionnaire_ids:
            return None

        return (
            Questionnaire.objects.filter(id__in=questionnaire_ids)
            .order_by("-applied_date", "-uploaded_at", "-id")
            .first()
        )

    # Filtra apenas as respostas do ciclo selecionado.
    def _answers_for_questionnaire(self, answers, questionnaire):
        if questionnaire is None:
            return list(answers)

        filtered = [
            answer
            for answer in answers
            if answer.questionnaire_answer_id == questionnaire.id
        ]
        return filtered

    # Converte a organização para um formato simples e estável para o frontend.
    def _serialize_organization(self, organization):
        return {
            "id": organization.id,
            "name": organization.name,
            "type": getattr(organization.organization_type, "name", None),
            "size": getattr(organization.organization_size, "name", None),
            "age_months": organization.age,
        }

    # Converte o ciclo para um resumo legível usado no topo das telas.
    def _serialize_cycle(self, questionnaire, answers):
        if questionnaire is None:
            return {
                "id": None,
                "label": "Aggregated organization snapshot",
                "applied_date": None,
                "answered_practices": len(answers),
            }

        applied_date = questionnaire.applied_date or questionnaire.uploaded_at
        return {
            "id": questionnaire.id,
            "label": (
                f"Questionnaire {questionnaire.id}"
                if applied_date is None
                else applied_date.strftime("%B %Y")
            ),
            "applied_date": applied_date,
            "answered_practices": len(answers),
        }

    # Calcula a pontuação do conjunto de respostas.
    def _score_for_answers(self, answers, expected_total=None, organization=None):
        """Calculate score for a set of answers.

        Uses instrument weights with median aggregation. When an
        expected_total is provided and the cycle is partial, missing answers
        are imputed as zeros before the median is computed.
        """
        weights = [
            self._instrument_weight(answer, organization=organization)
            for answer in answers
            if answer.adopted_level_answer is not None
        ]

        if not weights:
            return 0

        if expected_total is not None and len(weights) < expected_total:
            weights = weights + [0] * (expected_total - len(weights))

        return round(median(weights))

    def _questionnaire_status(self, answered_count, expected_total):
        if expected_total <= 0:
            return "Under Assessment"
        return "Complete" if answered_count >= expected_total else "Under Assessment"

    def _build_stage_coverage(self, answers, expected_stage_counts=None):
        grouped_counts = defaultdict(int)
        for answer in answers:
            stage = getattr(answer.statement_answer, "sth_stage", None)
            stage_name = getattr(stage, "name", None) or "Unknown stage"
            grouped_counts[stage_name] += 1

        stage_names = list(grouped_counts.keys())
        if expected_stage_counts:
            stage_names = list(
                dict.fromkeys([*expected_stage_counts.keys(), *stage_names]).keys()
            )

        represented = 0
        missing = []

        for stage_name in stage_names:
            count = grouped_counts.get(stage_name, 0)
            short_name = self.STAGE_SHORT_NAMES.get(stage_name, stage_name)
            if count > 0:
                represented += 1
            else:
                missing.append(short_name)

        return {
            "represented_stages": represented,
            "total_stages": len(stage_names),
            "missing_stages": missing,
        }

    # Traduz um score numérico para o nível de adoção mais próximo.
    def _resolve_average_level(self, score, organization=None):
        if not self.adopted_levels:
            return None

        closest = min(
            self.adopted_levels,
            key=lambda level: abs(
                self._weight_for_percentage(
                    level.percentage,
                    organization=organization,
                )
                - score
            ),
        )
        return closest.name

    # Agrupa as respostas por estágio e calcula os indicadores de cada grupo.
    def _build_stage_scores(
        self, answers, expected_stage_counts=None, organization=None
    ):
        grouped = defaultdict(list)
        for answer in answers:
            stage = getattr(answer.statement_answer, "sth_stage", None)
            stage_name = getattr(stage, "name", None) or "Unknown stage"
            grouped[stage_name].append(answer)

        items = []
        stage_names = list(grouped.keys())
        if expected_stage_counts:
            stage_names = list(
                dict.fromkeys([*expected_stage_counts.keys(), *stage_names]).keys()
            )

        for stage_name in stage_names:
            stage_answers = grouped.get(stage_name, [])
            expected_total = (
                expected_stage_counts.get(stage_name)
                if expected_stage_counts is not None
                else None
            )
            score = self._score_for_answers(
                stage_answers,
                expected_total=expected_total,
                organization=organization,
            )
            items.append(
                {
                    "key": slugify(stage_name),
                    "name": stage_name,
                    "short_name": self.STAGE_SHORT_NAMES.get(
                        stage_name,
                        stage_name,
                    ),
                    "score": score,
                    "current_level": self._resolve_average_level(
                        score,
                        organization=organization,
                    ),
                    "answered_practices": len(stage_answers),
                    "total_practices": (
                        expected_total
                        if expected_total is not None
                        else len(stage_answers)
                    ),
                    "strength_count": len(
                        [
                            answer
                            for answer in stage_answers
                            if answer.adopted_level_answer.percentage >= 60
                        ]
                    ),
                    "bottleneck_count": len(
                        [
                            answer
                            for answer in stage_answers
                            if answer.adopted_level_answer.percentage < 60
                        ]
                    ),
                }
            )

        return sorted(
            items,
            key=lambda item: self.STAGE_ORDER.get(item["name"], 999),
        )

    def _build_statement_targets(self, stage_scope):
        queryset = Statement.objects.select_related("sth_stage")

        if stage_scope == "ci_cd":
            queryset = queryset.filter(sth_stage__name__in=self.CI_CD_STAGE_NAMES)

        stage_counts = defaultdict(int)
        total = 0

        for statement in queryset:
            stage_name = getattr(statement.sth_stage, "name", None) or "Unknown stage"
            stage_counts[stage_name] += 1
            total += 1

        return total, dict(stage_counts)

    # Conta quantas práticas caem em cada nível de adoção.
    def _build_adoption_distribution(self, answers):
        total = len(answers) or 1
        grouped = defaultdict(list)
        for answer in answers:
            level = answer.adopted_level_answer
            grouped[level.id].append(answer)

        items = []
        for level in self.adopted_levels:
            count = len(grouped.get(level.id, []))
            items.append(
                {
                    "id": level.id,
                    "key": slugify(level.name),
                    "label": level.name,
                    "count": count,
                    "percentage": round((count / total) * 100),
                    "score": level.percentage,
                }
            )

        return items

    # Seleciona as práticas mais maduras para a seção de pontos fortes.
    def _build_strengths(self, answers, limit=3, organization=None):
        candidates = [
            answer for answer in answers if answer.adopted_level_answer.percentage >= 60
        ]
        candidates.sort(
            key=lambda answer: (
                -answer.adopted_level_answer.percentage,
                answer.statement_answer.code or "",
            )
        )
        return [
            self._serialize_insight(answer, organization=organization)
            for answer in candidates[:limit]
        ]

    # Seleciona as práticas mais críticas para a seção de gargalos.
    def _build_bottlenecks(self, answers, limit=3, organization=None):
        candidates = [
            answer for answer in answers if answer.adopted_level_answer.percentage < 60
        ]
        candidates.sort(
            key=lambda answer: (
                answer.adopted_level_answer.percentage,
                answer.statement_answer.code or "",
            )
        )
        return [
            self._serialize_insight(answer, organization=organization)
            for answer in candidates[:limit]
        ]

    # Agrupa resultados por tema/dimensão para facilitar a leitura do diagnóstico.
    def _build_dimension_results(self, answers, organization=None):
        grouped = defaultdict(list)
        for answer in answers:
            dimension_name = self._resolve_dimension_name(answer)
            grouped[dimension_name].append(answer)

        items = []
        for dimension_name, dimension_answers in grouped.items():
            score = self._score_for_answers(
                dimension_answers,
                organization=organization,
            )
            strongest = max(
                dimension_answers,
                key=lambda answer: answer.adopted_level_answer.percentage,
            )
            weakest = min(
                dimension_answers,
                key=lambda answer: answer.adopted_level_answer.percentage,
            )
            focus_codes = [
                answer.statement_answer.code
                for answer in dimension_answers[:3]
                if answer.statement_answer.code
            ]

            items.append(
                {
                    "key": slugify(dimension_name),
                    "name": dimension_name,
                    "focus": (
                        ", ".join(focus_codes) if focus_codes else "Practice cluster"
                    ),
                    "score": score,
                    "current_level": self._resolve_average_level(
                        score,
                        organization=organization,
                    ),
                    "answered_practices": len(dimension_answers),
                    "strength": self._compact_statement(
                        strongest.statement_answer.text
                    ),
                    "bottleneck": self._compact_statement(
                        weakest.statement_answer.text
                    ),
                    "strength_item": self._serialize_insight(
                        strongest,
                        organization=organization,
                    ),
                    "bottleneck_item": self._serialize_insight(
                        weakest,
                        organization=organization,
                    ),
                }
            )

        return sorted(
            items,
            key=lambda item: (-item["score"], item["name"]),
        )

    def _build_dimension_stage_overview(self, answers, organization=None):
        grouped = defaultdict(
            lambda: {
                "organization": [],
                "Agile": [],
                "CI": [],
                "CD": [],
                "Experimentation": [],
            }
        )

        for answer in answers:
            dimension_name = self._resolve_dimension_name(answer)
            if not dimension_name or dimension_name == "Unclassified":
                continue

            stage_name = getattr(answer.statement_answer.sth_stage, "name", None)
            stage_short_name = self.STAGE_SHORT_NAMES.get(stage_name, stage_name)
            score = self._instrument_weight(answer, organization=organization)

            grouped[dimension_name]["organization"].append(score)
            if stage_short_name in {"Agile", "CI", "CD", "Experimentation"}:
                grouped[dimension_name][stage_short_name].append(score)

        items = []
        agile_aggregate = []
        ci_aggregate = []
        cd_aggregate = []
        experimentation_aggregate = []
        organization_aggregate = []

        for dimension_name, buckets in grouped.items():
            agile_scores = buckets["Agile"]
            ci_scores = buckets["CI"]
            cd_scores = buckets["CD"]
            experimentation_scores = buckets["Experimentation"]
            org_scores = buckets["organization"]

            agile_aggregate.extend(agile_scores)
            ci_aggregate.extend(ci_scores)
            cd_aggregate.extend(cd_scores)
            experimentation_aggregate.extend(experimentation_scores)
            organization_aggregate.extend(org_scores)

            items.append(
                {
                    "key": slugify(dimension_name),
                    "name": dimension_name,
                    "agile_score": round(mean(agile_scores)) if agile_scores else None,
                    "ci_score": round(mean(ci_scores)) if ci_scores else None,
                    "cd_score": round(mean(cd_scores)) if cd_scores else None,
                    "experimentation_score": (
                        round(mean(experimentation_scores))
                        if experimentation_scores
                        else None
                    ),
                    "organization_score": round(mean(org_scores)) if org_scores else 0,
                    "agile_practice_count": len(agile_scores),
                    "ci_practice_count": len(ci_scores),
                    "cd_practice_count": len(cd_scores),
                    "experimentation_practice_count": len(experimentation_scores),
                    "practice_count": len(org_scores),
                }
            )

        items.sort(
            key=lambda item: (
                self.DIMENSION_ORDER.get(item["name"], 500),
                item["name"],
            )
        )

        return {
            "dimensions": items,
            "summary": {
                "agile_score": (
                    round(mean(agile_aggregate)) if agile_aggregate else None
                ),
                "ci_score": round(mean(ci_aggregate)) if ci_aggregate else None,
                "cd_score": round(mean(cd_aggregate)) if cd_aggregate else None,
                "experimentation_score": (
                    round(mean(experimentation_aggregate))
                    if experimentation_aggregate
                    else None
                ),
                "organization_score": (
                    round(mean(organization_aggregate)) if organization_aggregate else 0
                ),
                "statement_count": len(organization_aggregate),
            },
        }

    def _build_dimension_stage_matrix(
        self,
        stage_scope="all",
        statements=None,
        include_baseline=True,
    ):
        stage_name_to_key = {}
        stage_key_to_title = {}
        for stage in self.ADOPTION_OVERVIEW_STAGES:
            stage_key_to_title[stage["key"]] = stage["title"]
            for label in stage["labels"]:
                stage_name_to_key[label] = stage["key"]

        stage_order = [stage["key"] for stage in self.ADOPTION_OVERVIEW_STAGES]
        grouped = {
            dimension_name: {stage_key: 0 for stage_key in stage_order}
            for dimension_name in self.DIMENSION_STAGE_MATRIX_DIMENSIONS
        }

        if include_baseline and stage_scope != "ci_cd":
            for dimension_name, counts in self.DIMENSION_STAGE_BASELINE_COUNTS.items():
                grouped[dimension_name]["agile"] = counts["agile"]
                grouped[dimension_name]["experimentation"] = counts["experimentation"]

        if statements is None:
            queryset = Statement.objects.select_related(
                "sth_stage", "pe_element__dimension"
            )
            if stage_scope == "ci_cd" and hasattr(queryset, "filter"):
                queryset = queryset.filter(sth_stage__name__in=self.CI_CD_STAGE_NAMES)
            statements = list(queryset)
        elif stage_scope == "ci_cd":
            statements = [
                statement
                for statement in statements
                if getattr(getattr(statement, "sth_stage", None), "name", None)
                in self.CI_CD_STAGE_NAMES
            ]

        for statement in statements:
            stage_name = getattr(getattr(statement, "sth_stage", None), "name", None)
            stage_key = stage_name_to_key.get(stage_name)
            if not stage_key:
                continue

            if include_baseline and stage_key in {"agile", "experimentation"}:
                continue

            dimension_name = self._resolve_statement_dimension_name(statement)
            if dimension_name not in grouped:
                continue

            grouped[dimension_name][stage_key] += 1

        rows = []
        summary = {f"{stage_key}_count": 0 for stage_key in stage_order}
        statement_count = 0

        for dimension_name in self.DIMENSION_STAGE_MATRIX_DIMENSIONS:
            buckets = grouped[dimension_name]
            practice_count = sum(buckets.values())
            statement_count += practice_count

            for stage_key in stage_order:
                summary[f"{stage_key}_count"] += buckets[stage_key]

            rows.append(
                {
                    "key": slugify(dimension_name),
                    "name": dimension_name,
                    "agile_count": buckets["agile"],
                    "ci_count": buckets["ci"],
                    "cd_count": buckets["cd"],
                    "experimentation_count": buckets["experimentation"],
                    "practice_count": practice_count,
                }
            )

        summary["statement_count"] = statement_count
        summary["stage_titles"] = {
            "agile": "Agile Organization",
            "ci": stage_key_to_title["ci"],
            "cd": stage_key_to_title["cd"],
            "experimentation": "R&D as Innovation System",
        }

        return {
            "dimensions": rows,
            "summary": summary,
        }

    def _build_adoption_level_stage_overview(self, answers, organization=None):
        stage_name_to_key = {}
        for stage in self.ADOPTION_OVERVIEW_STAGES:
            for label in stage["labels"]:
                stage_name_to_key[label] = stage["key"]

        stage_level_counts = {
            stage["key"]: defaultdict(int) for stage in self.ADOPTION_OVERVIEW_STAGES
        }

        for answer in answers:
            stage_name = getattr(answer.statement_answer.sth_stage, "name", None)
            stage_key = stage_name_to_key.get(stage_name)
            if not stage_key:
                continue

            level_name = getattr(answer.adopted_level_answer, "name", "") or ""
            stage_level_counts[stage_key][level_name] += 1

        rows = []
        totals = {stage["key"]: 0 for stage in self.ADOPTION_OVERVIEW_STAGES}
        total_organization = 0
        weighted_scores = {stage["key"]: 0 for stage in self.ADOPTION_OVERVIEW_STAGES}
        weighted_organization = 0

        for level in self.adopted_levels:
            weight = self._weight_for_percentage(
                level.percentage,
                organization=organization,
            )
            level_counts = {}
            organization_count = 0

            for stage in self.ADOPTION_OVERVIEW_STAGES:
                count = stage_level_counts[stage["key"]].get(level.name, 0)
                level_counts[stage["key"]] = count
                totals[stage["key"]] += count
                weighted_scores[stage["key"]] += count * weight
                organization_count += count

            total_organization += organization_count
            weighted_organization += organization_count * weight

            row = {
                "key": slugify(level.name),
                "label": level.name,
                "weight": weight,
                "organization_count": organization_count,
            }
            for stage in self.ADOPTION_OVERVIEW_STAGES:
                row[f"{stage['key']}_count"] = level_counts[stage["key"]]

            rows.append(row)

        return {
            "stages": [
                {"key": stage["key"], "title": stage["title"]}
                for stage in self.ADOPTION_OVERVIEW_STAGES
            ],
            "levels": rows,
            "totals": {
                **{
                    f"{stage['key']}_count": totals[stage["key"]]
                    for stage in self.ADOPTION_OVERVIEW_STAGES
                },
                "organization_count": total_organization,
            },
            "degree_of_adoption": {
                **{
                    f"{stage['key']}_score": (
                        round(weighted_scores[stage["key"]] / totals[stage["key"]])
                        if totals[stage["key"]]
                        else None
                    )
                    for stage in self.ADOPTION_OVERVIEW_STAGES
                },
                "organization_score": (
                    round(weighted_organization / total_organization)
                    if total_organization
                    else None
                ),
            },
        }

    def _build_dimension_element_overview(
        self,
        answers=None,
        organization=None,
        stage_scope="all",
        statements=None,
        include_baseline=True,
    ):
        stage_name_to_key = {}
        stage_order = [stage["key"] for stage in self.ADOPTION_OVERVIEW_STAGES]
        for stage in self.ADOPTION_OVERVIEW_STAGES:
            for label in stage["labels"]:
                stage_name_to_key[label] = stage["key"]

        row_order = {}
        grouped = {}
        for order_index, item in enumerate(self.ELEMENT_STAGE_BASELINE_COUNTS):
            key = (item["dimension"], item["element"])
            row_order[key] = order_index
            grouped[key] = {stage_key: 0 for stage_key in stage_order}
            if include_baseline and stage_scope != "ci_cd":
                grouped[key]["agile"] = item["agile"]
                grouped[key]["experimentation"] = item["experimentation"]

        if statements is None:
            queryset = Statement.objects.select_related(
                "sth_stage", "pe_element__dimension"
            )
            if stage_scope == "ci_cd" and hasattr(queryset, "filter"):
                queryset = queryset.filter(sth_stage__name__in=self.CI_CD_STAGE_NAMES)
            statements = list(queryset)
        elif stage_scope == "ci_cd":
            statements = [
                statement
                for statement in statements
                if getattr(getattr(statement, "sth_stage", None), "name", None)
                in self.CI_CD_STAGE_NAMES
            ]

        for statement in statements:
            stage_name = getattr(getattr(statement, "sth_stage", None), "name", None)
            stage_key = stage_name_to_key.get(stage_name)
            if not stage_key:
                continue

            if include_baseline and stage_key in {"agile", "experimentation"}:
                continue

            dimension_name = self._resolve_statement_dimension_name(statement)
            element_name = self._resolve_statement_element_name(statement)
            if (
                not dimension_name
                or dimension_name == "Unclassified"
                or not element_name
            ):
                continue

            dimension_name, element_name = self._normalize_element_matrix_key(
                dimension_name,
                element_name,
            )
            key = (dimension_name, element_name)
            if key not in grouped:
                row_order[key] = len(row_order)
                grouped[key] = {stage_key: 0 for stage_key in stage_order}

            grouped[key][stage_key] += 1

        score_grouped = defaultdict(
            lambda: {stage_key: [] for stage_key in stage_order}
        )
        score_summary = {stage_key: [] for stage_key in stage_order}

        if answers:
            for answer in answers:
                statement = answer.statement_answer
                stage_name = getattr(
                    getattr(statement, "sth_stage", None), "name", None
                )
                if stage_scope == "ci_cd" and stage_name not in self.CI_CD_STAGE_NAMES:
                    continue

                stage_key = stage_name_to_key.get(stage_name)
                if not stage_key:
                    continue

                dimension_name = self._resolve_statement_dimension_name(statement)
                element_name = self._resolve_statement_element_name(statement)
                if (
                    not dimension_name
                    or dimension_name == "Unclassified"
                    or not element_name
                ):
                    continue

                dimension_name, element_name = self._normalize_element_matrix_key(
                    dimension_name,
                    element_name,
                )
                key = (dimension_name, element_name)
                if key not in grouped:
                    row_order[key] = len(row_order)
                    grouped[key] = {stage_key: 0 for stage_key in stage_order}

                score = self._instrument_weight(answer, organization=organization)
                score_grouped[key][stage_key].append(score)
                score_summary[stage_key].append(score)

        rows = []
        summary = {f"{stage_key}_count": 0 for stage_key in stage_order}
        statement_count = 0

        sorted_items = sorted(
            grouped.items(),
            key=lambda item: (
                self.DIMENSION_ORDER.get(item[0][0], 500),
                row_order.get(item[0], 9999),
                item[0][1],
            ),
        )

        for (dimension_name, element_name), buckets in sorted_items:
            practice_count = sum(buckets.values())
            score_buckets = score_grouped.get(
                (dimension_name, element_name),
                {stage_key: [] for stage_key in stage_order},
            )
            organization_scores = [
                score for stage_key in stage_order for score in score_buckets[stage_key]
            ]
            statement_count += practice_count
            for stage_key in stage_order:
                summary[f"{stage_key}_count"] += buckets[stage_key]

            rows.append(
                {
                    "key": slugify(f"{dimension_name}-{element_name}"),
                    "dimension_name": dimension_name,
                    "element_name": element_name,
                    "agile_count": buckets["agile"],
                    "ci_count": buckets["ci"],
                    "cd_count": buckets["cd"],
                    "experimentation_count": buckets["experimentation"],
                    "practice_count": practice_count,
                    "agile_score": (
                        round(mean(score_buckets["agile"]))
                        if score_buckets["agile"]
                        else None
                    ),
                    "ci_score": (
                        round(mean(score_buckets["ci"]))
                        if score_buckets["ci"]
                        else None
                    ),
                    "cd_score": (
                        round(mean(score_buckets["cd"]))
                        if score_buckets["cd"]
                        else None
                    ),
                    "experimentation_score": (
                        round(mean(score_buckets["experimentation"]))
                        if score_buckets["experimentation"]
                        else None
                    ),
                    "organization_score": (
                        round(mean(organization_scores))
                        if organization_scores
                        else None
                    ),
                    "agile_score_count": len(score_buckets["agile"]),
                    "ci_score_count": len(score_buckets["ci"]),
                    "cd_score_count": len(score_buckets["cd"]),
                    "experimentation_score_count": len(
                        score_buckets["experimentation"]
                    ),
                    "score_count": len(organization_scores),
                }
            )

        summary["statement_count"] = statement_count
        for stage_key in stage_order:
            summary[f"{stage_key}_score"] = (
                round(mean(score_summary[stage_key]))
                if score_summary[stage_key]
                else None
            )

        organization_summary_scores = [
            score for stage_scores in score_summary.values() for score in stage_scores
        ]
        summary["organization_score"] = (
            round(mean(organization_summary_scores))
            if organization_summary_scores
            else None
        )

        return {
            "rows": rows,
            "summary": summary,
        }

    def _build_process_overview(
        self, answers=None, organization=None, stage_scope="all"
    ):
        stage_name_to_key = {}
        stage_order = [stage["key"] for stage in self.ADOPTION_OVERVIEW_STAGES]
        for stage in self.ADOPTION_OVERVIEW_STAGES:
            for label in stage["labels"]:
                stage_name_to_key[label] = stage["key"]

        grouped = {
            process_name: {stage_key: [] for stage_key in stage_order}
            for process_name in self.PROCESS_OVERVIEW_PROCESSES
        }
        practice_counts = {
            process_name: 0 for process_name in self.PROCESS_OVERVIEW_PROCESSES
        }

        for processes in self.STATEMENT_PROCESS_CATALOG.values():
            for process_name in processes:
                if process_name in practice_counts:
                    practice_counts[process_name] += 1

        score_summary = {stage_key: [] for stage_key in stage_order}

        if answers:
            for answer in answers:
                statement = answer.statement_answer
                stage_name = getattr(
                    getattr(statement, "sth_stage", None), "name", None
                )
                if stage_scope == "ci_cd" and stage_name not in self.CI_CD_STAGE_NAMES:
                    continue

                stage_key = stage_name_to_key.get(stage_name)
                if not stage_key:
                    continue

                score = self._instrument_weight(answer, organization=organization)
                for process_name in self._resolve_statement_process_names(statement):
                    if process_name not in grouped:
                        continue
                    grouped[process_name][stage_key].append(score)
                    score_summary[stage_key].append(score)

        rows = []
        for process_name in self.PROCESS_OVERVIEW_PROCESSES:
            score_buckets = grouped[process_name]
            organization_scores = [
                score for stage_key in stage_order for score in score_buckets[stage_key]
            ]

            rows.append(
                {
                    "key": slugify(process_name),
                    "name": process_name,
                    "agile_score": (
                        round(mean(score_buckets["agile"]))
                        if score_buckets["agile"]
                        else None
                    ),
                    "ci_score": (
                        round(mean(score_buckets["ci"]))
                        if score_buckets["ci"]
                        else None
                    ),
                    "cd_score": (
                        round(mean(score_buckets["cd"]))
                        if score_buckets["cd"]
                        else None
                    ),
                    "experimentation_score": (
                        round(mean(score_buckets["experimentation"]))
                        if score_buckets["experimentation"]
                        else None
                    ),
                    "organization_score": (
                        round(mean(organization_scores))
                        if organization_scores
                        else None
                    ),
                    "practice_count": practice_counts[process_name],
                    "agile_score_count": len(score_buckets["agile"]),
                    "ci_score_count": len(score_buckets["ci"]),
                    "cd_score_count": len(score_buckets["cd"]),
                    "experimentation_score_count": len(
                        score_buckets["experimentation"]
                    ),
                    "score_count": len(organization_scores),
                }
            )

        summary = {
            "process_count": len(self.PROCESS_OVERVIEW_PROCESSES),
            "agile_score": (
                round(mean(score_summary["agile"])) if score_summary["agile"] else None
            ),
            "ci_score": (
                round(mean(score_summary["ci"])) if score_summary["ci"] else None
            ),
            "cd_score": (
                round(mean(score_summary["cd"])) if score_summary["cd"] else None
            ),
            "experimentation_score": (
                round(mean(score_summary["experimentation"]))
                if score_summary["experimentation"]
                else None
            ),
        }
        organization_scores = [
            score for stage_scores in score_summary.values() for score in stage_scores
        ]
        summary["organization_score"] = (
            round(mean(organization_scores)) if organization_scores else None
        )

        return {
            "rows": rows,
            "summary": summary,
        }

    # Gera recomendações para práticas abaixo do limiar de 60 por cento.
    def _build_recommendations(self, answers, organization=None):
        items = []
        recommendations_catalog = self._get_recommendations_catalog()
        candidates = [
            answer for answer in answers if self._is_recommendation_candidate(answer)
        ]
        candidates.sort(
            key=lambda answer: (
                self._instrument_weight(answer, organization=organization),
                self.STAGE_ORDER.get(
                    getattr(answer.statement_answer.sth_stage, "name", ""), 999
                ),
                answer.statement_answer.code or "",
            )
        )

        for answer in candidates:
            level = answer.adopted_level_answer
            statement = answer.statement_answer
            stage_name = getattr(
                statement.sth_stage,
                "name",
                None,
            )
            calibrated_score = self._instrument_weight(
                answer,
                organization=organization,
            )
            adopt_now_threshold = self._weight_for_percentage(
                10,
                organization=organization,
            )
            track = (
                "Adopt now"
                if calibrated_score <= adopt_now_threshold
                else "Consolidate"
            )
            priority = "High" if track == "Adopt now" else "Medium"
            catalog_entry = recommendations_catalog.get(statement.code, {})
            element_name = self._resolve_element_name(answer)

            items.append(
                {
                    "id": answer.id,
                    "question_id": statement.code,
                    "question_description": (
                        catalog_entry.get("question_description") or statement.text
                    ),
                    "stage_name": stage_name,
                    "stage_short_name": self.STAGE_SHORT_NAMES.get(
                        stage_name,
                        stage_name,
                    ),
                    "dimension_name": self._resolve_dimension_name(answer),
                    "element_name": element_name,
                    "track": track,
                    "priority": priority,
                    "current_level": self._resolve_average_level(
                        calibrated_score,
                        organization=organization,
                    ),
                    "title": self._recommendation_title(answer),
                    "recommendation": self._recommendation_copy(
                        answer,
                        track,
                    ),
                    "expected_impact": self._expected_impact(
                        answer,
                        track,
                    ),
                    "next_step": self._next_step(
                        answer,
                        track,
                    ),
                    "catalog_recommendation": catalog_entry.get(
                        "catalog_recommendation", ""
                    ),
                    "trigger_rule": self._recommendation_rule(level, track),
                    "reference_source": (
                        "Questionnaire recommendations catalog"
                        if catalog_entry.get("catalog_recommendation")
                        else "Generated from analytics rules"
                    ),
                    "status": "Suggested",
                }
            )

        return items

    # Reconstrói a linha do tempo dos ciclos da organização.
    def _build_history_cycles(
        self, answers, organization=None, expected_total=None, filter_incomplete=False
    ):
        answers = self._deduplicate_answers(answers, per_questionnaire=True)
        grouped = defaultdict(list)
        questionnaires = {}

        for answer in answers:
            if answer.questionnaire_answer_id is None:
                continue

            key = answer.questionnaire_answer_id
            grouped[key].append(answer)
            questionnaires[answer.questionnaire_answer_id] = answer.questionnaire_answer

        if organization:
            org_questionnaires = Questionnaire.objects.filter(
                employee_questionnaire__employee_organization_id=organization.id
            )
            for q in org_questionnaires:
                if q.id not in questionnaires:
                    questionnaires[q.id] = q
                    if q.id not in grouped:
                        grouped[q.id] = []

        def sort_key(item):
            key, cycle_answers = item
            questionnaire = questionnaires.get(key)
            if questionnaire is None:
                return ("9999-12-31", 999999)

            applied_date = questionnaire.applied_date or questionnaire.uploaded_at
            return (
                (
                    applied_date.isoformat()
                    if applied_date is not None
                    else "9999-12-30"
                ),
                questionnaire.id,
            )

        cycles = []
        for key, cycle_answers in sorted(grouped.items(), key=sort_key):
            questionnaire = questionnaires.get(key)
            is_complete = (
                True if expected_total is None else len(cycle_answers) >= expected_total
            )

            # When requested, skip incomplete cycles (used by radar/comparison selections).
            if filter_incomplete and not is_complete:
                continue

            overall_score = self._score_for_answers(
                cycle_answers,
                expected_total=expected_total,
                organization=organization,
            )
            stage_scores = self._build_stage_scores(
                cycle_answers,
                organization=organization,
            )
            adoption_counts = {
                item["key"]: item["count"]
                for item in self._build_adoption_distribution(cycle_answers)
            }

            cycles.append(
                {
                    "id": getattr(questionnaire, "id", None),
                    "label": (
                        f"Questionnaire {questionnaire.id}"
                        if questionnaire and questionnaire.applied_date is None
                        else (
                            (
                                questionnaire.applied_date or questionnaire.uploaded_at
                            ).strftime("%B %Y")
                            if questionnaire
                            else "Aggregated snapshot"
                        )
                    ),
                    "applied_date": (
                        questionnaire.applied_date or questionnaire.uploaded_at
                        if questionnaire
                        else None
                    ),
                    "overall_score": overall_score,
                    "overall_level": self._resolve_average_level(
                        overall_score,
                        organization=organization,
                    ),
                    "answered_practices": len(cycle_answers),
                    "complete": is_complete,
                    "recommendation_count": len(
                        [
                            answer
                            for answer in cycle_answers
                            if self._is_recommendation_candidate(answer)
                        ]
                    ),
                    "stage_scores": stage_scores,
                    "adoption_levels": adoption_counts,
                }
            )

        return cycles

    # Calcula a diferença entre o último e o penúltimo ciclo para um campo específico.
    def _history_delta(self, cycles, field_name):
        if len(cycles) < 2:
            return 0
        return cycles[-1][field_name] - cycles[-2][field_name]

    def _is_recommendation_candidate(self, answer):
        percentage = getattr(answer.adopted_level_answer, "percentage", 0)
        if percentage >= 60:
            return False

        statement_code = getattr(answer.statement_answer, "code", "") or ""
        return statement_code.startswith(("CI.", "CD."))

    # Padroniza o formato de forças e gargalos para o frontend.
    def _serialize_insight(self, answer, organization=None):
        stage_name = getattr(answer.statement_answer.sth_stage, "name", None)
        return {
            "id": answer.id,
            "question_id": answer.statement_answer.code,
            "stage_name": stage_name,
            "stage_short_name": self.STAGE_SHORT_NAMES.get(
                stage_name,
                stage_name,
            ),
            "current_level": self._resolve_average_level(
                self._instrument_weight(answer, organization=organization),
                organization=organization,
            ),
            "score": self._instrument_weight(answer, organization=organization),
            "title": self._compact_statement(answer.statement_answer.text),
            "evidence": self._insight_evidence(answer),
        }

    # Define qual texto de evidência será mostrado para cada insight.
    def _insight_evidence(self, answer):
        if answer.comment_answer:
            return answer.comment_answer.strip()

        dimension_name = getattr(
            getattr(
                answer.statement_answer.pe_element,
                "dimension",
                None,
            ),
            "name",
            None,
        )
        if dimension_name:
            return f"{answer.adopted_level_answer.name} in {dimension_name}."
        return answer.adopted_level_answer.name

    # Resolve a dimensao exibida na interface mesmo quando o catalogo
    # oficial informa apenas o stage da pergunta.
    def _resolve_dimension_name(self, answer):
        return self._resolve_statement_dimension_name(answer.statement_answer)

    def _resolve_statement_dimension_name(self, statement):
        statement_code = getattr(statement, "code", "") or ""
        instrument_entry = self.INSTRUMENT_PRACTICE_CATALOG.get(statement_code)
        if instrument_entry:
            return instrument_entry["dimension"]

        dimension = getattr(
            getattr(statement, "pe_element", None),
            "dimension",
            None,
        )
        if getattr(dimension, "name", None):
            return dimension.name

        stage_name = getattr(
            getattr(statement, "sth_stage", None),
            "name",
            None,
        )
        if stage_name:
            return self.DIMENSION_LABELS.get(stage_name, stage_name)

        if statement_code.startswith("AO."):
            return "Agile Development"
        if statement_code.startswith("CI."):
            return "Continuous Integration"
        if statement_code.startswith("CD."):
            return "Continuous Deployment"
        if statement_code.startswith("IS."):
            return "Continuous Experimentation"
        return "Unclassified"

    def _normalize_element_matrix_key(self, dimension_name, element_name):
        return (
            dimension_name,
            self.ELEMENT_NAME_ALIASES.get(element_name, element_name),
        )

    def _resolve_statement_element_name(self, statement):
        element_name = getattr(getattr(statement, "pe_element", None), "name", None)
        if element_name:
            return element_name

        statement_code = getattr(statement, "code", "") or ""
        instrument_entry = self.INSTRUMENT_PRACTICE_CATALOG.get(statement_code)
        if instrument_entry:
            return instrument_entry["element"]

        return None

    def _resolve_statement_process_names(self, statement):
        statement_code = getattr(statement, "code", "") or ""
        return self.STATEMENT_PROCESS_CATALOG.get(statement_code, ())

    def _resolve_element_name(self, answer):
        return self._resolve_statement_element_name(answer.statement_answer)

    def _resolve_organization_type_key(self, organization=None):
        organization_type_name = getattr(
            getattr(organization, "organization_type", None),
            "name",
            "",
        )
        normalized = slugify((organization_type_name or "").strip())

        if normalized in self.ORGANIZATION_TYPE_WEIGHT_MAP:
            return normalized

        return self.ORGANIZATION_TYPE_ALIASES.get(
            normalized,
            self.DEFAULT_ORGANIZATION_TYPE_KEY,
        )

    def _weights_for_organization(self, organization=None):
        return self.ORGANIZATION_TYPE_WEIGHT_MAP[
            self._resolve_organization_type_key(organization)
        ]

    def _weight_for_percentage(self, percentage, organization=None):
        return self._weights_for_organization(organization).get(percentage, percentage)

    def _instrument_weight(self, answer, organization=None):
        percentage = getattr(answer.adopted_level_answer, "percentage", 0)
        return self._weight_for_percentage(percentage, organization=organization)

    # Encurta textos longos para caber melhor nos cards e listas.
    def _compact_statement(self, text, limit=110):
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return f"{compact[: limit - 3].rstrip()}..."

    # Gera a frase-resumo exibida no topo do dashboard.
    def _build_executive_summary(self, stage_scores):
        if not stage_scores:
            return "No answered practices were found for the selected organization."

        strongest = max(stage_scores, key=lambda item: item["score"])
        weakest = min(stage_scores, key=lambda item: item["score"])
        return (
            f"{strongest['short_name']} currently leads the diagnosis with score "
            f"{strongest['score']}, while "
            f"{weakest['short_name']} needs the most attention "
            f"with score {weakest['score']}."
        )

    # Cria um título curto para cada recomendação do roadmap.
    def _recommendation_title(self, answer):
        code = answer.statement_answer.code or "Practice"
        return f"{code} - strengthen this practice"

    def _recommendation_rule(self, level, track):
        if track == "Adopt now":
            return (
                f"{level.name} practices should first be established as a stable "
                "working routine."
            )

        return (
            f"{level.name} practices should now be expanded from local usage to "
            "process-level capability."
        )

    # Gera a explicação principal da recomendação em linguagem natural.
    def _recommendation_copy(self, answer, track):
        statement = self._compact_statement(
            answer.statement_answer.text,
            limit=160,
        )
        if track == "Adopt now":
            return (
                f"Establish the practice described in '{statement}' as a "
                "repeatable team routine, "
                "with explicit ownership, execution criteria and evidence collection."
            )

        return (
            f"Expand the practice described in '{statement}' from local usage "
            "to a shared process, "
            "with documented expectations and wider team adoption."
        )

    # Resume o impacto esperado caso a recomendação seja executada.
    def _expected_impact(self, answer, track):
        stage_name = getattr(answer.statement_answer.sth_stage, "name", None)
        short_name = self.STAGE_SHORT_NAMES.get(stage_name, stage_name)
        if track == "Adopt now":
            return (
                f"Reduce low-maturity gaps in {short_name} and create a "
                "stable baseline for future cycles."
            )
        return (
            f"Move {short_name} practices from isolated adoption to a "
            "consistent process-level capability."
        )

    # Sugere a primeira ação concreta para colocar a recomendação em prática.
    def _next_step(self, answer, track):
        code = answer.statement_answer.code or "the selected practice"
        if track == "Adopt now":
            return (
                f"Map the current blockers around {code}, assign an owner "
                "and define a 30-day pilot."
            )
        return (
            f"Review how {code} is performed today and define what must "
            "change to standardize it across teams."
        )
