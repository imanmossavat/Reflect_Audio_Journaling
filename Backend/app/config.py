from app.services.settings_service import get_setting


class _Settings:
    @property
    def DEVICE(self) -> str:
        return get_setting("device")

    @property
    def WHISPER_MODEL(self) -> str:
        return get_setting("whisper_model")

    @property
    def LANGUAGE(self) -> str:
        return get_setting("language")

    @property
    def COMPUTE_TYPE(self) -> str:
        # CTranslate2 (faster-whisper) supports int8 on CPU, float16 on CUDA.
        # MPS uses openai-whisper (PyTorch) instead of CTranslate2; float16 there too.
        return "float16" if self.DEVICE in {"cuda", "mps"} else "int8"

    SAMPLE_RATE = 16000


settings = _Settings()
