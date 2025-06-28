from pydantic import BaseSettings, AnyHttpUrl, Field

class Settings(BaseSettings):
    # Node & chain
    rpc_url: AnyHttpUrl = Field(..., env="RPC_URL")
    rpc_timeout: float = Field(5.0, env="RPC_TIMEOUT")
    # Caching
    heartbeat_ttl: int = Field(120, env="HEARTBEAT_TTL")
    # Fee‐distribution
    fee_collector: str = Field("ORB.3C0738F00DE16991DDD5B506", env="FEE_COLLECTOR")
    milestone_interval: int = Field(1000, env="MILESTONE_INTERVAL")
    # Server
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(7000, env="PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()