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
import re
from http import HTTPStatus

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.core_api_utilities import CoreApiClient
from common.dynamodb_utilities import Dynamodb
from common.emails_api_utilities import EmailsApiClient
from dateutil import parser


APPOINTMENTS_TABLE = 'Appointments'


class AcuityAppointmentEvent:
    appointment_type_table = 'AppointmentTypes'

    def __init__(self, acuity_event, logger, correlation_id=None):
        self.logger = logger
        self.correlation_id = correlation_id
        self.acuity_client = AcuityClient(correlation_id=self.correlation_id)
        self.ddb_client = Dynamodb()
        self.core_api_client = CoreApiClient(correlation_id=self.correlation_id)

        event_pattern = re.compile(
            r"action=appointment\.(?P<action>scheduled|rescheduled|canceled|changed)"
            r"&id=(?P<appointment_id>\d+)"
            r"&calendarID=\d+"
            r"&appointmentTypeID=(?P<type_id>\d+)"
        )
        m = event_pattern.match(acuity_event)
        try:
            self.action = m.group('action')
            self.appointment_id = m.group('appointment_id')
            self.type_id = m.group('type_id')
        except AttributeError as err:
            self.logger.error('event_pattern does not match acuity_event', extra={'acuity_event': acuity_event})
            raise

        self.appointment_details = None
        self.appointment_type_name = None
        self.appointment_type_status = None
        self.appointment_type_user_specific_link = None
        self.participant_user_id = None

    def store_in_dynamodb(self):
        self.get_appointment_name()
        self.get_appointment_details()
        return self.ddb_client.put_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            item_type='acuity-appointment',
            item_details=self.appointment_details,
            item={
                'appointment_type_name': self.appointment_type_name,
                'participant_user_id': self.participant_user_id,
            },
            update_allowed=True
        )

    def get_appointment_type_id_to_name_map(self):
        appointment_types = self.acuity_client.get_appointment_types()
        return {x['id']: x['name'] for x in appointment_types}

    def get_appointment_name(self):
        if self.appointment_type_name is None:
            id_to_name = self.get_appointment_type_id_to_name_map()
            self.appointment_type_name = id_to_name[self.type_id]
        return self.appointment_type_name

    def get_appointment_details(self):
        if self.appointment_details is None:
            self.appointment_details = self.acuity_client.get_appointment_by_id(self.appointment_id)
        return self.appointment_details['email'], self.appointment_details['appointmentTypeID']

    def get_appointment_type_info_from_ddb(self):
        item = self.ddb_client.get_item(self.appointment_type_table, self.type_id, correlation_id=self.correlation_id)
        self.appointment_type_status = item['status']
        self.appointment_type_user_specific_link = item['user_specific_interview_link']
        return item['project_task_id'], self.appointment_type_status

    def notify_thiscovery_team(self):
        appointment_type_name = self.get_appointment_name()
        emails_client = EmailsApiClient(self.correlation_id)
        secrets_client = utils.SecretsManager()
        appointment_management_secret = secrets_client.get_secret_value('interviews')['appointment-management']
        appointment_manager = appointment_management_secret['manager']
        notification_email_source = appointment_management_secret['notification-email-source']
        appointment_date = f"{parser.parse(self.appointment_details['datetime']).strftime('%d/%m/%Y %H:%M')}-{self.appointment_details['endTime']}"
        interviewee_name = f"{self.appointment_details['firstName']} {self.appointment_details['lastName']}"
        interviewee_email = self.appointment_details['email']
        interviewer_calendar_name = self.appointment_details['calendar']
        confirmation_page = self.appointment_details['confirmationPage']
        email_dict = {
            "source": notification_email_source,
            "to": appointment_manager,
            "subject": f"[thiscovery-interviews] Appointment {self.appointment_id} {self.action}",
            "body_text": f"The following interview appointment has just been {self.action}:\n"
                         f"Type: {appointment_type_name}\n"
                         f"Date: {appointment_date}\n"
                         f"Interviewee name:{interviewee_name}\n"
                         f"Interviewee email: {interviewee_email}\n"
                         f"Interviewer:{interviewer_calendar_name}\n"
                         f"Cancel/reschedule: {confirmation_page}\n",
            "body_html": f"<p>The following interview appointment has just been {self.action}:</p>"
                         f"<ul>"
                         f"<li>Type: {appointment_type_name}</li>"
                         f"<li>Date: {appointment_date}</li>"
                         f"<li>Interviewee name:{interviewee_name}</li>"
                         f"<li>Interviewee email: {interviewee_email}</li>"
                         f"<li>Interviewer:{interviewer_calendar_name}</li>"
                         f"<li>Cancel/reschedule: {confirmation_page}</li>"
                         f"</ul>",
        }
        return emails_client.send_email(email_dict=email_dict)

    def complete_thiscovery_user_task(self):
        self.logger.info('Parsed Acuity event', extra={
            'action': self.action,
            'appointment_id': self.appointment_id,
            'type_id': self.type_id
        })
        email, appointment_type_id = self.get_appointment_details()
        assert str(appointment_type_id) == self.type_id, f'Unexpected appointment type id ({appointment_type_id}) in get_appointment_by_id response. ' \
                                                         f'Expected: {self.type_id}.'
        try:
            self.participant_user_id = self.core_api_client.get_user_id_by_email(email)
        except Exception as err:
            self.logger.error(f'Failed to retrieve user_id for {email}', extra={
                'exception': repr(err)
            })
            raise err

        try:
            project_task_id, appointment_type_status = self.get_appointment_type_info_from_ddb()
        except Exception as err:
            self.logger.error(f'Failed to retrieve project_task_id for appointment_type_id {self.type_id}', extra={
                'exception': repr(err)
            })
            raise err

        if appointment_type_status in ['active']:
            user_task_id = self.core_api_client.get_user_task_id_for_project(self.participant_user_id, project_task_id)
            self.logger.debug('user_task_id', extra={
                'user_task_id': user_task_id
            })
            result = self.core_api_client.set_user_task_completed(user_task_id)
            self.logger.info(f'Updated user task {user_task_id} status to complete')
            return result
        else:
            self.logger.info('Ignored appointment', extra={
                'appointment_id': self.appointment_id,
                'appointment_type_id': self.type_id,
                'appointment_type_status': appointment_type_status
            })
            return {
                "statusCode": HTTPStatus.NO_CONTENT
            }

    def process_event(self):
        task_completion_result = self.complete_thiscovery_user_task()
        storing_result = self.store_in_dynamodb()
        if (self.action in ['scheduled', 'rescheduled']) and (self.appointment_type_user_specific_link is True):
            email_notification_result = self.notify_thiscovery_team()
        return task_completion_result


