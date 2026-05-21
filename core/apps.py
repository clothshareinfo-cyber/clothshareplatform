from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """
        This method is called when the Django app is fully loaded and ready.
        This is where we connect our signals for automatic notifications.
        """
       
        try:
           
            import core.signals
            print(" ClothShare Core app loaded successfully!")
            print(" All notification signals connected and ready!")
            print(" Admin will now receive automatic email notifications!")
        except ImportError as e:
            print(f" Could not import signals: {e}")
        except Exception as e:
            print(f" Error loading Core app: {e}")
