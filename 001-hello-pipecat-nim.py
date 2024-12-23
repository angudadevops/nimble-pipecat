#
# Copyright (c) 2024, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os
import sys

import aiohttp
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.nim import NimLLMService
from pipecat.services.openai import OpenAILLMService
from pipecat.services.riva import FastPitchTTSService, ParakeetSTTService
from pipecat.transports.services.daily import DailyParams, DailyTransport

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

async def main():
    print(f"___________________________________*")
    print(f"___________________________________*")
    print(f"___________________________________* Navigate to")
    print(f"___________________________________* https://pc-34b1bdc94a7741719b57b2efb82d658e.daily.co/prod-test")
    print(f"___________________________________* to talk to NVIDIA NIM bot.")
    print(f"___________________________________*")
    print(f"___________________________________*")

    # Url to talk to the NVIDIA NIM bot
    room_url = "https://pc-34b1bdc94a7741719b57b2efb82d658e.daily.co/prod-test"
    
    transport = DailyTransport(
        room_url,
        None,
        "NVIDIA NIM",
        DailyParams(
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
        ),
    )

    stt = ParakeetSTTService(api_key=os.getenv("NVIDIA_API_KEY"))

    llm = NimLLMService(
        api_key=os.getenv("NVIDIA_API_KEY")
    )

    tts = FastPitchTTSService(api_key=os.getenv("NVIDIA_API_KEY"))

    messages = [
        {
            "role": "system",
            "content": "You are a helpful LLM in a WebRTC call. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way.",
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            stt,  # STT
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Please introduce yourself to the user."})
        await task.queue_frames([LLMMessagesFrame(messages)])

    runner = PipelineRunner()

    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
