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


APPOINTMENTS_TABLE = 'Appointments'
APPOINTMENT_TYPES_TABLE = 'AppointmentTypes'

COMMON_PROPERTIES = [
    'project_short_name',
    'user_first_name',
]

BOOKING_RESCHEDULING_PROPERTIES = [
    *COMMON_PROPERTIES,
    'appointment_date',
    'appointment_duration',
    'appointment_reschedule_url',
]

WEB_PROPERTIES = [
    *BOOKING_RESCHEDULING_PROPERTIES,
    'interview_url',
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
    },
    'researcher': {
        'booking': {
            'web': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
                },
            },
            'phone': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
                },
            },
        },
        'rescheduling': {
            'web': {
                'other': {
                    'name': "interview_rescheduled_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
                },
            },
            'phone': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
                },
            },
        },
        'cancellation': {
            'web': {
                'other': {
                    'name': "interview_cancelled_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
                },
            },
            'phone': {
                'other': {
                    'name': "interview_booked_researcher",
                    'custom_properties': [
                        'interview_url',
                    ]
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
    pprint(TEST_TEMPLATES)