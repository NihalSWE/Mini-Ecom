from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0018_remove_contactpage_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactpage',
            name='map_embed_url',
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
