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


class AcuityAppointment:
    appointment_type_table = 'AppointmentTypes'

    def __init__(self, appointment_id, logger, type_id=None, calendar_id=None, correlation_id=None):
        self.logger = logger
        self.correlation_id = correlation_id
        self.acuity_client = AcuityClient(correlation_id=self.correlation_id)
        self.ddb_client = Dynamodb()
        self.core_api_client = CoreApiClient(correlation_id=self.correlation_id)
        self.appointment_id = str(appointment_id)
        self.type_id = None
        if type_id:
            self.type_id = str(type_id)
        self.calendar_id = calendar_id
        self.calendar_name = None
        self.details = None
        self.type_name = None
        self.type_status = None
        self.has_link = None
        self.link = None
        self.participant_user_id = None

    def __repr__(self):
        return str(self.__dict__)

    def get_participant_user_id(self):
        if self.details is None:
            self.get_appointment_details()
        if self.participant_user_id is None:
            self.participant_user_id = self.core_api_client.get_user_id_by_email(
                email=self.details['email']
            )
        return self.participant_user_id

    def store_in_dynamodb(self, update_allowed=False):
        self.get_appointment_name()
        self.get_appointment_details()
        self.get_participant_user_id()
        return self.ddb_client.put_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            item_type='acuity-appointment',
            item_details=self.details,
            item={
                'type_id': self.type_id,
                'type_name': self.type_name,
                'participant_user_id': self.participant_user_id,
                'calendar_id': self.calendar_id,
                'calendar_name': self.calendar_name,
                'link': self.link,
            },
            update_allowed=update_allowed
        )

    def update_link(self, link):
        self.link = link
        result = self.ddb_client.update_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            name_value_pairs={
                'link': self.link
            }
        )
        assert result['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
            f'Call to ddb client update_item method failed with response {result}'
        return result

    def get_appointment_type_id_to_name_map(self):
        appointment_types = self.acuity_client.get_appointment_types()
        return {str(x['id']): x['name'] for x in appointment_types}

    def get_appointment_name(self):
        if self.type_name is None:
            id_to_name = self.get_appointment_type_id_to_name_map()
            self.type_name = id_to_name[self.type_id]
        return self.type_name

    def get_appointment_details(self):
        if self.details is None:
            self.details = self.acuity_client.get_appointment_by_id(self.appointment_id)
            self.details['appointmentTypeID'] = str(self.details['appointmentTypeID'])
            self.calendar_name = self.details['calendar']
        return self.details['email'], self.details['appointmentTypeID']

    def get_appointment_item_from_ddb(self):
        return self.ddb_client.get_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id
        )

    def get_appointment_type_info_from_ddb(self):
        item = self.ddb_client.get_item(self.appointment_type_table, self.type_id, correlation_id=self.correlation_id)
        self.type_status = item['status']
        self.has_link = item['user_specific_interview_link']
        return item['project_task_id'], self.type_status


