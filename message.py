from dataclasses import dataclass
import datetime

@dataclass
class Message:
    sender: str
    receiver: str
    content: object
    timestamp: datetime