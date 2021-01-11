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
import datetime
import json
import re
import thiscovery_lib.utilities as utils

from collections import ChainMap
from dateutil import parser
from http import HTTPStatus
from thiscovery_lib.core_api_utilities import CoreApiClient
from thiscovery_lib.dynamodb_utilities import Dynamodb
from thiscovery_lib.emails_api_utilities import EmailsApiClient


from common.acuity_utilities import AcuityClient
from common.constants import APPOINTMENTS_TABLE, APPOINTMENT_TYPES_TABLE, DEFAULT_TEMPLATES, STACK_NAME


class AppointmentType:
    """
    Represents an Acuity appointment type with additional attributes
    """
    def __init__(self, ddb_client=None, acuity_client=None, logger=None, correlation_id=None):
        self.type_id = None
        self.name = None
        self.category = None
        self.has_link = None
        self.send_notifications = None
        self.templates = None
        self.modified = None  # flag used in ddb_load method to check if ddb data was already fetched
        self.project_task_id = None

        self._logger = logger
        self._correlation_id = correlation_id
        if logger is None:
            self._logger = utils.get_logger()
        self._ddb_client = ddb_client
        if ddb_client is None:
            self._ddb_client = Dynamodb(stack_name=STACK_NAME)
        self._acuity_client = acuity_client
        if acuity_client is None:
            self._acuity_client = AcuityClient(correlation_id=self._correlation_id)

    def as_dict(self):
        return {k: v for k, v in self.__dict__.items() if (k[0] != "_") and (k not in ['created', 'modified'])}

    def from_dict(self, type_dict):
        self.__dict__.update(type_dict)

    def ddb_dump(self, update_allowed=False):
        return self._ddb_client.put_item(
            table_name=APPOINTMENT_TYPES_TABLE,
            key=str(self.type_id),
            item_type='acuity-appointment-type',
            item_details=None,
            item=self.as_dict(),
            update_allowed=update_allowed
        )

    def ddb_load(self):
        if self.modified is None:
            item = self._ddb_client.get_item(
                table_name=APPOINTMENT_TYPES_TABLE,
                key=str(self.type_id),
                correlation_id=self._correlation_id
            )
            try:
                self.__dict__.update(item)
            except TypeError:
                raise utils.ObjectDoesNotExistError(
                    f'Appointment type {self.type_id} could not be found in Dynamodb',
                    details={
                        'appointment_type': self.as_dict(),
                        'correlation_id': self._correlation_id,
                    }
                )

    def get_appointment_type_id_to_info_map(self):
        """
        Converts the list of appointment types returned by AcuityClient.get_appointment_types()
        to a dictionary indexed by id
        """
        appointment_types = self._acuity_client.get_appointment_types()
        return {str(x['id']): x for x in appointment_types}

    def get_appointment_type_info_from_acuity(self):
        """
        There is no direct method to get a appointment type by id (https://developers.acuityscheduling.com/reference), so
        we have to fetch all appointment types and lookup
        """
        if (self.name is None) or (self.category is None):
            id_to_info = self.get_appointment_type_id_to_info_map()
            self.name = id_to_info[str(self.type_id)]['name']
            self.category = id_to_info[str(self.type_id)]['category']


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
        self.latest_participant_notification = '0000-00-00 00:00:00+00:00'  # used as GSI sort key, so cannot be None
        self.appointment_date = None
        self.appointment_type_id = None

        self._logger = logger
        if self._logger is None:
            self._logger = utils.get_logger()
        self._correlation_id = correlation_id
        self._acuity_client = AcuityClient(correlation_id=self._correlation_id)
        self._ddb_client = Dynamodb(stack_name=STACK_NAME)
        self._core_api_client = CoreApiClient(correlation_id=self._correlation_id)

    def __repr__(self):
        return str(self.__dict__)

    def from_dict(self, appointment_dict):
        """Used to quickly load appointments into Dynamodb for testing"""
        self.__dict__.update(appointment_dict)

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
        try:
            item_app_type = item['appointment_type']
        except TypeError:
            raise utils.ObjectDoesNotExistError(
                f'Appointment {self.appointment_id} could not be found in Dynamodb',
                details={
                    'appointment': self.as_dict(),
                    'correlation_id': self._correlation_id,
                }
            )
        del item['appointment_type']
        self.__dict__.update(item)
        self.appointment_type.from_dict(item_app_type)

    def get_appointment_item_from_ddb(self):
        return self._ddb_client.get_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id
        )

    def get_participant_user_id(self):
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
        return result['ResponseMetadata']['HTTPStatusCode']

    def update_latest_participant_notification(self):
        self.latest_participant_notification = str(utils.now_with_tz())
        result = self._ddb_client.update_item(
            table_name=APPOINTMENTS_TABLE,
            key=self.appointment_id,
            name_value_pairs={
                'latest_participant_notification': self.latest_participant_notification
            }
        )
        assert result['ResponseMetadata']['HTTPStatusCode'] == HTTPStatus.OK, \
            f'Call to ddb client update_item method failed with response {result}'
        return result['ResponseMetadata']['HTTPStatusCode']

    def get_appointment_info_from_acuity(self, force_refresh=False):
        if (self.acuity_info is None) or (force_refresh is True):
            self.acuity_info = self._acuity_client.get_appointment_by_id(self.appointment_id)
            self.appointment_type.type_id = str(self.acuity_info['appointmentTypeID'])
            self.appointment_type_id = self.appointment_type.type_id
            self.calendar_name = self.acuity_info['calendar']
            self.calendar_id = str(self.acuity_info['calendarID'])
            self.participant_email = self.acuity_info['email']
            self.appointment_date = self.acuity_info['datetime'].split('T')[0]
        return self.acuity_info


