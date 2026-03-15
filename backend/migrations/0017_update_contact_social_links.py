from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0016_split_sitecontent_models'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contactpage',
            name='linkedin_url',
        ),
        migrations.RemoveField(
            model_name='contactpage',
            name='twitter_url',
        ),
        migrations.AddField(
            model_name='contactpage',
            name='youtube_url',
            field=models.URLField(blank=True),
        ),
    ]
