import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from engine.shared.schemas import WebhookContext

logger = logging.getLogger(__name__)


class BaseWebhookProcessor(ABC):
    # Child classes must define a unique processor name, for example: `processor_name = 'openai'`.
    processor_name: ClassVar[str]
    # Child classes must define which model validates `context.body`.
    payload_model: ClassVar[type[BaseModel]]
    _registry: ClassVar[dict[str, type['BaseWebhookProcessor']]] = {}

    @classmethod
    def register(cls, processor_cls: type['BaseWebhookProcessor']) -> type['BaseWebhookProcessor']:
        processor_name = processor_cls.processor_name.strip()
        if not processor_name:
            raise ValueError(f'{processor_cls.__name__} must define a non-empty processor_name')

        try:
            payload_model = processor_cls.payload_model
        except AttributeError as error:
            raise ValueError(f'{processor_cls.__name__} must define a payload_model') from error

        if not issubclass(payload_model, BaseModel):
            raise ValueError(f'{processor_cls.__name__} payload_model must inherit from BaseModel')

        existing = cls._registry.get(processor_name)
        if existing is not None and existing is not processor_cls:
            raise ValueError(f'A processor is already registered for provider {processor_name}')

        cls._registry[processor_name] = processor_cls
        return processor_cls

    @classmethod
    def get_processor(cls, context: WebhookContext) -> 'BaseWebhookProcessor':
        for processor_cls in cls._registry.values():
            if processor_cls.can_process(context):
                return processor_cls()

        raise ValueError('No webhook processor registered for request context')

    @classmethod
    def can_process(cls, context: WebhookContext) -> bool:
        # Override in child processors to choose which processor handles the webhook.
        # For example, we might want to ensure that the headers match a specific pattern.
        # This is how we make sure that (for example) the OpenAI webhook processor only processes OpenAI webhooks.
        return False

    async def process(self, context: WebhookContext) -> dict[str, Any]:
        try:
            payload = self.payload_model.model_validate(context.body)
        except ValidationError as error:
            raise ValueError(
                f'Invalid webhook payload for processor={self.processor_name}: {error}'
            ) from error

        self.pre_process(context, payload)
        result = await self.execute(context, payload)
        self.post_process(context, payload)

        return {
            'status': 'processed',
            'processor': self.processor_name,
            'result': result,
        }

    def pre_process(self, context: WebhookContext, payload: BaseModel) -> None:
        logger.info('Starting webhook processor=%s path=%s', self.__class__.__name__, context.path)

    def post_process(self, context: WebhookContext, payload: BaseModel) -> None:
        logger.info('Finished webhook processor=%s path=%s', self.__class__.__name__, context.path)

    @abstractmethod
    async def execute(self, context: WebhookContext, payload: Any) -> dict[str, Any]:
        """Implement provider-specific webhook logic in child processors."""
