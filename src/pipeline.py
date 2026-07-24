"""
Audio Customer Support Agent Pipeline

This module orchestrates the complete STT -> LLM -> TTS pipeline.

Supports two memory-saving modes, controlled via PipelineConfig:
- lazy_load: STT/TTS initialize on first actual use instead of at startup.
- text_only_mode: skips TTS synthesis entirely for text queries (process_text).

Both default to False (original eager-loading behavior) so local development
is unaffected. Set them via environment variables when deploying to
memory-constrained hosting (e.g. Render free tier).
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
import time
from dataclasses import dataclass

from src.stt.base_stt import BaseSTT, STTService
from src.llm.agent import BaseAgent, CustomerSupportAgent
from src.tts.base_tts import BaseTTS, TTSService


@dataclass
class TranscriptData:
    user_input: str
    agent_response: str


@dataclass
class PipelineConfig:
    """Configuration for the audio support pipeline."""
    stt_config: Dict[str, Any]
    llm_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    enable_logging: bool = True
    lazy_load: bool = False       # if True, STT/TTS init on first use, not at startup
    text_only_mode: bool = False  # if True, process_text skips TTS synthesis entirely


class AudioSupportPipeline:
    """
    Main pipeline class that orchestrates STT -> LLM -> TTS flow.
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize the audio support pipeline.

        Args:
            config: Pipeline configuration containing settings for all components
        """
        self.config = config
        self.stt: Optional[BaseSTT] = None
        self.llm_agent: Optional[BaseAgent] = None
        self.tts: Optional[BaseTTS] = None
        self.is_initialized = False

        if config.enable_logging:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.CRITICAL)

    async def initialize(self) -> None:
        """
        Initialize pipeline components. LLM agent always initializes eagerly
        (required for any query). STT/TTS initialize eagerly UNLESS
        config.lazy_load is True, in which case they initialize on first use.
        """
        try:
            self.logger.info("Initializing Audio Support Pipeline...")

            self.logger.info("Initializing LLM agent...")
            self.llm_agent = CustomerSupportAgent(self.config.llm_config)
            await self.llm_agent.initialize()

            if not self.config.lazy_load:
                self.logger.info("Initializing STT service...")
                self.stt = STTService(self.config.stt_config)
                await self.stt.initialize()

                self.logger.info("Initializing TTS service...")
                self.tts = TTSService(self.config.tts_config)
                await self.tts.initialize()
            else:
                self.logger.info(
                    "Lazy-load mode enabled: STT/TTS will initialize on first actual use."
                )

            if not self.llm_agent.is_initialized:
                raise RuntimeError("LLM agent failed to initialize")

            self.is_initialized = True
            self.logger.info("Pipeline initialized successfully!")

        except Exception as e:
            self.logger.error(f"Pipeline initialization failed: {str(e)}")
            await self.cleanup()
            raise

    async def _ensure_stt(self) -> None:
        """Lazily initialize STT on first use, if not already loaded."""
        if self.stt is None:
            self.logger.info("Lazy-loading STT service on first use...")
            self.stt = STTService(self.config.stt_config)
            await self.stt.initialize()

    async def _ensure_tts(self) -> None:
        """Lazily initialize TTS on first use, if not already loaded."""
        if self.tts is None:
            self.logger.info("Lazy-loading TTS service on first use...")
            self.tts = TTSService(self.config.tts_config)
            await self.tts.initialize()

    async def process_audio(self, audio_bytes: bytes, **kwargs) -> bytes:
        """
        Process audio input through the complete pipeline (STT -> LLM -> TTS).
        """
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        try:
            await self._ensure_stt()
            self.logger.info("Converting speech to text...")
            text_input = await self.stt.transcribe(audio_bytes, **kwargs)
            self.logger.info(f"Transcribed text: {text_input}")

            self.logger.info("Processing query with LLM agent...")
            agent_response = await self.llm_agent.process_query(text_input, **kwargs)
            self.logger.info(f"Agent response: {agent_response}")

            await self._ensure_tts()
            self.logger.info("Converting response to speech...")
            response_audio = await self.tts.synthesize(agent_response, **kwargs)
            self.logger.info("Audio response generated successfully")

            return response_audio

        except Exception as e:
            self.logger.error(f"Pipeline processing failed: {str(e)}")
            raise

    async def process_text(self, text_input: str, **kwargs) -> Tuple[str, bytes]:
        """
        Process text input (useful for testing without STT, and for
        text-only deployments where TTS is skipped to save memory).

        Args:
            text_input: Text query from user
            **kwargs: Additional parameters

        Returns:
            Tuple[str, bytes]: (agent_response_text, response_audio)
                response_audio will be b"" if text_only_mode is enabled.
        """
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        try:
            self.logger.info(f"Processing text query: {text_input}")
            agent_response = await self.llm_agent.process_query(text_input, **kwargs)

            if self.config.text_only_mode:
                self.logger.info("text_only_mode enabled: skipping TTS synthesis.")
                return agent_response, b""

            await self._ensure_tts()
            response_audio = await self.tts.synthesize(agent_response, **kwargs)

            return agent_response, response_audio

        except Exception as e:
            self.logger.error(f"Text processing failed: {str(e)}")
            raise

    async def process_audio_with_transcript(self, audio_bytes: bytes, **kwargs) -> Tuple[bytes, Dict[str, str], int]:
        if not self.is_initialized:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")

        start_time = time.time()

        await self._ensure_stt()
        text_input = await self.stt.transcribe(audio_bytes, **kwargs)
        agent_response = await self.llm_agent.process_query(text_input, **kwargs)

        await self._ensure_tts()
        response_audio = await self.tts.synthesize(agent_response, **kwargs)

        processing_time_ms = int((time.time() - start_time) * 1000)

        transcript = {
            "user_input": text_input,
            "agent_response": agent_response
        }

        return response_audio, transcript, processing_time_ms

    async def health_check(self) -> Dict[str, bool]:
        """
        Check the health status of all pipeline components.
        Note: stt_ready/tts_ready reflect lazy-load state - False simply
        means "not yet loaded," not "broken," when lazy_load is enabled.
        """
        return {
            "pipeline_initialized": self.is_initialized,
            "stt_ready": self.stt.is_ready() if self.stt else False,
            "llm_ready": self.llm_agent.is_initialized if self.llm_agent else False,
            "tts_ready": self.tts.is_ready() if self.tts else False,
        }

    async def cleanup(self) -> None:
        """Cleanup all pipeline resources."""
        self.logger.info("Cleaning up pipeline resources...")

        try:
            if self.stt:
                await self.stt.cleanup()
            if self.llm_agent:
                await self.llm_agent.cleanup()
            if self.tts:
                await self.tts.cleanup()

            self.stt = None
            self.llm_agent = None
            self.tts = None
            self.is_initialized = False

            self.logger.info("Pipeline cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise


async def create_pipeline(
    stt_config: Dict[str, Any],
    llm_config: Dict[str, Any],
    tts_config: Dict[str, Any],
    enable_logging: bool = True,
    lazy_load: bool = False,
    text_only_mode: bool = False,
) -> AudioSupportPipeline:
    """
    Factory function to create and initialize a pipeline.

    Args:
        stt_config: STT configuration
        llm_config: LLM configuration
        tts_config: TTS configuration
        enable_logging: Whether to enable logging
        lazy_load: If True, STT/TTS initialize on first use, not at startup
        text_only_mode: If True, process_text skips TTS synthesis entirely

    Returns:
        AudioSupportPipeline: Initialized pipeline instance
    """
    config = PipelineConfig(
        stt_config=stt_config,
        llm_config=llm_config,
        tts_config=tts_config,
        enable_logging=enable_logging,
        lazy_load=lazy_load,
        text_only_mode=text_only_mode,
    )

    pipeline = AudioSupportPipeline(config)
    await pipeline.initialize()

    return pipeline


if __name__ == "__main__":
    """
    Example usage of the pipeline.
    """
    async def main():
        stt_config = {"provider": "whisper", "model": "tiny"}
        llm_config = {"model": "gpt-3.5-turbo", "temperature": 0.2}
        tts_config = {"provider": "edge", "voice": "en-US-AriaNeural"}

        pipeline = await create_pipeline(stt_config, llm_config, tts_config)
        response_text, _ = await pipeline.process_text("What is your return policy?")
        print(f"Response: {response_text}")
        await pipeline.cleanup()

    asyncio.run(main())