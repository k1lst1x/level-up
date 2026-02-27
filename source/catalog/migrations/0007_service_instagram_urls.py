from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_service_image_4_service_image_5_service_image_6"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="instagram_urls",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Вставь 2–4 ссылки на посты/Reels, разделяя пробелами, запятой или с новой строки.",
                verbose_name="Instagram ссылки (2–4)"
            ),
        ),
    ]
