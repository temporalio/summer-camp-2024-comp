from typing import Optional

from pydantic import BaseSettings
from temporalio.client import TLSConfig


class TemporalClusterSettings(BaseSettings):
    host: str
    namespace: str = "default"
    # For connection with Cloud Managed Temporal Cluster Server
    client_cert: Optional[str]
    client_private_key: Optional[str]
    tls_config: Optional[TLSConfig] = None

    class Config:
        env_prefix = "temporal_cluster_"
        case_insensitive = True
