from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trips', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('score', models.DecimalField(decimal_places=2, max_digits=3)),
                ('comment', models.CharField(blank=True, default='', max_length=500)),
                ('trip', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='trips.trip')),
                ('given_by_rider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings_given', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'ratings',
                'ordering': ['-created_at'],
            },
        ),
    ]