class AppointmentNotifier:
    calendar_table = 'Calendars'

    def __init__(self, appointment, logger, ddb_client=None, correlation_id=None):
        """
        Args:
            appointment: instance of AcuityAppointment
            logger:
            correlation_id:
        """
        self.appointment = appointment
        try:
            self.participant_email = self.appointment.details['email'].lower()
        except TypeError:
            self.appointment.get_appointment_details()
            self.participant_email = self.appointment.details['email'].lower()
        self.logger = logger,
        self.correlation_id = correlation_id
        self.ddb_client = ddb_client
        if self.ddb_client is None:
            self.ddb_client = Dynamodb()

    def _get_email_template(self, recipient_type, event_type):
        email_domain = 'other'
        if (recipient_type == 'participant') and ('@nhs' in self.participant_email):
            email_domain = 'nhs'
        template_dict = {
            'participant': {
                'booking': {
                    'nhs': "interview_booked_nhs_participant",
                    'other': "interview_booked_participant",
                },
                'rescheduling': {
                    'nhs': "interview_rescheduled_nhs_participant",
                    'other': "interview_rescheduled_participant",
                },
                'cancellation': {
                    'nhs': "interview_cancelled_nhs_participant",
                    'other': "interview_cancelled_participant",
                },
            },
            'researcher': {
                'booking': {
                    'other': "interview_booked_researcher",
                },
                'rescheduling': {
                    'other': "interview_rescheduled_researcher",
                },
                'cancellation': {
                    'other': "interview_cancelled_researcher",
                },
            },
        }
        return template_dict[recipient_type][event_type][email_domain]

    def _get_researcher_email_address(self):
        if self.appointment.calendar_name is None:
            self.appointment.get_appointment_details()
        return self.ddb_client.get_item(
            table_name=self.calendar_table,
            key=self.appointment.calendar_name
        )['emails_to_notify']

    def _check_appointment_cancelled(self):
        """
        Gets latest appointment info from Acuity to ensure appointment is still valid before sending out notification

        Returns:
            True is appointment is cancelled; False if it is not cancelled
        """
        self.appointment.get_appointment_details()
        return self.appointment.details['canceled'] is True

    def _notify_participant(self, event_type, extra_custom_properties=dict()):
        if not event_type == 'cancellation':
            if self._check_appointment_cancelled():
                self.logger.info('Notification aborted; appointment has been cancelled', extra={
                    'appointment': self.appointment,
                    'correlation_id': self.correlation_id
                })
                return None

        result = self.appointment.core_api_client.send_transactional_email(
            template_name=self._get_email_template(
                recipient_type='participant',
                event_type=event_type,
            ),
            to_recipient_id=self.appointment.participant_user_id,
            custom_properties={
                'interview_url': self.appointment.link,
                **extra_custom_properties,
            }
        )
        if result['statusCode'] != HTTPStatus.NO_CONTENT:
            self.logger.error(f'Failed to notify {self.participant_email} of new interview appointment', extra={
                'appointment': self.appointment,
                'correlation_id': self.correlation_id
            })
        return result

    def _notify_researcher(self, event_type, extra_custom_properties=dict()):
        if not event_type == 'cancellation':
            if self._check_appointment_cancelled():
                self.logger.info('Notification aborted; appointment has been cancelled', extra={
                    'appointment': self.appointment,
                    'correlation_id': self.correlation_id
                })
                return None

        for researcher_email in self._get_researcher_email_address():
            result = self.appointment.core_api_client.send_transactional_email(
                template_name=self._get_email_template(
                    recipient_type='researcher',
                    event_type=event_type,
                ),
                to_recipient_email=researcher_email,
                custom_properties={
                    'interview_url': self.appointment.link,
                    **extra_custom_properties,
                }
            )
            if result['statusCode'] != HTTPStatus.NO_CONTENT:
                self.logger.error(f'Failed to notify {researcher_email} of new interview appointment', extra={'appointment': self.appointment})

    def send_participant_booking_info(self):
        return self._notify_participant('booking')

    def send_participant_rescheduling_info(self):
        return self._notify_participant('rescheduling')

    def send_participant_cancellation_info(self):
        return self._notify_participant('cancellation')

    def send_researcher_booking_info(self):
        self._notify_researcher('booking')

    def send_researcher_rescheduling_info(self):
        self._notify_researcher('rescheduling')

    def send_researcher_cancellation_info(self):
        self._notify_researcher('cancellation')


