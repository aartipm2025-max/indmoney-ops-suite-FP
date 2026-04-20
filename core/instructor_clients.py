from functools import lru_cache

import groq
import instructor


@lru_cache(maxsize=1)
def get_instructor_primary() -> instructor.Instructor:
    from config import settings

    client = groq.Groq(api_key=settings.groq_api_key)
    return instructor.from_groq(client, mode=instructor.Mode.TOOLS)


@lru_cache(maxsize=1)
def get_instructor_fast() -> instructor.Instructor:
    from config import settings

    client = groq.Groq(api_key=settings.groq_api_key)
    return instructor.from_groq(client, mode=instructor.Mode.TOOLS)
