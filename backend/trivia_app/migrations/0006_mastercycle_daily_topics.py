from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('trivia_app', '0005_alter_trophyaward_user')]

    operations = [
        migrations.AddField(
            model_name='mastercycle',
            name='daily_topics',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
