from datetime import datetime

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import UserOrganizationPreference
from apps.employee.models import Employee
from apps.organization.models import (
    Organization,
    OrganizationCategory,
    OrganizationType,
    Size,
)
from apps.questionnaire.models import AdoptedLevel, Answer, Questionnaire, Statement


class Command(BaseCommand):
    help = (
        "Load a small deterministic benchmark seed with six organizations, "
        "one complete questionnaire per org, and a demo user linked to every org."
    )

    seed_username = "benchmark.seed"
    seed_email = "benchmark.seed@zeppelin.local"
    seed_password = "zeppelin-benchmark-123"
    seed_first_name = "Benchmark"
    seed_last_name = "Seed"

    organization_seed = (
        {
            "name": "Benchmark Seed - Atlas Forge",
            "description": "B2B technology org used as the benchmark current organization.",
            "organization_country": "Brazil",
            "organization_sector": "Software",
            "target_audience": "B2B",
            "category": "Technology",
            "size": "1-10",
            "type": "Platform Startup",
            "type_description": "Early-stage platform company.",
            "age": 6,
            "role": "CTO",
            "applied_date": datetime(2025, 9, 10, 10, 0, 0),
            "profile": "high",
        },
        {
            "name": "Benchmark Seed - Beta Flow",
            "description": "B2B technology org with a second complete snapshot.",
            "organization_country": "Brazil",
            "organization_sector": "Software",
            "target_audience": "B2B",
            "category": "Technology",
            "size": "11-50",
            "type": "Growth Platform",
            "type_description": "Growing platform company.",
            "age": 9,
            "role": "Head of Engineering",
            "applied_date": datetime(2025, 10, 8, 10, 0, 0),
            "profile": "high",
        },
        {
            "name": "Benchmark Seed - Gamma Ops",
            "description": "B2B technology org with a balanced profile.",
            "organization_country": "Brazil",
            "organization_sector": "Software",
            "target_audience": "B2B",
            "category": "Technology",
            "size": "51-200",
            "type": "Scale-up Software",
            "type_description": "Scale-up software company.",
            "age": 12,
            "role": "Engineering Manager",
            "applied_date": datetime(2025, 11, 12, 10, 0, 0),
            "profile": "medium",
        },
        {
            "name": "Benchmark Seed - Delta Care",
            "description": "B2B healthcare org with a balanced profile.",
            "organization_country": "Brazil",
            "organization_sector": "Health",
            "target_audience": "B2B",
            "category": "Healthcare",
            "size": "51-200",
            "type": "Clinical SaaS",
            "type_description": "Healthcare software company.",
            "age": 15,
            "role": "Engineering Lead",
            "applied_date": datetime(2025, 12, 4, 10, 0, 0),
            "profile": "medium",
        },
        {
            "name": "Benchmark Seed - Epsilon Shop",
            "description": "B2B retail org used to diversify the peer group.",
            "organization_country": "Brazil",
            "organization_sector": "Commerce",
            "target_audience": "B2B",
            "category": "Retail",
            "size": "201-500",
            "type": "Commerce Platform",
            "type_description": "Commerce software company.",
            "age": 18,
            "role": "Product Engineering Manager",
            "applied_date": datetime(2026, 1, 15, 10, 0, 0),
            "profile": "low",
        },
        {
            "name": "Benchmark Seed - Zeta Learn",
            "description": "B2C education org that stays out of the B2B peer group.",
            "organization_country": "Brazil",
            "organization_sector": "Education",
            "target_audience": "B2C",
            "category": "Education",
            "size": "501-1000",
            "type": "Learning Platform",
            "type_description": "Education software company.",
            "age": 8,
            "role": "Engineering Manager",
            "applied_date": datetime(2026, 2, 5, 10, 0, 0),
            "profile": "low",
        },
    )

    profile_stage_percentages = {
        "high": {
            "Traditional Development": [30, 30, 60, 60, 60],
            "Agile R&D Organization": [60, 100, 60, 100, 60, 100, 60, 100],
            "Continuous Integration": [60, 100, 60, 100, 60, 100, 60, 100],
            "Continuous Deployment": [60, 60, 100, 60, 60, 100, 60, 100],
            "R&D as an Experiment System": [30, 60, 30, 60, 30, 60, 100, 60],
        },
        "medium": {
            "Traditional Development": [10, 30, 30, 30, 10],
            "Agile R&D Organization": [30, 60, 30, 60, 30, 60, 30, 60],
            "Continuous Integration": [30, 60, 30, 60, 30, 60, 30, 60],
            "Continuous Deployment": [30, 30, 60, 30, 60, 30, 60, 30],
            "R&D as an Experiment System": [10, 30, 10, 30, 10, 30, 10, 30],
        },
        "low": {
            "Traditional Development": [0, 10, 10, 10, 0],
            "Agile R&D Organization": [0, 10, 30, 10, 0, 10],
            "Continuous Integration": [0, 10, 30, 10, 0, 10],
            "Continuous Deployment": [0, 10, 30, 10, 0, 10],
            "R&D as an Experiment System": [0, 10, 0, 10, 0, 10],
        },
    }

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Loading benchmark E2E seed..."))

        call_command("load_initial_questionnaire_data")

        adopted_levels = {
            level.percentage: level
            for level in AdoptedLevel.objects.order_by("percentage")
        }
        statements = list(
            Statement.objects.select_related("sth_stage").order_by("code")
        )

        if not statements:
            self.stdout.write(
                self.style.ERROR("No questionnaire statements were found.")
            )
            return

        demo_user = self._create_or_update_seed_user()
        organizations = {}
        employees = {}

        for scenario in self.organization_seed:
            organization = self._create_or_update_organization(scenario)
            employee = self._create_or_update_employee(scenario, organization)
            organizations[scenario["name"]] = organization
            employees[scenario["name"]] = employee

        self._clear_previous_seed_data(employees)

        total_answers = 0
        created_questionnaires = []

        for scenario in self.organization_seed:
            organization = organizations[scenario["name"]]
            employee = employees[scenario["name"]]
            questionnaire = self._create_questionnaire(employee, scenario)
            created_questionnaires.append((organization, questionnaire))
            total_answers += self._create_answers_for_questionnaire(
                organization=organization,
                questionnaire=questionnaire,
                statements=statements,
                adopted_levels=adopted_levels,
                profile_key=scenario["profile"],
            )

        preference, _ = UserOrganizationPreference.objects.get_or_create(user=demo_user)
        preference.current_organization = organizations[
            self.organization_seed[0]["name"]
        ]
        preference.save(update_fields=["current_organization"])

        self.stdout.write(self.style.SUCCESS("Benchmark E2E seed loaded successfully."))
        self.stdout.write(
            f"Seed user: {demo_user.username} / password: {self.seed_password}"
        )
        self.stdout.write(
            f"Current organization: {organizations[self.organization_seed[0]['name']].name}"
        )
        self.stdout.write(f"Organizations created or updated: {len(organizations)}")
        self.stdout.write(f"Questionnaires created: {len(created_questionnaires)}")
        self.stdout.write(f"Answers created: {total_answers}")

    def _create_or_update_seed_user(self):
        user, created = User.objects.get_or_create(
            username=self.seed_username,
            defaults={"email": self.seed_email},
        )

        changed = created
        if user.email != self.seed_email:
            user.email = self.seed_email
            changed = True
        if user.first_name != self.seed_first_name:
            user.first_name = self.seed_first_name
            changed = True
        if user.last_name != self.seed_last_name:
            user.last_name = self.seed_last_name
            changed = True
        if not user.check_password(self.seed_password):
            user.set_password(self.seed_password)
            changed = True
        if changed:
            user.save()

        return user

    def _create_or_update_organization(self, scenario):
        category, _ = OrganizationCategory.objects.get_or_create(
            name=scenario["category"]
        )
        organization_type, _ = OrganizationType.objects.get_or_create(
            name=scenario["type"],
            defaults={
                "description": scenario["type_description"],
                "category_organization_type": category,
            },
        )

        if (
            organization_type.description != scenario["type_description"]
            or organization_type.category_organization_type_id != category.id
        ):
            organization_type.description = scenario["type_description"]
            organization_type.category_organization_type = category
            organization_type.save(
                update_fields=["description", "category_organization_type"]
            )

        size, _ = Size.objects.get_or_create(name=scenario["size"])

        organization, _ = Organization.objects.update_or_create(
            name=scenario["name"],
            defaults={
                "description": scenario["description"],
                "organization_country": scenario["organization_country"],
                "organization_sector": scenario["organization_sector"],
                "target_audience": scenario["target_audience"],
                "organization_size": size,
                "organization_type": organization_type,
                "age": scenario["age"],
            },
        )
        return organization

    def _create_or_update_employee(self, scenario, organization):
        employee, _ = Employee.objects.update_or_create(
            e_mail=self.seed_email,
            employee_organization=organization,
            defaults={
                "name": f"{self.seed_first_name} {self.seed_last_name}",
                "role": scenario["role"],
            },
        )
        return employee

    def _clear_previous_seed_data(self, employees):
        demo_questionnaires = Questionnaire.objects.filter(
            employee_questionnaire__in=list(employees.values())
        )
        Answer.objects.filter(questionnaire_answer__in=demo_questionnaires).delete()
        demo_questionnaires.delete()

    def _create_questionnaire(self, employee, scenario):
        questionnaire = Questionnaire(
            applied_date=timezone.make_aware(scenario["applied_date"]),
            employee_questionnaire=employee,
        )
        questionnaire.document.save(
            f"{scenario['name'].lower().replace(' ', '-')}.txt",
            ContentFile(
                f"Benchmark seed questionnaire for {employee.employee_organization.name}".encode(
                    "utf-8"
                )
            ),
            save=False,
        )
        questionnaire.save()
        return questionnaire

    def _create_answers_for_questionnaire(
        self,
        organization,
        questionnaire,
        statements,
        adopted_levels,
        profile_key,
    ):
        created_answers = 0
        stage_counters = {}

        for statement in statements:
            stage_name = getattr(statement.sth_stage, "name", "") or "Unknown stage"
            percentage = self._resolve_percentage(
                profile_key, stage_name, stage_counters
            )
            adopted_level = adopted_levels[percentage]

            Answer.objects.create(
                questionnaire_answer=questionnaire,
                adopted_level_answer=adopted_level,
                statement_answer=statement,
                comment_answer=(
                    f"Benchmark seed {profile_key} profile for {stage_name}"
                ),
                organization_answer=organization,
            )

            stage_counters[stage_name] = stage_counters.get(stage_name, 0) + 1
            created_answers += 1

        return created_answers

    def _resolve_percentage(self, profile_key, stage_name, stage_counters):
        stage_pattern = self.profile_stage_percentages.get(profile_key, {}).get(
            stage_name
        )
        if not stage_pattern:
            return 30

        index = stage_counters.get(stage_name, 0)
        return stage_pattern[index % len(stage_pattern)]
