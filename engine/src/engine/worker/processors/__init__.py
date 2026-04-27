from engine.worker.processors.BaseProcessor import BaseProcessor
from engine.worker.processors.example_task_processor import ExampleTaskProcessor
from engine.worker.processors.example_task_processor_2 import ExampleTaskProcessor2
from engine.worker.processors.example_task_processor_3 import ExampleTaskProcessor3

PROCESSOR_CLASSES: list[type[BaseProcessor]] = [
    ExampleTaskProcessor,
    ExampleTaskProcessor2,
    ExampleTaskProcessor3,
]


def register_processors() -> None:
    for processor_class in PROCESSOR_CLASSES:
        BaseProcessor.register(processor_class)