class InterviewUrlHandler(AcuityAppointmentEvent):
    participant_email_template_name = "interview_appointment_participant"
    researcher_email_template_name = "interview_appointment_researcher"

    def __init__(self, appointment_id, correlation_id=None):
        self.appointment_id = appointment_id
        self.correlation_id = correlation_id
        self.ddb_client = Dynamodb()
        self.core_api_client = CoreApiClient(correlation_id=self.correlation_id)
        self.participant_user_id = None
        self.interview_url = None

    def get_appointment_from_ddb(self):
        return self.ddb_client.get_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id
        )

    def get_participant_user_id(self):
        self.participant_user_id = self.get_appointment_from_ddb()['participant_user_id']
        return self.participant_user_id

    def set_interview_url(self, interview_url):
        self.interview_url = interview_url
        result = self.ddb_client.update_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            name_value_pairs={
                'interview_url': interview_url
            }
        )
        assert result['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
            f'Call to ddb client update_item method failed with response {result}'
        return result

    def email_participant(self):
        result = self.core_api_client.send_transactional_email(
            template_name=self.participant_email_template_name,
            to_recipient_id=self.get_participant_user_id(),
            custom_properties={
                'interview_url': self.interview_url,
            }
        )
        return result

    def email_researcher(self):
        self.core_api_client.send_transactional_email(
            template_name=self.researcher_email_template_name,
            to_recipient_id=NotImplementedError,
            custom_properties={
                'interview_url': self.interview_url,
            }
        )

    def main(self, interview_url):
        raise NotImplementedError


@utils.lambda_wrapper
@utils.api_error_handler
def interview_appointment_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    acuity_event = event['body']
    appointment_event = AcuityAppointmentEvent(acuity_event, logger, correlation_id=correlation_id)
    return appointment_event.process_event()


@utils.lambda_wrapper
@utils.api_error_handler
def set_interview_url_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    body = event['body']
    url_handler = InterviewUrlHandler(
        appointment_id=body['appointment_id'],
        correlation_id=correlation_id
    )
    logger.debug('API call', extra={'body': body, 'correlation_id': correlation_id})
    url_handler.set_interview_url(
        interview_url=body['interview_url']
    )
    return {"statusCode": HTTPStatus.OK}
