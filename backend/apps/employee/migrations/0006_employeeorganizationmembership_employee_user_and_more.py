from django.conf import settings
from django.db import migrations, models
from django.db.models import Q, F
import django.db.models.deletion
from django.utils import timezone


def forwards_populate_memberships_and_user(apps, schema_editor):
    Employee = apps.get_model("apps_employee", "Employee")
    Membership = apps.get_model("apps_employee", "EmployeeOrganizationMembership")
    User = apps.get_model(
        settings.AUTH_USER_MODEL.split(".")[0], settings.AUTH_USER_MODEL.split(".")[1]
    )

    for employee in Employee.objects.all().iterator():
        if employee.user_id is None and getattr(employee, "e_mail", None):
            matched_user = (
                User.objects.filter(email__iexact=employee.e_mail)
                .order_by("id")
                .first()
            )
            if matched_user is not None:
                employee.user_id = matched_user.id
                employee.save(update_fields=["user"])

        organization_id = getattr(employee, "employee_organization_id", None)
        if not organization_id:
            continue

        has_membership = Membership.objects.filter(
            employee_id=employee.id,
            organization_id=organization_id,
        ).exists()
        if has_membership:
            continue

        Membership.objects.create(
            employee_id=employee.id,
            organization_id=organization_id,
            started_at=employee.created_at or timezone.now(),
            ended_at=None,
            role_at_org=getattr(employee, "role", None),
            is_primary=True,
        )


def backwards_noop(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("apps_organization", "0001_initial"),
        ("apps_employee", "0005_alter_sthstageexperiencelevel_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="employee_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="EmployeeOrganizationMembership",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("started_at", models.DateTimeField()),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "role_at_org",
                    models.CharField(blank=True, max_length=300, null=True),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("modified_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_memberships",
                        to="apps_employee.employee",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="employee_memberships",
                        to="apps_organization.organization",
                    ),
                ),
            ],
            options={
                "db_table": "employee_organization_membership",
                "ordering": ["-started_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="employee",
            name="organizations",
            field=models.ManyToManyField(
                blank=True,
                related_name="member_employees",
                through="apps_employee.EmployeeOrganizationMembership",
                to="apps_organization.organization",
            ),
        ),
        migrations.AddConstraint(
            model_name="employeeorganizationmembership",
            constraint=models.CheckConstraint(
                check=Q(ended_at__isnull=True) | Q(ended_at__gte=F("started_at")),
                name="employee_org_membership_valid_period",
            ),
        ),
        migrations.AddIndex(
            model_name="employeeorganizationmembership",
            index=models.Index(
                fields=["employee", "organization"],
                name="employee_or_employe_0ea258_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="employeeorganizationmembership",
            index=models.Index(
                fields=["employee", "ended_at"], name="employee_or_employe_81831d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="employeeorganizationmembership",
            index=models.Index(
                fields=["organization", "ended_at"],
                name="employee_or_organiz_619738_idx",
            ),
        ),
        migrations.RunPython(forwards_populate_memberships_and_user, backwards_noop),
    ]
