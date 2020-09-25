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
import json
import re
from http import HTTPStatus

import common.utilities as utils
from common.acuity_utilities import AcuityClient
from common.core_api_utilities import CoreApiClient
from common.dynamodb_utilities import Dynamodb
from common.emails_api_utilities import EmailsApiClient
from dateutil import parser


APPOINTMENTS_TABLE = 'Appointments'

DEFAULT_TEMPLATES = {  # fallback default templates (to be overwritten if specified in Dynamodb table)
    'participant': {
        'booking': {
            'nhs': {
                'name': "interview_booked_nhs_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
            'other': {
                'name': "interview_booked_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
        'rescheduling': {
            'nhs': {
                'name': "interview_rescheduled_nhs_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
            'other': {
                'name': "interview_rescheduled_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
        'cancellation': {
            'nhs': {
                'name': "interview_cancelled_nhs_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
            'other': {
                'name': "interview_cancelled_participant",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
    },
    'researcher': {
        'booking': {
            'other': {
                'name': "interview_booked_researcher",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
        'rescheduling': {
            'other': {
                'name': "interview_rescheduled_researcher",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
        'cancellation': {
            'other': {
                'name': "interview_cancelled_researcher",
                'custom_properties': [
                    'interview_url',
                ]
            },
        },
    },
}


class AppointmentType:
    """
    Represents an Acuity appointment type with additional attributes
    """
    _appointment_type_table = 'AppointmentTypes'

    def __init__(self, ddb_client=None, acuity_client=None, logger=None, correlation_id=None):
        self.type_id = None
        self.name = None
        self.status = None
        self.has_link = None
        self.send_notifications = None
        self.templates = DEFAULT_TEMPLATES
        self.modified = None  # flag used in ddb_load method to check if ddb data was already fetched

        self._logger = logger
        if logger is None:
            self._logger = utils.get_logger()
        self._ddb_client = ddb_client
        if ddb_client is None:
            self._ddb_client = Dynamodb()
        self._acuity_client = acuity_client
        if acuity_client is None:
            self._acuity_client = AcuityClient(correlation_id=self._correlation_id)
        self._correlation_id = correlation_id

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if (k[0] != "_") and (k not in ['created', 'modified'])}

    def from_dict(self, type_dict):
        self.__dict__.update(type_dict)

    def ddb_dump(self, update_allowed=False):
        return self._ddb_client.put_item(
            table_name=self._appointment_type_table,
            key=self.type_id,
            item_type='acuity-appointment-type',
            item_details=None,
            item=self.as_dict(),
            update_allowed=update_allowed
        )

    def ddb_load(self):
        if self.modified is None:
            item = self._ddb_client.get_item(self._appointment_type_table, self.type_id, correlation_id=self._correlation_id)
            self.__dict__.update(item)

    def get_appointment_type_id_to_name_map(self):
        appointment_types = self._acuity_client.get_appointment_types()
        return {str(x['id']): x['name'] for x in appointment_types}

    def get_appointment_type_name(self):
        """
        There is no direct method to get a appointment type by id (https://developers.acuityscheduling.com/reference), so
        we have to fetch all appointment types and lookup
        """
        if self.name is None:
            id_to_name = self.get_appointment_type_id_to_name_map()
            self.name = id_to_name[self.type_id]
        return self.name

class AcuityAppointment:
    """
    Represents an Acuity appointment
    """
    def __init__(self, appointment_id, logger=None, correlation_id=None):
        self.appointment_id = str(appointment_id)
        self.acuity_info = None
        self.calendar_id = None
        self.calendar_name = None
        self.link = None
        self.participant_email = None
        self.participant_user_id = None
        self.appointment_type = AppointmentType()

        self._logger = logger
        if self._logger is None:
            self._logger = utils.get_logger()
        self._correlation_id = correlation_id
        self._acuity_client = AcuityClient(correlation_id=self._correlation_id)
        self._ddb_client = Dynamodb()
        self._core_api_client = CoreApiClient(correlation_id=self._correlation_id)

    def __repr__(self):
        return str(self.__dict__)

    def as_dict(self):
        d = {k: v for k, v in self.__dict__.items() if (k[0] != "_") and (k not in ['created', 'modified', 'appointment_type'])}
        d['appointment_type'] = self.appointment_type.as_dict()
        return d

    def ddb_dump(self, update_allowed=False):
        self.get_appointment_info_from_acuity()  # populates self.appointment_type.type_id
        self.appointment_type.ddb_load()
        # self.get_participant_user_id()
        return self._ddb_client.put_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            item_type='acuity-appointment',
            item_details=None,
            item=self.as_dict(),
            update_allowed=update_allowed
        )

    def ddb_load(self):
        item = self.get_appointment_item_from_ddb()
        item_app_type = item['appointment_type']
        del item['appointment_type']
        self.__dict__.update(item)
        self.appointment_type.from_dict(item_app_type)

    def get_appointment_item_from_ddb(self):
        return self._ddb_client.get_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id
        )

    def get_participant_user_id(self):
        """
        Not currently used, but might be useful in the near future.
        """
        if self.participant_user_id is None:
            if self.participant_email is None:
                self.get_appointment_info_from_acuity()
            self.participant_user_id = self._core_api_client.get_user_id_by_email(
                email=self.participant_email
            )
        return self.participant_user_id

    def update_link(self, link):
        self.link = link
        result = self._ddb_client.update_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            name_value_pairs={
                'link': self.link
            }
        )
        assert result['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
            f'Call to ddb client update_item method failed with response {result}'
        return result

    def get_appointment_info_from_acuity(self):
        if self.acuity_info is None:
            self.acuity_info = self._acuity_client.get_appointment_by_id(self.appointment_id)
            self.appointment_type.type_id = str(self.acuity_info['appointmentTypeID'])
            self.calendar_name = self.acuity_info['calendar']
            self.calendar_id = str(self.acuity_info['calendarID'])
            self.participant_email = self.acuity_info['email']
        return self.acuity_info


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
            self.appointment.get_appointment_info_from_acuity()
            self.participant_email = self.appointment.details['email'].lower()
        self.logger = logger
        self.correlation_id = correlation_id
        self.ddb_client = ddb_client
        if self.ddb_client is None:
            self.ddb_client = Dynamodb()

    def _get_email_template(self, recipient_email, recipient_type, event_type):
        email_domain = 'other'
        if (recipient_type == 'participant') and ('@nhs' in recipient_email):
            email_domain = 'nhs'
        return self.appointment.appointment_type.templates[recipient_type][event_type][email_domain]

    def _get_researcher_email_address(self):
        if self.appointment.calendar_id is None:
            self.appointment.get_appointment_info_from_acuity()
        return self.ddb_client.get_item(
            table_name=self.calendar_table,
            key=self.appointment.calendar_id
        )['emails_to_notify']

    def _check_appointment_cancelled(self):
        """
        Gets latest appointment info from Acuity to ensure appointment is still valid before sending out notification

        Returns:
            True is appointment is cancelled; False if it is not cancelled
        """
        self.appointment.get_appointment_info_from_acuity()
        return self.appointment.details['canceled'] is True

    def _abort_notification_check(self, event_type):
        if self.appointment.get_appointment_type_info_from_ddb()
        if not event_type == 'cancellation':
            if self._check_appointment_cancelled():
                self.logger.info('Notification aborted; appointment has been cancelled', extra={
                    'appointment': self.appointment,
                    'correlation_id': self.correlation_id
                })
                return True
        return False

    def _get_custom_properties(self, properties_list):
        if properties_list:
            properties_map = {
                'interview_url': self.appointment.link,
            }
            try:
                return {k: properties_map[k] for k in properties_list}
            except KeyError:
                raise utils.DetailedValueError('Custom property name not found in properties_map', details={
                    'properties_list': properties_list,
                    'properties_map': properties_map,
                    'correlation_id': self.correlation_id,
                })

    def _notify_email(self, recipient_email, recipient_type, event_type):
        template = self._get_email_template(
            recipient_email=recipient_email,
            recipient_type=recipient_type,
            event_type=event_type,
        )
        return self.appointment._core_api_client.send_transactional_email(
            template_name=template['name'],
            to_recipient_email=recipient_email,
            custom_properties=self._get_custom_properties(template['custom_properties'])
        )

    def _notify_participant(self, event_type):
        if self._abort_notification_check(event_type=event_type) is True:
            return 'aborted'
        result = self._notify_email(
            recipient_email=self.participant_email,
            recipient_type='participant',
            event_type=event_type
        )
        if result['statusCode'] != HTTPStatus.NO_CONTENT:
            self.logger.error(f'Failed to notify {self.participant_email} of new interview appointment', extra={
                'appointment': self.appointment,
                'correlation_id': self.correlation_id
            })
        return result

    def _notify_researchers(self, event_type):
        if self._abort_notification_check(event_type=event_type) is True:
            return 'aborted'

        for researcher_email in self._get_researcher_email_address():
            result = self._notify_email(
                recipient_email=researcher_email,
                recipient_type='researcher',
                event_type=event_type
            )
            if result['statusCode'] != HTTPStatus.NO_CONTENT:
                self.logger.error(f'Failed to notify {researcher_email} of new interview appointment', extra={'appointment': self.appointment})

    def send_notifications(self, event_type):
        self._notify_participant(event_type=event_type)
        self._notify_researchers(event_type=event_type)


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
            self.event_type = m.group('action')
            appointment_id = m.group('appointment_id')
            type_id = m.group('type_id')
            # self.calendar_id = m.group('calendar_id')
        except AttributeError as err:
            self.logger.error('event_pattern does not match acuity_event', extra={'acuity_event': acuity_event})
            raise
        self.appointment = AcuityAppointment(
            appointment_id=appointment_id,
            logger=self.logger,
            correlation_id=self.correlation_id,
        )
        self.appointment.appointment_type.type_id = type_id
        self.appointment.appointment_type.ddb_load()

    def __repr__(self):
        return str(self.__dict__)

    def notify_thiscovery_team(self):
        if self.appointment.details is None:
            self.appointment.get_appointment_info_from_acuity()
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
            "subject": f"[thiscovery-interviews] Appointment {self.appointment_id} {self.event_type}",
            "body_text": f"The following interview appointment has just been {self.event_type}:\n"
                         f"Type: {appointment_type_name}\n"
                         f"Date: {appointment_date}\n"
                         f"Interviewee name: {interviewee_name}\n"
                         f"Interviewee email: {interviewee_email}\n"
                         f"Interviewer: {interviewer_calendar_name}\n"
                         f"Cancel/reschedule: {confirmation_page}\n",
            "body_html": f"<p>The following interview appointment has just been {self.event_type}:</p>"
                         f"<ul>"
                         f"<li>Type: {appointment_type_name}</li>"
                         f"<li>Date: {appointment_date}</li>"
                         f"<li>Interviewee name: {interviewee_name}</li>"
                         f"<li>Interviewee email: {interviewee_email}</li>"
                         f"<li>Interviewer: {interviewer_calendar_name}</li>"
                         f"<li>Cancel/reschedule: {confirmation_page}</li>"
                         f"</ul>",
        }
        result = emails_client.send_email(email_dict=email_dict)
        assert result == HTTPStatus.OK, 'Failed to email Thiscovery team'
        return result

    def complete_thiscovery_user_task(self):
        """
        This is a legacy method that should be no longer used. Leaving the code here for now but raising an error if it is called.
        """
        raise utils.DetailedValueError('complete_thiscovery_user_task should no longer be used', details={})

        self._logger.info('Parsed Acuity event', extra={
            'action': self.event_type,
            'appointment_id': self.appointment_id,
            'type_id': self.type_id
        })
        email, appointment_type_id = self.appointment.get_appointment_info_from_acuity()
        assert str(appointment_type_id) == self.type_id, f'Unexpected appointment type id ({appointment_type_id}) in get_appointment_by_id response. ' \
                                                         f'Expected: {self.type_id}.'
        try:
            self.appointment.participant_user_id = self._core_api_client.get_user_id_by_email(email)
        except Exception as err:
            self._logger.error(f'Failed to retrieve user_id for {email}', extra={
                'exception': repr(err)
            })
            raise err

        try:
            project_task_id, appointment_type_status = self.appointment.get_appointment_type_info_from_ddb()
        except Exception as err:
            self._logger.error(f'Failed to retrieve project_task_id for appointment_type_id {self.type_id}', extra={
                'exception': repr(err)
            })
            raise err

        if appointment_type_status in ['active']:
            user_task_id = self._core_api_client.get_user_task_id_for_project(self.appointment.participant_user_id, project_task_id)
            self._logger.debug('user_task_id', extra={
                'user_task_id': user_task_id
            })
            result = self._core_api_client.set_user_task_completed(user_task_id)
            self._logger.info(f'Updated user task {user_task_id} status to complete')
            return result
        else:
            self._logger.info('Ignored appointment', extra={
                'appointment_id': self.appointment_id,
                'appointment_type_id': self.type_id,
                'type_status': appointment_type_status
            })
            return {
                "statusCode": HTTPStatus.NO_CONTENT
            }

    def _notify_participant_and_researchers(self, event_type):
        if self.appointment.appointment_type.send_notifications is True:
            notifier = AppointmentNotifier(
                appointment=self.appointment,
                logger=self.logger,
                correlation_id=self.correlation_id,
            )
            return notifier.send_notifications(event_type=event_type)

    def _process_booking(self):
        storing_result = self.appointment.ddb_dump()
        if self.appointment.appointment_type.has_link:
            self.notify_thiscovery_team()
        else:
            self._notify_participant_and_researchers(event_type='booking')
        return storing_result

    def _process_cancellation(self):
        storing_result = self.appointment.ddb_dump(update_allowed=True)
        self._notify_participant_and_researchers(event_type='cancellation')
        return storing_result

    def _process_rescheduling(self):
        original_booking_info = self.appointment.get_appointment_item_from_ddb()
        storing_result = self.appointment.ddb_dump(update_allowed=True)
        if original_booking_info['calendar_id'] == self.appointment.calendar_id:
            self._notify_participant_and_researchers(event_type='rescheduling')
        else:
            self.notify_thiscovery_team()
        return storing_result

    def process(self):
        if self.event_type == 'scheduled':
            result = self._process_booking()
        elif self.event_type == 'canceled':
            result = self._process_cancellation()
        elif self.event_type == 'rescheduled':
            result = self._process_rescheduling()
        else:
            raise NotImplementedError(f'Processing of a {self.event_type} appointment has not been implemented')

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
        logger=logger,
        correlation_id=correlation_id,
    )
    appointment.ddb_load()
    appointment.update_link(
        link=interview_url
    )
    if appointment.appointment_type.send_notifications is True:
        notifier = AppointmentNotifier(
            appointment=appointment,
            logger=logger,
            correlation_id=correlation_id,
        )
        notifier.send_notifications(
            event_type=event_type
        )


def send_reminder():
    ddb_client = Dynamodb()
    ddb_client.scan(
        table_name=APPOINTMENTS_TABLE,
        filter_attr_name='reminder',
        filter_attr_values=[None]
    )


@utils.lambda_wrapper
def interview_reminder_handler(event, context):
    """
    To be implemented
    """
    raise NotImplementedError


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
    body = json.loads(event['body'])
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
