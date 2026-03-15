from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0017_update_contact_social_links'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='contactpage',
            name='description',
        ),
    ]
