from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.questionnaire.analytics import QuestionnaireAnalyticsService
from apps.questionnaire.api_views import (
    QuestionnaireComparisonAnalyticsView,
    QuestionnaireDashboardAnalyticsView,
    QuestionnaireHistoryAnalyticsView,
    QuestionnaireRecommendationsAnalyticsView,
    QuestionnaireResultsAnalyticsView,
)


def make_level(level_id, name, percentage):
    return SimpleNamespace(id=level_id, name=name, percentage=percentage)


def make_questionnaire(questionnaire_id, days_ago):
    applied_date = timezone.now() - timedelta(days=days_ago)
    return SimpleNamespace(
        id=questionnaire_id,
        applied_date=applied_date,
        uploaded_at=applied_date,
    )


def make_organization(type_name):
    return SimpleNamespace(
        id=1,
        name="Zeppelin Labs",
        organization_type=SimpleNamespace(name=type_name),
        organization_size=None,
        age=48,
    )


def make_answer(
    answer_id,
    code,
    text,
    stage_name,
    dimension_name,
    level,
    questionnaire,
    comment="",
    organization_id=1,
    element_name=None,
):
    stage = SimpleNamespace(name=stage_name)
    dimension = SimpleNamespace(name=dimension_name)
    statement = SimpleNamespace(
        code=code,
        text=text,
        sth_stage=stage,
        pe_element=SimpleNamespace(dimension=dimension, name=element_name),
    )
    return SimpleNamespace(
        id=answer_id,
        questionnaire_answer=questionnaire,
        questionnaire_answer_id=questionnaire.id,
        adopted_level_answer=level,
        statement_answer=statement,
        comment_answer=comment,
        organization_answer_id=organization_id,
    )


def make_statement(code, stage_name, dimension_name, element_name=None):
    stage = SimpleNamespace(name=stage_name)
    dimension = SimpleNamespace(name=dimension_name)
    return SimpleNamespace(
        code=code,
        sth_stage=stage,
        pe_element=SimpleNamespace(dimension=dimension, name=element_name),
    )


