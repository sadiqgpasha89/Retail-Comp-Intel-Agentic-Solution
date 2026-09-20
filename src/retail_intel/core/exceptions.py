"""Custom domain exceptions for Retail Competitor Intelligence Platform."""


class RetailIntelException(Exception):
    """Base exception for all domain errors."""
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IngestionError(RetailIntelException):
    """Raised when harvest or raw payload ingestion fails."""
    pass


class NormalizationError(RetailIntelException):
    """Raised when schema normalization or barcode validation fails."""
    pass


class DriftThresholdExceededError(RetailIntelException):
    """Raised when statistical PSI or Wasserstein distance crosses critical tolerance."""
    pass


class AmbiguousMatchError(RetailIntelException):
    """Raised when candidate similarity is between 0.65 and 0.92 requiring agentic arbitration."""
    pass


class PhantomStockDetectedError(RetailIntelException):
    """Raised when competitor price reflects an unfulfilled or phantom stock listing."""
    pass


class HoneypotDetectedError(RetailIntelException):
    """Raised when scraper detects synthetic anti-bot honeypot content."""
    pass


class MultimodalClashError(RetailIntelException):
    """Raised when text claims contradict visual OCR or review evidence."""
    pass


class AgentBudgetExceededError(RetailIntelException):
    """Raised when an agent hits its maximum step or iteration ceiling."""
    pass
