import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ValidationError

from engine.shared.schemas import JobMessage, TaskStatus

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    # Child classes must define a unique task name, for example: `task_name = 'generate_report'`.
    task_name: ClassVar[str]
    # Child classes must define which model validates `message.data`.
    payload_model: ClassVar[type[BaseModel]]
    _registry: ClassVar[dict[str, type['BaseProcessor']]] = {}

    @classmethod
    def register(cls, processor_cls: type['BaseProcessor']) -> type['BaseProcessor']:
        """Register a processor class with the base processor.

        Args:
            processor_cls: The processor class to register.

        Raises:
            ValueError: If the processor class does not define a non-empty task_name.
            ValueError: If a processor is already registered for the task.

        Returns:
            The processor class.
        """
        task_name = processor_cls.task_name.strip()
        if not task_name:
            raise ValueError(f'{processor_cls.__name__} must define a non-empty task_name')

        try:
            payload_model = processor_cls.payload_model
        except AttributeError as error:
            raise ValueError(f'{processor_cls.__name__} must define a payload_model') from error

        if not issubclass(payload_model, BaseModel):
            raise ValueError(f'{processor_cls.__name__} payload_model must inherit from BaseModel')

        existing = cls._registry.get(task_name)
        if existing is not None and existing is not processor_cls:
            raise ValueError(f'A processor is already registered for task {task_name}')

        cls._registry[task_name] = processor_cls
        return processor_cls

    @classmethod
    def get_processor(cls, task_name: str) -> 'BaseProcessor':
        """Given a task name, return the appropriate processor class.

        Args:
            task_name: The name of the task to get the processor for.

        Returns:
            The processor class for the task.

        Raises:
            ValueError: If no processor is registered for the task.
        """
        processor_cls = cls._registry.get(task_name)
        if processor_cls is None:
            raise ValueError(f'No processor registered for task {task_name}')

        return processor_cls()

    async def process(self, message: JobMessage) -> None:
        """Process a task message.

        Args:
            message: The task message to process.

        Raises:
            ValueError: If the task message is not valid.
        """
        # Check if the task should be processed
        if not self.should_process(message):
            logger.info(
                'Skipping task id=%s for task=%s status=%s',
                message.id,
                message.task,
                message.status,
            )
            return

        # Validate the data payload
        try:
            payload = self.payload_model.model_validate(message.data)
        except ValidationError as error:
            logger.error(
                'Invalid data payload for task id=%s task=%s processor=%s: %s',
                message.id,
                message.task,
                self.__class__.__name__,
                error,
            )
            return

        # Execute the task
        self.pre_process(message, payload)
        await self.execute(message, payload)
        self.post_process(message, payload)

    def should_process(self, message: JobMessage) -> bool:
        # Override in child processors to gate processing and run task-specific checks.
        return message.status == TaskStatus.QUEUED

    def pre_process(self, message: JobMessage, payload: BaseModel) -> None:
        logger.info('Starting processor=%s task_id=%s', self.__class__.__name__, message.id)

    def post_process(self, message: JobMessage, payload: BaseModel) -> None:
        logger.info('Finished processor=%s task_id=%s', self.__class__.__name__, message.id)

    @abstractmethod
    async def execute(self, message: JobMessage, payload: Any) -> None:
        """Implement task-specific logic in child processors."""