# Esta suite evita dependencia de banco real.
# O foco aqui e testar o comportamento da camada analitica e o contrato dos endpoints.
class QuestionnaireAnalyticsServiceTests(SimpleTestCase):
    def setUp(self):
        self.service = QuestionnaireAnalyticsService.__new__(
            QuestionnaireAnalyticsService
        )
        self.service.adopted_levels = [
            make_level(1, "Not adopted", 0),
            make_level(2, "Abandoned", 10),
            make_level(3, "Realized at project/product level", 30),
            make_level(4, "Realized at process level", 60),
            make_level(5, "Institutionalized", 100),
        ]

        self.old_cycle = make_questionnaire(1, 180)
        self.current_cycle = make_questionnaire(2, 30)

        self.old_answers = [
            make_answer(
                1,
                "CI.01",
                "Every commit triggers an automated build.",
                "Continuous Integration",
                "Integration practices",
                self.service.adopted_levels[0],
                self.old_cycle,
                "No build automation yet.",
            ),
            make_answer(
                2,
                "CD.01",
                "Deployment packages are produced automatically.",
                "Continuous Deployment",
                "Delivery practices",
                self.service.adopted_levels[2],
                self.old_cycle,
                "Some teams deploy with scripts.",
            ),
        ]
        self.current_answers = [
            make_answer(
                3,
                "CI.02",
                "Automated tests are executed consistently in the pipeline.",
                "Continuous Integration",
                "Integration practices",
                self.service.adopted_levels[4],
                self.current_cycle,
                "Pipeline tests are enforced centrally.",
            ),
            make_answer(
                4,
                "CD.02",
                "Production deployments are repeatable and observable.",
                "Continuous Deployment",
                "Delivery practices",
                self.service.adopted_levels[1],
                self.current_cycle,
                "Deployment repeatability regressed after tool changes.",
            ),
        ]
        self.all_answers = self.old_answers + self.current_answers

    def test_score_for_answers_returns_average_percentage(self):
        score = self.service._score_for_answers(self.current_answers)

        self.assertEqual(score, 55)

    def test_score_for_answers_uses_calibrated_weights_by_organization_type(self):
        process_answer = [
            make_answer(
                99,
                "CI.99",
                "A process-level practice.",
                "Continuous Integration",
                "Integration practices",
                self.service.adopted_levels[3],
                self.current_cycle,
            )
        ]

        startup_score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Startup"),
        )
        software_house_score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Software House"),
        )
        it_department_score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Organization with IT Department"),
        )

        self.assertEqual(startup_score, 61)
        self.assertEqual(software_house_score, 60)
        self.assertEqual(it_department_score, 68)

    def test_score_for_answers_falls_back_to_software_house_scale_for_unknown_type(
        self,
    ):
        process_answer = [
            make_answer(
                100,
                "CI.100",
                "A process-level practice.",
                "Continuous Integration",
                "Integration practices",
                self.service.adopted_levels[3],
                self.current_cycle,
            )
        ]

        score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Unknown Organization Type"),
        )

        self.assertEqual(score, 60)

    def test_score_for_answers_treats_missing_responses_as_zero_when_total_is_provided(
        self,
    ):
        score = self.service._score_for_answers(self.current_answers, expected_total=4)

        # Median aggregation with zero-imputation for missing answers.
        # current_answers use the default software-house scale -> weights [100, 10]
        # with expected_total=4 -> [100,10,0,0]
        # median([0,0,10,100]) == 5 (rounded)
        self.assertEqual(score, 5)

    def test_score_for_answers_accepts_organization_type_aliases(self):
        process_answer = [
            make_answer(
                101,
                "CI.101",
                "A process-level practice.",
                "Continuous Integration",
                "Integration practices",
                self.service.adopted_levels[3],
                self.current_cycle,
            )
        ]

        software_alias_score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Software"),
        )
        it_department_alias_score = self.service._score_for_answers(
            process_answer,
            organization=make_organization("Organization with TI Department"),
        )

        self.assertEqual(software_alias_score, 60)
        self.assertEqual(it_department_alias_score, 68)

    def test_questionnaire_status_returns_incomplete_when_answers_are_missing(self):
        status = self.service._questionnaire_status(answered_count=2, expected_total=4)

        self.assertEqual(status, "Under Assessment")

    def test_build_recommendations_generates_tracks_from_low_maturity_answers(self):
        recommendations = self.service._build_recommendations(self.all_answers)

        self.assertEqual(len(recommendations), 3)
        self.assertEqual(recommendations[0]["track"], "Adopt now")
        self.assertEqual(recommendations[0]["current_level"], "Not adopted")
        self.assertEqual(recommendations[1]["track"], "Adopt now")
        self.assertEqual(recommendations[1]["current_level"], "Abandoned")
        self.assertEqual(recommendations[2]["track"], "Consolidate")
        self.assertEqual(
            recommendations[2]["current_level"],
            "Realized at project/product level",
        )
        self.assertEqual(
            recommendations[0]["question_description"],
            "The software architecture is modular in order to allow automated testing.",
        )
        self.assertTrue(recommendations[0]["catalog_recommendation"])
        self.assertEqual(
            recommendations[0]["reference_source"],
            "Questionnaire recommendations catalog",
        )

    def test_build_recommendations_ignores_ao_and_is_answers(self):
        ao_answer = make_answer(
            5,
            "AO.01",
            "Agile roles are defined in the organization.",
            "Agile R&D Organization",
            "Agile practices",
            self.service.adopted_levels[0],
            self.current_cycle,
        )
        is_answer = make_answer(
            6,
            "IS.01",
            "Customer feedback is captured for experimentation.",
            "R&D as an Experiment System",
            "Experimentation practices",
            self.service.adopted_levels[1],
            self.current_cycle,
        )

        recommendations = self.service._build_recommendations(
            self.all_answers + [ao_answer, is_answer]
        )

        self.assertEqual(len(recommendations), 3)
        self.assertTrue(
            all(
                item["question_id"].startswith(("CI.", "CD."))
                for item in recommendations
            )
        )

    def test_history_cycles_ignore_ao_and_is_answers_in_recommendation_counts(self):
        ao_answer = make_answer(
            5,
            "AO.01",
            "Agile roles are defined in the organization.",
            "Agile R&D Organization",
            "Agile practices",
            self.service.adopted_levels[0],
            self.old_cycle,
        )
        is_answer = make_answer(
            6,
            "IS.01",
            "Customer feedback is captured for experimentation.",
            "R&D as an Experiment System",
            "Experimentation practices",
            self.service.adopted_levels[1],
            self.current_cycle,
        )

        cycles = self.service._build_history_cycles(
            self.all_answers + [ao_answer, is_answer]
        )

        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0]["recommendation_count"], 2)
        self.assertEqual(cycles[1]["recommendation_count"], 1)

    def test_build_history_cycles_summarizes_two_cycles(self):
        cycles = self.service._build_history_cycles(self.all_answers)

        self.assertEqual(len(cycles), 2)
        self.assertEqual(cycles[0]["id"], self.old_cycle.id)
        self.assertEqual(cycles[1]["id"], self.current_cycle.id)
        self.assertEqual(cycles[0]["recommendation_count"], 2)
        self.assertEqual(cycles[1]["recommendation_count"], 1)

    def test_build_history_cycles_deduplicates_answers_within_same_cycle(self):
        duplicate_current_answer = make_answer(
            99,
            "CD.02",
            "Production deployments are repeatable and observable.",
            "Continuous Deployment",
            "Delivery practices",
            self.service.adopted_levels[4],
            self.current_cycle,
            "Latest answer should replace the earlier duplicate.",
        )

        cycles = self.service._build_history_cycles(
            self.all_answers + [duplicate_current_answer]
        )

        current_cycle = cycles[1]
        self.assertEqual(current_cycle["answered_practices"], 2)
        self.assertEqual(current_cycle["recommendation_count"], 0)

    def test_build_history_cycles_skips_aggregated_snapshot_without_questionnaire(
        self,
    ):
        aggregate_answer = make_answer(
            99,
            "CI.99",
            "Aggregated answer without a questionnaire cycle.",
            "Continuous Integration",
            "Integration practices",
            self.service.adopted_levels[3],
            self.current_cycle,
        )
        aggregate_answer.questionnaire_answer = None
        aggregate_answer.questionnaire_answer_id = None

        cycles = self.service._build_history_cycles(
            self.all_answers + [aggregate_answer]
        )

        self.assertEqual(len(cycles), 2)
        self.assertNotIn(
            "Aggregated snapshot",
            [cycle["label"] for cycle in cycles],
        )

    def test_organization_size_matches_filter_uses_numeric_buckets(self):
        class FakeQuerySet(list):
            def filter(self, **kwargs):
                size = kwargs.get("organization_size__name__iexact")
                if size is None:
                    return FakeQuerySet(self)

                return FakeQuerySet(
                    [
                        item
                        for item in self
                        if getattr(
                            getattr(item, "organization_size", None), "name", ""
                        ).lower()
                        == size.lower()
                    ]
                )

        organizations = FakeQuerySet(
            [
                SimpleNamespace(
                    id=1,
                    name="Small exact match",
                    organization_size=SimpleNamespace(name="1-10"),
                ),
                SimpleNamespace(
                    id=2,
                    name="Large exact match",
                    organization_size=SimpleNamespace(name="1000+"),
                ),
                SimpleNamespace(
                    id=3,
                    name="Numeric size",
                    organization_size=SimpleNamespace(name="7"),
                ),
            ]
        )

        request = SimpleNamespace(query_params={"organization_size": "1-10"})

        with patch(
            "apps.questionnaire.analytics.Organization.objects.all",
            return_value=organizations,
        ):
            filtered = self.service._resolve_benchmark_peer_organizations(request)

        self.assertEqual([org.name for org in filtered], ["Small exact match"])

    def test_resolve_dimension_name_uses_instrument_catalog_for_ci_cd_questions(self):
        dimension_name = self.service._resolve_dimension_name(self.old_answers[0])

        self.assertEqual(dimension_name, "Development")

    def test_dimension_stage_overview_includes_non_ci_cd_dimensions(self):
        team_answer = make_answer(
            101,
            "AO.99",
            "Team practice outside the CI/CD catalog.",
            "Agile R&D Organization",
            "Team",
            self.service.adopted_levels[3],
            self.current_cycle,
        )
        operation_answer = make_answer(
            102,
            "IS.99",
            "Operation practice outside the CI/CD catalog.",
            "R&D as an Experiment System",
            "Operation",
            self.service.adopted_levels[4],
            self.current_cycle,
        )

        overview = self.service._build_dimension_stage_overview(
            self.all_answers + [team_answer, operation_answer]
        )
        dimension_names = [item["name"] for item in overview["dimensions"]]

        self.assertIn("Team", dimension_names)
        self.assertIn("Operation", dimension_names)

    def test_dimension_stage_matrix_counts_statements_by_dimension_and_stage(self):
        statements = [
            make_statement("AO.100", "Agile R&D Organization", "Development"),
            make_statement("AO.101", "Agile R&D Organization", "Development"),
            make_statement("CI.100", "Continuous Integration", "Quality"),
            make_statement("CD.100", "Continuous Deployment", "Business"),
            make_statement(
                "IS.100",
                "R&D as an Experiment System",
                "User/Customer",
            ),
        ]

        matrix = self.service._build_dimension_stage_matrix(
            statements=statements,
            include_baseline=False,
        )
        rows_by_name = {item["name"]: item for item in matrix["dimensions"]}

        self.assertEqual(rows_by_name["Development"]["agile_count"], 2)
        self.assertEqual(rows_by_name["Quality"]["ci_count"], 1)
        self.assertEqual(rows_by_name["Business"]["cd_count"], 1)
        self.assertEqual(
            rows_by_name["User/Customer"]["experimentation_count"],
            1,
        )
        self.assertEqual(rows_by_name["Development"]["practice_count"], 2)
        self.assertEqual(matrix["summary"]["agile_count"], 2)
        self.assertEqual(matrix["summary"]["ci_count"], 1)
        self.assertEqual(matrix["summary"]["cd_count"], 1)
        self.assertEqual(matrix["summary"]["experimentation_count"], 1)
        self.assertEqual(matrix["summary"]["statement_count"], 5)

    def test_dimension_element_overview_includes_non_ci_cd_dimensions(self):
        team_answer = make_answer(
            103,
            "AO.100",
            "Team element outside the CI/CD catalog.",
            "Agile R&D Organization",
            "Team",
            self.service.adopted_levels[3],
            self.current_cycle,
            element_name="Self-reflection and discipline",
        )
        operation_answer = make_answer(
            104,
            "IS.100",
            "Operation element outside the CI/CD catalog.",
            "R&D as an Experiment System",
            "Operation",
            self.service.adopted_levels[4],
            self.current_cycle,
            element_name="Reusable infrastructure",
        )

        overview = self.service._build_dimension_element_overview(
            self.all_answers + [team_answer, operation_answer],
            statements=[
                answer.statement_answer
                for answer in self.all_answers + [team_answer, operation_answer]
            ],
            include_baseline=False,
        )
        dimension_names = [item["dimension_name"] for item in overview["rows"]]
        element_names = [item["element_name"] for item in overview["rows"]]

        self.assertIn("Team", dimension_names)
        self.assertIn("Operation", dimension_names)
        self.assertIn("Self-reflection and discipline", element_names)
        self.assertIn("Reusable infrastructure", element_names)

    def test_process_overview_groups_scores_by_process_and_stage(self):
        organization = make_organization("Startup")
        answers = [
            make_answer(
                105,
                "AO.01",
                "Business alignment in agile stage.",
                "Agile R&D Organization",
                "Business",
                self.service.adopted_levels[4],
                self.current_cycle,
            ),
            make_answer(
                106,
                "CI.02",
                "Planning and control in CI.",
                "Continuous Integration",
                "Development",
                self.service.adopted_levels[2],
                self.current_cycle,
            ),
            make_answer(
                107,
                "CD.04",
                "Release controls in CD.",
                "Continuous Deployment",
                "Quality",
                self.service.adopted_levels[1],
                self.current_cycle,
            ),
        ]

        overview = self.service._build_process_overview(
            answers,
            organization=organization,
        )
        rows_by_name = {item["name"]: item for item in overview["rows"]}

        self.assertEqual(rows_by_name["Business Alignment"]["agile_score"], 100)
        self.assertEqual(rows_by_name["Business Alignment"]["cd_score"], 17)
        self.assertEqual(
            rows_by_name["Continuous Planning, Monitoring and Control"]["ci_score"],
            33,
        )
        self.assertEqual(
            rows_by_name["Continuous Quality Assurance"]["cd_score"],
            17,
        )
        self.assertEqual(
            rows_by_name["Continuous Software Measurement"]["cd_score"],
            17,
        )
        self.assertEqual(overview["summary"]["agile_score"], 100)
        self.assertEqual(overview["summary"]["ci_score"], 33)
        self.assertEqual(overview["summary"]["cd_score"], 17)
        self.assertEqual(overview["summary"]["organization_score"], 37)

    def test_dashboard_payload_uses_current_context_data(self):
        organization = make_organization("Startup")
        request = SimpleNamespace(query_params={}, user=None)

        with patch.object(
            self.service,
            "_resolve_context",
            return_value={
                "organization": organization,
                "questionnaire": self.current_cycle,
                "stage_scope": "ci_cd",
                "all_answers": self.all_answers,
                "current_answers": self.current_answers,
                "expected_statement_count": 4,
                "expected_stage_counts": {
                    "Continuous Integration": 2,
                    "Continuous Deployment": 2,
                },
            },
        ), patch(
            "apps.questionnaire.analytics.Questionnaire.objects.filter"
        ) as mock_filter:
            mock_filter.return_value = []
            payload = self.service.get_dashboard_payload(request)

        self.assertEqual(payload["organization"]["name"], "Zeppelin Labs")
        self.assertEqual(payload["cycle"]["id"], self.current_cycle.id)
        # With organization type 'Startup' the instrument weights map 10->17.
        # Dashboard snapshot uses expected_total=4 so missing answers are imputed as zeros.
        # Weights -> [100,17,0,0] -> median = 8.5 -> round to 8
        self.assertEqual(payload["snapshot"]["overall_score"], 8)
        # With the new median + zero-imputation scoring the overall score is 8,
        # which maps to the closest adopted level of 0 -> 'Not adopted'.
        self.assertEqual(payload["snapshot"]["overall_level"], "Not adopted")
        self.assertEqual(payload["snapshot"]["answered_practices"], 2)
        self.assertEqual(
            payload["snapshot"]["questionnaire_status"], "Under Assessment"
        )
        self.assertEqual(payload["snapshot"]["recommendation_count"], 1)
        self.assertEqual(len(payload["stage_scores"]), 2)
        self.assertEqual(payload["stage_scores"][0]["score"], 50)
        self.assertEqual(payload["stage_scores"][1]["score"], 8)

    def test_results_payload_reports_questionnaire_status(self):
        organization = make_organization("Startup")
        request = SimpleNamespace(query_params={}, user=None)
        statements = [
            make_statement("CI.01", "Continuous Integration", "Development"),
            make_statement("CI.04", "Continuous Integration", "Quality"),
            make_statement("CD.01", "Continuous Deployment", "User/Customer"),
            make_statement("CD.02", "Continuous Deployment", "Quality"),
        ]

        with patch.object(
            self.service,
            "_resolve_context",
            return_value={
                "organization": organization,
                "questionnaire": self.current_cycle,
                "stage_scope": "ci_cd",
                "all_answers": self.all_answers,
                "current_answers": self.current_answers,
                "expected_statement_count": 4,
                "expected_stage_counts": {
                    "Continuous Integration": 2,
                    "Continuous Deployment": 2,
                },
            },
        ), patch(
            "apps.questionnaire.analytics.Statement.objects.select_related",
            return_value=statements,
        ):
            payload = self.service.get_results_payload(request)

        self.assertEqual(payload["summary"]["questionnaire_status"], "Under Assessment")
        self.assertEqual(payload["summary"]["represented_stages"], 2)
        self.assertEqual(payload["summary"]["total_stages"], 2)
        self.assertEqual(payload["summary"]["missing_stages"], [])
        self.assertEqual(payload["summary"]["overall_score"], 58)

    def test_recommendations_payload_reports_questionnaire_status(self):
        organization = make_organization("Startup")
        request = SimpleNamespace(query_params={}, user=None)

        with patch.object(
            self.service,
            "_resolve_context",
            return_value={
                "organization": organization,
                "questionnaire": self.current_cycle,
                "stage_scope": "ci_cd",
                "all_answers": self.all_answers,
                "current_answers": self.current_answers,
                "expected_statement_count": 4,
                "expected_stage_counts": {
                    "Continuous Integration": 2,
                    "Continuous Deployment": 2,
                },
            },
        ):
            payload = self.service.get_recommendations_payload(request)

        self.assertEqual(payload["summary"]["questionnaire_status"], "Under Assessment")

    def test_adoption_level_stage_overview_reproduces_all_stage_counts(self):
        agile_answer = make_answer(
            5,
            "AO.01",
            "Agile roles are defined in the organization.",
            "Agile R&D Organization",
            "Agile practices",
            self.service.adopted_levels[2],
            self.current_cycle,
        )
        experimentation_answer = make_answer(
            6,
            "IS.01",
            "Customer feedback is captured for experimentation.",
            "R&D as an Experiment System",
            "Experimentation practices",
            self.service.adopted_levels[4],
            self.current_cycle,
        )
        overview = self.service._build_adoption_level_stage_overview(
            self.all_answers + [agile_answer, experimentation_answer],
            organization=make_organization("Organization with IT Department"),
        )

        self.assertEqual(len(overview["stages"]), 4)
        self.assertEqual(overview["totals"]["agile_count"], 1)
        self.assertEqual(overview["totals"]["ci_count"], 2)
        self.assertEqual(overview["totals"]["cd_count"], 2)
        self.assertEqual(overview["totals"]["experimentation_count"], 1)
        self.assertEqual(overview["totals"]["organization_count"], 6)
        self.assertEqual(overview["degree_of_adoption"]["agile_score"], 38)
        self.assertEqual(overview["degree_of_adoption"]["ci_score"], 50)
        self.assertEqual(overview["degree_of_adoption"]["cd_score"], 30)
        self.assertEqual(overview["degree_of_adoption"]["experimentation_score"], 100)
        self.assertEqual(overview["degree_of_adoption"]["organization_score"], 50)

        not_adopted_row = next(
            item for item in overview["levels"] if item["label"] == "Not adopted"
        )
        abandoned_row = next(
            item for item in overview["levels"] if item["label"] == "Abandoned"
        )
        institutionalized_row = next(
            item for item in overview["levels"] if item["label"] == "Institutionalized"
        )

        project_row = next(
            item
            for item in overview["levels"]
            if item["label"] == "Realized at project/product level"
        )

        self.assertEqual(not_adopted_row["ci_count"], 1)
        self.assertEqual(not_adopted_row["cd_count"], 0)
        self.assertEqual(abandoned_row["cd_count"], 1)
        self.assertEqual(institutionalized_row["ci_count"], 1)
        self.assertEqual(project_row["agile_count"], 1)
        self.assertEqual(institutionalized_row["experimentation_count"], 1)

    def test_dimension_element_overview_groups_rows_by_dimension_and_element(self):
        overview = self.service._build_dimension_element_overview(
            self.current_answers,
            statements=[answer.statement_answer for answer in self.current_answers],
            include_baseline=False,
        )

        self.assertEqual(overview["summary"]["ci_count"], 1)
        self.assertEqual(overview["summary"]["cd_count"], 1)
        self.assertEqual(overview["summary"]["statement_count"], 2)

        ci_row = next(
            item
            for item in overview["rows"]
            if item["element_name"] == "Modularized architecture and design"
        )
        cd_row = next(
            item for item in overview["rows"] if item["element_name"] == "Audits"
        )

        self.assertEqual(ci_row["dimension_name"], "Development")
        self.assertEqual(ci_row["ci_count"], 1)
        self.assertEqual(ci_row["ci_score"], 100)
        self.assertEqual(ci_row["practice_count"], 1)
        self.assertEqual(cd_row["dimension_name"], "Quality")
        self.assertEqual(cd_row["cd_count"], 1)
        self.assertEqual(cd_row["cd_score"], 10)

    def test_dimension_element_overview_uses_baseline_for_full_instrument(self):
        overview = self.service._build_dimension_element_overview(statements=[])

        rows_by_element = {item["element_name"]: item for item in overview["rows"]}

        self.assertEqual(
            rows_by_element["Continuous planning activities"]["agile_count"],
            6,
        )
        self.assertEqual(
            rows_by_element["Contemporary and continuously evolving skills"][
                "experimentation_count"
            ],
            2,
        )
        self.assertEqual(overview["summary"]["agile_count"], 26)
        self.assertEqual(overview["summary"]["experimentation_count"], 13)


