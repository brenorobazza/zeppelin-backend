from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        (
            "apps_employee",
            "0007_rename_employee_or_employe_0ea258_idx_employee_or_employe_a918e8_idx_and_more",
        ),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="employeeorganizationmembership",
            constraint=models.UniqueConstraint(
                condition=Q(ended_at__isnull=True, is_primary=True),
                fields=("employee",),
                name="employee_single_active_primary_membership",
            ),
        ),
    ]
