#
#   Thiscovery API - THIS Institute’s citizen science platform
#   Copyright (C) 2019 THIS Institute
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   A copy of the GNU Affero General Public License is available in the
#   docs folder of this project.  It is also available www.gnu.org/licenses/
#
import copy


STACK_NAME = 'thiscovery-interviews'
APPOINTMENTS_TABLE = 'Appointments'
APPOINTMENT_TYPES_TABLE = 'AppointmentTypes'


ACUITY_USER_METADATA_INTAKE_FORM_ID = 1606751


COMMON_PROPERTIES = [
    'project_short_name',
    'user_first_name',
]

BOOKING_RESCHEDULING_PROPERTIES = [
    *COMMON_PROPERTIES,
    'appointment_date',
    'appointment_duration',
    'appointment_reschedule_url',
    'appointment_time',
    'interviewer_first_name',
]

WEB_PROPERTIES = [
    *BOOKING_RESCHEDULING_PROPERTIES,
    'interview_url',
]

INTERVIEWER_CANCELLATION = [
    'appointment_date',
    'appointment_duration',
    'appointment_time',
    'appointment_type_name',
    'interviewer_first_name',
    'interviewer_url',
    'user_first_name',
    'user_last_name',
    'user_email',
    'anon_project_specific_user_id',
]

INTERVIEWER_BOOKING_RESCHEDULING = [
    *INTERVIEWER_CANCELLATION,
    'project_short_name',
]


DEFAULT_TEMPLATES = {  # fallback default templates (to be overwritten if specified in Dynamodb table)
    'participant': {
        'booking': {
            'web': {
                'nhs': {
                    'name': "interview_booked_web_nhs_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_booked_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
            'phone': {
                'nhs': {
                    'name': "interview_booked_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_booked_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
        },
        'rescheduling': {
            'web': {
                'nhs': {
                    'name': "interview_rescheduled_web_nhs_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_rescheduled_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
            'phone': {
                'nhs': {
                    'name': "interview_rescheduled_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_rescheduled_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
        },
        'cancellation': {
            'web': {
                'nhs': {
                    'name': "interview_cancelled_participant",
                    'custom_properties': COMMON_PROPERTIES
                },
                'other': {
                    'name': "interview_cancelled_participant",
                    'custom_properties': COMMON_PROPERTIES
                },
            },
            'phone': {
                'nhs': {
                    'name': "interview_cancelled_participant",
                    'custom_properties': COMMON_PROPERTIES
                },
                'other': {
                    'name': "interview_cancelled_participant",
                    'custom_properties': COMMON_PROPERTIES
                },
            },
        },
        'reminder': {
            'web': {
                'nhs': {
                    'name': "interview_reminder_web_nhs_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_reminder_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
            'phone': {
                'nhs': {
                    'name': "interview_reminder_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
                'other': {
                    'name': "interview_reminder_web_participant",
                    'custom_properties': WEB_PROPERTIES
                },
            },
        },
    },
    'researcher': {
        'booking': {
            'web': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': INTERVIEWER_BOOKING_RESCHEDULING
                },
            },
            'phone': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': INTERVIEWER_BOOKING_RESCHEDULING
                },
            },
        },
        'rescheduling': {
            'web': {
                'other': {
                    'name': "interview_rescheduled_researcher",
                    'custom_properties': INTERVIEWER_BOOKING_RESCHEDULING
                },
            },
            'phone': {
                'other': {
                    'name': "interview_rescheduled_researcher",
                    'custom_properties': INTERVIEWER_BOOKING_RESCHEDULING
                },
            },
        },
        'cancellation': {
            'web': {
                'other': {
                    'name': "interview_cancelled_researcher",
                    'custom_properties': INTERVIEWER_CANCELLATION
                },
            },
            'phone': {
                'other': {
                    'name': "interview_cancelled_researcher",
                    'custom_properties': INTERVIEWER_CANCELLATION
                },
            },
        },
    },
}


def replace_item(obj, key, replace_value):
    """
    From https://stackoverflow.com/a/45335542
    """
    for k, v in obj.items():
        if isinstance(v, dict):
            obj[k] = replace_item(v, key, replace_value)
    if key in obj:
        obj[key] = replace_value
    return obj


TEST_TEMPLATES = replace_item(copy.deepcopy(DEFAULT_TEMPLATES), 'name', 'non-existent')


if __name__ == '__main__':
    from pprint import pprint
    pprint(WEB_PROPERTIES)