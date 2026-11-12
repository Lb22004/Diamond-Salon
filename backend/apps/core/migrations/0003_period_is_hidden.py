from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_core_domain_and_seed"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountingperiod",
            name="is_hidden",
            field=models.BooleanField(
                default=False,
                help_text="Oculto en el selector de períodos (sigue existiendo y es válido).",
            ),
        ),
        migrations.AddConstraint(
            model_name="accountingperiod",
            constraint=models.CheckConstraint(
                condition=~Q(is_active=True, is_hidden=True),
                name="ck_core_period_active_not_hidden",
            ),
        ),
    ]
