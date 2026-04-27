from engine.gateway.processors.BaseWebhookProcessor import BaseWebhookProcessor
from engine.gateway.processors.example_webhook_processor import ExampleWebhookProcessor
from engine.gateway.processors.example_webhook_processor_2 import ExampleWebhookProcessor2
from engine.gateway.processors.example_webhook_processor_3 import ExampleWebhookProcessor3

PROCESSOR_CLASSES: list[type[BaseWebhookProcessor]] = [
    ExampleWebhookProcessor,
    ExampleWebhookProcessor2,
    ExampleWebhookProcessor3,
]


def register_processors() -> None:
    for processor_class in PROCESSOR_CLASSES:
        BaseWebhookProcessor.register(processor_class)