class AppointmentNotifier:
    calendar_table = 'Calendars'

    def __init__(self, appointment, logger=None, ddb_client=None, correlation_id=None):
        """
        Args:
            appointment: instance of AcuityAppointment
            logger:
            correlation_id:
        """
        self.appointment = appointment
        self.project_id = None
        self.project_short_name = None
        self.anon_project_specific_user_id = None
        self.interviewer_calendar_ddb_item = None

        if self.appointment.participant_email is None:
            self.appointment.get_appointment_info_from_acuity()

        self.logger = logger
        if logger is None:
            self.logger = utils.get_logger()
        self.correlation_id = correlation_id
        self.ddb_client = ddb_client
        if ddb_client is None:
            self.ddb_client = Dynamodb(stack_name=STACK_NAME)

    def _get_email_template(self, recipient_email, recipient_type, event_type):
        email_domain = 'other'
        if (recipient_type == 'participant') and ('@nhs' in recipient_email):
            email_domain = 'nhs'
        interview_medium = 'phone'
        if self.appointment.appointment_type.has_link is True:
            interview_medium = 'web'

        templates = DEFAULT_TEMPLATES
        if isinstance(self.appointment.appointment_type.templates, dict):
            templates = ChainMap(self.appointment.appointment_type.templates, DEFAULT_TEMPLATES)
        return templates[recipient_type][event_type][interview_medium][email_domain]

    def _get_calendar_ddb_item(self):
        if self.appointment.calendar_id is None:
            self.appointment.get_appointment_info_from_acuity()
        self.interviewer_calendar_ddb_item = self.ddb_client.get_item(
            table_name=self.calendar_table,
            key=self.appointment.calendar_id
        )
        if not self.interviewer_calendar_ddb_item:
            raise utils.ObjectDoesNotExistError(
                f'Calendar {self.appointment.calendar_id} not found in Dynamodb',
                details={
                    'appointment': self.appointment.as_dict(),
                    'correlation_id': self.correlation_id,
                }
            )
        return self.interviewer_calendar_ddb_item

    def _get_interviewer_myinterview_link(self):
        if self.interviewer_calendar_ddb_item is None:
            self._get_calendar_ddb_item()
        try:
            return self.interviewer_calendar_ddb_item['myinterview_link']
        except KeyError:
            raise utils.ObjectDoesNotExistError(
                f'Calendar {self.appointment.calendar_id} Dynamodb item does not contain a myinterview_link column',
                details={
                    'appointment': self.appointment.as_dict(),
                    'correlation_id': self.correlation_id,
                }
            )

    def _get_researcher_email_address(self):
        if self.interviewer_calendar_ddb_item is None:
            self._get_calendar_ddb_item()
        try:
            return self.interviewer_calendar_ddb_item['emails_to_notify']
        except KeyError:
            raise utils.ObjectDoesNotExistError(
                f'Calendar {self.appointment.calendar_id} Dynamodb item does not contain an emails_to_notify column',
                details={
                    'appointment': self.appointment.as_dict(),
                    'correlation_id': self.correlation_id,
                }
            )

    def _check_appointment_cancelled(self):
        """
        Gets latest appointment info from Acuity to ensure appointment is still valid before sending out notification

        Returns:
            True is appointment is cancelled; False if it is not cancelled
        """
        self.appointment.get_appointment_info_from_acuity(force_refresh=True)
        return self.appointment.acuity_info['canceled'] is True

    def _abort_notification_check(self, event_type):
        if not event_type == 'cancellation':
            if self._check_appointment_cancelled():
                self.logger.info('Notification aborted; appointment has been cancelled', extra={
                    'appointment': self.appointment.as_dict(),
                    'correlation_id': self.correlation_id
                })
                return True
        return check_appointment_in_the_past(self.appointment)

    def _get_project_short_name(self):
        project_list = self.appointment._core_api_client.get_projects()
        for p in project_list:
            for t in p['tasks']:
                if t['id'] == self.appointment.appointment_type.project_task_id:
                    self.project_id = p['id']
                    self.project_short_name = p['short_name']
                    return self.project_short_name
        raise utils.ObjectDoesNotExistError(f'Project task {self.appointment.appointment_type.project_task_id} not found', details={})

    def _get_anon_project_specific_user_id(self):
        if self.appointment.participant_user_id is None:
            try:
                self.appointment.get_participant_user_id()
            except AssertionError:
                self.logger.info(f'User {self.appointment.participant_email} does not seem to have a thiscovery account',
                                 extra={
                                     'appointment': self.appointment.as_dict(),
                                     'correlation_id': self.correlation_id,
                                 })
                return None
        try:
            user_projects = self.appointment._core_api_client.get_userprojects(self.appointment.participant_user_id)
        except AssertionError:
            self.logger.info(f'Could not get user projects for user_id {self.appointment.participant_user_id}',
                             extra={
                                 'appointment': self.appointment.as_dict(),
                                 'correlation_id': self.correlation_id,
                             })
            return None
        if self.project_id is None:
            self._get_project_short_name()
        for up in user_projects:
            if up['project_id'] == self.project_id:
                self.anon_project_specific_user_id = up['anon_project_specific_user_id']
                return self.anon_project_specific_user_id
        self.logger.info(f'anon_project_specific_user_id could not be found for {self.appointment.participant_email}', extra={
            'appointment': self.appointment.as_dict(),
            'correlation_id': self.correlation_id
        })

    def _get_custom_properties(self, properties_list, template_type):
        self.logger.debug('Properties list and template type', extra={
            'properties_list': properties_list,
            'template_type': template_type,
        })
        if properties_list:
            if ('project_short_name' in properties_list) and (self.project_short_name is None):
                self._get_project_short_name()
            if (template_type == 'researcher') and (self.anon_project_specific_user_id is None):
                self._get_anon_project_specific_user_id()
            appointment_datetime = parser.parse(self.appointment.acuity_info['datetime'])
            properties_map = {
                'anon_project_specific_user_id': self.anon_project_specific_user_id,
                'appointment_date': f"{appointment_datetime.strftime('%A %d %B %Y')}",
                'appointment_duration': f"{self.appointment.acuity_info['duration']} minutes",
                'appointment_reschedule_url': self.appointment.acuity_info['confirmationPage'],
                'appointment_time': f"{appointment_datetime.strftime('%H:%M')}",
                'appointment_type_name': self.appointment.appointment_type.name,
                'interviewer_first_name': self.appointment.acuity_info['calendar'].split()[0],
                'interview_url': 'We will call you on the phone number provided',
                'project_short_name': self.project_short_name,
                'user_email': self.appointment.participant_email,
                'user_first_name': self.appointment.acuity_info['firstName'],
                'user_last_name': self.appointment.acuity_info['lastName'],
            }
            if self.appointment.appointment_type.has_link is True:
                properties_map['interview_url'] = f'<a href="{self.appointment.link}" style="color:#dd0031" ' \
                                                  f'rel="noopener">{self.appointment.link}</a>'

            if template_type == 'researcher':
                if self.appointment.appointment_type.has_link is True:
                    interviewer_url = self._get_interviewer_myinterview_link()
                else:
                    if self.appointment.acuity_info['phone']:
                        interviewer_url = f"Please call participant on {self.appointment.acuity_info['phone']}"
                    else:
                        interviewer_url = f"Participant did not provide a phone number. " \
                                                          f"Please contact them by email to obtain a contact number"
                properties_map['interviewer_url'] = interviewer_url

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
            custom_properties=self._get_custom_properties(
                properties_list=template['custom_properties'],
                template_type=recipient_type,
            )
        )

    def _notify_participant(self, event_type):
        if self._abort_notification_check(event_type=event_type) is True:
            return {'statusCode': 'aborted'}
        result = self._notify_email(
            recipient_email=self.appointment.participant_email,
            recipient_type='participant',
            event_type=event_type
        )
        if result['statusCode'] != HTTPStatus.NO_CONTENT:
            self.logger.error(f'Failed to notify {self.appointment.participant_email} of interview appointment', extra={
                'appointment': self.appointment.as_dict(),
                'event_type': event_type,
                'correlation_id': self.correlation_id
            })
        else:
            self.appointment.update_latest_participant_notification()
        return result

    def _notify_researchers(self, event_type):
        researchers_email_list = self._get_researcher_email_address()
        if self._abort_notification_check(event_type=event_type) is True:
            return [{'statusCode': 'aborted'}] * len(researchers_email_list)

        results = list()
        for researcher_email in researchers_email_list:
            r = self._notify_email(
                recipient_email=researcher_email,
                recipient_type='researcher',
                event_type=event_type
            )
            if r['statusCode'] != HTTPStatus.NO_CONTENT:
                self.logger.error(f'Failed to notify {researcher_email} of new interview appointment', extra={
                    'appointment': self.appointment.as_dict()
                })
            results.append(r)
        return results

    def send_notifications(self, event_type):
        # todo: split this into two functions when EventBridge is in place
        participant_result = self._notify_participant(event_type=event_type)
        researchers_results = None
        try:
            researchers_notifications_results = self._notify_researchers(event_type=event_type)
            researchers_results = [r['statusCode'] for r in researchers_notifications_results]
        except:
            self.logger.error('Failed to notify researchers', extra={
                'appointment': self.appointment.as_dict(),
                'correlation_id': self.correlation_id,
            })
        return {
            'participant': participant_result.get('statusCode'),
            'researchers': researchers_results,
        }

    def send_reminder(self):
        return self._notify_participant(event_type='reminder')