class AcuityEvent:

    def __init__(self, acuity_event, logger, correlation_id=None):
        self.logger = logger
        self.correlation_id = correlation_id
        event_pattern = re.compile(
            r"action=appointment\.(?P<action>scheduled|rescheduled|canceled|changed)"
            r"&id=(?P<appointment_id>\d+)"
            r"&calendarID=(?P<calendar_id>\d+)"
            r"&appointmentTypeID=(?P<type_id>\d+)"
        )
        m = event_pattern.match(acuity_event)
        try:
            self.action = m.group('action')
            self.appointment_id = m.group('appointment_id')
            self.type_id = m.group('type_id')
            self.calendar_id = m.group('calendar_id')
        except AttributeError as err:
            self.logger.error('event_pattern does not match acuity_event', extra={'acuity_event': acuity_event})
            raise
        self.appointment = AcuityAppointment(
            appointment_id=self.appointment_id,
            logger=self.logger,
            correlation_id=self.correlation_id,
            type_id=self.type_id,
            calendar_id=self.calendar_id,
        )
        self.appointment.get_appointment_type_info_from_ddb()

    def __repr__(self):
        return str(self.__dict__)

    def notify_thiscovery_team(self):
        if self.appointment.details is None:
            self.appointment.get_appointment_details()
        appointment_type_name = self.appointment.get_appointment_name()
        emails_client = EmailsApiClient(self.correlation_id)
        appointment_management_secret = utils.get_secret('interviews')['appointment-management']
        appointment_manager = appointment_management_secret['manager']
        if utils.running_unit_tests():
            appointment_manager = appointment_management_secret['tester']
        notification_email_source = appointment_management_secret['notification-email-source']
        appointment_date = f"{parser.parse(self.appointment.details['datetime']).strftime('%d/%m/%Y %H:%M')}" \
                           f"-{self.appointment.details['endTime']}"
        interviewee_name = f"{self.appointment.details['firstName']} {self.appointment.details['lastName']}"
        interviewee_email = self.appointment.details['email']
        interviewer_calendar_name = self.appointment.details['calendar']
        confirmation_page = self.appointment.details['confirmationPage']
        email_dict = {
            "source": notification_email_source,
            "to": appointment_manager,
            "subject": f"[thiscovery-interviews] Appointment {self.appointment_id} {self.action}",
            "body_text": f"The following interview appointment has just been {self.action}:\n"
                         f"Type: {appointment_type_name}\n"
                         f"Date: {appointment_date}\n"
                         f"Interviewee name: {interviewee_name}\n"
                         f"Interviewee email: {interviewee_email}\n"
                         f"Interviewer: {interviewer_calendar_name}\n"
                         f"Cancel/reschedule: {confirmation_page}\n",
            "body_html": f"<p>The following interview appointment has just been {self.action}:</p>"
                         f"<ul>"
                         f"<li>Type: {appointment_type_name}</li>"
                         f"<li>Date: {appointment_date}</li>"
                         f"<li>Interviewee name: {interviewee_name}</li>"
                         f"<li>Interviewee email: {interviewee_email}</li>"
                         f"<li>Interviewer: {interviewer_calendar_name}</li>"
                         f"<li>Cancel/reschedule: {confirmation_page}</li>"
                         f"</ul>",
        }
        return emails_client.send_email(email_dict=email_dict)

    def complete_thiscovery_user_task(self):
        """
        This is a legacy method that should be no longer used. Leaving the code here for now but raising an error if it is called.
        """
        raise utils.DetailedValueError('complete_thiscovery_user_task should no longer be used', details={})

        self.logger.info('Parsed Acuity event', extra={
            'action': self.action,
            'appointment_id': self.appointment_id,
            'type_id': self.type_id
        })
        email, appointment_type_id = self.appointment.get_appointment_details()
        assert str(appointment_type_id) == self.type_id, f'Unexpected appointment type id ({appointment_type_id}) in get_appointment_by_id response. ' \
                                                         f'Expected: {self.type_id}.'
        try:
            self.appointment.participant_user_id = self.core_api_client.get_user_id_by_email(email)
        except Exception as err:
            self.logger.error(f'Failed to retrieve user_id for {email}', extra={
                'exception': repr(err)
            })
            raise err

        try:
            project_task_id, appointment_type_status = self.appointment.get_appointment_type_info_from_ddb()
        except Exception as err:
            self.logger.error(f'Failed to retrieve project_task_id for appointment_type_id {self.type_id}', extra={
                'exception': repr(err)
            })
            raise err

        if appointment_type_status in ['active']:
            user_task_id = self.core_api_client.get_user_task_id_for_project(self.appointment.participant_user_id, project_task_id)
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
                'type_status': appointment_type_status
            })
            return {
                "statusCode": HTTPStatus.NO_CONTENT
            }

    def _process_booking(self):
        storing_result = self.appointment.store_in_dynamodb()
        if self.appointment.has_link:
            email_notification_result = self.notify_thiscovery_team()
            assert email_notification_result == HTTPStatus.OK, 'Failed to email Thiscovery team'
        return storing_result

    def _process_cancellation(self):
        storing_result = self.appointment.store_in_dynamodb(update_allowed=True)
        if self.appointment.has_link:
            notifier = AppointmentNotifier(
                appointment=self.appointment,
                logger=self.logger,
                correlation_id=self.correlation_id,
            )
            notifier.send_participant_cancellation_info()
            notifier.send_researcher_cancellation_info()
        return storing_result

    def _process_resheduling(self):
        original_booking_info = self.appointment.get_appointment_item_from_ddb()
        storing_result = self.appointment.store_in_dynamodb(update_allowed=True)
        if self.appointment.has_link:
            if original_booking_info['calendar_id'] == self.calendar_id:
                notifier = AppointmentNotifier(
                    appointment=self.appointment,
                    logger=self.logger,
                    correlation_id=self.correlation_id,
                )
                notifier.send_participant_rescheduling_info()
                notifier.send_researcher_rescheduling_info()
            else:
                email_notification_result = self.notify_thiscovery_team()
                assert email_notification_result == HTTPStatus.OK, 'Failed to email Thiscovery team'
        return storing_result

    def process(self):
        if self.action == 'scheduled':
            result = self._process_booking()
        elif self.action == 'canceled':
            result = self._process_cancellation()
        elif self.action == 'rescheduled':
            result = self._process_resheduling()
        else:
            raise NotImplementedError(f'Processing of a {self.action} appointment has not been implemented')

        return result