# Esta suite valida se as views expostas ao frontend respondem com o contrato esperado.
class QuestionnaireAnalyticsApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(
            is_authenticated=True,
            email="alex@example.com",
            username="alex@example.com",
        )

    def _dispatch(self, view, url, payload_key, payload):
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        with patch(
            "apps.questionnaire.api_views.QuestionnaireAnalyticsService"
        ) as mocked:
            service = mocked.return_value
            getattr(service, payload_key).return_value = payload
            response = view.as_view()(request)

        return response

    def test_dashboard_endpoint_returns_payload(self):
        response = self._dispatch(
            QuestionnaireDashboardAnalyticsView,
            "/questionnaire/analytics/dashboard/",
            "get_dashboard_payload",
            {"snapshot": {"overall_score": 55}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["snapshot"]["overall_score"], 55)

    def test_results_endpoint_returns_payload(self):
        response = self._dispatch(
            QuestionnaireResultsAnalyticsView,
            "/questionnaire/analytics/results/",
            "get_results_payload",
            {"summary": {"stage_gap": 20}, "dimensions": []},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["stage_gap"], 20)

    def test_recommendations_endpoint_returns_payload(self):
        response = self._dispatch(
            QuestionnaireRecommendationsAnalyticsView,
            "/questionnaire/analytics/recommendations/",
            "get_recommendations_payload",
            {"summary": {"triggered_recommendations": 3}, "items": []},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["triggered_recommendations"], 3)

    def test_history_endpoint_returns_payload(self):
        response = self._dispatch(
            QuestionnaireHistoryAnalyticsView,
            "/questionnaire/analytics/history/",
            "get_history_payload",
            {"summary": {"cycle_count": 2}, "cycles": []},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["cycle_count"], 2)

    def test_comparison_endpoint_returns_payload(self):
        response = self._dispatch(
            QuestionnaireComparisonAnalyticsView,
            "/questionnaire/analytics/comparison/",
            "get_comparison_payload",
            {"summary": {"delta": 10}, "lenses": {}},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["delta"], 10)

    def test_dashboard_endpoint_returns_400_for_validation_error(self):
        request = self.factory.get("/questionnaire/analytics/dashboard/")
        force_authenticate(request, user=self.user)

        with patch(
            "apps.questionnaire.api_views.QuestionnaireAnalyticsService"
        ) as mocked:
            service = mocked.return_value
            service.get_dashboard_payload.side_effect = ValidationError(
                "organization_id not found"
            )
            response = QuestionnaireDashboardAnalyticsView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "organization_id not found")
