from enum import Enum, IntEnum
from pydantic import AfterValidator, BaseModel, Field, ConfigDict
from typing import Annotated, Literal
import phonenumbers


class StudyYear(IntEnum):
    YEAR_1 = 1
    YEAR_2 = 2
    YEAR_3 = 3
    YEAR_4 = 4
    YEAR_5 = 5
    YEAR_6 = 6
    GRADUATED = 7

    def __str__(self):
        if self <= 4:
            return f"{self.value} курс"
        elif self == 5:
            return "1 магістр"
        elif self == 6:
            return "2 магістр"
        else:
            return "Закінчив"


def normalize_phone_number(number: str) -> str:
    try:
        parsed_number = phonenumbers.parse(number, None)
    except phonenumbers.NumberParseException as e:
        raise ValueError(f"Invalid phone number: {e}")

    if not phonenumbers.is_possible_number(parsed_number):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(
        parsed_number, phonenumbers.PhoneNumberFormat.E164
    )


NormalizedPhone = Annotated[str, AfterValidator(normalize_phone_number)]


class ParticipationFormat(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class Form(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Annotated[str, Field(description="The full name of the user")]

    email: Annotated[str, Field(description="The email address of the user")]

    telegram: Annotated[str, Field(description="The Telegram handle of the user")]

    phone: Annotated[NormalizedPhone, Field(description="The phone number of the user")]

    university_id: Annotated[int, Field(description="The ID of the user's university")]

    category_id: Annotated[
        int, Field(description="The category of interest for the user")
    ]

    study_year: Annotated[
        StudyYear, Field(description="The current year of study of the user")
    ]

    skills: Annotated[
        list[str], Field(description="List of skills the user has")
    ]

    format: Annotated[
        ParticipationFormat,
        Field(description="The preferred format of participation for the user"),
    ]

    has_team: Annotated[bool, Field(description="Whether the user has a team or not")]

    team_leader: Annotated[
        bool, Field(description="Whether the user is the team lead or not")
    ]

    team_name: Annotated[str, Field(description="The name of the user's team")]

    wants_job: Annotated[
        bool, Field(description="Whether the user is looking for a job or not")
    ]

    job_description: Annotated[
        str, Field(description="Description of the job the user is looking for")
    ]

    cv: Annotated[str, Field(description="URL to the user's CV file")]
    linkedin: Annotated[str, Field(description="URL to the user's LinkedIn profile")]
    work_consent: Annotated[
        bool, Field(description="Whether the user consents to work terms")
    ]

    source: Annotated[str, Field(description="How the user heard about the event")]

    otherSource: Annotated[str | None, Field(description="Other source if applicable")]

    comment: Annotated[
        str | None, Field(description="Additional comments from the user")
    ]

    personal_data_consent: Annotated[
        Literal[True], Field(description="Consent for personal data processing")
    ]