def set_interview_url(appointment_id, interview_url, event_type, logger=None, correlation_id=None):
    """

    Args:
        appointment_id:
        interview_url:
        event_type (str): passed on to AppointmentNotifier ('booking', 'rescheduling' or 'cancellation')
        logger:
        correlation_id:

    Returns:

    """
    if logger is None:
        logger = utils.get_logger()
    appointment = AcuityAppointment(
        appointment_id=appointment_id,
        correlation_id=correlation_id,
    )
    appointment.update_link(
        link=interview_url
    )
    notifier = AppointmentNotifier(
        appointment=appointment,
        logger=logger,
        correlation_id=correlation_id,
    )
    if event_type == 'booking':
        notifier.send_participant_booking_info()
        notifier.send_researcher_booking_info()
    elif event_type == 'rescheduling':
        notifier.send_participant_rescheduling_info()
        notifier.send_researcher_rescheduling_info()
    else:
        raise NotImplementedError(f'Processing of {event_type} events not implemented')


def send_reminder():
    ddb_client = Dynamodb()
    ddb_client.scan(
        table_name=APPOINTMENTS_TABLE,
        filter_attr_name='reminder',
        filter_attr_values=[None]
    )



@utils.lambda_wrapper
def interview_reminder_handler(event, context):
    pass


@utils.lambda_wrapper
@utils.api_error_handler
def interview_appointment_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    acuity_event = event['body']
    appointment_event = AcuityEvent(acuity_event, logger, correlation_id=correlation_id)
    return appointment_event.process()


@utils.lambda_wrapper
@utils.api_error_handler
def set_interview_url_api(event, context):
    logger = event['logger']
    correlation_id = event['correlation_id']
    body = event['body']
    logger.debug('API call', extra={
        'body': body,
        'correlation_id': correlation_id
    })
    set_interview_url(
        appointment_id=body['appointment_id'],
        interview_url=body['interview_url'],
        event_type=body['event_type'],
        logger=logger,
        correlation_id=correlation_id,
    )
    return {"statusCode": HTTPStatus.OK}
