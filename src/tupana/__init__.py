"""SDK oficial de Tupana para Python.

.. code-block:: python

    from tupana import Tupana

    tupana = Tupana()  # lee TUPANA_API_KEY
    batch = tupana.documents.create_batch(
        [
            {
                "dte_type": {"code": "33"},
                "document_issuer": {"rut": "76543210-3"},
                "document_receiver": {"rut": "77777777-7"},
                "details": [{"item_name": "Asesoría", "quantity": 1, "unit_price": 150000}],
            }
        ],
        use_defaults=True,
    )
"""

from . import types
from ._base import DEFAULT_BASE_URL, random_idempotency_key
from ._client import AsyncTupana, Tupana
from ._errors import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    BatchTimeoutError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PayloadTooLargeError,
    PermissionDeniedError,
    RateLimitError,
    TupanaError,
    UnprocessableEntityError,
    WebhookVerificationError,
)
from ._version import __version__
from .resources.documents import MAX_BATCH_SIZE
from .webhooks import (
    compute_webhook_signature,
    construct_webhook_event,
    verify_webhook_signature,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "MAX_BATCH_SIZE",
    "APIConnectionError",
    "APIError",
    "APITimeoutError",
    "AsyncTupana",
    "AuthenticationError",
    "BadRequestError",
    "BatchTimeoutError",
    "ConflictError",
    "InternalServerError",
    "NotFoundError",
    "PayloadTooLargeError",
    "PermissionDeniedError",
    "RateLimitError",
    "Tupana",
    "TupanaError",
    "UnprocessableEntityError",
    "WebhookVerificationError",
    "__version__",
    "compute_webhook_signature",
    "construct_webhook_event",
    "random_idempotency_key",
    "types",
    "verify_webhook_signature",
]
