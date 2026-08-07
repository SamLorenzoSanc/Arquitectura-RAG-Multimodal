from pydantic import BaseModel


class SpeechWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class SpeechSegment(BaseModel):
    start: float
    end: float
    text: str
    words: list[SpeechWord]


class SpeechResponse(BaseModel):
    text: str
    language: str
    duration: float
    segments: list[SpeechSegment]
