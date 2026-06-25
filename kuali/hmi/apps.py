from django.apps import AppConfig


class HmiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hmi'

    def ready(self):
        from devices.plc.runtime import start_plc_poller
        from integrations.mqtt.order_listener import start_order_listener
        start_plc_poller()
        start_order_listener()