class AcuityEvent:

    def __init__(self, acuity_event, logger=None, correlation_id=None):
        self.logger = logger
        if logger is None:
            self.logger = utils.get_logger()
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
        except AttributeError as err:
            self.logger.error('event_pattern does not match acuity_event', extra={'acuity_event': acuity_event})
            raise
        self.appointment = AcuityAppointment(
            appointment_id=appointment_id,
            logger=self.logger,
            correlation_id=self.correlation_id,
        )
        self.appointment.appointment_type.type_id = type_id
        try:
            self.appointment.appointment_type.ddb_load()
        except utils.ObjectDoesNotExistError:
            self.logger.error(
                'Failed to process Acuity event (Appointment type not found in Dynamodb)',
                extra={
                    'event': acuity_event,
                    'correlation_id': self.correlation_id
                }
            )
            raise

    def __repr__(self):
        return str(self.__dict__)

    def notify_thiscovery_team(self):
        if self.appointment.acuity_info is None:
            self.appointment.get_appointment_info_from_acuity()
        if check_appointment_in_the_past(self.appointment):
            return 'aborted'
        appointment_type_name = self.appointment.appointment_type.name
        emails_client = EmailsApiClient(self.correlation_id)
        appointment_management_secret = utils.get_secret('interviews')['appointment-management']
        appointment_manager = appointment_management_secret['manager']
        if utils.running_unit_tests():
            appointment_manager = appointment_management_secret['tester']
        notification_email_source = appointment_management_secret['notification-email-source']
        appointment_date = f"{parser.parse(self.appointment.acuity_info['datetime']).strftime('%d/%m/%Y %H:%M')}" \
                           f"-{self.appointment.acuity_info['endTime']}"
        interviewee_name = f"{self.appointment.acuity_info['firstName']} {self.appointment.acuity_info['lastName']}"
        interviewee_email = self.appointment.acuity_info['email']
        interviewer_calendar_name = self.appointment.acuity_info['calendar']
        confirmation_page = self.appointment.acuity_info['confirmationPage']
        email_dict = {
            "source": notification_email_source,
            "to": appointment_manager,
            "subject": f"[thiscovery-interviews] Appointment {self.appointment.appointment_id} {self.event_type}",
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
        assert result['statusCode'] == HTTPStatus.OK, f'Failed to email Thiscovery team. ' \
                                                      f'Send-email endpoint returned {result}'
        return result['statusCode']

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
        thiscovery_team_notification_result = None
        participant_and_researchers_notification_results = None
        if self.appointment.appointment_type.has_link:
            thiscovery_team_notification_result = self.notify_thiscovery_team()
        else:
            participant_and_researchers_notification_results = self._notify_participant_and_researchers(event_type='booking')
        return storing_result, thiscovery_team_notification_result, participant_and_researchers_notification_results

    def _get_original_booking(self):
        original_booking_info = self.appointment.get_appointment_item_from_ddb()
        self.appointment.link = original_booking_info['link']
        self.appointment.latest_participant_notification = original_booking_info.get('latest_participant_notification', '0000-00-00 00:00:00+00:00')
        return original_booking_info

    def _process_cancellation(self):
        self._get_original_booking()
        storing_result = self.appointment.ddb_dump(update_allowed=True)
        thiscovery_team_notification_result = None
        participant_and_researchers_notification_results = self._notify_participant_and_researchers(event_type='cancellation')
        return storing_result, thiscovery_team_notification_result, participant_and_researchers_notification_results

    def _process_rescheduling(self):
        original_booking_info = self._get_original_booking()
        storing_result = self.appointment.ddb_dump(update_allowed=True)
        thiscovery_team_notification_result = None
        participant_and_researchers_notification_results = None
        if original_booking_info['calendar_id'] == self.appointment.calendar_id:
            if not self.appointment.appointment_type.has_link:
                participant_and_researchers_notification_results = self._notify_participant_and_researchers(event_type='rescheduling')
            else:
                if self.appointment.link:
                    participant_and_researchers_notification_results = self._notify_participant_and_researchers(event_type='rescheduling')
                else:
                    self.logger.debug(
                        'Appointment rescheduled before interview link was generated. '
                        'Participant will be notified once link is received',
                        extra={
                            'appointment_dict': self.appointment.as_dict(),
                            'correlation_id': self.correlation_id,
                        }
                    )
        else:
            thiscovery_team_notification_result = self.notify_thiscovery_team()
        return storing_result, thiscovery_team_notification_result, participant_and_researchers_notification_results

    def process(self):
        """
        Returns: Tuple containing:
            storing_result,
            thiscovery_team_notification_result,
            participant_and_researchers_notification_results
        """
        if self.event_type == 'scheduled':
            return self._process_booking()
        elif self.event_type == 'canceled':
            return self._process_cancellation()
        elif self.event_type == 'rescheduled':
            return self._process_rescheduling()
        else:
            raise NotImplementedError(f'Processing of a {self.event_type} appointment has not been implemented')


def check_appointment_in_the_past(appointment_instance):
    two_hours_ago = utils.now_with_tz() - datetime.timedelta(hours=2)
    appointment_datetime = parser.parse(appointment_instance.acuity_info['datetime'])
    if appointment_datetime < two_hours_ago:
        appointment_instance._logger.info('Notification aborted; appointment is in the past', extra={
            'appointment': appointment_instance.as_dict(),
            'correlation_id': appointment_instance._correlation_id
        })
        return True
    else:
        return False


def set_interview_url(appointment_id, interview_url, event_type, logger=None, correlation_id=None):
    """

    Args:
        appointment_id:
        interview_url:
        event_type (str): passed on to AppointmentNotifier ('booking', 'rescheduling' or 'cancellation')
        logger:
        correlation_id:

    Returns:
        update_result:
        notification_results (dict): Dictionary containing participant and researchers notification results

    """
    if logger is None:
        logger = utils.get_logger()
    appointment = AcuityAppointment(
        appointment_id=appointment_id,
        logger=logger,
        correlation_id=correlation_id,
    )
    appointment.ddb_load()
    update_result = appointment.update_link(
        link=interview_url
    )
    notification_results = {
        'participant': None,
        'researchers': list(),
    }
    if appointment.appointment_type.send_notifications is True:
        notifier = AppointmentNotifier(
            appointment=appointment,
            logger=logger,
            correlation_id=correlation_id,
        )
        notification_results = notifier.send_notifications(
            event_type=event_type
        )
    return update_result, notification_results


@utils.lambda_wrapper
@utils.api_error_handler
def interview_appointment_api(event, context):
    """
    Listens to events posted by Acuity via webhooks
    """
    logger = event['logger']
    correlation_id = event['correlation_id']
    acuity_event = event['body']
    appointment_event = AcuityEvent(acuity_event, logger, correlation_id=correlation_id)
    result = appointment_event.process()
    return {
        "statusCode": HTTPStatus.OK,
        'body': json.dumps(result)
    }


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
    alarm_test = body.get('brew_coffee')
    if alarm_test:
        raise utils.DeliberateError('Coffee is not available', details={})
    update_result, notification_results = set_interview_url(
        appointment_id=body['appointment_id'],
        interview_url=body['interview_url'],
        event_type=body['event_type'],
        logger=logger,
        correlation_id=correlation_id,
    )
    response_body = {
        'update_result': update_result,
        'notification_results': notification_results,
        'correlation_id': correlation_id,
    }
    return {"statusCode": HTTPStatus.OK, 'body': json.dumps(response_body)}
