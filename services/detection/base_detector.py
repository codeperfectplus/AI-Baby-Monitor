from abc import ABC, abstractmethod


class BaseDetector(ABC):
    """Abstract base class for object detectors"""

    @abstractmethod
    def detect(self, frame):
        raise NotImplementedError("Subclasses must implement this method")
