from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0020_contactmessage'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('order', 'Order'), ('user', 'User'), ('contact', 'Contact')], max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('link', models.CharField(blank=True, max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Admin Notification',
                'verbose_name_plural': 'Admin Notifications',
                'ordering': ['-created_at'],
            },
        ),
    ]
