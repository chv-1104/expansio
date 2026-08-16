from django.apps import AppConfig


class ExpansioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expansio'

    def ready(self):
        import expansio.signals
