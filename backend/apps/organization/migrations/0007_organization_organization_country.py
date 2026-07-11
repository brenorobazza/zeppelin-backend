from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("apps_organization", "0006_organization_organization_sector_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="organization_country",
            field=models.CharField(
                blank=True,
                help_text="organization country",
                max_length=100,
                null=True,
            ),
        ),
    ]
